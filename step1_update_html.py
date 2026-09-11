import re
import subprocess
import os

with open("templates/index.html", "r", encoding="utf-8") as f:
    content = f.read()

# 1. Add new CSS before </style>
new_css = """
    .hero-stats-chips { display: flex; flex-wrap: wrap; gap: 8px; justify-content: center; margin: 12px 0 16px; }
    .stat-chip { display: inline-flex; align-items: center; gap: 6px; background: rgba(255,255,255,0.88); border: 1px solid var(--line); padding: 5px 12px; border-radius: 20px; font-size: 0.78rem; color: #334155; font-weight: 500; box-shadow: 0 1px 3px rgba(0,0,0,0.04); }
    .stat-chip i { color: var(--primary); }

    .comp-honest-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(270px, 1fr)); gap: 14px; margin-bottom: 24px; }
    .comp-honest-card { background: white; border: 1px solid var(--line); border-radius: var(--radius-md); padding: 14px 16px; box-shadow: var(--shadow-sm); transition: transform 0.15s; }
    .comp-honest-card:hover { transform: translateY(-1px); box-shadow: var(--shadow-md); }
    .comp-app-head { font-weight: 700; font-size: 0.98rem; color: var(--ink-teal-deep); margin-bottom: 10px; display: flex; align-items: center; gap: 8px; border-bottom: 1px solid #f1f5f9; padding-bottom: 6px; }
    .comp-app-head i { color: var(--primary); }
    .comp-point-row { display: flex; flex-direction: column; gap: 3px; margin-bottom: 8px; font-size: 0.84rem; line-height: 1.4; }
    .badge-pro { display: inline-flex; align-items: center; gap: 5px; color: #166534; font-weight: 700; font-size: 0.78rem; text-transform: uppercase; letter-spacing: 0.03em; }
    .badge-con { display: inline-flex; align-items: center; gap: 5px; color: #991b1b; font-weight: 700; font-size: 0.78rem; text-transform: uppercase; letter-spacing: 0.03em; }
    .comp-point-text { color: #334155; padding-left: 2px; }

    .usp-cards-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 14px; }
    .usp-card { background: white; border: 1px solid var(--line); border-radius: var(--radius-md); padding: 16px 18px; box-shadow: var(--shadow-sm); }
    .usp-card-icon { width: 38px; height: 38px; border-radius: 10px; display: flex; align-items: center; justify-content: center; font-size: 1.1rem; margin-bottom: 10px; }
    .usp-card h4 { font-size: 0.95rem; font-weight: 700; color: var(--ink-teal-deep); margin-bottom: 6px; }
    .usp-card p { font-size: 0.83rem; color: #475569; line-height: 1.45; margin: 0; }

    .usp-closing-box { background: linear-gradient(135deg, #f0fdf4 0%, #f7fee7 100%); border: 1.5px solid #bbf7d0; border-radius: var(--radius-md); padding: 18px 22px; margin-top: 22px; display: flex; align-items: flex-start; gap: 14px; }
    .usp-quote-icon { font-size: 1.5rem; color: #16a34a; flex-shrink: 0; margin-top: 2px; }
    .usp-closing-box p { margin: 0; font-size: 0.95rem; font-weight: 600; color: #14532d; line-height: 1.5; font-style: italic; }

    .jan-aushadhi-box { background: #f0fdf4; border: 1.5px solid #86efac; border-radius: var(--radius-md); padding: 10px 14px; margin-top: 10px; }
    .jan-aushadhi-head { display: flex; justify-content: space-between; align-items: center; font-weight: 700; font-size: 0.85rem; color: #166534; margin-bottom: 6px; flex-wrap: wrap; gap: 6px; }
    .jan-aushadhi-badge { background: #16a34a; color: white; padding: 2px 8px; border-radius: 12px; font-size: 0.72rem; font-weight: 700; }
    .jan-aushadhi-details { display: flex; justify-content: space-between; align-items: center; font-size: 0.82rem; color: #334155; flex-wrap: wrap; gap: 8px; }
    .jan-aushadhi-link { display: inline-flex; align-items: center; gap: 5px; color: #15803d; font-weight: 600; font-size: 0.78rem; text-decoration: underline; text-underline-offset: 2px; }

    .badge-server-verified { display: inline-flex; align-items: center; gap: 5px; background: #ecfdf5; border: 1px solid #a7f3d0; color: #047857; font-size: 0.75rem; font-weight: 700; padding: 3px 10px; border-radius: 20px; text-transform: uppercase; letter-spacing: 0.03em; }
    .scan-quality-warning { background: #fffbeb; border: 1px solid #fde68a; color: #92400e; padding: 10px 14px; border-radius: 8px; font-size: 0.84rem; margin-bottom: 12px; display: none; align-items: center; gap: 8px; }

    #printable-doctor-summary { display: none; }
    @media print {
      body * { visibility: hidden; }
      #printable-doctor-summary, #printable-doctor-summary * { visibility: visible; }
      #printable-doctor-summary {
        display: block !important;
        position: absolute;
        left: 0;
        top: 0;
        width: 100%;
        margin: 0;
        padding: 24px;
        background: white;
        color: #0f172a;
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
      }
    }
  </style>"""

