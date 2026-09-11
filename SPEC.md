# AI Health Companion (SIH 2026) — Feature Specification (SPEC.md)

## Overview & Background
This specification defines the 4 requested enhancements for the **AI Health Companion** (SIH 2026) prototype (live at `https://ai-health-companion-mh55.onrender.com/`), ensuring zero regression to existing functional systems (**Voice Assistant is strictly preserved and untouched**, OCR pipeline, SQLite/data stores, and Analytics dashboard remain intact).

---

## 1. Feature 1: MedTrace Prescription-Check & Drug Interaction Pipeline
### Objective
Automatically analyze extracted prescription medicines for dangerous drug-drug interactions, duplicate active molecules, and patient contraindications immediately following OCR or manual entry.

### Changes & Architecture
1. **Prescription OCR to MedTrace Integration**:
   - In `app.py`: `/api/ocr` and `/api/parse-report-text` already detect medicines. Enhance the response to return fully computed `medicine_safety` containing:
     - Pairwise interaction warnings from curated `interactions.json` (severity: high/moderate/low, mechanism, recommendations).
     - Duplicate active ingredient alerts (e.g. Paracetamol overdose risk from Dolo + Crocin).
     - Multi-NSAID alerts (e.g. Brufen + Voveran).
     - Contraindications with patient age, pregnancy, kidney conditions, and allergies.
   - In `templates/index.html`:
     - Inside `renderFullReport(parsedReport, medicineSafety)`: Add a dedicated, beautifully styled **"MedTrace Rx Safety & Drug Interaction Analysis"** block directly underneath the Prescribed Medicines section.
     - Render:
       - **Overall Combination Safety Verdict** (🚨 HIGH RISK / CONTRAINDICATED, ⚠️ CAUTION, ✅ SAFE COMBINATION).
       - **Duplicate Molecule Alerts**: Highlights shared active salts to prevent accidental toxicity.
       - **Pairwise Interaction Cards**: Displays interacting drug pairs, clinical severity badge, interaction mechanism, and clear guidance in the active language (MR/HI/EN).
       - **Interactive CTA**: Button to "Open in MedTrace Lab" with 1-click auto-population into Tab 2 for deep parameter testing.

---

## 2. Feature 2: Explainable Risk Reasoning for Disease Predictions
### Objective
Provide clear, transparent, Explainable AI (XAI) reasoning for all 3 disease risk assessments (Diabetes, Heart CVD, Kidney Health) showing *why* a risk score was assigned and *which* factors contributed.

### Changes & Architecture
1. **Backend Explainability Engine (`app.py`)**:
   - Update `screen_disease_risk(age, gender, bmi_cat, bp_cat, glucose_cat, activity)` to return:
     - `score`: Indicative percentage (0-95%).
     - `level`: low / moderate / high.
     - `contributing_factors`: List of active risk drivers with factor name, point impact (e.g., `+20 pts`), weight (`High` / `Moderate`), and clinical explanation in Marathi, Hindi, and English.
     - `mitigating_factors`: Protective factors (e.g., active lifestyle, normal BMI).
     - `modifiable_target`: The highest-impact modifiable factor (e.g., "Reducing BP below 130 can lower heart risk by ~20%").
2. **Frontend UI Rendering (`templates/index.html`)**:
   - In `tab-risk`, replace static single-line descriptions with an **"Explainable Risk Reasoning" breakdown card**:
     - Visual factor chips with impact badges (🔴 High Impact, 🟠 Moderate Impact, 🟢 Low/Protective).
     - "Why this score?" collapsible or inline reasoning section.
     - Dynamic translation in Marathi, Hindi, and English.
   - Update client-side `calculateRisk()` and backend `/api/risk-screen` to keep both offline on-device and server-verified calculations completely in sync.

---

## 3. Feature 3: High-Visibility Red-Flag Emergency Alert Banner
### Objective
Make red-flag emergency alerts unmissable, prominent, and actionable whenever severe symptoms or critical lab/vital thresholds are detected.

