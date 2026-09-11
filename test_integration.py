import sys
import io
import requests
from PIL import Image, ImageDraw, ImageFont

sys.stdout.reconfigure(encoding='utf-8')

BASE_URL = "http://127.0.0.1:5000"

def test_home():
    print("Testing GET / ...")
    r = requests.get(f"{BASE_URL}/")
    assert r.status_code == 200
    assert "AI Health Companion" in r.text
    assert "ocr-raw-text" in r.text
    assert "tab-meds" in r.text
    assert "tab-compare" in r.text
    assert "tab-refs" in r.text
    print("✓ GET / returned 200 and contained all required UI elements.")

def test_medicine_checks():
    print("\nTesting POST /api/check-medicine-safety ...")
    
    # 1. Duplicate paracetamol
    payload1 = {"medicines": ["Dolo 650", "Crocin 500"], "profile": {}}
    r1 = requests.post(f"{BASE_URL}/api/check-medicine-safety", json=payload1)
    assert r1.status_code == 200
    d1 = r1.json()
    assert d1["overall_verdict"] == "consult_doctor"
    assert len(d1.get("warnings", [])) > 0
    print("✓ Duplicate paracetamol correctly flagged as consult_doctor with warnings.")

    # 2. Multiple NSAIDs
    payload2 = {"medicines": ["Brufen 400", "Voveran 50"], "profile": {}}
    r2 = requests.post(f"{BASE_URL}/api/check-medicine-safety", json=payload2)
    assert r2.status_code == 200
    d2 = r2.json()
    assert d2["overall_verdict"] == "consult_doctor"
    print("✓ Multiple NSAIDs correctly flagged as consult_doctor.")

    # 3. Safe combination for normal profile
    payload3 = {"medicines": ["Losar 50", "Atorva 10"], "profile": {"age": 45, "gender": "male"}}
    r3 = requests.post(f"{BASE_URL}/api/check-medicine-safety", json=payload3)
    assert r3.status_code == 200
    d3 = r3.json()
    assert d3["overall_verdict"] == "safe"
    print("✓ Safe combination (Losar + Atorva) correctly flagged as safe for normal adult.")

    # 4. Safe combination when patient is pregnant
    payload4 = {"medicines": ["Losar 50", "Atorva 10"], "profile": {"age": 28, "pregnant": True}}
    r4 = requests.post(f"{BASE_URL}/api/check-medicine-safety", json=payload4)
    assert r4.status_code == 200
    d4 = r4.json()
    assert d4["overall_verdict"] == "consult_doctor"
    assert any("pregnancy" in m.get("reason", "").lower() or "pregnancy" in m.get("reason_mr", "").lower() or "गर्भ" in m.get("reason_mr", "") or "गर्भ" in m.get("reason_hi", "") for m in d4.get("medicines", []))
    print("✓ Pregnancy contraindication correctly flagged for Losar/Atorva.")

    # 5. Penicillin allergy with Augmentin
    payload5 = {"medicines": ["Augmentin 625"], "profile": {"allergies": ["penicillin"]}}
    r5 = requests.post(f"{BASE_URL}/api/check-medicine-safety", json=payload5)
    assert r5.status_code == 200
    d5 = r5.json()
    assert d5["overall_verdict"] == "consult_doctor"
    assert any("penicillin" in m.get("reason", "").lower() for m in d5.get("medicines", []))
    print("✓ Penicillin allergy correctly flagged with Augmentin.")

