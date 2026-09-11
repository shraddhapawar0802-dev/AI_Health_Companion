"""
AI Health Companion — backend
Educational screening-aid, NOT a diagnostic tool. All interaction and lab-range
data below is a curated clinical set for SIH 2026 based on ICMR / WHO guidelines.
"""
import os
import re
import json
import difflib
import tempfile
import shutil

from flask import Flask, request, jsonify, send_from_directory, render_template
import pytesseract
from PIL import Image, ImageOps
import cv2
import numpy as np
import pypdf

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# ---------- Tesseract discovery & setup ----------
def find_tesseract():
    cmd = os.environ.get("TESSERACT_CMD")
    if cmd and os.path.exists(cmd):
        return cmd
    which = shutil.which("tesseract")
    if which:
        return which
    local_bin = os.path.join(BASE_DIR, "bin", "tesseract.exe")
    if os.path.exists(local_bin):
        return local_bin
    candidates = [
        r"C:\Program Files\Tesseract-OCR\tesseract.exe",
        r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
        r"C:\ProgramData\chocolatey\bin\tesseract.exe",
        r"C:\ProgramData\chocolatey\lib\tesseract\tools\tesseract.exe",
        os.path.expanduser(r"~\AppData\Local\Programs\Tesseract-OCR\tesseract.exe"),
        r"/usr/bin/tesseract",
        r"/usr/local/bin/tesseract",
    ]
    for c in candidates:
        if os.path.exists(c):
            return c
    return None

TESS_BIN = find_tesseract()
if TESS_BIN:
    pytesseract.pytesseract.tesseract_cmd = TESS_BIN

TESSDATA_DIR = os.path.join(BASE_DIR, "tessdata")
if os.path.isdir(TESSDATA_DIR) and os.path.exists(os.path.join(TESSDATA_DIR, "eng.traineddata")):
    os.environ["TESSDATA_PREFIX"] = TESSDATA_DIR
    if os.path.exists(os.path.join(TESSDATA_DIR, "hin.traineddata")):
        OCR_LANGS = "eng+hin"
    else:
        OCR_LANGS = "eng"
else:
    OCR_LANGS = "eng"

app = Flask(__name__, static_folder="static", template_folder="templates")
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024  # 16 MB upload cap

# ---------- Load curated datasets once at startup ----------
with open(os.path.join(BASE_DIR, "data", "medicines.json"), encoding="utf-8") as f:
    MEDICINES = json.load(f)
with open(os.path.join(BASE_DIR, "data", "interactions.json"), encoding="utf-8") as f:
    INTERACTIONS = json.load(f)
with open(os.path.join(BASE_DIR, "data", "lab_ranges.json"), encoding="utf-8") as f:
    LAB_RANGES = json.load(f)

NSAID_GENERICS = {"Ibuprofen", "Diclofenac", "Aceclofenac", "Mefenamic acid",
                   "Ibuprofen + Paracetamol"}

ALIAS_INDEX = []  # [(alias_lowercase, medicine_dict), ...]
for med in MEDICINES:
    for alias in med.get("aliases", []) + [med["brand"]]:
        ALIAS_INDEX.append((alias.lower(), med))


