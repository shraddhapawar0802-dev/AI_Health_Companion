import sys
import app

# Avoid Windows console cp1252 crash
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

text = '''
Dr. R. K. Sharma, MD (Medicine)
City Care Pathology & Diagnostic Centre
Date: 12/08/2026
Patient Name: Ramesh Patel    Age: 52 Y / Male
Diagnosis: Type 2 Diabetes Mellitus with Mild Hypertension

Test Name                Result        Unit         Reference Range
Fasting Blood Sugar      148.0         mg/dL        70 - 99
HbA1c                    7.8           %            < 5.7
Blood Pressure           145/95        mmHg         120/80
Total Cholesterol        225           mg/dL        < 200
Serum Creatinine         1.4           mg/dL        0.7 - 1.3
Hemoglobin               13.8          g/dL         13.0 - 17.0

Rx:
1. Tab Glycomet 500mg - 1-0-1 after food
2. Tab Telma 40mg - 1-0-0 before food
3. Tab Dolo 650mg - SOS for body pain
'''

parsed = app.parse_medical_report(text)
print("Patient:", parsed['metadata']['patient_name'])
print("Age/Gender:", parsed['metadata']['age'], parsed['metadata']['gender'])
print("Doctor:", parsed['metadata']['doctor_name'])
print("Hospital/Lab:", parsed['metadata']['hospital_or_lab'])
print("Diagnosis:", parsed['metadata']['diagnosis_notes'])
print("\nParsed Tests:", len(parsed['tests']))
for t in parsed['tests']:
    print(f" - {t['name_en']}: {t['value']} {t['unit']} (Ref: {t['reference_range']}) -> Status: {t['status']}")

print("\nCondition Alerts:", len(parsed.get('condition_alerts', [])))
for ca in parsed.get('condition_alerts', []):
    print(f" ! [{ca['severity'].upper()}] {ca['title_en']}: {ca['desc_en']}")

print("\nPrescriptions:", len(parsed['prescriptions']))
for p in parsed['prescriptions']:
    print(f" - {p['brand']} ({p['generic']}): {p['dosage']} | {p['frequency_en']}")

safety = app.check_medicine_safety(parsed['detected_medicines'], {
    'age': parsed['metadata']['age'],
    'gender': parsed['metadata']['gender'],
    'vitals': {'sugar': 148, 'creat': 1.4, 'bp': '145/95'}
})

print("\nMedicine Safety Check:")
print("Overall Safety:", safety['overall_safety'])
for e in safety['evaluations']:
    print(f" * {e['brand']} -> Verdict: {e['verdict']} ({e['label_en']} / {e['label_hi']} / {e['label_mr']})")
    print(f"   Reason: {e['reasons_en']}")
    print(f"   Action: {e['action_en']}")
