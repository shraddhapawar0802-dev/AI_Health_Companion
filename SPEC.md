# AI Health Companion (SIH 2026) — Final Specification (SPEC.md)

## 1. Project Overview & Baseline Status
- **Repository Baseline Commit**: `cacf9b0` (Initial working state) + `8bfa933` (app.py syntax verification)
- **Live Reference**: `https://ai-health-companion-mh55.onrender.com`
- **Tech Stack**: Python Flask (Backend), Vanilla HTML/CSS/JavaScript (Frontend). No new framework will be introduced.
- **Preservation Policy**:
  - **Voice Assistant**: The working Voice Assistant (`speakReport`, `speakAloud`, `startVoiceAssistant`, `stopVoiceAssistant`, `onVoiceCommand`, Web Speech API) will **NOT be touched, altered, or removed**.
  - **Existing Features**: OCR pipeline (OpenCV + Tesseract), Dashboard, History, Competitor analysis, and Clinical references remain 100% functional.
  - **Zero Regression**: Every addition runs with automated fallback if server is unreachable.

---

## 2. Exact Files to be Modified / Added

### File 1: [MODIFY] `app.py`
- **Purpose**:
  1. Return enriched `medicine_safety` automatically in `/api/ocr` and `/api/parse-report-text` with pairwise drug-drug interactions, duplicate molecule warnings, and patient contraindications.
  2. Enhance `screen_disease_risk` and `/api/risk-screen` with **Explainable AI (XAI) Risk Factors breakdown**:
     - `contributing_factors`: List of active drivers with points (e.g. `+20 pts`), severity weight, and clinical reason in Marathi, Hindi, and English.
     - `mitigating_factors`: Protective factors (e.g. active lifestyle).
     - `modifiable_target`: Primary recommended change to reduce risk score.
  3. Add severe symptom recognition patterns in clinical notes/impressions (e.g., severe chest pain, radiating arm pain, breathlessness at rest, hemoptysis, stroke FAST signs).

### File 2: [MODIFY] `templates/index.html`
- **Purpose**:
  1. **MedTrace Prescription-Check Merge**:
     - In `renderFullReport()`: Add a dedicated **"MedTrace Rx Safety & Drug Interaction Analysis"** box immediately below extracted prescriptions.
     - Render overall combination status (🚨 HIGH RISK / CONTRAINDICATED, ⚠️ CAUTION, ✅ SAFE), duplicate molecule warning (e.g. Paracetamol overdose risk), multi-NSAID warning, and pairwise interaction cards with mechanism and recommendations.
     - Add 1-click CTA button to sync medicines into the MedTrace tab.
  2. **Explainable Risk Reasoning UI**:
     - In `tab-risk`, replace generic single-line descriptions with an **Explainable Risk Reasoning Breakdown card** for each disease (Diabetes, Heart CVD, Kidney):
       - Visual factor chips with impact tags (🔴 High Contributor, 🟠 Moderate, 🟢 Protective/Normal).
       - Plain-language causal explanation ("Why this score?").
       - Modifiable target guidance in MR, HI, and EN.
     - Update client-side `calculateRisk()` so explainable reasoning works seamlessly offline and during typing preview.
  3. **High-Visibility Red-Flag Emergency Alert Banner**:
     - Upgrade `#emergency-banner` into a prominent, high-contrast pulsing red warning banner.
     - Automatically triggered on critical vitals (BP ≥ 180/120, SpO2 ≤ 89%, Sugar ≤ 55 or ≥ 300, HR > 130 or < 45, Creatinine ≥ 2.5), high-risk drug interactions, or severe clinical symptoms.
     - Display active one-touch emergency call buttons:
       - 📞 `108 रुग्णवाहिका (Call 108 Ambulance)`
       - 📞 `112 राष्ट्रीय आपत्कालीन (Call 112 Emergency)`
       - 🏥 `जवळचे रुग्णालय शोधा (Find Nearest Hospital)`
  4. **Fully Functional Multilingual Toggle (Hindi / Marathi / English)**:
     - Complete `I18N` dictionaries (`mr`, `hi`, `en`) for 100% of UI elements:
       - All form labels, placeholder texts, and section headings.
       - All dropdown `<select>` options: BMI categories, BP categories, Fasting Glucose categories, Activity levels.
       - Explainable Risk Reasoning factor names and descriptions.
       - MedTrace interaction warnings and emergency banner texts.
     - Upgrade `setLanguage(lang)` to dynamically update dropdown options and re-render active reports, medicine checks, and risk screens without resetting user input.

### File 3: [NEW] `test_sih_features.py`
- **Purpose**: Dedicated automated test script to verify:
  1. MedTrace prescription OCR drug interaction detection (duplicate molecules, high-risk pairs).
  2. Disease risk explainability factors and scoring logic.
  3. Red-flag emergency alert trigger conditions.
  4. Trilingual dictionary completeness (verifying no missing keys across `mr`, `hi`, `en`).
  5. Preservation of existing endpoints (`/`, `/api/ocr`, `/api/medicines`, `/api/risk-screen`, etc.).

---

## 3. Step-by-Step Implementation & Verification Plan
1. **Step 1 — Backend updates (`app.py`)**:
   - Implement explainable factors in `screen_disease_risk()` and severe symptom detection.
   - Run `python -m py_compile app.py` and `python test_backend.py`.
2. **Step 2 — Frontend UI updates (`templates/index.html`)**:
   - Add MedTrace prescription safety section to Report view.
   - Add Explainable Risk Reasoning breakdown cards to Health Risk tab.
   - Style and activate High-Visibility Red-Flag Emergency Banner with emergency call buttons.
   - Complete `I18N` dictionaries and dropdown option translations in `setLanguage()`.
   - Ensure all Voice Assistant code remains completely untouched.
3. **Step 3 — Testing & Verification**:
   - Run `python test_sih_features.py`.
   - Test in browser (or via test runner) to confirm Voice Assistant, OCR, and Dashboard work smoothly without errors.
4. **Step 4 — Git Commit & Final Walkthrough**:
   - Commit changes with clear messages.

---

## 4. Rollback Plan
If any step fails or an unexpected error occurs:
- Immediate rollback can be executed using `git reset --hard 8bfa933` to restore the exact clean working state.