# ---------- Advanced Preprocessing ----------
def preprocess_image_advanced(path):
    """
    OpenCV preprocessing pipeline for medical reports & prescriptions:
    1. Dimension & aspect-ratio normalization for optimal Tesseract font height
    2. Automatic deskewing via contour minimum area rect
    3. Illumination / shadow normalization via morphological background subtraction
    4. Contrast enhancement using CLAHE
    5. Edge-preserving bilateral filtering (retains decimal points and digits)
    6. Otsu thresholding binarization
    Returns (enhanced_grayscale_path, binarized_path)
    """
    img = cv2.imread(path)
    if img is None:
        return path, path

    h, w = img.shape[:2]
    min_dim = min(h, w)
    max_dim = max(h, w)

    # Scale small images up for clean character recognition
    if min_dim < 1500:
        scale = min(4.0, 1800.0 / float(min_dim))
        new_w, new_h = int(w * scale), int(h * scale)
        img = cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_LANCZOS4)
        h, w = new_h, new_w
    elif max_dim > 3200:
        # Scale down ultra-high-res camera captures to maintain speed and OCR accuracy
        scale = 2400.0 / float(max_dim)
        new_w, new_h = int(w * scale), int(h * scale)
        img = cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_AREA)
        h, w = new_h, new_w

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # Apply gentle unsharp masking if upscaled from small source
    if min_dim < 900:
        blur = cv2.GaussianBlur(gray, (0, 0), 2.0)
        gray = cv2.addWeighted(gray, 1.5, blur, -0.5, 0)

    # Deskewing
    try:
        thresh_temp = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)[1]
        coords = np.column_stack(np.where(thresh_temp > 0))
        if len(coords) > 100:
            angle = cv2.minAreaRect(coords)[-1]
            if angle < -45:
                angle = -(90 + angle)
            elif angle > 45:
                angle = 90 - angle
            else:
                angle = -angle
            if 0.5 < abs(angle) < 30.0:
                center = (w // 2, h // 2)
                M = cv2.getRotationMatrix2D(center, angle, 1.0)
                gray = cv2.warpAffine(gray, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
    except Exception:
        pass

    # Shadow & illumination correction (morphological background division)
    ksize = max(25, int(min(h, w) * 0.02) | 1)
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (ksize, ksize))
    bg = cv2.morphologyEx(gray, cv2.MORPH_CLOSE, kernel)
    norm = cv2.divide(gray, bg, scale=255)

    # CLAHE contrast enhancement
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    enhanced_gray = clahe.apply(norm)

    # Bilateral filter (denoises paper texture while keeping thin letters and dots sharp)
    denoised = cv2.bilateralFilter(enhanced_gray, 7, 50, 50)

    # Otsu thresholding
    _, thresh_otsu = cv2.threshold(denoised, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

    gray_out = path + "_gray.png"
    bin_out = path + "_bin.png"
    cv2.imwrite(gray_out, denoised)
    cv2.imwrite(bin_out, thresh_otsu)
    return gray_out, bin_out


def _ocr_pass(image, lang, psm=3):
    config = f"--oem 1 --psm {psm}"
    data = pytesseract.image_to_data(image, lang=lang, config=config, output_type=pytesseract.Output.DICT)
    words = []
    line_map = {}
    n = len(data["text"])
    for i in range(n):
        text = data["text"][i].strip()
        conf = int(data["conf"][i]) if data["conf"][i] not in ("-1", -1) else -1
        if not text or conf < 0:
            continue
        words.append({"text": text, "confidence": conf})
        key = (data["block_num"][i], data["par_num"][i], data["line_num"][i])
        line_map.setdefault(key, []).append((text, conf))

    lines = []
    for key in sorted(line_map.keys()):
        parts = line_map[key]
        line_text = " ".join(t for t, _ in parts)
        avg_conf = round(sum(c for _, c in parts) / len(parts), 1)
        lines.append({"text": line_text, "confidence": avg_conf})

    full_text = "\n".join(l["text"] for l in lines)
    overall_conf = (sum(w["confidence"] for w in words) / len(words)) if words else 0
    return {"lines": lines, "words": words, "full_text": full_text, "_overall_conf": overall_conf}


def run_ocr(image_path):
    """
    Multi-pass OCR strategy:
    Tries original image, enhanced grayscale and clean Otsu binarized inputs with eng and regional models.
    Scores candidates by confidence and recognized clinical tokens.
    """
    tess = find_tesseract()
    if tess:
        pytesseract.pytesseract.tesseract_cmd = tess
    elif not shutil.which("tesseract"):
        raise RuntimeError("Tesseract OCR executable not found on host. Please verify installation.")

    gray_path, bin_path = preprocess_image_advanced(image_path)
    candidates = []

    # Test all variations: raw image, enhanced grayscale, and clean binarized
    for p in [image_path, gray_path, bin_path]:
        try:
            im = Image.open(p)
            candidates.append(_ocr_pass(im, "eng", psm=3))
            if OCR_LANGS != "eng":
                candidates.append(_ocr_pass(im, OCR_LANGS, psm=3))
            candidates.append(_ocr_pass(im, "eng", psm=6))
        except Exception:
            continue

    if not candidates:
        im = Image.open(image_path)
        candidates.append(_ocr_pass(im, "eng", psm=3))

    def score_cand(c):
        text = c.get("full_text", "")
        conf = c.get("_overall_conf", 0)
        nums = len(re.findall(r"\b\d+(?:\.\d+)?\b", text))
        kws = len(re.findall(r"(?i)\b(glucose|sugar|blood|pressure|hemoglobin|haemoglobin|cholesterol|creatinine|wbc|rbc|platelet|pcv|mcv|mch|mchc|tab|cap|mg|daily|food|report|test|patient|doctor|normal|count|differential|drlogy|pathology|investigation)\b", text))
        return conf + (nums * 1.5) + (kws * 2.5)

    best = max(candidates, key=score_cand)
    best.pop("_overall_conf", None)
    return best


def extract_pdf_data(pdf_path, tmp_dir):
    """
    Extracts text from PDF documents.
    If digital text exists, uses it directly (100% precision).
    If scanned pages, extracts page images and applies OpenCV preprocessing + OCR.
    """
    full_text = ""
    try:
        reader = pypdf.PdfReader(pdf_path)
        page_texts = []
        for p in reader.pages:
            t = p.extract_text()
            if t and t.strip():
                page_texts.append(t.strip())
        full_text = "\n".join(page_texts)
    except Exception:
        full_text = ""

    if full_text and len(full_text.strip()) >= 30:
        lines = [{"text": line.strip(), "confidence": 98.0} for line in full_text.splitlines() if line.strip()]
        words = [{"text": w, "confidence": 98} for line in lines for w in line["text"].split()]
        return {"full_text": full_text, "lines": lines, "words": words}

    # Scanned PDF: extract page images
    extracted_texts = []
    try:
        reader = pypdf.PdfReader(pdf_path)
        img_idx = 0
        for p in reader.pages:
            for img_obj in p.images:
                img_path = os.path.join(tmp_dir, f"pdf_img_{img_idx}.png")
                with open(img_path, "wb") as f:
                    f.write(img_obj.data)
                img_idx += 1
                ocr_res = run_ocr(img_path)
                if ocr_res.get("full_text"):
                    extracted_texts.append(ocr_res["full_text"])
    except Exception:
        pass

    if extracted_texts:
        combined_text = "\n".join(extracted_texts)
        lines = [{"text": l.strip(), "confidence": 85.0} for l in combined_text.splitlines() if l.strip()]
        words = [{"text": w, "confidence": 85} for l in lines for w in l["text"].split()]
        return {"full_text": combined_text, "lines": lines, "words": words}

    lines = [{"text": l.strip(), "confidence": 80.0} for l in full_text.splitlines() if l.strip()]
    words = [{"text": w, "confidence": 80} for l in lines for w in l["text"].split()]
    return {"full_text": full_text, "lines": lines, "words": words}


# ---------- Medical Report & Prescription Parser ----------
def parse_medical_report(raw_text):
    """
    Parses OCR text into structured report data:
    - Patient name, age, gender, date, doctor/clinic name, notes
    - Full lab test parameters (CBC, Sugar, HbA1c, Lipids, KFT, LFT, Thyroid, Vitals)
    - Prescription details (medicine, strength, dosage frequency, instructions)
    """
    text = raw_text or ""
    lines = [l.strip() for l in text.splitlines() if l.strip()]

    meta = {
        "patient_name": "",
        "age": None,
        "gender": "",
        "date": "",
        "doctor_name": "",
        "hospital_or_lab": "",
        "document_type": "report",
        "diagnosis_notes": ""
    }
    # Patient metadata extraction
    for idx, line in enumerate(lines):
        # 1. Hospital / Lab Name
        if not meta["hospital_or_lab"]:
            m_lab = re.search(r"(?i)([A-Za-z0-9\s]{3,40}(?:hospital|clinic|diagnostics?|laboratory|pathology(?:\s*lab)?|lab(?:oratory)?|centre|center))\b", line)
            if m_lab and not any(k in m_lab.group(1).lower() for k in ["primary", "sample", "complete", "investigation"]):
                meta["hospital_or_lab"] = m_lab.group(1).strip()

        # 2. Patient Name
        if not meta["patient_name"]:
            m_name = re.search(r"(?i)(?:patient(?:\s*name)?|pt(?:\s*name)?|name|रुग्ण)\s*[:\-]\s*([A-Za-z\.\s]{2,35}?)(?=\s+(?:age|sex|gender|date|\d|yr|y\b|sample|ref)|$)", line)
            if m_name and m_name.group(1).strip().lower() not in ("name", "patient", "pt", "investigation", "sample", "complete"):
                meta["patient_name"] = m_name.group(1).strip()
            else:
                m_lead = re.search(r"^([A-Z][a-z]+(?:\s+[A-Z]\.?)?\s+[A-Z][a-z]+)\s+(?:Sample|Ref|Age|Date|Room|ID|Bar|Sex)", line)
                if m_lead:
                    cand = m_lead.group(1).strip()
                    if not any(k in cand.lower() for k in ["complete", "blood", "count", "primary", "sample", "biology", "pathology"]):
                        meta["patient_name"] = cand

        # 3. Age
        if meta["age"] is None:
            m_age = re.search(r"(?i)(?:age|वय|उम्र)\s*[:\-]?\s*(\d{1,3})\s*(?:y|yrs|years)?", line)
            if m_age:
                val = int(m_age.group(1))
                if 1 <= val <= 115:
                    meta["age"] = val

        # 4. Gender
        if not meta["gender"]:
            m_gen = re.search(r"(?i)(?:gender|sex|लिंग)\s*[:\-]?\s*(male|female|m|f|पुरुष|महिला)", line)
            if m_gen:
                g = m_gen.group(1).lower()
                meta["gender"] = "male" if g in ("male", "m", "पुरुष") else "female"
            elif re.search(r"(?i)\b(?:female|महिला)\b", line):
                meta["gender"] = "female"
            elif re.search(r"(?i)\b(?:male|पुरुष)\b", line):
                meta["gender"] = "male"

        # 5. Doctor Name
        if not meta["doctor_name"]:
            m_doc = re.search(r"(?i)\bdr\.?\s+([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)+)", line)
            if m_doc:
                meta["doctor_name"] = "Dr. " + m_doc.group(1).replace("Dr.", "").strip()
            else:
                m_doc2 = re.search(r"(?i)(?:ref(?:erred)?(?:\.|\s*by)?|consultant|physician)\s*[:\-]?\s*(?:dr\.?)?\s*([A-Za-z\.\s]{3,35})", line)
                if m_doc2 and not any(k in m_doc2.group(1).lower() for k in ["room", "sample", "lab"]):
                    doc_part = m_doc2.group(1).strip()
                    if not doc_part.lower().startswith("dr"):
                        doc_part = "Dr. " + doc_part
                    meta["doctor_name"] = doc_part

        # 6. Date
        if not meta["date"]:
            m_date = re.search(r"(?i)(?:date|दिनांक|तारीख)?\s*[:\-]?\s*\b(\d{1,2}[\/\-\.\s](?:[a-zA-Z]{3,9}|\d{1,2})[\/\-\.\s]\d{2,4})\b", line)
            if m_date:
                meta["date"] = m_date.group(1).strip()

    # Demographic fallback
    if meta["age"] is None or not meta["gender"]:
        m_demo = re.search(r"\b(\d{1,3})\s*(?:Y|y|yrs)?\s*[\/,]\s*([MFmf]|Male|Female)\b", text)
        if m_demo:
            if meta["age"] is None:
                val = int(m_demo.group(1))
                if 1 <= val <= 115:
                    meta["age"] = val
            if not meta["gender"]:
                meta["gender"] = "male" if m_demo.group(2).lower().startswith("m") else "female"

    # Fallback patient name from top lines
    if not meta["patient_name"]:
        for line in lines[:8]:
            m = re.match(r"^([A-Z][a-zA-Z\.]+(?:\s+[A-Z][a-zA-Z\.]+){1,3})$", line.strip())
            if m:
                cand = m.group(1).strip()
                if not any(k in cand.lower() for k in ["pathology", "biology", "laboratory", "hospital", "report", "count", "investigation", "sample"]):
                    meta["patient_name"] = cand
                    break

    # Clinical impression / diagnosis notes
    notes_m = re.search(r"(?i)(?:diagnosis|impression|advice|notes|symptoms|history)\s*[:\-]\s*(.+)", text)
    if notes_m:
        meta["diagnosis_notes"] = notes_m.group(1).split("\n")[0].strip()

    # Full Lab Tests Catalog (Blood Sugar, CBC, Vitals, KFT, LFT, Thyroid)
    tests_catalog = [
        # Blood Sugar / Diabetes
        {
            "key": "fasting_sugar",
            "name_en": "Fasting Blood Sugar", "name_hi": "फास्टिंग ब्लड शुगर", "name_mr": "उपाशीपोटी साखर (Fasting Sugar)",
            "unit": "mg/dL", "ref": "70 - 99 mg/dL",
            "pattern": r"(?i)(?:fasting\s*sugar|fasting\s*glucose|fbs|fasting\s*blood\s*sugar)\s*[:\-]?\s*([0-9]{2,3}(?:\.[0-9]+)?)",
            "type": "numeric", "low_flag": 70, "elevated": 100, "high": 126, "emergency": 200, "emergency_low": 55
        },
        {
            "key": "pp_sugar",
            "name_en": "Post-Meal (PP) Glucose", "name_hi": "खाने के बाद शुगर (PP)", "name_mr": "जेवणानंतरची साखर (PP Sugar)",
            "unit": "mg/dL", "ref": "< 140 mg/dL",
            "pattern": r"(?i)(?:post\s*prandial|pp\s*glucose|pp\s*sugar|ppbs|after\s*food\s*sugar)\s*[:\-]?\s*([0-9]{2,3}(?:\.[0-9]+)?)",
            "type": "numeric", "low_flag": 70, "elevated": 140, "high": 200, "emergency": 300, "emergency_low": 55
        },
        {
            "key": "hba1c",
            "name_en": "HbA1c (Average Glucose)", "name_hi": "एचबीए1सी (HbA1c)", "name_mr": "HbA1c (सरासरी साखर)",
            "unit": "%", "ref": "< 5.7 %",
            "pattern": r"(?i)(?:hba1c|hb\s*a1c|glycated\s*hemoglobin|glycated\s*haemoglobin)\s*[:\-]?\s*([0-9]{1,2}(?:\.[0-9]+)?)",
            "type": "numeric", "elevated": 5.7, "high": 6.5, "emergency": 9.0
        },

        # Complete Blood Count (CBC) Parameters
        {
            "key": "hemoglobin",
            "name_en": "Hemoglobin (Hb)", "name_hi": "हीमोग्लोबिन (Hb)", "name_mr": "हीमोग्लोबिन (Hemoglobin Hb)",
            "unit": "g/dL", "ref": "13.0 - 17.0 g/dL" if meta.get("gender") == "male" else "12.0 - 15.5 g/dL",
            "pattern": r"(?i)(?:ha?emoglobin(?:\s*\([a-z0-9\s]+\))?|hb|hgb)\s*[:\-]?\s*([0-9]{1,2}(?:\.[0-9]+)?)",
            "type": "custom_hb"
        },
        {
            "key": "rbc",
            "name_en": "Total RBC Count", "name_hi": "कुल आरबीसी (Red Blood Cells)", "name_mr": "तांबड्या पेशी (RBC Count)",
            "unit": "mill/cumm", "ref": "4.5 - 5.5 mill/cumm",
            "pattern": r"(?i)(?:total\s*rbc(?:\s*count)?|rbc(?:\s*count)?|red\s*blood\s*cells?)\s*[:\-]?\s*([0-9]{1,2}(?:\.[0-9]+)?)",
            "type": "numeric", "low_flag": 4.5, "high": 5.5
        },
        {
            "key": "pcv",
            "name_en": "Packed Cell Volume (PCV)", "name_hi": "पीसीवी (हेमाटोक्रिट PCV)", "name_mr": "पीसीव्ही (PCV / Hematocrit)",
            "unit": "%", "ref": "40 - 50 %" if meta.get("gender") == "male" else "36 - 46 %",
            "pattern": r"(?i)(?:packed\s*cell\s*volume(?:\s*\([a-z0-9\s]+\))?|pcv|ha?ematocrit(?:\s*\([a-z0-9\s]+\))?|hct)\s*[:\-]?\s*([0-9]{1,2}(?:\.[0-9]+)?)",
            "type": "numeric", "low_flag": 40 if meta.get("gender") == "male" else 36, "high": 50 if meta.get("gender") == "male" else 46
        },
        {
            "key": "mcv",
            "name_en": "Mean Corpuscular Volume (MCV)", "name_hi": "एमसीवी (MCV)", "name_mr": "एमसीव्ही पेशी आकार (MCV)",
            "unit": "fL", "ref": "83 - 101 fL",
            "pattern": r"(?i)(?:mean\s*corpuscular\s*volume(?:\s*\([a-z0-9\s]+\))?|mcv)\s*[:\-]?\s*([0-9]{1,3}(?:\.[0-9]+)?)",
            "type": "numeric", "low_flag": 83, "high": 101
        },
        {
            "key": "mch",
            "name_en": "Mean Corpuscular Hemoglobin (MCH)", "name_hi": "एमसीएच (MCH)", "name_mr": "एमसीएच (MCH)",
            "unit": "pg", "ref": "27 - 32 pg",
            "pattern": r"(?i)\bmch\b(?!\s*c)\s*[:\-]?\s*([0-9]{1,2}(?:\.[0-9]+)?)",
            "type": "numeric", "low_flag": 27, "high": 32
        },
        {
            "key": "mchc",
            "name_en": "MCHC", "name_hi": "एमसीएचसी (MCHC)", "name_mr": "एमसीएचसी (MCHC)",
            "unit": "g/dL", "ref": "32.5 - 34.5 g/dL",
            "pattern": r"(?i)\bmchc\b\s*[:\-]?\s*([0-9]{1,2}(?:\.[0-9]+)?)",
            "type": "numeric", "low_flag": 32.5, "high": 34.5
        },
        {
            "key": "rdw",
            "name_en": "Red Cell Distribution Width (RDW)", "name_hi": "आरडीडब्ल्यू (RDW)", "name_mr": "आरडीडब्ल्यू (RDW)",
            "unit": "%", "ref": "11.6 - 14.0 %",
            "pattern": r"(?i)\brdw(?:\s*-\s*cv)?\b\s*[:\-]?\s*([0-9]{1,2}(?:\.[0-9]+)?)",
            "type": "numeric", "low_flag": 11.6, "high": 14.0
        },
        {
            "key": "wbc",
            "name_en": "Total WBC / Leukocyte Count", "name_hi": "कुल डब्ल्यूबीसी (TLC)", "name_mr": "पांढऱ्या पेशी (WBC/TLC)",
            "unit": "/cumm", "ref": "4,000 - 11,000 /cumm",
            "pattern": r"(?i)(?:total\s*wbc(?:\s*count)?|total\s*leukocytes?(?:\s*count)?|wbc(?:\s*count)?|tlc)\s*[:\-]?\s*([0-9]{1,2}(?:,\d{3})|\d{4,5})",
            "type": "numeric", "low_flag": 4000, "elevated": 11000, "high": 14000, "emergency": 18000
        },
        # Differential WBC Count
        {
            "key": "neutrophils",
            "name_en": "Neutrophils", "name_hi": "न्यूट्रोफिल्स (Neutrophils)", "name_mr": "न्यूट्रोफिल्स (Neutrophils)",
            "unit": "%", "ref": "50 - 62 %",
            "pattern": r"(?i)(?:neutrophils?|polymorphs?)\s*[:\-]?\s*([0-9]{1,2}(?:\.[0-9]+)?)",
            "type": "numeric", "low_flag": 50, "high": 62
        },
        {
            "key": "lymphocytes",
            "name_en": "Lymphocytes", "name_hi": "लिम्फोसाइट्स (Lymphocytes)", "name_mr": "लिम्फोसाइट्स (Lymphocytes)",
            "unit": "%", "ref": "20 - 40 %",
            "pattern": r"(?i)(?:lymphocytes?|lymphs?)\s*[:\-]?\s*([0-9]{1,2}(?:\.[0-9]+)?)",
            "type": "numeric", "low_flag": 20, "high": 40
        },
        {
            "key": "eosinophils",
            "name_en": "Eosinophils", "name_hi": "इओसिनोफिल्स (Eosinophils)", "name_mr": "इओसिनोफिल्स (Eosinophils)",
            "unit": "%", "ref": "0 - 6 %",
            "pattern": r"(?i)(?:eosinophils?|eos)\s*[:\-]?\s*([0-9]{1,2}(?:\.[0-9]+)?)",
            "type": "numeric", "high": 6
        },
        {
            "key": "monocytes",
            "name_en": "Monocytes", "name_hi": "मोनोसाइट्स (Monocytes)", "name_mr": "मोनोसाइट्स (Monocytes)",
            "unit": "%", "ref": "0 - 10 %",
            "pattern": r"(?i)(?:monocytes?|mono)\s*[:\-]?\s*([0-9]{1,2}(?:\.[0-9]+)?)",
            "type": "numeric", "high": 10
        },
        {
            "key": "basophils",
            "name_en": "Basophils", "name_hi": "बेसोफिल्स (Basophils)", "name_mr": "बेसोफिल्स (Basophils)",
            "unit": "%", "ref": "0 - 2 %",
            "pattern": r"(?i)(?:basophils?|baso)\s*[:\-]?\s*([0-9]{1,2}(?:\.[0-9]+)?)",
            "type": "numeric", "high": 2
        },
        # Platelet Count
        {
            "key": "platelets",
            "name_en": "Platelet Count", "name_hi": "प्लेटलेट काउंट", "name_mr": "प्लेटलेट्स (Platelets)",
            "unit": "/cumm", "ref": "1,50,000 - 4,10,000 /cumm",
            "pattern": r"(?i)(?:platelet\s*count|platelets|plt)\s*[:\-]?\s*(\d{4,7}|[0-9]{1,3}(?:,\d{2,3})+|[0-9]{1,2}(?:\.[0-9]+)?)",
            "type": "custom_platelet"
        },

        # Vitals & Other Labs
        {
            "key": "heart_rate",
            "name_en": "Heart Rate / Pulse", "name_hi": "हार्ट रेट (हृदय गति)", "name_mr": "हृदयाचे ठोके (Heart Rate)",
            "unit": "BPM", "ref": "60 - 100 BPM",
            "pattern": r"(?i)(?:heart\s*rate|pulse|pulse\s*rate|hr|bpm)\s*[:\-]?\s*([0-9]{2,3})",
            "type": "numeric", "low_flag": 50, "elevated": 100, "high": 115, "emergency": 130, "emergency_low": 45
        },
        {
            "key": "spo2",
            "name_en": "Blood Oxygen (SpO2)", "name_hi": "ऑक्सीजन स्तर (SpO2)", "name_mr": "ऑक्सिजन पातळी (SpO2)",
            "unit": "%", "ref": "95 - 100 %",
            "pattern": r"(?i)(?:spo2|oxygen|oxygen\s*saturation|o2)\s*[:\-]?\s*([0-9]{2,3})",
            "type": "numeric_low_bad", "normal_min": 95, "abnormal_max": 94, "emergency_max": 89
        },
        {
            "key": "cholesterol",
            "name_en": "Total Cholesterol", "name_hi": "कुल कोलेस्ट्रॉल", "name_mr": "कोलेस्टेरॉल (Total Cholesterol)",
            "unit": "mg/dL", "ref": "< 200 mg/dL",
            "pattern": r"(?i)(?:total\s*cholesterol|serum\s*cholesterol|cholesterol|total\s*chol)\s*[:\-]?\s*([0-9]{2,3}(?:\.[0-9]+)?)",
            "type": "numeric", "elevated": 200, "high": 240, "emergency": 280
        },
        {
            "key": "triglycerides",
            "name_en": "Triglycerides", "name_hi": "ट्राइग्लिसराइड्स", "name_mr": "ट्रायग्लिसराइड्स (Triglycerides)",
            "unit": "mg/dL", "ref": "< 150 mg/dL",
            "pattern": r"(?i)(?:triglycerides|tg|serum\s*triglycerides)\s*[:\-]?\s*([0-9]{2,3}(?:\.[0-9]+)?)",
            "type": "numeric", "elevated": 150, "high": 200, "emergency": 500
        },
        {
            "key": "creatinine",
            "name_en": "Serum Creatinine", "name_hi": "सीरम क्रिएटिनिन (किडनी)", "name_mr": "क्रिएटिनिन (Serum Creatinine)",
            "unit": "mg/dL", "ref": "0.7 - 1.3 mg/dL",
            "pattern": r"(?i)(?:serum\s*creatinine|creatinine|s\.\s*creat)\s*[:\-]?\s*([0-9]+(?:\.[0-9]+)?)",
            "type": "numeric", "elevated": 1.3, "high": 1.6, "emergency": 2.5
        },
        {
            "key": "urea",
            "name_en": "Blood Urea", "name_hi": "ब्लड यूरिया", "name_mr": "ब्लड युरिया (Blood Urea)",
            "unit": "mg/dL", "ref": "15 - 40 mg/dL",
            "pattern": r"(?i)(?:blood\s*urea|urea|bun)\s*[:\-]?\s*([0-9]{1,3}(?:\.[0-9]+)?)",
            "type": "numeric", "elevated": 40, "high": 55, "emergency": 80
        },
        {
            "key": "bilirubin",
            "name_en": "Total Bilirubin (Liver)", "name_hi": "कुल बिलीरुबिन (लिवर)", "name_mr": "बिलीरुबिन (Total Bilirubin)",
            "unit": "mg/dL", "ref": "0.2 - 1.2 mg/dL",
            "pattern": r"(?i)(?:total\s*bilirubin|bilirubin\s*total|serum\s*bilirubin)\s*[:\-]?\s*([0-9]+(?:\.[0-9]+)?)",
            "type": "numeric", "elevated": 1.2, "high": 2.0, "emergency": 3.5
        },
        {
            "key": "tsh",
            "name_en": "TSH (Thyroid)", "name_hi": "टीएसएच (थायरॉयड)", "name_mr": "टीएसएच (Thyroid TSH)",
            "unit": "mIU/L", "ref": "0.4 - 4.2 mIU/L",
            "pattern": r"(?i)(?:tsh|thyroid\s*stimulating\s*hormone)\s*[:\-]?\s*([0-9]+(?:\.[0-9]+)?)",
            "type": "numeric", "low_flag": 0.4, "elevated": 4.2, "high": 7.0, "emergency": 12.0
        }
    ]

    parsed_tests = []
    seen_keys = set()

    # Extract BP first: search for labeled BP first, then fallback to valid numeric systolic/diastolic ratios
    bp_found = False
    for m in re.finditer(r"(?i)(?:bp|blood\s*pressure|pressure)\s*[:\-]?\s*([0-9]{2,3})\s*[\/\\]\s*([0-9]{2,3})", text):
        sys_v, dia_v = int(m.group(1)), int(m.group(2))
        if sys_v > dia_v and 60 <= sys_v <= 260 and 30 <= dia_v <= 160:
            status = "normal"
            if sys_v >= 180 or dia_v >= 120:
                status = "emergency"
            elif sys_v >= 140 or dia_v >= 90:
                status = "high"
            elif sys_v >= 120 or dia_v >= 80:
                status = "borderline"
            parsed_tests.append({
                "key": "bp",
                "name_en": "Blood Pressure",
                "name_hi": "ब्लड प्रेशर (रक्तचाप)",
                "name_mr": "रक्तदाब (Blood Pressure)",
                "value": f"{sys_v}/{dia_v}",
                "unit": "mmHg",
                "reference_range": "120/80 mmHg",
                "status": status,
                "interpretation_en": f"Blood pressure is {status}." if status != "normal" else "Optimal blood pressure.",
                "interpretation_hi": "रक्तचाप सामान्य सीमा में है।" if status == "normal" else f"रक्तचाप {status} है।",
                "interpretation_mr": "रक्तदाब सामान्य मर्यादेत आहे." if status == "normal" else f"रक्तदाब {status} पातळीवर आहे."
            })
            seen_keys.add("bp")
            bp_found = True
            break

    if not bp_found:
        for m in re.finditer(r"\b([0-9]{2,3})\s*[\/\\]\s*([0-9]{2,3})\b", text):
            sys_v, dia_v = int(m.group(1)), int(m.group(2))
            if sys_v > dia_v and 80 <= sys_v <= 260 and 40 <= dia_v <= 160:
                status = "normal"
                if sys_v >= 180 or dia_v >= 120:
                    status = "emergency"
                elif sys_v >= 140 or dia_v >= 90:
                    status = "high"
                elif sys_v >= 120 or dia_v >= 80:
                    status = "borderline"
                parsed_tests.append({
                    "key": "bp",
                    "name_en": "Blood Pressure",
                    "name_hi": "ब्लड प्रेशर (रक्तचाप)",
                    "name_mr": "रक्तदाब (Blood Pressure)",
                    "value": f"{sys_v}/{dia_v}",
                    "unit": "mmHg",
                    "reference_range": "120/80 mmHg",
                    "status": status,
                    "interpretation_en": f"Blood pressure is {status}." if status != "normal" else "Optimal blood pressure.",
                    "interpretation_hi": "रक्तचाप सामान्य सीमा में है।" if status == "normal" else f"रक्तचाप {status} है।",
                    "interpretation_mr": "रक्तदाब सामान्य मर्यादेत आहे." if status == "normal" else f"रक्तदाब {status} पातळीवर आहे."
                })
                seen_keys.add("bp")
                break

    # Extract numeric and catalog lab tests
    for t_def in tests_catalog:
        if t_def["key"] in seen_keys:
            continue
        m = re.search(t_def["pattern"], text)
        if not m:
            continue
        val_str = m.group(1).replace(",", "").replace(" ", "").strip()
        try:
            val = float(val_str)
        except ValueError:
            continue

        status = "normal"
        t_type = t_def.get("type", "numeric")
        display_val = val
        display_unit = t_def["unit"]
        display_ref = t_def["ref"]

        if t_type == "custom_hb":
            is_male = meta.get("gender") == "male"
            norm_min = 13.0 if is_male else 12.0
            if val < 8.0:
                status = "emergency"
            elif val < 11.0:
                status = "high"
            elif val < norm_min:
                status = "borderline"
            elif val > 18.0:
                status = "high"
            else:
                status = "normal"
        elif t_type == "custom_platelet":
            if val <= 15:  # in lakhs
                val_cumm = val * 100000
                display_unit = "lakh/cumm"
                display_ref = "1.5 - 4.5 lakh"
            else:
                val_cumm = val
                display_val = f"{int(val):,}"

            if val_cumm < 50000:
                status = "emergency"
            elif val_cumm < 150000:
                status = "borderline"
            elif val_cumm > 450000:
                status = "high"
            else:
                status = "normal"
        elif t_type == "numeric":
            if "emergency" in t_def and val >= t_def["emergency"]:
                status = "emergency"
            elif "emergency_low" in t_def and val <= t_def["emergency_low"]:
                status = "emergency"
            elif "high" in t_def and val >= t_def["high"]:
                status = "high"
            elif "elevated" in t_def and val >= t_def["elevated"]:
                status = "borderline"
            elif "low_flag" in t_def and val < t_def["low_flag"]:
                status = "borderline" if t_def.get("key") in ("pcv", "rbc") else "low"
        elif t_type == "numeric_low_bad":
            if "emergency_max" in t_def and val <= t_def["emergency_max"]:
                status = "emergency"
            elif "abnormal_max" in t_def and val <= t_def["abnormal_max"]:
                status = "high"
            else:
                status = "normal"

        exp_en = f"Value ({display_val} {display_unit}) is {status}."
        exp_hi = f"वैल्यू ({display_val} {display_unit}) {status} है।"
        exp_mr = f"मूल्य ({display_val} {display_unit}) {status} आहे."

        parsed_tests.append({
            "key": t_def["key"],
            "name_en": t_def["name_en"],
            "name_hi": t_def["name_hi"],
            "name_mr": t_def["name_mr"],
            "value": display_val,
            "unit": display_unit,
            "reference_range": display_ref,
            "status": status,
            "interpretation_en": exp_en,
            "interpretation_hi": exp_hi,
            "interpretation_mr": exp_mr
        })
        seen_keys.add(t_def["key"])

    # Extract Prescriptions
    detected_meds = detect_medicines(text)
    prescriptions = []
    for med in detected_meds:
        brand = med["brand"]
        pattern = re.compile(rf"(?i){re.escape(brand)}[^\n]*", re.MULTILINE)
        m_line = pattern.search(text)
        line_ctx = m_line.group(0) if m_line else ""

        dosage = med.get("strengths", ["Standard"])[0]
        dose_m = re.search(r"(\d+\s*(?:mg|mcg|gm|ml))", line_ctx, re.IGNORECASE)
        if dose_m:
            dosage = dose_m.group(1)

        freq = "As directed by doctor"
        freq_hi = "डॉक्टर के निर्देशानुसार"
        freq_mr = "डॉक्टरांच्या सल्ल्यानुसार"
        if re.search(r"(?i)\b(?:1-0-1|bd|bid|twice\s*daily|दोनदा)\b", line_ctx):
            freq = "Twice daily (1-0-1)"
            freq_hi = "दिन में दो बार (1-0-1)"
            freq_mr = "दिवसातून दोनदा (1-0-1)"
        elif re.search(r"(?i)\b(?:1-1-1|tds|tid|thrice\s*daily|तीनदा)\b", line_ctx):
            freq = "Thrice daily (1-1-1)"
            freq_hi = "दिन में तीन बार (1-1-1)"
            freq_mr = "दिवसातून तीन वेळा (1-1-1)"
        elif re.search(r"(?i)\b(?:1-0-0|0-1-0|0-0-1|od|once\s*daily|एकदा)\b", line_ctx):
            freq = "Once daily (1-0-0)"
            freq_hi = "दिन में एक बार (1-0-0)"
            freq_mr = "दिवसातून एकदा (1-0-0)"
        elif re.search(r"(?i)\b(?:sos|as\s*needed|garaj\s*aslyas)\b", line_ctx):
            freq = "As needed (SOS)"
            freq_hi = "ज़रूरत पड़ने पर (SOS)"
            freq_mr = "गरज असल्यास (SOS)"

        timing = "After food" if re.search(r"(?i)\b(?:after\s*food|after\s*meals|pc|जेवणानंतर|खाने के बाद)\b", line_ctx) else ""
        if not timing and re.search(r"(?i)\b(?:before\s*food|empty\s*stomach|ac|जेवणापूर्वी|खाली पेट)\b", line_ctx):
            timing = "Before food"

        prescriptions.append({
            "brand": brand,
            "generic": med.get("generic", brand),
            "dosage": dosage,
            "frequency_en": freq + (f" ({timing})" if timing else ""),
            "frequency_hi": freq_hi + (f" ({timing})" if timing else ""),
            "frequency_mr": freq_mr + (f" ({timing})" if timing else ""),
            "form": med.get("form", "Tablet")
        })

    # Generate Condition Risk Alerts for Patient (ICMR / WHO guidelines)
    condition_alerts = []

    # 1. Diabetes & Blood Sugar
    fbs = next((t for t in parsed_tests if t["key"] == "fasting_sugar"), None)
    ppbs = next((t for t in parsed_tests if t["key"] == "pp_sugar"), None)
    hba1c = next((t for t in parsed_tests if t["key"] == "hba1c"), None)
    if (fbs and fbs["value"] >= 126) or (ppbs and ppbs["value"] >= 200) or (hba1c and hba1c["value"] >= 6.5):
        condition_alerts.append({
            "condition": "diabetes",
            "severity": "high",
            "title_en": "High Blood Sugar / Diabetes Risk",
            "title_hi": "उच्च ब्लड शुगर / डायबिटीज जोखिम",
            "title_mr": "रक्तातील उच्च साखर / मधुमेह (Diabetes) जोखीम",
            "desc_en": "Fasting glucose (>=126 mg/dL) or HbA1c (>=6.5%) indicates probable diabetes. Consult your physician for medical management and dietary guidance.",
            "desc_hi": "खाली पेट शुगर (126+) या HbA1c (6.5%+) डायबिटीज का संकेत देता है। उचित उपचार और आहार योजना के लिए डॉक्टर से मिलें।",
            "desc_mr": "उपाशीपोटी साखर (१२६+) किंवा HbA1c (६.५%+) मधुमेहाचा संकेत देते. डॉक्टरांचा सल्ला घेऊन योग्य औषधोपचार व आहार नियोजन सुरू करा.",
            "action_en": "Consult an endocrinologist or general physician; do not start or stop medications on your own.",
            "action_hi": "डॉक्टर से परामर्श लें; खुद से दवा शुरू या बंद न करें।",
            "action_mr": "डॉक्टरांचा सल्ला घ्या; स्वतःहून कोणतीही औषधे सुरू किंवा बंद करू नका."
        })
    elif (fbs and 100 <= fbs["value"] < 126) or (hba1c and 5.7 <= hba1c["value"] < 6.5):
        condition_alerts.append({
            "condition": "prediabetes",
            "severity": "moderate",
            "title_en": "Pre-Diabetes Indicator",
            "title_hi": "प्री-डायबिटीज संकेत (Pre-Diabetes)",
            "title_mr": "प्रिडायबिटीज संकेत (Pre-Diabetes)",
            "desc_en": "Glucose is in the pre-diabetic range (100-125 mg/dL). Lifestyle modifications and daily brisk walking can reverse this stage.",
            "desc_hi": "ब्लड शुगर प्री-डायबिटीज स्तर (100-125) पर है। मीठे से परहेज़, दैनिक व्यायाम और वजन नियंत्रण से इसे सामान्य किया जा सकता है।",
            "desc_mr": "साखर प्रिडायबिटीज पातळीवर (१००-१२५) आहे. गोड पदार्थ टाळून आणि दररोज ४५ मिनिटे चालल्यास हे पूर्ववत होऊ शकते.",
            "action_en": "Reduce refined carbs/sugar and get retested in 3 months.",
            "action_hi": "मीठा व तली चीजें कम करें और 3 महीने बाद दोबारा जांच कराएं।",
            "action_mr": "गोड व तेलकट पदार्थ कमी करा आणि ३ महिन्यांनी पुन्हा तपासणी करा."
        })
    elif (fbs and fbs["value"] < 70) or (ppbs and ppbs["value"] < 70):
        val = fbs["value"] if fbs else ppbs["value"]
        condition_alerts.append({
            "condition": "hypoglycemia",
            "severity": "emergency" if val <= 55 else "high",
            "title_en": "Hypoglycemia (Low Sugar Alert)",
            "title_hi": "हाइपोग्लाइसीमिया (कम शुगर चेतावनी)",
            "title_mr": "हायपोग्लायसेमिया (कमी साखर इशारा)",
            "desc_en": f"Blood glucose ({val} mg/dL) is dangerously low. Symptoms can include trembling, cold sweat, confusion, or fainting.",
            "desc_hi": f"ब्लड शुगर ({val} mg/dL) खतरनाक रूप से कम है। कंपकंपी या चक्कर आने पर तुरंत मीठा खाएं।",
            "desc_mr": f"रक्तातील साखर ({val} mg/dL) अत्यंत कमी आहे. थरथरणे किंवा चक्कर आल्यास तात्काळ साखर/गूळ खा.",
            "action_en": "Consume 15-20g fast-acting sugar (fruit juice or glucose) and seek urgent medical help if unresponsive.",
            "action_hi": "तुरंत ग्लूकोज, फल का रस या चीनी लें और डॉक्टर से संपर्क करें।",
            "action_mr": "लगेच ग्लुकोज किंवा फळांचा रस प्या आणि तात्काळ डॉक्टरांशी संपर्क साधा."
        })

    # 2. Blood Pressure / Cardiovascular Alert
    bp_test = next((t for t in parsed_tests if t["key"] == "bp"), None)
    if bp_test:
        if bp_test["status"] == "emergency":
            condition_alerts.append({
                "condition": "hypertensive_crisis",
                "severity": "emergency",
                "title_en": "🚨 Hypertensive Crisis Alert",
                "title_hi": "🚨 गंभीर रक्तचाप संकट (Hypertensive Crisis)",
                "title_mr": "🚨 अति-गंभीर उच्च रक्तदाब आणीबाणी इशारा",
                "desc_en": f"Blood pressure ({bp_test['value']} mmHg) is at a critical emergency level. High risk of cardiovascular or neurological complications.",
                "desc_hi": f"रक्तचाप ({bp_test['value']} mmHg) अत्यधिक खतरनाक स्तर पर है। हृदय या मस्तिष्क आघात का गंभीर खतरा रहता है।",
                "desc_mr": f"रक्तदाब ({bp_test['value']} mmHg) अतिशय गंभीर धोक्याच्या पातळीवर आहे. हृदय किंवा मेंदूला इजा होण्याचा धोका असतो.",
                "action_en": "Proceed to the nearest emergency room or hospital immediately.",
                "action_hi": "बिना देर किए तुरंत आपातकालीन अस्पताल जाएं।",
                "action_mr": "कोणताही वेळ न घालवता लगेच जवळच्या इमर्जन्सी हॉस्पिटलमध्ये जा."
            })
        elif bp_test["status"] == "high":
            condition_alerts.append({
                "condition": "hypertension",
                "severity": "high",
                "title_en": "High Blood Pressure (Hypertension)",
                "title_hi": "उच्च रक्तचाप (Hypertension)",
                "title_mr": "उच्च रक्तदाब (Hypertension)",
                "desc_en": f"Blood pressure ({bp_test['value']} mmHg) exceeds safe limits. Chronic hypertension strains arteries and kidneys.",
                "desc_hi": f"रक्तचाप ({bp_test['value']} mmHg) सामान्य से अधिक है। लंबे समय तक उच्च बीपी हृदय और किडनी को नुकसान पहुंचाता है।",
                "desc_mr": f"रक्तदाब ({bp_test['value']} mmHg) सामान्यपेक्षा जास्त आहे. यामुळे रक्तवाहिन्या आणि किडनीवर ताण येतो.",
                "action_en": "Consult a physician for anti-hypertensive therapy and reduce sodium intake.",
                "action_hi": "डॉक्टर से मिलकर दवा शुरू करें और खाने में नमक कम करें।",
                "action_mr": "डॉक्टरांच्या सल्ल्याने औषधोपचार सुरू करा आणि जेवणात मीठ कमी करा."
            })

    # Combined BP + Sugar Risk
    has_high_sugar = bool((fbs and fbs["value"] >= 126) or (ppbs and ppbs["value"] >= 200) or (hba1c and hba1c["value"] >= 6.5))
    has_high_bp_flag = bool(bp_test and bp_test["status"] in ("high", "emergency"))
    if has_high_sugar and has_high_bp_flag:
        condition_alerts.append({
            "condition": "combined_cardio_metabolic",
            "severity": "emergency" if (bp_test and bp_test["status"] == "emergency") else "high",
            "title_en": "Combined Risk: High Blood Pressure + High Sugar",
            "title_hi": "संयुक्त जोखिम: हाई बीपी + हाई शुगर",
            "title_mr": "एकत्रित जोखीम: उच्च रक्तदाब + उच्च साखर",
            "desc_en": "Simultaneous hypertension and hyperglycemia compound the risk to your heart, kidneys, and retinas (ICMR/WHO).",
            "desc_hi": "बीपी और शुगर दोनों एक साथ ज्यादा होने से हृदय, गुर्दे और आंखों पर दोहरा खतरा बढ़ जाता है।",
            "desc_mr": "रक्तदाब आणि साखर दोन्ही एकाच वेळी जास्त असल्याने हृदय, मूत्रपिंड आणि डोळ्यांवर दुहेरी ताण येतो.",
            "action_en": "Urgent comprehensive medical review recommended.",
            "action_hi": "जल्द से जल्द डॉक्टर से समग्र स्वास्थ्य जांच कराएं।",
            "action_mr": "लवकरात लवकर डॉक्टरांना भेटून तपासणी करून घ्या."
        })

    # 3. Kidney Function & Creatinine
    creat_test = next((t for t in parsed_tests if t["key"] == "creatinine"), None)
    if creat_test and creat_test["value"] >= 1.3:
        is_crit = creat_test["value"] >= 2.5
        condition_alerts.append({
            "condition": "kidney_impairment",
            "severity": "emergency" if is_crit else "high",
            "title_en": "Kidney Strain / Elevated Creatinine Alert",
            "title_hi": "किडनी पर दबाव / बढ़ा हुआ क्रिएटिनिन",
            "title_mr": "किडनीवर ताण / वाढलेला क्रिएटिनिन इशारा",
            "desc_en": f"Creatinine ({creat_test['value']} mg/dL) indicates impaired kidney filtration. Avoid NSAID painkillers like Ibuprofen/Diclofenac.",
            "desc_hi": f"क्रिएटिनिन ({creat_test['value']} mg/dL) किडनी की कार्यक्षमता में कमी दर्शाता है। दर्द निवारक दवाएं बिल्कुल न लें।",
            "desc_mr": f"क्रिएटिनिन ({creat_test['value']} mg/dL) वाढलेला आहे. आयबुप्रोफेन/डायक्लोफेनाक सारख्या पेनकिलर गोळ्या टाळा.",
            "action_en": "Consult a nephrologist or general physician promptly; monitor hydration.",
            "action_hi": "नेफ्रोलॉजिस्ट या डॉक्टर से परामर्श लें और पानी का संतुलन बनाए रखें।",
            "action_mr": "तातडीने डॉक्टरांचा सल्ला घ्या आणि पुरेशा प्रमाणात पाणी प्या."
        })

    # 4. Anemia / Low Hemoglobin Alert (Borderline or Severe)
    hb_test = next((t for t in parsed_tests if t["key"] == "hemoglobin"), None)
    if hb_test:
        try:
            hb_val = float(hb_test["value"])
            is_male = meta.get("gender") == "male"
            norm_min = 13.0 if is_male else 12.0
            if hb_val < norm_min:
                is_crit = hb_val < 8.0
                is_high = hb_val < 11.0
                sev = "emergency" if is_crit else ("high" if is_high else "moderate")
                condition_alerts.append({
                    "condition": "anemia",
                    "severity": sev,
                    "title_en": "Mild Anemia / Low Hemoglobin Alert" if sev == "moderate" else "Anemia (Low Hemoglobin Alert)",
                    "title_hi": "हल्का एनीमिया / कम हीमोग्लोबिन जोखिम" if sev == "moderate" else "एनीमिया (कम हीमोग्लोबिन चेतावनी)",
                    "title_mr": "सौम्य ॲनिमिया / कमी हीमोग्लोबिन जोखीम" if sev == "moderate" else "ॲनिमिया (कमी हीमोग्लोबिन इशारा)",
                    "desc_en": f"Hemoglobin ({hb_val} g/dL) is below the recommended range ({hb_test['reference_range']}). Can cause fatigue, reduced stamina, and breathlessness on exertion.",
                    "desc_hi": f"हीमोग्लोबिन ({hb_val} g/dL) सामान्य सीमा ({hb_test['reference_range']}) से कम है। इससे थकान, कमजोरी और जल्दी सांस फूलना हो सकता है।",
                    "desc_mr": f"हीमोग्लोबिन ({hb_val} g/dL) सामान्य मर्यादेपेक्षा ({hb_test['reference_range']}) कमी आहे. यामुळे थकवा, अशक्तपणा आणि धाप लागणे जाणवू शकते.",
                    "action_en": "Include iron-rich foods (spinach, beetroot, jaggery, lentils, dates) and consult your physician for dietary advice or iron profile.",
                    "action_hi": "आयरन युक्त आहार लें (पालक, चुकंदर, गुड़, दालें, खजूर) और डॉक्टर से आहार या सप्लीमेंट पर सलाह लें।",
                    "action_mr": "आहारात लोहयुक्त पदार्थ वाढवा (पालक, बीट, गूळ, खजूर, डाळी) आणि डॉक्टरांचा सल्ला घ्या."
                })
        except Exception:
            pass

    # 5. Low Platelet Alert (Thrombocytopenia)
    plt_test = next((t for t in parsed_tests if t["key"] == "platelets"), None)
    if plt_test and plt_test["status"] in ("emergency", "borderline", "low"):
        condition_alerts.append({
            "condition": "thrombocytopenia",
            "severity": plt_test["status"],
            "title_en": "Low Platelets Alert (Thrombocytopenia)",
            "title_hi": "कम प्लेटलेट चेतावनी (Thrombocytopenia)",
            "title_mr": "कमी प्लेटलेट्स इशारा (Thrombocytopenia)",
            "desc_en": f"Platelet count ({plt_test['value']} {plt_test['unit']}) is below normal range. Monitor closely if fever, body ache, or bleeding tendencies are present.",
            "desc_hi": f"प्लेटलेट काउंट ({plt_test['value']} {plt_test['unit']}) सामान्य से कम है। बुखार या कमजोरी होने पर तुरंत डॉक्टर को दिखाएं।",
            "desc_mr": f"प्लेटलेट्स संख्या ({plt_test['value']} {plt_test['unit']}) सामान्यपेक्षा कमी आहे. ताप किंवा अशक्तपणा असल्यास त्वरित डॉक्टरांना दाखवा.",
            "action_en": "Consult doctor immediately if associated with fever or dengue symptoms; stay well hydrated.",
            "action_hi": "बुखार या डेंगू के लक्षण होने पर तुरंत डॉक्टर से संपर्क करें।",
            "action_mr": "ताप किंवा डेंग्यू सदृश लक्षणे असल्यास त्वरित डॉक्टरांचा सल्ला घ्या."
        })

    # 6. Elevated WBC Count (Infection indicator)
    wbc_test = next((t for t in parsed_tests if t["key"] == "wbc"), None)
    if wbc_test and wbc_test["status"] in ("emergency", "high"):
        condition_alerts.append({
            "condition": "leukocytosis",
            "severity": wbc_test["status"],
            "title_en": "Elevated WBC / Infection Alert",
            "title_hi": "सफेद रक्त कणिका वृद्धि / संक्रमण चेतावनी",
            "title_mr": "वाढलेल्या पांढऱ्या पेशी / संसर्ग इशारा (WBC)",
            "desc_en": f"Total leukocyte count ({wbc_test['value']} {wbc_test['unit']}) is elevated, indicating active bodily infection or inflammatory response.",
            "desc_hi": f"कुल डब्ल्यूबीसी संख्या ({wbc_test['value']} {wbc_test['unit']}) अधिक है, जो शरीर में किसी संक्रमण या सूजन का संकेत देती है।",
            "desc_mr": f"एकूण पांढऱ्या पेशींची संख्या ({wbc_test['value']} {wbc_test['unit']}) जास्त आहे, जी शरीरातील संसर्ग (Infection) दर्शवते.",
            "action_en": "Consult your physician for clinical evaluation and appropriate anti-infective treatment.",
            "action_hi": "उचित जांच और उपचार के लिए डॉक्टर से मिलें।",
            "action_mr": "तपासणी व योग्य उपचारांसाठी डॉक्टरांशी संपर्क साधा."
        })

    # 7. Low Oxygen Saturation
    spo2_test = next((t for t in parsed_tests if t["key"] == "spo2"), None)
    if spo2_test and spo2_test["value"] < 95:
        is_crit = spo2_test["value"] < 90
        condition_alerts.append({
            "condition": "hypoxemia",
            "severity": "emergency" if is_crit else "high",
            "title_en": "Low Blood Oxygen (SpO2 Alert)",
            "title_hi": "कम ऑक्सीजन स्तर (SpO2 चेतावनी)",
            "title_mr": "कमी ऑक्सिजन पातळी (SpO2 इशारा)",
            "desc_en": f"Blood oxygen level ({spo2_test['value']}%) is sub-optimal. Significant shortness of breath requires urgent attention.",
            "desc_hi": f"ऑक्सीजन स्तर ({spo2_test['value']}%) सामान्य से कम है। सांस लेने में तकलीफ होने पर तुरंत चिकित्सा सहायता लें।",
            "desc_mr": f"ऑक्सिजन पातळी ({spo2_test['value']}%) सामान्य मर्यादेपेक्षा कमी आहे. श्वसनाचा त्रास असल्यास तातडीने मदत घ्या.",
            "action_en": "Seek immediate oxygen evaluation at a clinic or hospital.",
            "action_hi": "तुरंत अस्पताल में ऑक्सीजन जांच कराएं।",
            "action_mr": "तातडीने रुग्णालयात ऑक्सिजन तपासणी करून घ्या."
        })
    for ca in condition_alerts:
        ca["title"] = ca.get("title_en")
        ca["description"] = ca.get("desc_en")
        ca["action"] = ca.get("action_en")

    return {
        "metadata": meta,
        "tests": parsed_tests,
        "condition_alerts": condition_alerts,
        "prescriptions": prescriptions,
        "detected_medicines": detected_meds
    }


# ---------- Clinical Medicine Safety Engine ----------
def check_medicine_safety(medicines, patient_profile=None):
    """
    Evaluates detected or entered medicines against patient profile:
    - Age (pediatric vs adult vs elderly >= 65)
    - Health conditions (Kidney disease/high creatinine, Hypertension, Diabetes, Pregnancy)
    - Allergies (Penicillin, NSAID/Aspirin, Sulfa)
    - Multi-drug interactions (duplicate paracetamol, NSAID combinations, ARB + NSAID, etc.)
    - Unknown/unverified medicines (defaults to Consult Doctor for patient safety)
    Returns structured verdict per medicine: Safe / Caution / Consult doctor with ICMR/WHO reasoning.
    """
    profile = patient_profile or {}

    # Normalize medicines input (supports list of dicts, list of strings, or text string)
    norm_medicines = []
    if isinstance(medicines, str):
        medicines = detect_medicines(medicines)
    elif isinstance(medicines, dict):
        medicines = [medicines]

    for m in (medicines or []):
        if isinstance(m, str):
            matched = detect_medicines(m)
            if matched:
                norm_medicines.extend(matched)
            else:
                norm_medicines.append({
                    "brand": m.strip(),
                    "generic": m.strip(),
                    "is_unknown": True
                })
        elif isinstance(m, dict):
            brand = m.get("brand") or m.get("name") or "Medicine"
            generic = m.get("generic")
            if not generic or generic == brand:
                matched = detect_medicines(brand)
                if matched:
                    m["brand"] = matched[0]["brand"]
                    m["generic"] = matched[0]["generic"]
                    m["aliases"] = matched[0].get("aliases", [])
                else:
                    m["generic"] = brand
                    m["is_unknown"] = True
            norm_medicines.append(m)

    medicines = norm_medicines

    try:
        age = int(profile.get("age") or 0)
    except (TypeError, ValueError):
        age = 0
    gender = (profile.get("gender") or "female").strip().lower()
    is_pregnant = bool(profile.get("is_pregnant") or profile.get("pregnant") or profile.get("pregnancy"))
    has_kidney_disease = bool(profile.get("kidney_disease") or profile.get("kidney"))

    vitals = profile.get("vitals") or {}
    creat = vitals.get("creat") or profile.get("creat") or profile.get("creatinine")
    try:
        creat_val = float(creat) if creat not in (None, "") else None
    except ValueError:
        creat_val = None

    sugar = vitals.get("sugar") or profile.get("sugar")
    try:
        sugar_val = float(sugar) if sugar not in (None, "") else None
    except ValueError:
        sugar_val = None

    bp = vitals.get("bp") or profile.get("bp") or ""
    has_high_bp = False
    if bp:
        m = re.match(r"(\d+)\s*[\/\\]\s*(\d+)", str(bp))
        if m and (int(m.group(1)) >= 140 or int(m.group(2)) >= 90):
            has_high_bp = True

    # Patient Allergies
    allergies = profile.get("allergies") or []
    if isinstance(allergies, str):
        allergies = [a.strip().lower() for a in allergies.split(",")]
    else:
        allergies = [str(a).strip().lower() for a in allergies]
    has_penicillin_allergy = bool(profile.get("allergy_penicillin") or any("penicillin" in a for a in allergies))
    has_nsaid_allergy = bool(profile.get("allergy_nsaid") or profile.get("allergy_aspirin") or any(a in ("nsaid", "aspirin", "painkiller") for a in allergies))
    has_sulfa_allergy = bool(profile.get("allergy_sulfa") or any("sulfa" in a for a in allergies))

    # Identify generics list
    generics = []
    for m in medicines:
        g = m.get("generic") or m.get("brand")
        if g:
            generics.append(g)

    # Check pairwise interactions
    pairwise_warnings = check_interactions(generics)

    evaluations = []
    for med in medicines:
        brand = med.get("brand") or med.get("name") or "Medicine"
        generic = med.get("generic") or brand
        is_unverified = bool(med.get("is_unknown"))

        verdict = "safe"  # safe | caution | consult_doctor
        reasons_en = []
        reasons_hi = []
        reasons_mr = []
        actions_en = []
        actions_hi = []
        actions_mr = []

        # 0. Unverified / Unknown medicine check
        if is_unverified:
            verdict = "consult_doctor"
            reasons_en.append("Medicine not found in our curated clinical database. Verify dosage and safety with a doctor or pharmacist.")
            reasons_hi.append("यह दवा हमारे क्लिनिकल डेटाबेस में नहीं मिली। उपयोग से पहले डॉक्टर या फार्मासिस्ट से पुष्टि करें।")
            reasons_mr.append("हे औषध आमच्या प्रमाणित क्लिनिकल डेटाबेसमध्ये आढळले नाही. घेण्यापूर्वी डॉक्टर किंवा फार्मासिस्टची खात्री करा.")
            actions_en.append("Do not consume without prescription validation.")
            actions_hi.append("डॉक्टर की सलाह के बिना सेवन न करें।")
            actions_mr.append("डॉक्टरांच्या सल्ल्याशिवाय सेवन करू नका.")

        # 1. Multi-drug interaction hits for this medicine
        for w in pairwise_warnings:
            pair = w.get("pair", [])
            matches_pair = False
            if generic in pair:
                matches_pair = True
            elif any(p.lower() in generic.lower() or generic.lower() in p.lower() for p in pair):
                matches_pair = True

            if matches_pair:
                sev = w.get("severity", "moderate")
                if sev == "high":
                    verdict = "consult_doctor"
                elif verdict != "consult_doctor":
                    verdict = "caution"
                reasons_en.append(w.get("message_en", "Drug interaction warning."))
                reasons_hi.append(w.get("message_hi", "दवाओं के संयोजन में चेतावनी।"))
                reasons_mr.append(w.get("message_mr") or w.get("message_hi") or w.get("message_en", "दवांच्या परस्पर परिणामाचा इशारा."))
                actions_en.append(w.get("action", "Consult a doctor or pharmacist."))
                actions_hi.append(w.get("action", "डॉक्टर या फार्मासिस्ट से परामर्श लें।"))
                actions_mr.append(w.get("action", "डॉक्टर किंवा फार्मासिस्टचा सल्ला घ्या."))

        # 2. Known Allergies
        gen_lower = generic.lower()
        brand_lower = brand.lower()

        if has_penicillin_allergy and (
            "penicillin" in gen_lower or "amoxicillin" in gen_lower or "ampicillin" in gen_lower or
            "augmentin" in brand_lower or "mox" in brand_lower
        ):
            verdict = "consult_doctor"
            reasons_en.append("Penicillin allergy detected: This medicine contains a penicillin-class antibiotic (risk of severe allergic anaphylaxis).")
            reasons_hi.append("पेनिसिलिन एलर्जी चेतावनी: इस दवा में पेनिसिलिन वर्ग है जिससे गंभीर एनाफिलेक्सिस रिएक्शन का खतरा है।")
            reasons_mr.append("पेनिसिलिन ॲलर्जी इशारा: या औषधात पेनिसिलिन वर्ग असल्याने तीव्र ॲलर्जी अथवा शॉकचा धोका संभवतो.")
            actions_en.append("Do not take. Request a non-penicillin alternative from your doctor.")
            actions_hi.append("यह दवा न लें। डॉक्टर से पेनिसिलिन-मुक्त विकल्प मांगें।")
            actions_mr.append("हे औषध घेऊ नका. डॉक्टरांकडून पेनिसिलिन-मुक्त पर्यायी औषध घ्या.")

        if has_nsaid_allergy and (generic in NSAID_GENERICS or generic == "Aspirin" or "ibuprofen" in gen_lower or "diclofenac" in gen_lower):
            verdict = "consult_doctor"
            reasons_en.append("NSAID/Aspirin allergy detected: Painkiller risks severe bronchospasm, hives, or anaphylaxis.")
            reasons_hi.append("NSAID/Aspirin एलर्जी चेतावनी: दर्द निवारक से गंभीर सांस की तकलीफ या एलर्जी हो सकती है।")
            reasons_mr.append("वेदनाशामक (NSAID/Aspirin) ॲलर्जी इशारा: यामुळे श्वास घेण्यास त्रास किंवा तीव्र रिॲक्शन होऊ शकते.")
            actions_en.append("Contraindicated. Use non-NSAID analgesics under medical advice.")
            actions_hi.append("प्रतिबंधित। डॉक्टर की सलाह पर सुरक्षित विकल्प लें।")
            actions_mr.append("प्रतिबंधित. डॉक्टरांच्या सल्ल्याने सुरक्षित पर्याय वापरा.")

        if has_sulfa_allergy and ("sulfa" in gen_lower or "cotrimoxazole" in gen_lower or "septran" in brand_lower or "bactrim" in brand_lower):
            verdict = "consult_doctor"
            reasons_en.append("Sulfa allergy detected: Sulfonamide antibiotic risks severe cutaneous allergic reaction.")
            reasons_hi.append("सल्फा एलर्जी चेतावनी: इस दवा से त्वचा पर गंभीर एलर्जिक रिएक्शन का खतरा है।")
            reasons_mr.append("सल्फा ॲलर्जी इशारा: यामुळे त्वचेवर गंभीर ॲलर्जीचा धोका असतो.")
            actions_en.append("Do not take. Ask doctor for non-sulfa antibiotic.")
            actions_hi.append("सल्फा-मुक्त एंटीबायोटिक के लिए डॉक्टर से संपर्क करें।")
            actions_mr.append("सल्फा-मुक्त पर्यायासाठी डॉक्टरांशी संपर्क साधा.")

        # 3. Age Checks (ICMR / WHO)
        if age > 0:
            # Pediatric (< 12)
            if age < 12:
                if generic == "Aspirin":
                    verdict = "consult_doctor"
                    reasons_en.append("Aspirin is strictly contraindicated in children under 12-18 due to fatal Reye's syndrome risk (WHO).")
                    reasons_hi.append("12 साल से कम उम्र में Aspirin से रेये सिंड्रोम का घातक खतरा रहता है (WHO)।")
                    reasons_mr.append("12 वर्षांखालील मुलांमध्ये Aspirin मुळे Reye's Syndrome चा जीवघेणा धोका असतो (WHO).")
                    actions_en.append("Do not administer to children; use pediatric paracetamol as directed by doctor.")
                elif generic in ("Ciprofloxacin", "Norfloxacin"):
                    if verdict != "consult_doctor":
                        verdict = "caution"
                    reasons_en.append("Fluoroquinolone antibiotics require strict pediatric weight-based dosing (ICMR).")
                    reasons_hi.append("बच्चों में एंटीबायोटिक खुराक वजन के अनुसार होनी चाहिए (ICMR)।")
                    reasons_mr.append("लहान मुलांमध्ये अँटीबायोटिक डोस वजनानुसार देणे आवश्यक आहे (ICMR).")
                elif "650" in brand or "650 mg" in str(med.get("strengths", [])):
                    if verdict != "consult_doctor":
                        verdict = "caution"
                    reasons_en.append("650mg is an adult dose; children require weight-adjusted pediatric syrup/drops.")
                    reasons_hi.append("650mg वयस्कों की खुराक है; बच्चों के लिए सिरप की उचित मात्रा दें।")
                    reasons_mr.append("650mg हा मोठ्यांचा डोस आहे; मुलांसाठी वजनानुसार सिरप द्या.")
            # Elderly (>= 65)
            elif age >= 65:
                if generic in NSAID_GENERICS:
                    if verdict != "consult_doctor":
                        verdict = "caution"
                    reasons_en.append("Elderly patients (>=65) have elevated risk of gastric bleeding and renal impairment with NSAIDs (Beers/WHO criteria).")
                    reasons_hi.append("65+ उम्र में दर्द निवारक (NSAID) से पेट में अल्सर और किडनी पर दबाव का खतरा रहता है (WHO)।")
                    reasons_mr.append("65 वर्षांवरील व्यक्तींमध्ये वेदनाशामक गोळ्यांमुळे पोटातील अल्सर व किडनीवर ताण येतो (WHO).")
                    actions_en.append("Use lowest effective dose and consider gastro-protection.")
                elif generic == "Glimepiride":
                    if verdict != "consult_doctor":
                        verdict = "caution"
                    reasons_en.append("Sulfonylureas increase risk of prolonged hypoglycemia in elderly patients.")
                    reasons_hi.append("बुजुर्गों में शुगर अचानक बहुत कम होने का खतरा रहता है।")
                    reasons_mr.append("ज्येष्ठ नागरिकांमध्ये साखर अचानक कमी होण्याचा धोका असतो.")

        # 4. Organ & Condition Contraindications
        # Kidney Impairment
        if has_kidney_disease or (creat_val is not None and creat_val > 1.3):
            if generic == "Metformin":
                verdict = "consult_doctor"
                reasons_en.append("Elevated creatinine/kidney disease: Metformin requires physician review to prevent lactic acidosis (ICMR).")
                reasons_hi.append("किडनी की बीमारी में मेटफॉर्मिन से लैक्टिक एसिडोसिस का गंभीर खतरा हो सकता है।")
                reasons_mr.append("किडनी विकारात मेटफॉर्मिनमुळे लॅक्टिक ॲसिडोसिसचा धोका असतो; डॉक्टरांचा सल्ला अनिवार्य आहे.")
            elif generic in NSAID_GENERICS:
                verdict = "consult_doctor"
                reasons_en.append("Known kidney disease / elevated creatinine: NSAID painkillers further reduce kidney filtration.")
                reasons_hi.append("किडनी समस्या में दर्द निवारक (NSAID) दवाएं किडनी के कार्य को नुकसान पहुंचाती हैं।")
                reasons_mr.append("किडनी विकारात वेदनाशामक औषधांमुळे किडनीवर गंभीर दुष्परिणाम होऊ शकतो.")

        # Hypertension
        if has_high_bp and generic in NSAID_GENERICS:
            if verdict != "consult_doctor":
                verdict = "caution"
            reasons_en.append("NSAIDs cause fluid retention and blunt the blood-pressure lowering effects of antihypertensives.")
            reasons_hi.append("दर्द निवारक दवाएं बीपी की दवाओं का असर कम कर सकती हैं।")
            reasons_mr.append("वेदना निवारक औषधांमुळे बीपी औषधांचा प्रभाव कमी होऊ शकतो.")

        # Diabetes & Steroids
        if sugar_val is not None and sugar_val >= 126 and generic in ("Prednisolone", "Betamethasone"):
            if verdict != "consult_doctor":
                verdict = "caution"
            reasons_en.append("Steroids elevate blood sugar significantly; close glucose monitoring is essential (ICMR).")
            reasons_hi.append("स्टेरॉयड से ब्लड शुगर काफी बढ़ सकता है; नियमित जांच जरूरी है।")
            reasons_mr.append("स्टेरॉईडमुळे रक्तातील साखर वेगाने वाढू शकते; साखर सतत तपासणे आवश्यक.")

        # Pregnancy
        if is_pregnant or (gender == "female" and 18 <= age <= 45 and profile.get("pregnancy_alert")):
            if generic in ("Telmisartan", "Losartan", "Atorvastatin"):
                verdict = "consult_doctor"
                reasons_en.append("Contraindicated during pregnancy due to fetal safety risks (WHO/FDA Category D/X).")
                reasons_hi.append("गर्भावस्था में यह दवा भ्रूण के लिए असुरक्षित व प्रतिबंधित मानी गई है (WHO)।")
                reasons_mr.append("गर्भधारणेदरम्यान हे औषध गर्भासाठी अत्यंत घातक व प्रतिबंधित मानले जाते (WHO).")
            elif generic in NSAID_GENERICS:
                verdict = "consult_doctor"
                reasons_en.append("NSAIDs are contraindicated during pregnancy (especially 3rd trimester) due to premature ductus closure risk.")
                reasons_hi.append("गर्भावस्था में दर्द निवारक (NSAID) दवाएं भ्रूण के हृदय के लिए असुरक्षित हैं।")
                reasons_mr.append("गर्भधारणेदरम्यान वेदनाशामक गोळ्या गर्भाच्या हृदयासाठी घातक ठरू शकतात.")

        # Default safe text if no alerts triggered and medicine is verified
        if verdict == "safe":
            reasons_en.append("Aligns with patient profile; no high-risk contraindication or interaction found in curated clinical database.")
            reasons_hi.append("मरीज की प्रोफाइल के अनुसार सुरक्षित; हमारे क्लिनिकल डेटाबेस में कोई ज्ञात बड़ा खतरा नहीं मिला।")
            reasons_mr.append("रुग्णाच्या प्रोफाइलनुसार योग्य; आमच्या प्रमाणित क्लिनिकल डेटामध्ये कोणतीही मोठी जोखीम आढळली नाही.")
            actions_en.append("Take strictly as prescribed by your doctor.")
            actions_hi.append("डॉक्टर के परामर्श अनुसार समय पर लें।")
            actions_mr.append("डॉक्टरांच्या सल्ल्यानुसार वेळेवर घ्या.")

        labels = {
            "safe": {"en": "Safe", "hi": "सुरक्षित", "mr": "सुरक्षित", "color": "green"},
            "caution": {"en": "Caution", "hi": "सावधानी", "mr": "सावधगिरी", "color": "yellow"},
            "consult_doctor": {"en": "Consult Doctor", "hi": "डॉक्टर से परामर्श लें", "mr": "डॉक्टरांचा सल्ला घ्या", "color": "red"}
        }

        med_match = next((med for med in MEDICINES if med["brand"].lower() == brand.lower() or med["generic"].lower() == generic.lower()), None)
        brand_mrp = (med_match.get("brand_mrp") if med_match else None) or m.get("brand_mrp") or 45
        ja_mrp = (med_match.get("ja_mrp") if med_match else None) or m.get("ja_mrp") or 9
        savings_pct = (med_match.get("savings_pct") if med_match else None) or m.get("savings_pct") or 80

        evaluations.append({
            "brand": brand,
            "generic": generic,
            "verdict": verdict,
            "label_en": labels[verdict]["en"],
            "label_hi": labels[verdict]["hi"],
            "label_mr": labels[verdict]["mr"],
            "color": labels[verdict]["color"],
            "reasons_en": " ".join(reasons_en),
            "reasons_hi": " ".join(reasons_hi),
            "reasons_mr": " ".join(reasons_mr),
            "reason_en": " ".join(reasons_en),
            "reason_hi": " ".join(reasons_hi),
            "reason_mr": " ".join(reasons_mr),
            "reason": " ".join(reasons_en),
            "action_en": " ".join(actions_en) if actions_en else "Consult your physician.",
            "action_hi": " ".join(actions_hi) if actions_hi else "डॉक्टर से सलाह लें।",
            "action_mr": " ".join(actions_mr) if actions_mr else "डॉक्टरांचा सल्ला घ्या.",
            "brand_mrp": brand_mrp,
            "ja_mrp": ja_mrp,
            "savings_pct": savings_pct,
            "generic_alt": f"Generic {generic} (Jan Aushadhi)"
        })

    overall = ("consult_doctor" if any(e["verdict"] == "consult_doctor" for e in evaluations)
               else "caution" if any(e["verdict"] == "caution" for e in evaluations)
               else "safe")
    return {
        "evaluations": evaluations,
        "medicines": evaluations,
        "pairwise_warnings": pairwise_warnings,
        "warnings": pairwise_warnings,
        "overall_safety": overall,
        "overall_verdict": overall
    }


def detect_medicines(text):
    """Fuzzy-match tokens/phrases in OCR text against the curated brand dictionary."""
    found = {}
    lowered = text.lower()
    tokens = re.findall(r"[a-zA-Z][a-zA-Z\-]{2,}", lowered)
    candidates = set(tokens)
    words = lowered.split()
    for i in range(len(words) - 1):
        candidates.add(words[i] + " " + words[i + 1])

    all_aliases = [a for a, _ in ALIAS_INDEX]
    for cand in candidates:
        matches = difflib.get_close_matches(cand, all_aliases, n=1, cutoff=0.82)
        if not matches:
            continue
        matched_alias = matches[0]
        for alias, med in ALIAS_INDEX:
            if alias == matched_alias:
                found[med["brand"]] = med
                break
    return list(found.values())


def check_interactions(generic_list):
    """
    Evaluates multi-drug interactions including duplicate active ingredients
    and drug-drug interaction pairs from curated ICMR/WHO guidelines.
    """
    generics = set(generic_list)
    warnings = []

    for rule in INTERACTIONS:
        a, b = rule["pair"]
        if a == b:
            # Duplicate active ingredient check (e.g. Paracetamol + Paracetamol)
            count = sum(1 for g in generic_list if a.lower() in g.lower())
            if count >= 2:
                warnings.append({
                    "pair": [a, a],
                    "type": "duplicate_ingredient",
                    "severity": "high",
                    "message_en": rule.get("message_en", f"Duplicate {a} detected across multiple prescriptions."),
                    "message_hi": rule.get("message_hi", f"एक से अधिक दवाओं में {a} पाया गया है।"),
                    "message_mr": f"एकापेक्षा जास्त औषधांमध्ये {a} हा एकच सक्रिय घटक आढळला आहे (दुहेरी डोसचा धोका).",
                    "action": rule.get("action", "Avoid duplicate doses — consult doctor or pharmacist.")
                })
        else:
            if a in generics and b in generics:
                warnings.append(rule)

    nsaid_hits = [g for g in generics if g in NSAID_GENERICS]
    if len(nsaid_hits) >= 2:
        warnings.append({
            "pair": list(nsaid_hits),
            "type": "multiple_nsaid",
            "severity": "high",
            "message_en": "More than one pain-relief medicine from the same NSAID family was found together.",
            "message_hi": "एक ही तरह (NSAID) की एक से ज़्यादा दर्द निवारक दवाएं साथ मिली हैं।",
            "message_mr": "एकाच प्रकारची (NSAID) एकापेक्षा जास्त वेदनाशामक औषधे एकत्र आढळली आहेत.",
            "action": "Taking multiple NSAIDs together raises stomach and kidney risk — confirm with a pharmacist or doctor."
        })
    return warnings


def categorize_lab_value(test_key, value):
    test = LAB_RANGES.get(test_key)
    if not test:
        return None
    low_cutoff = test.get("low_cutoff")
    if low_cutoff is not None and value < low_cutoff:
        severe = value < low_cutoff * 0.7
        return {
            "category": "low_emergency" if severe else "low",
            "color": "darkred" if severe else "yellow",
            "label_en": test["label_en"], "label_hi": test["label_hi"], "unit": test["unit"],
            "low_flag": True,
        }
    for band in test["bands"]:
        if value <= band["max"]:
            return {
                "category": band["category"], "color": band["color"],
                "label_en": test["label_en"], "label_hi": test["label_hi"], "unit": test["unit"],
                "low_flag": False,
            }
    return None


CATEGORY_TEXT = {
    "low":        {"en": "This is below the normal range (low).", "hi": "यह सामान्य सीमा से कम है।",
                   "next_en": "Eat or drink something sugary now, and mention this to your doctor.",
                   "next_hi": "अभी कुछ मीठा खाएं या पिएं, और डॉक्टर को इस बारे में बताएं।"},
    "low_emergency": {"en": "This is dangerously low.", "hi": "यह खतरनाक रूप से कम है।",
                   "next_en": "Take sugar immediately and seek urgent medical help.",
                   "next_hi": "तुरंत चीनी/मीठा लें और तुरंत मेडिकल मदद लें।"},
    "normal":     {"en": "Within the normal range.", "hi": "यह सामान्य सीमा में है।",
                   "next_en": "No urgent action needed. Keep up your routine follow-up.",
                   "next_hi": "अभी कोई जल्दी कदम नहीं। नियमित जांच जारी रखें।"},
    "borderline": {"en": "Slightly outside the normal range.", "hi": "यह सामान्य सीमा से थोड़ा बाहर है।",
                   "next_en": "Ask your doctor about this at your next routine visit.",
                   "next_hi": "अगली नियमित जांच में डॉक्टर से इस बारे में पूछें।"},
    "high":       {"en": "Clearly outside the normal range.", "hi": "यह सामान्य सीमा से काफी बाहर है।",
                   "next_en": "Please consult a doctor soon — do not change any medicine yourself.",
                   "next_hi": "जल्द डॉक्टर से मिलें — खुद से कोई दवा न बदलें।"},
    "emergency":  {"en": "This value needs urgent medical attention.", "hi": "इस वैल्यू पर तुरंत डॉक्टर से संपर्क ज़रूरी है।",
                   "next_en": "Seek urgent medical help now.", "next_hi": "अभी urgent medical help लें।"},
}


def analyze_vitals(bp, sugar, hr, spo2, chol, creat, gender):
    """Mirrors frontend thresholds exactly, returning markers, red flags and combined risk."""
    markers = []
    red_flags = []
    has_bp_high = has_sugar_high = False

    def mk(name_mr, name_hi, name_en, val, unit, normal, status, exp_mr, exp_hi, exp_en, source):
        return {"name_mr": name_mr, "name_hi": name_hi, "name_en": name_en,
                "val": val, "unit": unit, "normal": normal, "status": status,
                "exp_mr": exp_mr, "exp_hi": exp_hi, "exp_en": exp_en, "source": source}

    if bp:
        m = re.match(r"(\d+)\s*[/\\]\s*(\d+)", bp)
        if m:
            sys_, dia = int(m.group(1)), int(m.group(2))
            status = "normal"
            exp = ("रक्तदाब सामान्य मर्यादेत (< 120/80 mmHg) आहे. हृदय सुरक्षित आहे.",
                   "रक्तचाप सामान्य सीमा (< 120/80 mmHg) में है। हृदय सुरक्षित है।",
                   "Blood pressure is optimal (< 120/80 mmHg).")
            if sys_ >= 180 or dia >= 120:
                status = "red_flag"
                exp = (f"रक्तदाब ({sys_}/{dia} mmHg) धोक्याच्या पातळीवर आहे. तात्काळ हॉस्पिटलमध्ये जा.",
                       f"रक्तचाप ({sys_}/{dia} mmHg) गंभीर खतरे में है। तुरंत आपातकालीन डॉक्टर से मिलें।",
                       f"Critical hypertensive crisis ({sys_}/{dia} mmHg). Seek emergency care.")
                red_flags.append(f"BP Crisis ({sys_}/{dia} mmHg)"); has_bp_high = True
            elif sys_ >= 140 or dia >= 90:
                status = "abnormal"
                exp = ("रक्तदाब वाढलेला आहे (हायपरटेन्शन). डॉक्टरांचा सल्ला घेऊन औषधे सुरू करा.",
                       "रक्तचाप बढ़ा हुआ है। डॉक्टर से मिलकर उपचार शुरू करें।",
                       "High blood pressure (Stage 2 Hypertension). Medical evaluation advised.")
                has_bp_high = True
            elif sys_ >= 120 or dia >= 80:
                status = "elevated"
                exp = ("रक्तदाब किंचित वाढलेला आहे. आहारातील मीठ कमी करा आणि दररोज चाला.",
                       "रक्तचाप थोड़ा बढ़ा हुआ है। नमक कम करें और टहलें।",
                       "Pre-hypertension stage. Reduce sodium intake and monitor.")
            markers.append(mk("रक्तदाब (Blood Pressure)", "रक्तचाप (Blood Pressure)", "Blood Pressure",
                              f"{sys_}/{dia}", "mmHg", "120/80 mmHg", status, *exp, "WHO"))

    if sugar is not None:
        status = "normal"
        exp = ("उपाशीपोटी साखर सामान्य (70-99 mg/dL) आहे.", "खाली पेट शुगर सामान्य सीमा (70-99 mg/dL) में है।",
               "Fasting blood glucose is healthy.")
        if sugar >= 200 or sugar <= 55:
            status = "red_flag"
            exp = (f"साखर ({sugar} mg/dL) अत्यंत धोक्याच्या पातळीवर आहे. लगेच डॉक्टरांना भेटा.",
                   f"शुगर ({sugar} mg/dL) अत्यंत गंभीर स्तर पर है। तुरंत डॉक्टर से संपर्क करें।",
                   f"Critically abnormal glucose ({sugar} mg/dL). Urgent attention needed.")
            red_flags.append(f"Glucose Alert ({sugar} mg/dL)"); has_sugar_high = True
        elif sugar >= 126:
            status = "abnormal"
            exp = ("उपाशीपोटी साखर 126+ mg/dL मधुमेहाचे लक्षण आहे. HbA1c टेस्ट करून डॉक्टरांचा सल्ला घ्या.",
                   "खाली पेट शुगर 126+ mg/dL डायबिटीज का संकेत है। डॉक्टर से परामर्श लें।",
                   "Fasting glucose > 126 mg/dL indicates probable Diabetes.")
            has_sugar_high = True
        elif sugar >= 100:
            status = "elevated"
            exp = ("प्रिडायबिटीज पातळी (100-125 mg/dL). गोड पदार्थ टाळा आणि वजन नियंत्रणात ठेवा.",
                   "प्री-डायबिटीज (100-125 mg/dL)। मीठे से परहेज करें और व्यायाम करें।",
                   "Pre-diabetes range (100-125 mg/dL). Lifestyle modifications indicated.")
        elif sugar < 70:
            status = "elevated"
            exp = (f"साखर ({sugar} mg/dL) सामान्य मर्यादेपेक्षा कमी आहे. काहीतरी गोड खा/प्या आणि डॉक्टरांना कळवा.",
                   f"शुगर ({sugar} mg/dL) सामान्य सीमा से कम है। कुछ मीठा खाएं/पिएं और डॉक्टर को बताएं।",
                   f"Fasting glucose ({sugar} mg/dL) is below the normal range. Eat or drink something sugary and inform your doctor.")
        markers.append(mk("उपाशीपोटी साखर (Fasting Sugar)", "खाली पेट शुगर (Fasting Sugar)", "Fasting Blood Sugar",
                          sugar, "mg/dL", "70-99 mg/dL", status, *exp, "ICMR"))

    if hr is not None:
        status = "normal"
        exp = ("हृदयाचे ठोके सामान्य (60-100 BPM) आहेत.", "हार्ट रेट सामान्य (60-100 BPM) है।", "Resting heart rate is normal.")
        if hr >= 130 or hr <= 45:
            status = "red_flag"
            exp = (f"हृदयाचे ठोके ({hr} BPM) असामान्य वेगाने आहेत. तातडीने ECG करा.",
                   f"हार्ट रेट ({hr} BPM) अत्यधिक तेज/धीमी है। तुरंत ईसीजी कराएं।",
                   f"Critical pulse rate ({hr} BPM). Immediate cardiac evaluation indicated.")
            red_flags.append(f"Pulse Alert ({hr} BPM)")
        elif hr > 100:
            status = "elevated"
            exp = ("हृदयाचे ठोके वाढलेले आहेत (> 100 BPM). विश्रांती घ्या आणि पाणी प्या.",
                   "हार्ट रेट तेज है (> 100 BPM)। तनाव या बुखार हो सकता है।", "Elevated pulse (> 100 BPM). Rest and hydrate.")
        markers.append(mk("हृदयाचे ठोके (Heart Rate)", "हार्ट रेट (Heart Rate)", "Heart Rate",
                          hr, "BPM", "60-100 BPM", status, *exp, "WHO"))

    if spo2 is not None:
        status = "normal"
        exp = ("रक्तातील ऑक्सिजन पातळी उत्तम (95-100%) आहे.", "ऑक्सीजन स्तर सामान्य (95-100%) है।", "Blood oxygen saturation is normal.")
        if spo2 < 90:
            status = "red_flag"
            exp = (f"ऑक्सिजन पातळी ({spo2}%) अत्यंत कमी आहे. त्वरित ऑक्सिजन सपोर्ट व रुग्णालय गाठा.",
                   f"ऑक्सीजन ({spo2}%) गंभीर रूप से कम है। तुरंत ऑक्सीजन सपोर्ट लें।",
                   f"Severe hypoxemia ({spo2}%). Urgent oxygen therapy required.")
            red_flags.append(f"Low Oxygen SpO2 ({spo2}%)")
        elif spo2 < 95:
            status = "abnormal"
            exp = ("ऑक्सिजन पातळी थोडी कमी आहे (90-94%). श्वसनाचा त्रास असल्यास डॉक्टरांना सांगा.",
                   "ऑक्सीजन स्तर हल्का कम है (90-94%)। डॉक्टर की सलाह लें।", "Mildly low oxygen (90-94%). Consult a doctor if breathless.")
        markers.append(mk("SpO2 (ऑक्सिजन पातळी)", "SpO2 (ऑक्सीजन स्तर)", "SpO2 (Blood Oxygen)",
                          spo2, "%", "95-100%", status, *exp, "WHO"))

    if chol is not None:
        status = "normal"
        exp = ("एकूण कोलेस्टेरॉल सामान्य (< 200 mg/dL) आहे.", "कुल कोलेस्ट्रॉल सामान्य (< 200 mg/dL) है।", "Total cholesterol is within a healthy range.")
        if chol >= 280:
            status = "red_flag"
            exp = (f"कोलेस्टेरॉल ({chol} mg/dL) अतिशय जास्त आहे — हृदयविकाराचा गंभीर धोका. डॉक्टरांना भेटा.",
                   f"कोलेस्ट्रॉल ({chol} mg/dL) बहुत अधिक है — हृदय रोग का गंभीर खतरा। डॉक्टर से मिलें।",
                   f"Very high cholesterol ({chol} mg/dL) — serious cardiac risk. See a doctor.")
            red_flags.append(f"Cholesterol Alert ({chol} mg/dL)")
        elif chol >= 240:
            status = "abnormal"
            exp = ("कोलेस्टेरॉल जास्त आहे (240+). आहारात बदल करून तपासणी करा.",
                   "कोलेस्ट्रॉल अधिक है (240+)। आहार में बदलाव कर जांच कराएं।", "High cholesterol (240+). Dietary change and follow-up advised.")
        elif chol >= 200:
            status = "elevated"
            exp = ("कोलेस्टेरॉल किंचित जास्त आहे (200-239). तेलकट पदार्थ कमी करा.",
                   "कोलेस्ट्रॉल थोड़ा अधिक है (200-239)। तली-भुनी चीज़ें कम करें।", "Borderline high cholesterol (200-239). Reduce fried/fatty food.")
        markers.append(mk("कोलेस्टेरॉल (Cholesterol)", "कोलेस्ट्रॉल (Cholesterol)", "Total Cholesterol",
                          chol, "mg/dL", "< 200 mg/dL", status, *exp, "WHO"))

    if creat is not None:
        is_male = gender == "male"
        upper = 1.3 if is_male else 1.1
        lower = 0.7 if is_male else 0.6
        status = "normal"
        exp = (f"किडनीचे कार्य सामान्य आहे (क्रिएटिनिन {lower}-{upper} mg/dL मर्यादेत).",
               f"किडनी कार्य सामान्य है (क्रिएटिनिन {lower}-{upper} mg/dL सीमा में)।",
               f"Kidney function is normal (creatinine within {lower}-{upper} mg/dL).")
        if creat >= 2.5:
            status = "red_flag"
            exp = (f"क्रिएटिनिन ({creat} mg/dL) खूप जास्त — मूत्रपिंडाची गंभीर समस्या असू शकते. त्वरित डॉक्टरांना भेटा.",
                   f"क्रिएटिनिन ({creat} mg/dL) बहुत अधिक — गुर्दे की गंभीर समस्या हो सकती है। तुरंत डॉक्टर से मिलें।",
                   f"Very high creatinine ({creat} mg/dL) — possible serious kidney impairment. See a doctor urgently.")
            red_flags.append(f"Creatinine Alert ({creat} mg/dL)")
        elif creat > upper:
            status = "abnormal"
            exp = (f"क्रिएटिनिन सामान्य मर्यादेपेक्षा जास्त आहे ({creat} mg/dL). किडनी तपासणी करा.",
                   f"क्रिएटिनिन सामान्य सीमा से अधिक है ({creat} mg/dL)। किडनी की जांच कराएं।",
                   f"Creatinine above normal range ({creat} mg/dL). Kidney function test advised.")
        gender_label = ("पुरुष", "पुरुष", "male") if is_male else ("महिला", "महिला", "female")
        markers.append(mk("क्रिएटिनिन (Creatinine)", "क्रिएटिनिन (Creatinine)", "Serum Creatinine",
                          creat, "mg/dL", f"{lower}-{upper} mg/dL ({gender_label[2]})", status, *exp, "NKF"))

    verdict_key = "normal"
    if red_flags:
        verdict_key = "red"
    elif any(m["status"] == "abnormal" for m in markers):
        verdict_key = "abnormal"
    elif any(m["status"] == "elevated" for m in markers):
        verdict_key = "watch"

    return {
        "markers": markers, "red_flags": red_flags, "verdict_key": verdict_key,
        "combined_risk": has_bp_high and has_sugar_high,
    }


def screen_disease_risk(age, gender, bmi_cat, bp_cat, glucose_cat, activity):
    """Rule-based indicative disease risk score for SIH 2026 — with Explainable AI (XAI) factor breakdown."""

    def level(pct):
        return "high" if pct >= 55 else "moderate" if pct >= 30 else "low"

    def impact(pts):
        return "high" if pts >= 20 else "moderate" if pts >= 10 else "low"

    # ---- DIABETES RISK ----
    diab_factors = []
    diab_mitigating = []
    diab_pts = 0

    if age >= 45:
        diab_pts += 20
        diab_factors.append({"factor": "Age ≥ 45", "points": 20, "impact": "high",
            "reason_en": "Age ≥ 45 significantly increases insulin resistance risk (ICMR).",
            "reason_hi": "45+ उम्र में इंसुलिन प्रतिरोध का खतरा काफी बढ़ जाता है।",
            "reason_mr": "वय ४५+ असल्यास इन्सुलिन प्रतिरोधाचा धोका मोठ्या प्रमाणात वाढतो."})
    elif age >= 30:
        diab_pts += 10
        diab_factors.append({"factor": "Age 30–44", "points": 10, "impact": "moderate",
            "reason_en": "Age 30–44 carries a moderate rise in diabetes risk.",
            "reason_hi": "30–44 उम्र में मधुमेह का मध्यम खतरा बढ़ता है।",
            "reason_mr": "वय ३०-४४ मध्ये मधुमेहाचा मध्यम धोका वाढतो."})
    else:
        diab_mitigating.append({"factor": "Young age (< 30)", "impact": "protective",
            "reason_en": "Age < 30 is protective against type 2 diabetes.",
            "reason_hi": "30 से कम उम्र में टाइप 2 मधुमेह का खतरा कम है।",
            "reason_mr": "वय ३० पेक्षा कमी असल्यास टाइप 2 मधुमेहाचा धोका कमी असतो."})

    if bmi_cat == "obese":
        diab_pts += 30
        diab_factors.append({"factor": "Obesity (BMI ≥ 30)", "points": 30, "impact": "high",
            "reason_en": "Obesity is a primary modifiable risk factor for type 2 diabetes (WHO).",
            "reason_hi": "मोटापा टाइप 2 मधुमेह का सबसे बड़ा परिवर्तनीय जोखिम कारक है।",
            "reason_mr": "लठ्ठपणा हा टाइप 2 मधुमेहाचा सर्वात मोठा बदलता येणारा जोखीम घटक आहे."})
    elif bmi_cat == "overweight":
        diab_pts += 15
        diab_factors.append({"factor": "Overweight (BMI 25–29.9)", "points": 15, "impact": "moderate",
            "reason_en": "Overweight increases insulin resistance moderately.",
            "reason_hi": "अधिक वजन इंसुलिन प्रतिरोध को मध्यम स्तर तक बढ़ाता है।",
            "reason_mr": "जास्त वजनामुळे इन्सुलिन प्रतिरोध मध्यम प्रमाणात वाढतो."})
    else:
        diab_mitigating.append({"factor": "Normal BMI", "impact": "protective",
            "reason_en": "Normal body weight lowers diabetes risk.",
            "reason_hi": "सामान्य वजन मधुमेह का खतरा कम करता है।",
            "reason_mr": "सामान्य वजन मधुमेहाचा धोका कमी करते."})

    if glucose_cat == "diabetes":
        diab_pts += 55
        diab_factors.append({"factor": "Fasting Glucose ≥ 126 mg/dL", "points": 55, "impact": "high",
            "reason_en": "High fasting glucose is the strongest direct indicator of diabetes (ICMR/WHO).",
            "reason_hi": "उच्च उपवास ग्लूकोज मधुमेह का सबसे प्रत्यक्ष संकेतक है।",
            "reason_mr": "उच्च उपवास शर्करा हा मधुमेहाचा सर्वात थेट सूचक आहे."})
    elif glucose_cat == "prediabetes":
        diab_pts += 30
        diab_factors.append({"factor": "Prediabetes (Glucose 100–125)", "points": 30, "impact": "high",
            "reason_en": "Prediabetes significantly raises risk of progressing to type 2 diabetes within 5 years.",
            "reason_hi": "प्रिडायबिटीज 5 साल में टाइप 2 मधुमेह बनने का उच्च खतरा है।",
            "reason_mr": "प्रिडायबिटीजमुळे ५ वर्षांत मधुमेह होण्याचा धोका जास्त असतो."})
    else:
        diab_mitigating.append({"factor": "Normal fasting glucose", "impact": "protective",
            "reason_en": "Normal glucose levels are a strong protective factor.",
            "reason_hi": "सामान्य ग्लूकोज स्तर एक मजबूत सुरक्षात्मक कारक है।",
            "reason_mr": "सामान्य साखर पातळी हा एक महत्त्वाचा संरक्षणात्मक घटक आहे."})

    if activity == "sedentary":
        diab_pts += 10
        diab_factors.append({"factor": "Sedentary Lifestyle", "points": 10, "impact": "moderate",
            "reason_en": "Physical inactivity impairs glucose metabolism (ICMR).",
            "reason_hi": "शारीरिक निष्क्रियता ग्लूकोज चयापचय को बाधित करती है।",
            "reason_mr": "शारीरिक हालचाल नसल्यामुळे ग्लुकोज चयापचय बिघडते."})
    elif activity == "moderate":
        diab_pts += 5
        diab_factors.append({"factor": "Moderate Activity", "points": 5, "impact": "low",
            "reason_en": "Moderate activity provides partial metabolic benefit.",
            "reason_hi": "मध्यम गतिविधि आंशिक चयापचय लाभ देती है।",
            "reason_mr": "मध्यम हालचालीमुळे आंशिक चयापचय फायदा मिळतो."})
    else:
        diab_mitigating.append({"factor": "Active Lifestyle", "impact": "protective",
            "reason_en": "Daily physical activity significantly reduces diabetes risk.",
            "reason_hi": "दैनिक व्यायाम मधुमेह के खतरे को काफी कम करता है।",
            "reason_mr": "दररोज व्यायाम केल्याने मधुमेहाचा धोका लक्षणीयरीत्या कमी होतो."})

    diab_pct = min(95, diab_pts)
    diab_modifiable = None
    if bmi_cat in ("obese", "overweight"):
        diab_modifiable = {"action_en": "Losing weight to a normal BMI can reduce diabetes risk by 20–30%.", "action_hi": "सामान्य BMI तक वजन घटाने से मधुमेह का खतरा 20–30% कम हो सकता है।", "action_mr": "वजन सामान्य BMI पर्यंत कमी केल्यास मधुमेहाचा धोका 20–30% कमी होऊ शकतो."}
    elif activity == "sedentary":
        diab_modifiable = {"action_en": "Adding 30 min daily walking can lower risk by ~10%.", "action_hi": "रोज 30 मिनट पैदल चलने से जोखिम ~10% कम हो सकता है।", "action_mr": "दररोज ३० मिनिट चालल्यास धोका ~१०% कमी होऊ शकतो."}

    # ---- HEART CVD RISK ----
    heart_factors = []
    heart_mitigating = []
    heart_pts = 0

    if age >= 55:
        heart_pts += 25
        heart_factors.append({"factor": "Age ≥ 55", "points": 25, "impact": "high",
            "reason_en": "Age ≥ 55 significantly raises cardiovascular disease risk (ESC/WHO).",
            "reason_hi": "55+ उम्र में हृदय रोग का खतरा काफी बढ़ जाता है।",
            "reason_mr": "वय ५५+ असल्यास हृदयविकाराचा धोका मोठ्या प्रमाणात वाढतो."})
    elif age >= 40:
        heart_pts += 12
        heart_factors.append({"factor": "Age 40–54", "points": 12, "impact": "moderate",
            "reason_en": "Age 40–54 starts raising cardiovascular risk.",
            "reason_hi": "40–54 उम्र में हृदय रोग का खतरा बढ़ने लगता है।",
            "reason_mr": "वय ४०-५४ मध्ये हृदयविकाराचा धोका वाढू लागतो."})
    else:
        heart_mitigating.append({"factor": "Young age (< 40)", "impact": "protective",
            "reason_en": "Age < 40 is cardiovascular-protective.",
            "reason_hi": "40 से कम उम्र में हृदय रोग का खतरा कम होता है।",
            "reason_mr": "वय ४० पेक्षा कमी असल्यास हृदयविकाराचा धोका कमी आहे."})

    if bp_cat == "high":
        heart_pts += 35
        heart_factors.append({"factor": "High Blood Pressure (≥ 140 mmHg)", "points": 35, "impact": "high",
            "reason_en": "High BP (hypertension stage 2) is the leading modifiable risk for heart disease (ICMR).",
            "reason_hi": "उच्च रक्तचाप हृदय रोग का सबसे बड़ा परिवर्तनीय कारण है।",
            "reason_mr": "उच्च रक्तदाब हा हृदयविकाराचा सर्वात मोठा बदलता येणारा कारण आहे."})
    elif bp_cat == "elevated":
        heart_pts += 15
        heart_factors.append({"factor": "Elevated Blood Pressure (130–139 mmHg)", "points": 15, "impact": "moderate",
            "reason_en": "Elevated BP places moderate strain on heart arteries.",
            "reason_hi": "बढ़ा हुआ रक्तचाप हृदय धमनियों पर मध्यम दबाव डालता है।",
            "reason_mr": "वाढलेला रक्तदाब हृदयाच्या रक्तवाहिन्यांवर मध्यम ताण आणतो."})
    else:
        heart_mitigating.append({"factor": "Normal Blood Pressure", "impact": "protective",
            "reason_en": "Normal BP protects the heart and arteries.",
            "reason_hi": "सामान्य रक्तचाप हृदय और धमनियों को सुरक्षित रखता है।",
            "reason_mr": "सामान्य रक्तदाब हृदय व रक्तवाहिन्यांचे रक्षण करतो."})

    if bmi_cat == "obese":
        heart_pts += 20
        heart_factors.append({"factor": "Obesity (BMI ≥ 30)", "points": 20, "impact": "high",
            "reason_en": "Obesity increases cardiac workload and promotes atherosclerosis.",
            "reason_hi": "मोटापा दिल पर काम का बोझ बढ़ाता है और धमनियों को सख्त करता है।",
            "reason_mr": "लठ्ठपणामुळे हृदयावर ताण वाढतो व रक्तवाहिन्या कठोर होतात."})
    elif bmi_cat == "overweight":
        heart_pts += 10
        heart_factors.append({"factor": "Overweight (BMI 25–29.9)", "points": 10, "impact": "moderate",
            "reason_en": "Overweight moderately increases cardiovascular risk.",
            "reason_hi": "अधिक वजन हृदय रोग के जोखिम को मध्यम रूप से बढ़ाता है।",
            "reason_mr": "जास्त वजनामुळे हृदयाचा धोका मध्यम प्रमाणात वाढतो."})

    if glucose_cat == "diabetes":
        heart_pts += 15
        heart_factors.append({"factor": "Diabetes", "points": 15, "impact": "high",
            "reason_en": "Diabetes doubles cardiovascular risk through vascular inflammation (ICMR/WHO).",
            "reason_hi": "मधुमेह रक्त वाहिकाओं में सूजन से हृदय रोग का खतरा दोगुना करता है।",
            "reason_mr": "मधुमेहामुळे रक्तवाहिन्यांमध्ये जळजळ होऊन हृदयविकाराचा धोका दुप्पट होतो."})
    elif glucose_cat == "prediabetes":
        heart_pts += 8
        heart_factors.append({"factor": "Prediabetes", "points": 8, "impact": "moderate",
            "reason_en": "Prediabetes causes vascular inflammation that stresses the heart.",
            "reason_hi": "प्रिडायबिटीज रक्त वाहिकाओं में सूजन बढ़ाती है।",
            "reason_mr": "प्रिडायबिटीजमुळे रक्तवाहिन्यांमध्ये जळजळ वाढते."})

    if activity == "sedentary":
        heart_pts += 12
        heart_factors.append({"factor": "Sedentary Lifestyle", "points": 12, "impact": "moderate",
            "reason_en": "Sedentary behavior is an independent risk factor for heart disease (ESC).",
            "reason_hi": "बैठी जीवनशैली हृदय रोग का स्वतंत्र जोखिम कारक है।",
            "reason_mr": "बैठी जीवनशैली हा हृदयविकाराचा स्वतंत्र जोखीम घटक आहे."})
    else:
        heart_mitigating.append({"factor": "Active Lifestyle", "impact": "protective",
            "reason_en": "Regular physical activity significantly reduces CVD risk.",
            "reason_hi": "नियमित व्यायाम हृदय रोग के खतरे को काफी कम करता है।",
            "reason_mr": "नियमित व्यायामामुळे हृदयविकाराचा धोका लक्षणीयरीत्या कमी होतो."})

    heart_pct = min(95, heart_pts)
    heart_modifiable = None
    if bp_cat == "high":
        heart_modifiable = {"action_en": "Reducing BP below 130 mmHg can lower heart risk by ~30%.", "action_hi": "BP को 130 से नीचे लाने से हृदय जोखिम ~30% कम हो सकता है।", "action_mr": "BP १३० खाली आणल्यास हृदयाचा धोका ~३०% कमी होऊ शकतो."}
    elif bmi_cat in ("obese", "overweight"):
        heart_modifiable = {"action_en": "Weight reduction and salt reduction can significantly reduce heart risk.", "action_hi": "वजन और नमक कम करने से हृदय जोखिम काफी घट सकता है।", "action_mr": "वजन व मीठ कमी केल्यास हृदयाचा धोका लक्षणीयरीत्या कमी होतो."}

    # ---- KIDNEY RISK ----
    kidney_factors = []
    kidney_mitigating = []
    kidney_pts = 0

    if bp_cat == "high":
        kidney_pts += 30
        kidney_factors.append({"factor": "High Blood Pressure (≥ 140 mmHg)", "points": 30, "impact": "high",
            "reason_en": "High BP is the second leading cause of chronic kidney disease (ICMR).",
            "reason_hi": "उच्च रक्तचाप पुरानी किडनी रोग का दूसरा प्रमुख कारण है।",
            "reason_mr": "उच्च रक्तदाब हा जुन्या किडनी आजाराचे दुसरे प्रमुख कारण आहे."})
    elif bp_cat == "elevated":
        kidney_pts += 10
        kidney_factors.append({"factor": "Elevated Blood Pressure", "points": 10, "impact": "moderate",
            "reason_en": "Elevated BP strains kidney filtration units over time.",
            "reason_hi": "बढ़ा हुआ रक्तचाप समय के साथ किडनी की छानने की क्षमता को कम करता है।",
            "reason_mr": "वाढलेला रक्तदाब कालांतराने किडनीच्या गाळण्याच्या क्षमतेवर ताण आणतो."})
    else:
        kidney_mitigating.append({"factor": "Normal Blood Pressure", "impact": "protective",
            "reason_en": "Normal BP preserves kidney filtration function.",
            "reason_hi": "सामान्य रक्तचाप किडनी की छानने की क्षमता सुरक्षित रखता है।",
            "reason_mr": "सामान्य रक्तदाब किडनीची गाळण्याची क्षमता टिकवून ठेवतो."})

    if glucose_cat == "diabetes":
        kidney_pts += 35
        kidney_factors.append({"factor": "Diabetes", "points": 35, "impact": "high",
            "reason_en": "Diabetes is the leading cause of kidney failure worldwide (ICMR/WHO).",
            "reason_hi": "मधुमेह दुनिया भर में किडनी विफलता का सबसे बड़ा कारण है।",
            "reason_mr": "मधुमेह हे जगभरात किडनी निकामी होण्याचे सर्वात मोठे कारण आहे."})
    elif glucose_cat == "prediabetes":
        kidney_pts += 10
        kidney_factors.append({"factor": "Prediabetes", "points": 10, "impact": "moderate",
            "reason_en": "Prediabetes begins to impair kidney microvessels.",
            "reason_hi": "प्रिडायबिटीज किडनी की छोटी रक्त वाहिकाओं को नुकसान पहुंचाना शुरू करती है।",
            "reason_mr": "प्रिडायबिटीजमुळे किडनीच्या सूक्ष्म रक्तवाहिन्यांना नुकसान होऊ लागते."})
    else:
        kidney_mitigating.append({"factor": "Normal glucose", "impact": "protective",
            "reason_en": "Normal blood sugar protects kidney microvasculature.",
            "reason_hi": "सामान्य ग्लूकोज किडनी की सूक्ष्म वाहिकाओं की रक्षा करता है।",
            "reason_mr": "सामान्य साखर किडनीच्या सूक्ष्म रक्तवाहिन्यांचे रक्षण करते."})

    if age >= 60:
        kidney_pts += 15
        kidney_factors.append({"factor": "Age ≥ 60", "points": 15, "impact": "moderate",
            "reason_en": "Kidney filtration rate (eGFR) naturally declines after age 60.",
            "reason_hi": "60 के बाद किडनी की छानने की दर (eGFR) स्वाभाविक रूप से कम हो जाती है।",
            "reason_mr": "वय ६० नंतर किडनीची गाळण्याची दर (eGFR) नैसर्गिकरित्या कमी होते."})

    if bmi_cat == "obese":
        kidney_pts += 10
        kidney_factors.append({"factor": "Obesity (BMI ≥ 30)", "points": 10, "impact": "moderate",
            "reason_en": "Obesity increases glomerular hyperfiltration, straining kidneys.",
            "reason_hi": "मोटापा किडनी पर अतिरिक्त छानने का दबाव डालता है।",
            "reason_mr": "लठ्ठपणामुळे किडनीवर अतिरिक्त गाळण्याचा दबाव येतो."})

    kidney_pct = min(95, kidney_pts)
    kidney_modifiable = None
    if glucose_cat == "diabetes":
        kidney_modifiable = {"action_en": "Tight blood sugar control (HbA1c < 7%) can slow kidney damage significantly.", "action_hi": "कड़ा ग्लूकोज नियंत्रण (HbA1c < 7%) किडनी के नुकसान को काफी धीमा कर सकता है।", "action_mr": "साखर नियंत्रण (HbA1c < ७%) किडनीच्या नुकसानास लक्षणीयरीत्या मंद करू शकते."}
    elif bp_cat == "high":
        kidney_modifiable = {"action_en": "BP control below 130/80 mmHg is the most effective kidney protector.", "action_hi": "BP को 130/80 से नीचे रखना किडनी की सबसे प्रभावी सुरक्षा है।", "action_mr": "BP १३०/८० खाली ठेवणे हे किडनीचे सर्वात प्रभावी संरक्षण आहे."}

    return {
        "diabetes": {
            "pct": diab_pct, "level": level(diab_pct),
            "contributing_factors": diab_factors,
            "mitigating_factors": diab_mitigating,
            "modifiable_target": diab_modifiable
        },
        "heart": {
            "pct": heart_pct, "level": level(heart_pct),
            "contributing_factors": heart_factors,
            "mitigating_factors": heart_mitigating,
            "modifiable_target": heart_modifiable
        },
        "kidney": {
            "pct": kidney_pct, "level": level(kidney_pct),
            "contributing_factors": kidney_factors,
            "mitigating_factors": kidney_mitigating,
            "modifiable_target": kidney_modifiable
        },
        "disclaimer": "This percentage is a rule-based indicative score, not a calibrated clinical probability from a trained model.",
    }


# ---------- Routes ----------
@app.route("/")
def index():
    return render_template("index.html")


@app.route("/manifest.json")
def manifest():
    return send_from_directory("static", "manifest.json")


@app.route("/service-worker.js")
def sw():
    resp = send_from_directory("static", "service-worker.js")
    resp.headers["Cache-Control"] = "no-cache"
    return resp


@app.route("/api/medicines", methods=["GET"])
def api_medicines():
    return jsonify(MEDICINES)


@app.route("/api/interactions-data", methods=["GET"])
def api_interactions_data():
    return jsonify(INTERACTIONS)


@app.route("/api/lab-ranges", methods=["GET"])
def api_lab_ranges():
    return jsonify(LAB_RANGES)


@app.route("/api/ocr", methods=["POST"])
def api_ocr():
    """
    Unified OCR endpoint supporting images and PDF documents.
    Applies OpenCV preprocessing, Tesseract multi-pass OCR,
    parses complete structured report details, detects medicines,
    and runs initial safety check.
    """
    if "image" not in request.files:
        return jsonify({"error": "no_image", "detail": "No file uploaded."}), 400
    file = request.files["image"]
    if not file.filename:
        return jsonify({"error": "empty_filename", "detail": "Selected file is empty."}), 400

    filename = file.filename.lower()
    is_pdf = filename.endswith(".pdf") or file.mimetype == "application/pdf"

    tmp_dir = tempfile.mkdtemp(prefix="ahc_")
    try:
        if is_pdf:
            pdf_path = os.path.join(tmp_dir, "doc.pdf")
            file.save(pdf_path)
            result = extract_pdf_data(pdf_path, tmp_dir)
        else:
            raw_path = os.path.join(tmp_dir, "raw.png")
            try:
                img = Image.open(file.stream)
                img = ImageOps.exif_transpose(img)
                img.convert("RGB").save(raw_path)
            except Exception as e:
                return jsonify({"error": "invalid_image", "detail": f"Could not read image file: {str(e)}"}), 400

            result = run_ocr(raw_path)

        full_text = result.get("full_text", "")
        parsed = parse_medical_report(full_text)
        result["parsed_report"] = parsed
        result["detected_medicines"] = parsed["detected_medicines"]

        # Build clean formatted report summary so the human verification textarea displays all extracted details clearly
        meta = parsed.get("metadata", {})
        tests = parsed.get("tests", [])
        presc = parsed.get("prescriptions", [])

        summary_blocks = []
        patient_line = []
        if meta.get("patient_name"):
            patient_line.append(f"PATIENT: {meta['patient_name']}")
        if meta.get("age") or meta.get("gender"):
            age_str = f"{meta['age']}" if meta.get("age") else "?"
            gen_str = 'M' if meta.get("gender") == 'male' else ('F' if meta.get("gender") == 'female' else '')
            demo_str = f"({age_str}/{gen_str})" if gen_str else f"({age_str} yrs)"
            patient_line.append(demo_str)
        if meta.get("date"):
            patient_line.append(f"| DATE: {meta['date']}")
        if patient_line:
            summary_blocks.append(" ".join(patient_line))

        doc_line = []
        if meta.get("hospital_or_lab"):
            doc_line.append(f"LAB/HOSPITAL: {meta['hospital_or_lab']}")
        if meta.get("doctor_name"):
            doc_line.append(f"REF: {meta['doctor_name']}")
        if doc_line:
            summary_blocks.append(" | ".join(doc_line))

        if tests:
            summary_blocks.append("\nLAB PARAMETERS EXTRACTED:")
            for t in tests:
                flag = f" [{t['status'].upper()}]" if t.get('status') not in ('normal', None) else ""
                summary_blocks.append(f"  • {t['name_en']}: {t['value']} {t['unit']}{flag} (Ref: {t['reference_range']})")

        if presc:
            summary_blocks.append("\nPRESCRIPTIONS EXTRACTED:")
            for p in presc:
                summary_blocks.append(f"  • {p['brand']} ({p['generic']}) - {p['dosage']} - {p['frequency_en']}")

        if summary_blocks:
            formatted_summary = "\n".join(summary_blocks)
            result["full_text"] = formatted_summary + ("\n\n--- OCR RAW TEXT ---\n" + full_text if full_text else "")

        # Run safety evaluation if medicines were found
        if parsed["detected_medicines"]:
            profile = {
                "age": parsed["metadata"].get("age"),
                "gender": parsed["metadata"].get("gender"),
                "vitals": {t["key"]: t["value"] for t in parsed.get("tests", [])}
            }
            result["medicine_safety"] = check_medicine_safety(parsed["detected_medicines"], profile)
        else:
            result["medicine_safety"] = None

        return jsonify(result)

    except Exception as exc:
        return jsonify({"error": "ocr_failed", "detail": str(exc)}), 500
    finally:
        # Privacy: delete uploaded/processed temporary files immediately
        shutil.rmtree(tmp_dir, ignore_errors=True)


@app.route("/api/parse-report-text", methods=["POST"])
def api_parse_report_text():
    """
    Parses edited or manually entered OCR text into structured report data
    and updates test values and medicine safety checks.
    """
    payload = request.get_json(force=True, silent=True) or {}
    text = payload.get("text", "")
    profile = payload.get("profile") or {}

    parsed = parse_medical_report(text)
    medicines = parsed["detected_medicines"]

    if profile.get("age"):
        parsed["metadata"]["age"] = profile["age"]
    if profile.get("gender"):
        parsed["metadata"]["gender"] = profile["gender"]

    safety = check_medicine_safety(medicines, profile) if medicines else None
    res = dict(parsed)
    res["parsed_report"] = parsed
    res["detected_medicines"] = medicines
    res["medicine_safety"] = safety
    return jsonify(res)


@app.route("/api/detect-medicines", methods=["POST"])
def api_detect_medicines():
    payload = request.get_json(force=True, silent=True) or {}
    text = payload.get("text", "")
    return jsonify(detect_medicines(text))


@app.route("/api/check-interactions", methods=["POST"])
def api_check_interactions():
    payload = request.get_json(force=True, silent=True) or {}
    generics = payload.get("generics", [])
    warnings = check_interactions(generics)
    if not warnings:
        return jsonify({
            "warnings": [],
            "message_en": "No interaction found in our curated high-risk list. This is not a complete check — please confirm with a pharmacist or doctor.",
            "message_hi": "हमारी curated सूची में कोई ज्ञात interaction नहीं मिला। यह पूरी जांच नहीं है — कृपया pharmacist या डॉक्टर से पुष्टि करें।"
        })
    return jsonify({"warnings": warnings})


@app.route("/api/check-medicine-safety", methods=["POST"])
def api_check_medicine_safety():
    """
    Full clinical medicine safety evaluation including patient age,
    pregnancy, kidney/hypertension/diabetes risks and drug interactions.
    """
    payload = request.get_json(force=True, silent=True) or {}
    meds = payload.get("medicines") or []
    if not meds and payload.get("text"):
        meds = detect_medicines(payload["text"])
    profile = payload.get("profile") or payload
    safety = check_medicine_safety(meds, profile)
    return jsonify(safety)


@app.route("/api/lab-explain", methods=["POST"])
def api_lab_explain():
    payload = request.get_json(force=True, silent=True) or {}
    test_key = (payload.get("test") or "").strip().lower().replace(" ", "_")
    try:
        value = float(payload.get("value"))
    except (TypeError, ValueError):
        return jsonify({"error": "invalid_value"}), 400

    result = categorize_lab_value(test_key, value)
    if not result:
        return jsonify({"error": "unknown_test"}), 404

    cat_text = CATEGORY_TEXT[result["category"]]
    result.update({
        "value": value,
        "explanation_en": cat_text["en"],
        "explanation_hi": cat_text["hi"],
        "next_step_en": cat_text["next_en"],
        "next_step_hi": cat_text["next_hi"],
        "disclaimer": "General adult reference range only — not adjusted for age, pregnancy or existing conditions. Not a diagnosis."
    })
    return jsonify(result)


@app.route("/api/analyze-vitals", methods=["POST"])
def api_analyze_vitals():
    payload = request.get_json(force=True, silent=True) or {}

    def as_float(key):
        v = payload.get(key)
        if v in (None, ""):
            return None
        try:
            return float(v)
        except (TypeError, ValueError):
            return None

    bp = (payload.get("bp") or "").strip()
    result = analyze_vitals(
        bp=bp,
        sugar=as_float("sugar"),
        hr=as_float("hr"),
        spo2=as_float("spo2"),
        chol=as_float("chol"),
        creat=as_float("creat"),
        gender=(payload.get("gender") or "female").strip().lower(),
    )
    return jsonify(result)


@app.route("/api/risk-screen", methods=["POST"])
def api_risk_screen():
    payload = request.get_json(force=True, silent=True) or {}
    try:
        age = int(payload.get("age") or 0)
    except (TypeError, ValueError):
        age = 0
    result = screen_disease_risk(
        age=age,
        gender=(payload.get("gender") or "female").strip().lower(),
        bmi_cat=(payload.get("bmi") or "").strip().lower(),
        bp_cat=(payload.get("bp_cat") or "").strip().lower(),
        glucose_cat=(payload.get("glucose_cat") or "").strip().lower(),
        activity=(payload.get("activity") or "").strip().lower(),
    )
    return jsonify(result)


@app.route("/api/delete-scan", methods=["POST"])
def api_delete_scan():
    return jsonify({"deleted": True})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