content = content.replace("  </style>", new_css)

# 2. Add hero-stats-chips under hero-sub
hero_stats_html = """    <p class="hero-sub" id="txt-hero-sub">Upload a medical report or prescription to get instant patient-friendly explanations and emergency safety alerts in your language.</p>
    <div class="hero-stats-chips" id="hero-stats-chips">
      <span class="stat-chip"><i class="fa-solid fa-chart-pie"></i> <span id="txt-stat-1">12.4% Rx comprehension rate (Mumbai study)</span></span>
      <span class="stat-chip"><i class="fa-solid fa-heart-pulse"></i> <span id="txt-stat-2">~48% chronic medication non-adherence in India</span></span>
      <span class="stat-chip"><i class="fa-solid fa-shield-halved"></i> <span id="txt-stat-3">DPDP Act 2023 · Zero Retention</span></span>
    </div>"""

content = content.replace('    <p class="hero-sub" id="txt-hero-sub">Upload a medical report or prescription to get instant patient-friendly explanations and emergency safety alerts in your language.</p>', hero_stats_html)

# 3. Add btn-doc-summary next to btn-download
action_btns_old = """            <button type="button" class="action-btn" id="btn-speak" onclick="speakReport()"><i class="fa-solid fa-volume-high"></i> <span id="btn-speak-txt">ऐका (Voice)</span></button>
            <button type="button" class="action-btn" id="btn-download" onclick="downloadPdfReport()"><i class="fa-solid fa-file-pdf"></i> <span id="btn-download-txt">PDF डाऊनलोड करा</span></button>"""

action_btns_new = """            <button type="button" class="action-btn" id="btn-speak" onclick="speakReport()"><i class="fa-solid fa-volume-high"></i> <span id="btn-speak-txt">ऐका (Voice)</span></button>
            <button type="button" class="action-btn" id="btn-download" onclick="downloadPdfReport()"><i class="fa-solid fa-file-pdf"></i> <span id="btn-download-txt">PDF डाऊनलोड करा</span></button>
            <button type="button" class="action-btn" id="btn-doc-summary" onclick="printDoctorSummary()"><i class="fa-solid fa-print"></i> <span id="btn-doc-summary-txt">एक-पानी डॉक्टर समरी (Print Doctor Summary)</span></button>"""

content = content.replace(action_btns_old, action_btns_new)

# 4. Replace tab-compare content completely with the user's honest comparison & differentiators
tab_compare_old = re.search(r'<div id="tab-compare" class="tab-pane">.*?</div>\s*</div>\s*<!-- TAB 4', content, re.DOTALL)
if not tab_compare_old:
    tab_compare_old = re.search(r'<div id="tab-compare" class="tab-pane">.*?</div>\s*</div>\s*</div>\s*<!-- TAB 4', content, re.DOTALL)