def test_parse_report_text():
    print("\nTesting POST /api/parse-report-text ...")
    
    # 1. Sugar report
    sugar_text = "Patient: Sunita Deshmukh\nAge: 48 Female\nFasting Blood Sugar: 168 mg/dL\nHbA1c: 8.2 %\nRx: Glycomet 500mg (Metformin)"
    r1 = requests.post(f"{BASE_URL}/api/parse-report-text", json={"text": sugar_text})
    assert r1.status_code == 200
    d1 = r1.json()
    assert d1["metadata"]["patient_name"] == "Sunita Deshmukh"
    assert any(t["key"] == "fasting_sugar" and t["status"] == "high" for t in d1["tests"])
    assert any("sugar" in a["title"].lower() or "diabetes" in a["title"].lower() for a in d1.get("condition_alerts", []))
    print("✓ Fasting Sugar & HbA1c correctly parsed with High Sugar / Diabetes Alert.")

    # 2. BP report
    bp_text = "Patient: Rajesh Kumar\nAge: 56 Male\nBlood Pressure: 165/105 mmHg\nRx: Telma 40mg (Telmisartan)"
    r2 = requests.post(f"{BASE_URL}/api/parse-report-text", json={"text": bp_text})
    assert r2.status_code == 200
    d2 = r2.json()
    assert any(t["key"] in ("bp", "blood_pressure") and t["status"] == "high" for t in d2["tests"])
    assert any("pressure" in a["title"].lower() or "hypertension" in a["title"].lower() for a in d2.get("condition_alerts", []))
    print("✓ High Blood Pressure correctly parsed with Hypertension Alert.")

    # 3. Kidney / Creatinine report
    kidney_text = "Patient: Anita Patil\nAge: 62 Female\nSerum Creatinine: 2.1 mg/dL\nBlood Urea: 55 mg/dL"
    r3 = requests.post(f"{BASE_URL}/api/parse-report-text", json={"text": kidney_text})
    assert r3.status_code == 200
    d3 = r3.json()
    assert any(t["key"] in ("creatinine", "serum_creatinine") and t["status"] == "high" for t in d3["tests"])
    assert any("kidney" in a["title"].lower() or "creatinine" in a["title"].lower() for a in d3.get("condition_alerts", []))
    print("✓ Elevated Creatinine correctly parsed with Kidney Strain Alert.")

def test_ocr_upload():
    print("\nTesting POST /api/ocr ...")
    # Generate a clean image in memory with report text
    img = Image.new('RGB', (800, 400), color=(255, 255, 255))
    d = ImageDraw.Draw(img)
    text = "LAB REPORT\nPatient Name: Amit Joshi\nAge: 42 Male\nFasting Blood Sugar: 145 mg/dL\nSerum Creatinine: 1.1 mg/dL\nRx: Dolo 650"
    d.text((40, 40), text, fill=(0, 0, 0))
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    buf.seek(0)
    
    files = {'image': ('sample_report.png', buf, 'image/png')}
    r = requests.post(f"{BASE_URL}/api/ocr", files=files)
    assert r.status_code == 200
    res = r.json()
    print(f"✓ OCR extracted text length: {len(res.get('full_text', ''))}")
    assert len(res.get("full_text", "")) > 0
    assert "Amit" in res.get("full_text") or "Sugar" in res.get("full_text") or "145" in res.get("full_text") or len(res.get("parsed_report", {}).get("tests", [])) > 0
    print("✓ OCR endpoint extracted and parsed image successfully.")

def test_edge_cases():
    print("\nTesting edge cases...")
    # 1. Empty upload
    r1 = requests.post(f"{BASE_URL}/api/ocr")
    assert r1.status_code == 400
    assert r1.json().get("error") == "no_image"
    print("✓ Handled empty upload without crashing (400 no_image).")

    # 2. Corrupted image file
    files_corrupt = {'image': ('test.png', io.BytesIO(b'NOT AN IMAGE'), 'image/png')}
    r2 = requests.post(f"{BASE_URL}/api/ocr", files=files_corrupt)
    assert r2.status_code == 400
    assert r2.json().get("error") == "invalid_image"
    print("✓ Handled corrupted image gracefully (400 invalid_image).")

    # 3. Delete scan endpoint
    r3 = requests.post(f"{BASE_URL}/api/delete-scan")
    assert r3.status_code == 200
    assert r3.json().get("deleted") is True
    print("✓ Delete scan privacy endpoint confirmed working.")

if __name__ == "__main__":
    test_home()
    test_medicine_checks()
    test_parse_report_text()
    test_ocr_upload()
    test_edge_cases()
    print("\n==========================================")
    print("ALL BACKEND & API INTEGRATION TESTS PASSED 100%!")
    print("==========================================")
