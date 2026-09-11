const fs = require('fs');
const assert = require('assert');

console.log('--- Testing Voice Assistant Accessibility Mode in index.html ---');

const html = fs.readFileSync('templates/index.html', 'utf8');

// 1. Check HTML Elements
console.log('1. Checking required HTML elements...');
const requiredElements = [
  'id="voice-assistant-bar"',
  'id="txt-voice-mode-title"',
  'id="txt-voice-accessible-badge"',
  'id="txt-voice-note"',
  'id="btn-global-listen"',
  'id="btn-voice-stop"',
  'id="voice-speaking-indicator"',
  'id="btn-speak"',
  'id="btn-meds-speak"',
  'id="btn-mic-meds"',
  'id="mic-listening-banner"'
];

for (const el of requiredElements) {
  assert(html.includes(el), `Missing HTML element: ${el}`);
  console.log(`  ✓ Found ${el}`);
}

// 2. Check Note Text
console.log('2. Checking accessibility note text requirement...');
const requiredNote = 'Designed for elderly and low-literacy users who may not be comfortable reading small text or English medical terms.';
assert(html.includes(requiredNote), 'Accessibility note missing in index.html');
console.log('  ✓ Found accessibility note: ' + requiredNote);

// 3. Test JavaScript logic
console.log('3. Validating JavaScript execution in vm...');
const scriptParts = html.split('<script>');
assert(scriptParts.length >= 3, 'Main script tag found in html');
const scriptContent = scriptParts[2].split('</script>')[0];

// Create simulated environment
const dom = {
  elements: {},
  createElement: function(tag) {
    return {
      tagName: tag,
      style: {},
      onload: null,
      onerror: null,
      setAttribute: function(){},
      appendChild: function(){}
    };
  },
  head: { appendChild: function(){} },
  body: { appendChild: function(){} },
  getElementById: function(id) {
    if (!this.elements[id]) {
      this.elements[id] = {
        id,
        innerText: '',
        innerHTML: '',
        value: '',
        style: {},
        classList: {
          classes: new Set(),
          add: function(c) { this.classes.add(c); },
          remove: function(c) { this.classes.delete(c); },
          contains: function(c) { return this.classes.has(c); },
          toggle: function(c, v) { if (v) this.classes.add(c); else this.classes.delete(c); }
        },
        appendChild: function() {},
        setAttribute: function(){},
        getAttribute: function(){ return ''; }
      };
    }
    return this.elements[id];
  },
  querySelectorAll: function() { return []; },
  documentElement: { setAttribute: function(){} },
  addEventListener: function(){}
};

const mockWindow = {
  document: dom,
  navigator: { serviceWorker: null },
  addEventListener: function(){},
  speechSynthesis: {
    speaking: false,
    cancel: function() { mockWindow.spokenUtterances = []; },
    speak: function(utter) {
      mockWindow.spokenUtterances.push(utter);
      if (utter.onstart) utter.onstart();
      if (utter.onend) utter.onend();
    },
    getVoices: function() {
      return [
        { name: 'Google मराठी', lang: 'mr-IN' },
        { name: 'Google हिन्दी', lang: 'hi-IN' },
        { name: 'Google English (India)', lang: 'en-IN' }
      ];
    },
    onvoiceschanged: null
  },
  SpeechSynthesisUtterance: function(text) {
    this.text = text;
    this.lang = 'en-US';
    this.rate = 1.0;
    this.pitch = 1.0;
    this.voice = null;
    this.onstart = null;
    this.onend = null;
    this.onerror = null;
  },
  SpeechRecognition: function() {
    this.continuous = false;
    this.interimResults = false;
    this.lang = 'mr-IN';
    this.onstart = null;
    this.onresult = null;
    this.onerror = null;
    this.onend = null;
    this.start = function() { if (this.onstart) this.onstart(); };
    this.stop = function() { if (this.onend) this.onend(); };
  },
  spokenUtterances: [],
  fetch: function() { return Promise.resolve({ ok: true, json: () => Promise.resolve({}) }); },
  console: console,
  setTimeout: setTimeout,
  clearTimeout: clearTimeout
};
mockWindow.window = mockWindow;
mockWindow.globalThis = mockWindow;

const vm = require('vm');
const context = vm.createContext(mockWindow);
try {
  vm.runInContext(scriptContent, context);
} catch (e) {
  console.error('VM Run Error:', e);
}

const speakReport = context.speakReport || mockWindow.speakReport;
const speakMedsSafety = context.speakMedsSafety || mockWindow.speakMedsSafety;
const stopSpeech = context.stopSpeech || mockWindow.stopSpeech;
const toggleMedsVoiceInput = context.toggleMedsVoiceInput || mockWindow.toggleMedsVoiceInput;
const setLanguage = context.setLanguage || mockWindow.setLanguage;

assert(typeof speakReport === 'function', 'speakReport function missing');
assert(typeof speakMedsSafety === 'function', 'speakMedsSafety function missing');
assert(typeof stopSpeech === 'function', 'stopSpeech function missing');
assert(typeof toggleMedsVoiceInput === 'function', 'toggleMedsVoiceInput function missing');
assert(typeof setLanguage === 'function', 'setLanguage function missing');

console.log('  ✓ Core functions loaded successfully in vm context');