tab_compare_new = """<div id="tab-compare" class="tab-pane">
      <div class="card">
        <div class="card-header">
          <div class="card-title"><i class="fa-solid fa-scale-balanced" style="color:var(--primary)"></i> <span id="txt-comp-title">How We Compare</span></div>
        </div>
        <p id="txt-comp-intro" style="color:var(--slate); margin-bottom:20px; font-size:0.95rem; line-height:1.5;">Several AI health apps exist today — here's an honest look at where we stand, and what we're doing differently.</p>

        <!-- Honest Competitor Comparison List -->
        <div class="comp-honest-grid">
          <!-- 1. ReportSaathi -->
          <div class="comp-honest-card">
            <div class="comp-app-head">
              <span class="comp-app-name"><i class="fa-solid fa-file-medical"></i> ReportSaathi</span>
            </div>
            <div class="comp-point-row">
              <span class="badge-pro"><i class="fa-solid fa-circle-check"></i> <span id="lbl-pro-1">What they do well:</span></span>
              <span id="txt-comp-app1-pro" class="comp-point-text">Good multilingual report summaries</span>
            </div>
            <div class="comp-point-row">
              <span class="badge-con"><i class="fa-solid fa-circle-xmark"></i> <span id="lbl-con-1">What's missing:</span></span>
              <span id="txt-comp-app1-con" class="comp-point-text">No generic medicine/cost-saving guidance</span>
            </div>
          </div>

          <!-- 2. DawaAI -->
          <div class="comp-honest-card">
            <div class="comp-app-head">
              <span class="comp-app-name"><i class="fa-solid fa-pills"></i> DawaAI</span>
            </div>
            <div class="comp-point-row">
              <span class="badge-pro"><i class="fa-solid fa-circle-check"></i> <span id="lbl-pro-2">What they do well:</span></span>
              <span id="txt-comp-app2-pro" class="comp-point-text">Strong drug interaction database</span>
            </div>
            <div class="comp-point-row">
              <span class="badge-con"><i class="fa-solid fa-circle-xmark"></i> <span id="lbl-con-2">What's missing:</span></span>
              <span id="txt-comp-app2-con" class="comp-point-text">English-first, limited regional language depth</span>
            </div>
          </div>

          <!-- 3. GoDavaii -->
          <div class="comp-honest-card">
            <div class="comp-app-head">
              <span class="comp-app-name"><i class="fa-solid fa-shield-halved"></i> GoDavaii</span>
            </div>
            <div class="comp-point-row">
              <span class="badge-pro"><i class="fa-solid fa-circle-check"></i> <span id="lbl-pro-3">What they do well:</span></span>
              <span id="txt-comp-app3-pro" class="comp-point-text">On-device privacy, wide language support</span>
            </div>
            <div class="comp-point-row">
              <span class="badge-con"><i class="fa-solid fa-circle-xmark"></i> <span id="lbl-con-3">What's missing:</span></span>
              <span id="txt-comp-app3-con" class="comp-point-text">No focus on affordability or government schemes</span>
            </div>
          </div>

          <!-- 4. AI Prescription Reader apps -->
          <div class="comp-honest-card">
            <div class="comp-app-head">
              <span class="comp-app-name"><i class="fa-solid fa-camera"></i> AI Prescription Reader apps</span>
            </div>
            <div class="comp-point-row">
              <span class="badge-pro"><i class="fa-solid fa-circle-check"></i> <span id="lbl-pro-4">What they do well:</span></span>
              <span id="txt-comp-app4-pro" class="comp-point-text">Good OCR extraction</span>
            </div>
            <div class="comp-point-row">
              <span class="badge-con"><i class="fa-solid fa-circle-xmark"></i> <span id="lbl-con-4">What's missing:</span></span>
              <span id="txt-comp-app4-con" class="comp-point-text">No health-risk alerts or generic alternatives</span>
            </div>
          </div>
        </div>

        <!-- Our Differentiators (USP Section) -->
        <div style="margin-top:28px;">
          <h3 style="font-size:1.15rem; font-weight:700; color:var(--ink-teal-deep); margin-bottom:14px; display:flex; align-items:center; gap:8px;">
            <i class="fa-solid fa-award" style="color:var(--amber)"></i> <span id="txt-usp-heading">Our Differentiators (USP)</span>
          </h3>
          <div class="usp-cards-grid">
            <div class="usp-card">
              <div class="usp-card-icon" style="background:#ecfdf5; color:#059669;"><i class="fa-solid fa-tags"></i></div>
              <h4 id="txt-usp-1-title">"Generic Alternative & Savings Finder"</h4>
              <p id="txt-usp-1-desc">We show cheaper generic salt equivalents for branded medicines and point users to their nearest Jan Aushadhi Kendra (govt. generic medicine store) — no other app in this space currently offers this cost-saving guidance.</p>
            </div>
            <div class="usp-card">
              <div class="usp-card-icon" style="background:#eff6ff; color:#2563eb;"><i class="fa-solid fa-language"></i></div>
              <h4 id="txt-usp-2-title">Deep Hindi & Marathi Support</h4>
              <p id="txt-usp-2-desc">Built for rural and semi-urban Indian users, not just translated UI — designed for real accessibility, not just localization.</p>
            </div>
            <div class="usp-card">
              <div class="usp-card-icon" style="background:#fef3c7; color:#d97706;"><i class="fa-solid fa-graduation-cap"></i></div>
              <h4 id="txt-usp-3-title">Free and Open</h4>
              <p id="txt-usp-3-desc">Built by students for a real civic problem, not a subscription-first product.</p>
            </div>
            <div class="usp-card">
              <div class="usp-card-icon" style="background:#fee2e2; color:#dc2626;"><i class="fa-solid fa-shield-heart"></i></div>
              <h4 id="txt-usp-4-title">Clear, Cautious Safety Design</h4>
              <p id="txt-usp-4-desc">We default to "Consult doctor" instead of falsely reassuring "Safe" when data is uncertain.</p>
            </div>
          </div>
        </div>

        <!-- Closing Line Quote Box -->
        <div class="usp-closing-box">
          <i class="fa-solid fa-quote-left usp-quote-icon"></i>
          <p id="txt-comp-closing">We're not claiming to be the first AI health app — we're building the one that actually helps an Indian family save money and stay safer with their medicines.</p>
        </div>
      </div>
    </div>"""

# Replace in content
start_idx = content.find('<div id="tab-compare" class="tab-pane">')
end_idx = content.find('<!-- TAB 4', start_idx)
if start_idx != -1 and end_idx != -1:
    content = content[:start_idx] + tab_compare_new + "\n\n    " + content[end_idx:]

# 5. Add printable-doctor-summary div right before </body>
printable_div = """  <!-- HIDDEN PRINTABLE ONE-PAGE DOCTOR SUMMARY (Rendered for Window Print) -->
  <div id="printable-doctor-summary"></div>
</body>"""
content = content.replace("</body>", printable_div)

with open("templates/index.html", "w", encoding="utf-8") as f:
    f.write(content)

print("Step 1 of HTML update completed.")
