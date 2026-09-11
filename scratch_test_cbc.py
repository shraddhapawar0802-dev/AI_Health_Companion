import re

sample_drlogy_ocr_text = """
BIOLOGY PATHOLOGY LAB
Accredited | Satisfying | Qualified
Phone: 0123456789 | Email: info@drlogy.com

Yash M. Patel          Sample Collected At: Room 102
Age: 21 Y / Male       Ref. By: Dr. Hiren Shah
Date: 28-Aug-2026

Complete Blood Count (CBC)
Investigation                  Result    Reference Value   Unit
Primary Sample Type: Blood
HAEMOGLOBIN
Hemoglobin (Hb)                12.5      13.0 - 17.0       g/dL
RBC COUNT
Total RBC count                5.2       4.5 - 5.5         mill/cumm
BLOOD INDICES
Packed Cell Volume (PCV)       37.5      40 - 50           %
Mean Corpuscular Volume (MCV)  87.5      83 - 101          fL
MCH                            27.5      27 - 32           pg
MCHC                           32.5      32.5 - 34.5       g/dL
RDW                            13.5      11.6 - 14.0       %
WBC COUNT
Total WBC count                9000      4000 - 11000      /cumm
DIFFERENTIAL WBC COUNT
Neutrophils                    60        50 - 62           %
Lymphocytes                    32        20 - 40           %
Eosinophils                    3         00 - 06           %
Monocytes                      4         00 - 10           %
Basophils                      1         00 - 02           %
PLATELET COUNT
Platelet Count                 150000    150000 - 410000   /cumm
"""