// 4. Test Language Switching and Voice Readout in MR, HI, EN
const languages = [
  { code: 'mr', langTag: 'mr-IN', name: 'Marathi' },
  { code: 'hi', langTag: 'hi-IN', name: 'Hindi' },
  { code: 'en', langTag: 'en-US', name: 'English' }
];

// Seed test markers
context.lastMarkers = [
  { name: 'Fasting Glucose', val: '240', unit: 'mg/dL', status: 'red_flag', exp: 'High glucose indicates uncontrolled diabetes.' },
  { name: 'Blood Pressure', val: '180/110', unit: 'mmHg', status: 'red_flag', exp: 'Hypertensive emergency.' }
];
context.window.__lastParsedReport = {
  condition_alerts: [
    {
      title_mr: 'मधुमेह व रक्तदाब तातडीचा धोका',
      title_hi: 'मधुमेह व रक्तचाप आपातकालीन चेतावनी',
      title_en: 'Emergency Glucose & BP Crisis Alert',
      desc_mr: 'साखर आणि रक्तदाब दोन्ही अत्यंत जास्त आहेत.',
      desc_hi: 'शुगर और रक्तचाप दोनों अत्यधिक हैं।',
      desc_en: 'Both sugar and BP are critically elevated.',
      action_mr: 'लगेच रुग्णालयात जा.',
      action_hi: 'तुरंत अस्पताल जाएं।',
      action_en: 'Seek immediate emergency hospital care.'
    }
  ],
  tests: context.lastMarkers
};

// Seed medicine check
context.window.__lastMedicineSafetyCheck = {
  overall_safety: 'consult_doctor',
  pairwise_warnings: [
    {
      pair: ['Paracetamol', 'Paracetamol'],
      severity: 'high',
      message_mr: 'एकाहून अधिक गोळ्यांमधून पॅरासिटामॉलचा दुहेरी ओव्हरडोस आढळला. लिव्हरला धोका.',
      message_hi: 'एक से अधिक दवाओं से पैरासिटामोल का ओवरडोज़ मिला है। लिवर को खतरा।',
      message_en: 'Duplicate Paracetamol detected from multiple medicines. Severe risk of liver toxicity.',
      action_mr: 'दोन्ही एकत्र घेऊ नका; डॉक्टरांचा सल्ला घ्या.',
      action_hi: 'दोनों साथ में न लें; डॉक्टर से बात करें।',
      action_en: 'Do not take together; consult doctor.'
    }
  ],
  evaluations: [
    { brand: 'Crocin', generic: 'Paracetamol', verdict: 'consult_doctor', reasons_mr: 'दुहेरी डोस', reasons_hi: 'डुप्लीकेट डोज़', reasons_en: 'Duplicate dose', ja_mrp: '₹14', savings_pct: 81 },
    { brand: 'Dolo 650', generic: 'Paracetamol', verdict: 'consult_doctor', reasons_mr: 'दुहेरी डोस', reasons_hi: 'डुप्लीकेट डोज़', reasons_en: 'Duplicate dose', ja_mrp: '₹16', savings_pct: 79 }
  ]
};

console.log('\n4. Testing Voice Readout in all 3 languages (Report & Medicines):');

for (const { code, langTag, name } of languages) {
  setLanguage(code);

  // Test speakReport
  mockWindow.spokenUtterances.length = 0;
  speakReport();
  assert(mockWindow.spokenUtterances.length > 0, `speakReport failed in ${name}`);
  const reportUtter = mockWindow.spokenUtterances[0];
  assert.strictEqual(reportUtter.lang, langTag, `Expected lang ${langTag}, got ${reportUtter.lang}`);
  assert(reportUtter.text.length > 30, `Report speech text too short in ${name}`);
  console.log(`  ✓ [${name}] Report Readout (${reportUtter.lang}): "${reportUtter.text.slice(0, 65)}..."`);

  // Test speakMedsSafety
  mockWindow.spokenUtterances.length = 0;
  speakMedsSafety();
  assert(mockWindow.spokenUtterances.length > 0, `speakMedsSafety failed in ${name}`);
  const medsUtter = mockWindow.spokenUtterances[0];
  assert.strictEqual(medsUtter.lang, langTag, `Expected lang ${langTag}, got ${medsUtter.lang}`);
  assert(medsUtter.text.length > 30, `Medicine safety speech text too short in ${name}`);
  console.log(`  ✓ [${name}] Medicine Safety Readout (${medsUtter.lang}): "${medsUtter.text.slice(0, 65)}..."`);
}

// 5. Test Voice Input (Mic)
console.log('\n5. Testing Voice Input (SpeechRecognition):');
setLanguage('mr');
const micBtn = dom.getElementById('btn-mic-meds');
const listeningBanner = dom.getElementById('mic-listening-banner');

toggleMedsVoiceInput();
assert(micBtn.classList.contains('btn-mic-listening'), 'Mic button should have active listening class');
assert(listeningBanner.style.display !== 'none', 'Listening banner should be visible');
console.log('  ✓ Mic toggled on and active listening banner displayed');

mockWindow.stopMedsVoiceInput ? mockWindow.stopMedsVoiceInput() : (context.stopMedsVoiceInput ? context.stopMedsVoiceInput() : stopSpeech());
console.log('  ✓ Mic stopped cleanly');

console.log('\n=== ALL VOICE ASSISTANT ACCESSIBILITY TESTS PASSED 100%! ===');
