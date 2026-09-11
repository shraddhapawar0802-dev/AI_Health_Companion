import sys
import app

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

print("--- 1. Duplicate Paracetamol Demo ---")
meds1 = app.detect_medicines("Tab Crocin 500mg\nTab Dolo 650mg")
res1 = app.check_medicine_safety(meds1, {})
print("Overall:", res1['overall_safety'])
print("Warnings:", len(res1['pairwise_warnings']))
for w in res1['pairwise_warnings']:
    print(" - Warning:", w['message_en'])
for e in res1['evaluations']:
    print(f" * {e['brand']}: {e['verdict']} -> {e['reasons_en']}")

print("\n--- 2. Multiple Painkillers (NSAID) Demo ---")
meds2 = app.detect_medicines("Tab Brufen 400mg\nTab Voveran 50mg\nTab Zerodol 100mg")
res2 = app.check_medicine_safety(meds2, {})
print("Overall:", res2['overall_safety'])
print("Warnings:", len(res2['pairwise_warnings']))
for w in res2['pairwise_warnings']:
    print(" - Warning:", w['message_en'])

print("\n--- 3. Safe Combination (Losartan + Atorvastatin) ---")
meds3 = app.detect_medicines("Tab Losar 50mg\nTab Atorva 10mg")
res3 = app.check_medicine_safety(meds3, {'age': 45, 'gender': 'male'})
print("Overall (Healthy male 45):", res3['overall_safety'])
for e in res3['evaluations']:
    print(f" * {e['brand']}: {e['verdict']}")

print("\n--- 3b. Safe Combination when Patient is Pregnant ---")
res3b = app.check_medicine_safety(meds3, {'age': 28, 'gender': 'female', 'pregnant': True})
print("Overall (Pregnant female 28):", res3b['overall_safety'])
for e in res3b['evaluations']:
    print(f" * {e['brand']}: {e['verdict']} -> {e['reasons_en']}")

print("\n--- 4. Allergy Check (Augmentin with Penicillin Allergy) ---")
meds4 = app.detect_medicines("Tab Augmentin 625mg")
res4 = app.check_medicine_safety(meds4, {'allergies': ['penicillin']})
print("Overall (Penicillin Allergy):", res4['overall_safety'])
for e in res4['evaluations']:
    print(f" * {e['brand']}: {e['verdict']} -> {e['reasons_en']}")