def prototype_parse_medical_report(raw_text):
    text = raw_text or ""
    lines = [l.strip() for l in text.splitlines() if l.strip()]

    meta = {
        "patient_name": "",
        "age": None,
        "gender": "",
        "date": "",
        "doctor_name": "",
        "hospital_or_lab": "",
        "diagnosis_notes": "",
        "document_type": "lab_report"
    }

    # Document type detection
    is_presc = bool(re.search(r"(?i)\b(rx|prescription|tablet|tab|cap|syrup|capsule|dosage|od|bd|tds|sos|after food|before food)\b", text))
    is_lab = bool(re.search(r"(?i)\b(pathology|laboratory|diagnostic|test name|investigation|specimen|reference range|serum|fasting|hba1c|cbc|lipid|ha?emoglobin|platelet|wbc|rbc)\b", text))
    if is_presc and not is_lab:
        meta["document_type"] = "prescription"
    elif is_presc and is_lab:
        meta["document_type"] = "report_and_prescription"
    else:
        meta["document_type"] = "lab_report"

    # Header / Meta extraction
    for idx, line in enumerate(lines):
        # 1. Hospital / Lab Name
        if not meta["hospital_or_lab"]:
            m_lab = re.search(r"(?i)([A-Za-z0-9\s]{3,40}(?:hospital|clinic|diagnostics?|laboratory|pathology(?:\s*lab)?|lab(?:oratory)?|centre|center))\b", line)
            if m_lab and not any(k in m_lab.group(1).lower() for k in ["primary", "sample", "complete", "investigation"]):
                meta["hospital_or_lab"] = m_lab.group(1).strip()

        # 2. Patient Name
        if not meta["patient_name"]:
            m_name = re.search(r"(?i)(?:patient(?:\s*name)?|pt(?:\s*name)?|name|रुग्ण)\s*[:\-]\s*([A-Za-z\.\s]{2,35}?)(?=\s+(?:age|sex|gender|date|\d|yr|y\b|sample|ref)|$)", line)
            if m_name and m_name.group(1).strip().lower() not in ("name", "patient", "pt", "investigation"):
                meta["patient_name"] = m_name.group(1).strip()
            else:
                # Check for line beginning with Name before "Sample Collected" or "Ref. By" or "Age"
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
            m_doc = re.search(r"(?i)(?:ref(?:\.|\s*by)?|consultant|dr\.|doctor)\s*[:\-]?\s*(?:dr\.)?\s*([A-Za-z\.\s]{3,35})", line)
            if m_doc:
                name_part = m_doc.group(1).strip()
                if not name_part.lower().startswith("dr"):
                    name_part = "Dr. " + name_part
                meta["doctor_name"] = name_part

        # 6. Date
        if not meta["date"]:
            m_date = re.search(r"(?i)(?:date|दिनांक|तारीख)?\s*[:\-]?\s*\b(\d{1,2}[\/\-\.\s](?:[a-zA-Z]{3,9}|\d{1,2})[\/\-\.\s]\d{2,4})\b", line)
            if m_date:
                meta["date"] = m_date.group(1).strip()

    # If patient_name still empty, look at first 6 lines
    if not meta["patient_name"]:
        for line in lines[:8]:
            m = re.match(r"^([A-Z][a-zA-Z\.]+(?:\s+[A-Z][a-zA-Z\.]+){1,3})$", line.strip())
            if m:
                cand = m.group(1).strip()
                if not any(k in cand.lower() for k in ["pathology", "biology", "laboratory", "hospital", "report", "count", "investigation"]):
                    meta["patient_name"] = cand
                    break

    # Comprehensive Tests Catalog
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
        # Complete Blood Count (CBC)
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
        # Platelets
        {
            "key": "platelets",
            "name_en": "Platelet Count", "name_hi": "प्लेटलेट काउंट", "name_mr": "प्लेटलेट्स (Platelets)",
            "unit": "/cumm", "ref": "1,50,000 - 4,10,000 /cumm",
            "pattern": r"(?i)(?:platelet\s*count|platelets|plt)\s*[:\-]?\s*([0-9]{1,3}(?:[,\s]\d{2,3})*(?:\.[0-9]+)?|\d{1,7})",
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
            "key": "creatinine",
            "name_en": "Serum Creatinine", "name_hi": "सीरम क्रिएटिनिन (किडनी)", "name_mr": "क्रिएटिनिन (Serum Creatinine)",
            "unit": "mg/dL", "ref": "0.7 - 1.3 mg/dL",
            "pattern": r"(?i)(?:serum\s*creatinine|creatinine|s\.\s*creat)\s*[:\-]?\s*([0-9]+(?:\.[0-9]+)?)",
            "type": "numeric", "elevated": 1.3, "high": 1.6, "emergency": 2.5
        }
    ]

    parsed_tests = []
    seen_keys = set()

    for t_def in tests_catalog:
        if t_def["key"] in seen_keys:
            continue
        m = re.search(t_def["pattern"], text)
        if not m:
            continue
        raw_val_str = m.group(1).replace(",", "").replace(" ", "").strip()
        try:
            val = float(raw_val_str)
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
            if val <= 15: # in lakhs
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

    # Condition Alerts
    condition_alerts = []
    hb_test = next((t for t in parsed_tests if t["key"] == "hemoglobin"), None)
    if hb_test:
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
                "desc_en": f"Hemoglobin ({hb_val} g/dL) is below the recommended range ({hb_test['reference_range']}). Can cause fatigue and decreased stamina.",
                "desc_hi": f"हीमोग्लोबिन ({hb_val} g/dL) सामान्य सीमा ({hb_test['reference_range']}) से कम है। इससे थकान व कमजोरी हो सकती है।",
                "desc_mr": f"हीमोग्लोबिन ({hb_val} g/dL) सामान्य मर्यादेपेक्षा ({hb_test['reference_range']}) कमी आहे. यामुळे थकवा व अशक्तपणा जाणवू शकतो.",
                "action_en": "Include iron-rich foods (spinach, beetroot, jaggery, lentils, dates) and consult your doctor.",
                "action_hi": "आयरन युक्त आहार लें (पालक, चुकंदर, गुड़, दालें) और डॉक्टर से सलाह लें।",
                "action_mr": "आहारात लोहयुक्त पदार्थ वाढवा (पालक, बीट, गूळ, खजूर, डाळी) आणि डॉक्टरांचा सल्ला घ्या."
            })

    plt_test = next((t for t in parsed_tests if t["key"] == "platelets"), None)
    if plt_test and plt_test["status"] in ("emergency", "borderline", "low"):
        condition_alerts.append({
            "condition": "thrombocytopenia",
            "severity": plt_test["status"],
            "title_en": "Low Platelets Alert (Thrombocytopenia)",
            "title_hi": "कम प्लेटलेट चेतावनी (Thrombocytopenia)",
            "title_mr": "कमी प्लेटलेट्स इशारा (Thrombocytopenia)",
            "desc_en": f"Platelet count ({plt_test['value']} {plt_test['unit']}) is below normal. Monitor for fever or bleeding symptoms.",
            "desc_hi": f"प्लेटलेट काउंट ({plt_test['value']} {plt_test['unit']}) सामान्य से कम है। बुखार या कमजोरी पर ध्यान दें।",
            "desc_mr": f"प्लेटलेट्स संख्या ({plt_test['value']} {plt_test['unit']}) सामान्यपेक्षा कमी आहे. ताप किंवा अशक्तपणा असल्यास त्वरित डॉक्टरांना दाखवा.",
            "action_en": "Consult doctor immediately if associated with fever, dengue symptoms, or unusual bruising.",
            "action_hi": "बुखार या डेंगू के लक्षण होने पर तुरंत डॉक्टर से संपर्क करें।",
            "action_mr": "ताप किंवा डेंग्यू सदृश लक्षणे असल्यास त्वरित डॉक्टरांचा सल्ला घ्या."
        })

    return {
        "metadata": meta,
        "tests": parsed_tests,
        "condition_alerts": condition_alerts
    }

res = prototype_parse_medical_report(sample_drlogy_ocr_text)
print("=== EXTRACTED METADATA ===")
print("Patient Name:", res["metadata"]["patient_name"])
print("Age:", res["metadata"]["age"])
print("Gender:", res["metadata"]["gender"])
print("Doctor:", res["metadata"]["doctor_name"])
print("Lab:", res["metadata"]["hospital_or_lab"])
print("Date:", res["metadata"]["date"])

print("\n=== EXTRACTED TESTS (Total:", len(res["tests"]), ") ===")
for t in res["tests"]:
    print(f"  {t['name_en']}: {t['value']} {t['unit']} [{t['status']}] (Ref: {t['reference_range']})")

print("\n=== CONDITION ALERTS (Total:", len(res["condition_alerts"]), ") ===")
for a in res["condition_alerts"]:
    print(f"  [{a['severity']}] {a['title_en']}: {a['desc_en']}")