### Changes & Architecture
1. **Critical Clinical Thresholds**:
   - Severe Hypertensive Crisis: Systolic ≥ 180 or Diastolic ≥ 120 mmHg.
   - Critical Hypoglycemia: Blood Glucose ≤ 55 mg/dL.
   - Diabetic Ketoacidosis (DKA) / Hyperglycemic Hyperosmolar Risk: Glucose ≥ 300 mg/dL.
   - Severe Hypoxemia: SpO2 ≤ 89%.
   - Critical Kidney Strain: Creatinine ≥ 2.5 mg/dL.
   - Critical Heart Rate: HR > 130 BPM (Tachycardia) or < 45 BPM (Severe Bradycardia).
   - High-Risk Contraindicated Drug Interaction (e.g., Warfarin + NSAID / dual anticoagulation).
   - Severe Symptoms detected in doctor notes / clinical text (e.g., chest pain radiating to arm/jaw, acute breathlessness at rest, sudden slurred speech / facial drooping, coughing blood).
2. **High-Visibility Emergency Banner UI**:
   - Modern, high-contrast emergency red banner with pulsing warning icon, thick crimson border, and prominent typography.
   - Displays exact detected red flags as distinct highlighted alert badges.
   - Direct Action Protocol: Clear first-aid guidance.
   - **One-Touch Emergency Dialing**:
     - `📞 108 रुग्णवाहिका (Call 108 Ambulance)`
     - `📞 112 राष्ट्रीय आपत्कालीन (Call 112 Emergency)`
     - `🏥 जवळचे आपत्कालीन केंद्र शोधा (Find Emergency Care)`
   - Banner appears prominently at the top of the report and vitals views when triggered, with smooth dismiss or scroll-to action.

---

## 4. Feature 4: Fully Functional Trilingual Toggle (Marathi / Hindi / English)
### Objective
Ensure that switching between Marathi, Hindi, and English instantly translates 100% of UI elements, form labels, select options, placeholders, dynamic result cards, and alert texts.

### Changes & Architecture
1. **Complete `I18N` Dictionary Coverage**:
   - Expand `I18N.mr`, `I18N.hi`, and `I18N.en` to include:
     - Form input labels and placeholder texts.
     - `<select>` options:
       - BMI dropdown (`opt-bmi-norm`, `opt-bmi-over`, `opt-bmi-obese`).
       - Blood pressure categories (`opt-bp-norm`, `opt-bp-ele`, `opt-bp-high`).
       - Fasting glucose categories (`opt-glu-norm`, `opt-glu-pre`, `opt-glu-diab`).
       - Physical activity levels (`opt-act-high`, `opt-act-mod`, `opt-act-low`).
     - Explainable Risk Reasoning factor names, labels, and descriptions.
     - MedTrace prescription interaction headers, warnings, and badges.
     - Emergency red-flag banner headlines, action instructions, and hotlines.
2. **Enhanced `setLanguage(lang)` Function**:
   - Update all static text nodes and innerHTML elements.
   - Dynamically update all `<select>` option texts without resetting user selections.
   - Re-render active results:
     - Re-render parsed report & MedTrace drug interactions in the newly selected language.
     - Re-render disease risk scores & explainable factor breakdowns in the newly selected language.
     - Re-render medicine safety evaluation in the newly selected language.
   - Persist selected language in `localStorage` so user preference is remembered across refreshes.

---

## 5. Non-Negotiable Guardrails (Safety & Stability)
- **Voice Assistant**: The Voice Assistant (`speakReport`, `speakAloud`, `startVoiceAssistant`, `stopVoiceAssistant`, `onVoiceCommand`, speech synthesis/recognition) will **NOT be touched or altered**.
- **Existing OCR & Backend Routes**: OpenCV preprocessing, multi-pass Tesseract OCR, PDF parser, and Flask REST endpoints will remain fully backward-compatible.
- **Offline / On-Device Capability**: All 4 features will support both server-verified responses and graceful in-browser fallback.

---

## Verification Plan
1. **Prescription Drug Interaction Check**: Test with sample prescriptions (e.g. Dolo + Crocin, Brufen + Voveran, Warfarin + Aspirin) to verify duplicate molecule warnings and pairwise interaction cards appear directly on the Report view.
2. **Explainable Risk Reasoning**: Test different age, BMI, BP, glucose, and activity combinations to verify factor points, badges, and plain-language reasoning update dynamically.
3. **Red-Flag Emergency Alert**: Test extreme values (BP 190/110, Glucose 45 mg/dL, SpO2 85%) and verify the high-visibility emergency banner appears with hotlines (108, 112).
4. **Multilingual Switch**: Toggle Marathi, Hindi, and English to verify 100% of labels, dropdown options, and dynamic cards switch smoothly without breaking state.
