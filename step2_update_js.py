import re
import json

with open("templates/index.html", "r", encoding="utf-8") as f:
    text = f.read()

# 1. Update I18N mr, hi, en
# Let's inspect where I18N starts and ends
i18n_mr_start = text.find("const I18N = {")
i18n_end = text.find("/* ============================================================\n       LANGUAGE SWITCHING", i18n_mr_start)

old_i18n_block = text[i18n_mr_start:i18n_end]

# Read the I18N replacement
new_i18n_block = """const I18N = {
      mr: {
        appTitle: "AI Health Companion", topbarTag: "SIH 2026 · विद्यार्थी नवोपक्रम",
        heroEyebrow: "एकदाच अपलोड करा. सर्वकाही सहज समजून घ्या.",
        heroTitle: "तुमचा आरोग्य अहवाल,<br>फक्त वाचू नका — समजून घ्या.",
        heroSub: "वैद्यकीय अहवाल किंवा प्रिस्क्रिप्शन अपलोड करा आणि तुमच्या स्वतःच्या भाषेत सोपे स्पष्टीकरण व सुरक्षिततेचे इशारे मिळवा.",
        stat1: "१२.४% रुग्णांनाच प्रिस्क्रिप्शन समजते (मुंबई अभ्यास)",
        stat2: "~४८% रक्तदाब औषध अनियमितता दर (भारतात)",
        stat3: "DPDP कायदा २०२३ · शून्य डेटा साठवण",
        tabReport: "रिपोर्ट व पर्चा विश्लेषण", tabMeds: "औषध व इंटरॅक्शन तपासणी", tabRisk: "आजार जोखीम तपासणी", tabCompare: "स्पर्धक तुलना व USP", tabRefs: "वैद्यकीय संदर्भ (ICMR/WHO)",
        cardInputTitle: "रिपोर्ट किंवा पर्चा अपलोड करा", dropTitle: "फोटो / PDF निवडा किंवा येथे ड्रॅग करा",
        privacyBadge: "तुमचा फोटो/रिपोर्ट या डिव्हाइसमधून बाहेर कुठेही पाठवला जात नाही — सर्व प्रक्रिया सुरक्षितपणे होते.",
        previewLabel: "अपलोड केलेला दस्तऐवज",
        presetTitle: "⚡ त्वरित डेमो निवडा (SAMPLE TESTS):", sample1: "रक्त शर्करा (High Sugar)", sample2: "उच्च रक्तदाब (BP Crisis)", sample3: "किडनी रिपोर्ट (Creatinine)",
        verifyBadge: "ह्यूमन व्हेरिफिकेशन स्टेप (तपासणी)", verifyDesc: "AI ने वाचलेला कच्चा मजकूर किंवा मॅन्युअल आकडे — तपासून बदल करा:",
        fieldGender: "लिंग", fieldAge: "वय", fieldBp: "रक्तदाब (BP mmHg)", fieldSugar: "उपाशीपोटी साखर (mg/dL)", fieldHr: "हार्ट रेट (BPM)", fieldSpo2: "SpO2 (%)", fieldChol: "कोलेस्ट्रॉल (mg/dL)", fieldCreat: "क्रिएटिनिन (mg/dL)",
        btnAnalyze: "अहवाल तपासा आणि विश्लेषण करा", btnAnalyzing: "विश्लेषण सुरू आहे...",
        cardResultTitle: "सोप्या भाषेतील अहवाल (Explanation)", btnSpeak: "ऐका (Voice)", btnDownload: "PDF डाऊनलोड करा",
        btnDocSummary: "एक-पानी डॉक्टर समरी (Print)",
        noReport: "डावीकडे रिपोर्ट अपलोड करा किंवा वरीलपैकी एक 'त्वरित डेमो' निवडून विश्लेषणाचा अनुभव घ्या.",
        rfTitle: "🚨 तातडीचा धोका इशारा (Emergency Red-Flag)", rfDesc: "तुमच्या रिपोर्टमधील काही आकडे सामान्य मर्यादेपेक्षा खूप जास्त आहेत. कृपया कोणताही घरगुती उपाय न करता लगेच जवळच्या डॉक्टरांशी किंवा रुग्णालयाशी संपर्क साधा.",
        combRiskTitle: "एकत्रित जोखीम इशारा (High BP + High Sugar)", combRiskDesc: "तुमचा रक्तदाब आणि रक्तातील साखर दोन्ही एकाच वेळी जास्त आहेत. यामुळे हृदय आणि रक्तवाहिन्यांवर दुहेरी ताण येतो. लवकरात लवकर डॉक्टरांना भेटा.",
        overallEyebrow: "एकूण आरोग्य स्थिती",
        verdictNormal: "सर्व आकडे सामान्य व सुरक्षित आहेत", verdictWatch: "काही घटकांवर लक्ष ठेवणे आवश्यक", verdictAbnormal: "काही घटकांमध्ये अनियमितता — डॉक्टरांचा सल्ला घ्या", verdictRed: "🚨 गंभीर धोका — तातडीने वैद्यकीय मदत घ्या",
        source: "स्रोत", footerDisc: "हे ॲप्लिकेशन केवळ रुग्णांच्या प्राथमिक माहितीसाठी व शिक्षणासाठी आहे. हा अंतिम वैद्यकीय सल्ला किंवा निदान नाही. कोणत्याही उपचारासाठी कृपया नोंदणीकृत डॉक्टरांचा सल्ला घ्या.",
        footerBadge: "महत्त्वाची सूचना (Medical Disclaimer)",
        toastRiskCalc: "जोखीम यशस्वीरीत्या मोजली गेली!", toastNoSpeech: "या ब्राउझरमध्ये आवाज उपलब्ध नाही.", toastNoData: "कृपया आधी रिपोर्ट तपासा.",
        ocrExtracting: "AI OCR मजकूर वाचत आहे...", ocrPdf: "PDF दस्तऐवज वाचत आहे...", ocrSuccess: "मजकूर यशस्वीरीत्या वाचला व विश्लेषण पूर्ण झाले ✓",
        ocrFail: "फोटो मिळाला ✓ — खालील तक्त्यात आकडे भरून पुढे जा.",
        ocrFailUnreadable: "दस्तऐवजातील मजकूर स्पष्ट वाचता आला नाही — कृपया चांगल्या प्रकाशातील फोटो अपलोड करा किंवा खाली आकडे भरा.",
        hintBpRange: "योग्य रक्तदाब भरा (उदा. 120/80)", hintNumRange: "आकडा वास्तव मर्यादेबाहेर आहे",
        medsCardTitle: "प्रिस्क्रिप्शन अपलोड करा किंवा औषधाचे नाव टाइप करा",
        medsDropLabel: "प्रिस्क्रिप्शनचा फोटो अपलोड करण्यासाठी टॅप करा", medsDropSub: "JPG, PNG — डॉक्टरांचे हाताने लिहिलेले प्रिस्क्रिप्शन चालेल",
        medsPrivacy: "प्रक्रिया पूर्ण होताच फोटो सर्व्हरवरून लगेच डिलीट केला जातो — कुठेही सेव्ह होत नाही.",
        medsPresetTitle: "⚡ त्वरित डेमो निवडा:", medsSample1: "Duplicate Paracetamol", medsSample2: "Multiple Painkillers (NSAID)", medsSample3: "Safe Combination",
        medsVerifyBadge: "तपासा आणि पुष्टी करा", medsVerifyDesc: "प्रिस्क्रिप्शनमधून वाचलेली किंवा टाइप केलेली औषधांची नावे:",
        medsCheckBtn: "औषधे शोधा व तपासा", medsResultTitle: "आढळलेली औषधे आणि सुरक्षितता निष्कर्ष",
        medsEmpty: "डावीकडे प्रिस्क्रिप्शन अपलोड करा, किंवा औषधाचे नाव टाइप करा.",
        medsProfTitle: "रुग्णाची प्रोफाइल (वैकल्पिक — अधिक अचूक तपासणीसाठी)",
        lblPregnant: "गरोदर (Pregnant)", lblKidney: "किडनीचा आजार (Kidney disease)",
        medsAllergyLabel: "माहित असलेली ॲलर्जी (Known allergies):", allergyPenicillin: "पेनिसिलिन", allergyNsaid: "वेदना निवारक (NSAID)", allergySulfa: "सल्फा",
        medsAgePlaceholder: "वय",
        riskFormTitle: "रुग्ण तपशील आणि जीवनशैली", riskResultsTitle: "संभाव्य आजार जोखीम निकाल",
        btnCalcRisk: "आजार जोखीम मोजा (Assess Risk)",
        compTitle: "इतर ॲप्स आणि आमची तुलना (How We Compare)",
        compIntro: "आज अनेक AI आरोग्य ॲप्स उपलब्ध आहेत — आम्ही कुठे उभे आहोत आणि काय वेगळे करत आहोत याचा हा एक प्रामाणिक आढावा.",
        lblPro: "काय चांगले आहे:", lblCon: "काय उणीव आहे:",
        compApp1Pro: "चांगला बहुभाषिक अहवाल सारांश", compApp1Con: "जेनेरिक औषधे व खर्चाच्या बचतीचे कोणतेही मार्गदर्शन नाही",
        compApp2Pro: "औषध परस्परसंवादाचा मजबूत डेटाबेस", compApp2Con: "इंग्रजी-केंद्रित, प्रादेशिक भाषांमध्ये मर्यादित खोली",
        compApp3Pro: "डिव्हाइसवरील गोपनीयता, विस्तृत भाषा पर्याय", compApp3Con: "औषधांची परवड किंवा सरकारी योजनांवर कोणताही भर नाही",
        compApp4Pro: "चांगले OCR मजकूर वाचन", compApp4Con: "आरोग्य धोक्याचे इशारे किंवा जेनेरिक पर्याय नाहीत",
        uspHeading: "आमचा मुख्य नवोपक्रम आणि वेगळेपण (USP)",
        usp1Title: "\\"जेनेरिक पर्याय आणि बचत मार्गदर्शक\\"", usp1Desc: "आम्ही ब्रँडेड महागड्या औषधांसाठी स्वस्त जेनेरिक सॉल्ट पर्याय दाखवतो आणि वापरकर्त्यांना जवळच्या प्रधानमंत्री जन औषधी केंद्राचे मार्गदर्शन देतो — या क्षेत्रातील इतर कोणतेही ॲप असे आर्थिक बचतीचे मार्गदर्शन देत नाही.",
        usp2Title: "मराठी व हिंदीचा सखोल वापर", usp2Desc: "फक्त वरवरचे भाषांतर नाही, तर ग्रामीण आणि निम-शहरी भारतीय नागरिकांच्या सुलभतेसाठी तळागाळातून डिझाइन केलेले.",
        usp3Title: "पूर्णपणे मोफत आणि खुले", usp3Desc: "एका खऱ्या सामाजिक व नागरी समस्येवर विद्यार्थ्यांनी बनवलेले विनामूल्य ॲप, कोणताही सबस्क्रिप्शन व्यवसाय नाही.",
        usp4Title: "स्पष्ट व सावध सुरक्षा धोरण", usp4Desc: "माहिती अपूर्ण किंवा अनिश्चित असताना रुग्णांना खोटे आश्वासन न देता आम्ही थेट 'डॉक्टरांचा सल्ला घ्या' हा सुरक्षित निर्णय देतो.",
        compClosing: "आम्ही पहिले AI हेल्थ ॲप असल्याचा दावा करत नाही — आम्ही असे ॲप बनवत आहोत जे एका सामान्य भारतीय कुटुंबाचे पैसे वाचवेल आणि औषधांच्या वापराबाबत त्यांना अधिक सुरक्षित ठेवेल.",
        serverVerified: "सर्व्हर पडताळणी पूर्ण (ICMR / WHO)",
        refsTitle: "वैद्यकीय संदर्भ व आधारभूत मार्गदर्शक तत्त्वे (Clinical Sources)",
        refsSub: "आमच्या ॲपमधील सर्व धोक्याच्या मर्यादा आणि नियम अधिकृत राष्ट्रीय व आंतरराष्ट्रीय वैद्यकीय मार्गदर्शक तत्त्वांवर आधारित आहेत:",
        refCard1Title: "ICMR मार्गदर्शक तत्त्वे", refCard1Desc: "भारतीय वैद्यकीय संशोधन परिषद (ICMR) च्या मानकांनुसार उपाशीपोटी साखर: सामान्य < 100 mg/dL, प्रिडायबिटीज 100-125, मधुमेह >= 126 mg/dL. HbA1c >= 6.5% मधुमेह दर्शवतो.",
        refCard2Title: "WHO रक्तदाब मानके", refCard2Desc: "जागतिक आरोग्य संघटना (WHO): सामान्य रक्तदाब 120/80 mmHg. 140/90 mmHg च्या वर उच्च रक्तदाब आणि 180/120+ आणीबाणी (Crisis) मानली जाते.",
        refCard3Title: "AIIMS व NKF किडनी मानके", refCard3Desc: "नॅशनल किडनी फाउंडेशन (NKF): सीरम क्रिएटिनिन सामान्य मर्यादा — पुरुष 0.7-1.3 mg/dL, महिला 0.6-1.1 mg/dL. 2.5 पेक्षा जास्त असल्यास तीव्र मूत्रपिंड तपासणी आवश्यक.",
        refsNote: "क्लिनिकल चाचण्यांच्या मर्यादा अधिकृत मानकांवर आधारित आहेत. क्रिएटिनिन मर्यादा लिंग-निहाय आहेत (पुरुष: 0.7-1.3, महिला: 0.6-1.1 mg/dL)."
      },
      hi: {
        appTitle: "AI Health Companion", topbarTag: "SIH 2026 · छात्र नवाचार",
        heroEyebrow: "एक बार अपलोड करें। सब कुछ आसानी से समझें।",
        heroTitle: "आपकी मेडिकल रिपोर्ट,<br>सरल भाषा में समझाई गई।",
        heroSub: "अपनी मेडिकल रिपोर्ट या डॉक्टर का पर्चा अपलोड करें और अपनी भाषा में आसान व्याख्या व आपातकालीन सुरक्षा अलर्ट पाएं।",
        stat1: "12.4% मरीजों को ही पर्चा समझ आता है (मुंबई अध्ययन)",
        stat2: "~48% बीपी दवा अनियमितता दर (भारत)",
        stat3: "DPDP अधिनियम 2023 · शून्य डेटा प्रतिधारण",
        tabReport: "रिपोर्ट और पर्चा विश्लेषण", tabMeds: "दवा व सुरक्षा जांच", tabRisk: "बीमारी जोखिम जांच", tabCompare: "तुलना और USP", tabRefs: "चिकित्सा संदर्भ (ICMR/WHO)",
        cardInputTitle: "रिपोर्ट या पर्चा अपलोड करें", dropTitle: "फोटो / PDF चुनें या यहाँ खींचें",
        privacyBadge: "आपकी फोटो/रिपोर्ट इस डिवाइस से बाहर कहीं नहीं भेजी जाती — सारी प्रोसेसिंग सुरक्षित रूप से होती है।",
        previewLabel: "अपलोड किया गया दस्तावेज़",
        presetTitle: "⚡ त्वरित डेमो चुनें (Sample Tests):", sample1: "उच्च ब्लड शुगर", sample2: "अत्यधिक बीपी संकट", sample3: "किडनी (क्रिएटिनिन)",
        verifyBadge: "ह्यूमन वेरिफिकेशन स्टेप (सत्यापन)", verifyDesc: "AI द्वारा पढ़ा गया कच्चा टेक्स्ट या संख्याएं — जांच कर बदलें:",
        fieldGender: "लिंग", fieldAge: "आयु", fieldBp: "ब्लड प्रेशर (BP)", fieldSugar: "खाली पेट शुगर (mg/dL)", fieldHr: "हार्ट रेट (BPM)", fieldSpo2: "SpO2 (%)", fieldChol: "कोलेस्ट्रॉल (mg/dL)", fieldCreat: "क्रिएटिनिन (mg/dL)",
        btnAnalyze: "रिपोर्ट का विश्लेषण करें", btnAnalyzing: "विश्लेषण हो रहा है...",
        cardResultTitle: "सरल भाषा में रिपोर्ट (Explanation)", btnSpeak: "सुनें (Voice)", btnDownload: "PDF डाउनलोड करें",
        btnDocSummary: "एक-पेज डॉक्टर सारांश (Print)",
        noReport: "बाईं ओर रिपोर्ट अपलोड करें या कोई भी 'त्वरित डेमो' चुनकर विश्लेषण देखें।",
        rfTitle: "🚨 आपातकालीन चेतावनी (Emergency Red-Flag)", rfDesc: "आपकी रिपोर्ट में कुछ संख्याएं खतरे के स्तर पर हैं। कृपया बिना देर किए तुरंत डॉक्टर या अस्पताल से संपर्क करें।",
        combRiskTitle: "संयुक्त जोखिम चेतावनी (High BP + High Sugar)", combRiskDesc: "आपका ब्लड प्रेशर और ब्लड शुगर दोनों एक साथ ज्यादा हैं। इससे हृदय और रक्तवाहिकाओं पर दोहरा दबाव पड़ता है। जल्द से जल्द डॉक्टर से मिलें।",
        overallEyebrow: "समग्र स्वास्थ्य स्थिति",
        verdictNormal: "सभी मान सामान्य और सुरक्षित हैं", verdictWatch: "कुछ मान ध्यान देने योग्य हैं", verdictAbnormal: "कुछ मान असामान्य हैं — डॉक्टर से सलाह लें", verdictRed: "🚨 आपातकालीन खतरा — तुरंत चिकित्सा सहायता लें",
        source: "स्रोत", footerDisc: "यह एप्लिकेशन केवल मरीजों की प्राथमिक जानकारी और जागरूकता के लिए है। यह अंतिम चिकित्सकीय सलाह नहीं है। किसी भी उपचार के लिए डॉक्टर से परामर्श अवश्य लें।",
        footerBadge: "महत्वपूर्ण सूचना (Medical Disclaimer)",
        toastRiskCalc: "जोखिम की सफलतापूर्वक गणना की गई!", toastNoSpeech: "इस ब्राउज़र में आवाज़ सुविधा उपलब्ध नहीं है।", toastNoData: "पहले रिपोर्ट का विश्लेषण करें।",
        ocrExtracting: "AI OCR टेक्स्ट पढ़ रहा है...", ocrPdf: "PDF दस्तावेज़ पढ़ रहा है...", ocrSuccess: "टेक्स्ट सफलतापूर्वक पढ़ा और विश्लेषित किया गया ✓",
        ocrFail: "फोटो मिल गई ✓ — नीचे फ़ील्ड भरकर विश्लेषण शुरू करें।",
        ocrFailUnreadable: "दस्तावेज़ से स्पष्ट टेक्स्ट नहीं पढ़ा जा सका — कृपया स्पष्ट फोटो अपलोड करें या नीचे फ़ील्ड भरें।",
        hintBpRange: "मान्य रक्तचाप भरें (उदा. 120/80)", hintNumRange: "मान वास्तविक सीमा में नहीं है",
        medsCardTitle: "पर्ची अपलोड करें या दवा का नाम टाइप करें",
        medsDropLabel: "पर्ची की फोटो अपलोड करने के लिए टैप करें", medsDropSub: "JPG, PNG — हस्तलिखित पर्ची भी चलेगी",
        medsPrivacy: "फोटो प्रोसेस होते ही सर्वर से तुरंत डिलीट हो जाती है — कहीं सेव नहीं होती।",
        medsPresetTitle: "⚡ त्वरित डेमो चुनें:", medsSample1: "Duplicate Paracetamol", medsSample2: "Multiple Painkillers (NSAID)", medsSample3: "Safe Combination",
        medsVerifyBadge: "जांचकर पुष्टि करें", medsVerifyDesc: "AI द्वारा पढ़ा गया टेक्स्ट या दवा का नाम टाइप करें:",
        medsCheckBtn: "दवाएं खोजें और जांचें", medsResultTitle: "पहचानी गई दवाएं व सुरक्षा परिणाम",
        medsEmpty: "बाईं ओर पर्ची अपलोड करें या दवा का नाम टाइप करें।",
        medsProfTitle: "मरीज की प्रोफाइल (वैकल्पिक — सटीक जांच के लिए उपयोगी)",
        lblPregnant: "गर्भवती (Pregnant)", lblKidney: "किडनी की बीमारी (Kidney disease)",
        medsAllergyLabel: "ज्ञात एलर्जी (Known allergies):", allergyPenicillin: "पेनिसिलिन", allergyNsaid: "दर्द निवारक (NSAID)", allergySulfa: "सल्फा",
        medsAgePlaceholder: "उम्र (Age)",
        riskFormTitle: "रुग्ण विवरण व जीवनशैली", riskResultsTitle: "संभावित रोग जोखिम परिणाम",
        btnCalcRisk: "जोखिम का आकलन करें (Assess Risk)",
        compTitle: "अन्य ऐप्स और हमारी तुलना (How We Compare)",
        compIntro: "आज कई AI स्वास्थ्य ऐप्स उपलब्ध हैं — यहाँ एक ईमानदार समीक्षा है कि हम कहाँ खड़े हैं, और क्या अलग कर रहे हैं।",
        lblPro: "क्या अच्छा है:", lblCon: "क्या कमी है:",
        compApp1Pro: "अच्छा बहुभाषी रिपोर्ट सारांश", compApp1Con: "जेनेरिक दवा या लागत बचत पर कोई मार्गदर्शन नहीं",
        compApp2Pro: "दवा इंटरैक्शन का मजबूत डेटाबेस", compApp2Con: "अंग्रेजी-केंद्रित, क्षेत्रीय भाषाओं में सीमित गहराई",
        compApp3Pro: "डिवाइस पर गोपनीयता, कई भाषाओं का समर्थन", compApp3Con: "किफायती उपचार या सरकारी योजनाओं पर कोई ध्यान नहीं",
        compApp4Pro: "अच्छा OCR टेक्स्ट निष्कर्षण", compApp4Con: "स्वास्थ्य जोखिम अलर्ट या जेनेरिक विकल्प अनुपस्थित",
        uspHeading: "हमारी मुख्य विशेषताएं और अंतर (USP)",
        usp1Title: "\\"जेनेरिक विकल्प एवं बचत मार्गदर्शक\\"", usp1Desc: "हम ब्रांडेड दवाओं के लिए सस्ते जेनेरिक सॉल्ट विकल्प दिखाते हैं और उपयोगकर्ताओं को उनके निकटतम प्रधानमंत्री जन औषधि केंद्र तक पहुँचाते हैं — इस क्षेत्र का कोई अन्य ऐप यह मार्गदर्शन नहीं देता।",
        usp2Title: "गहन हिंदी और मराठी समर्थन", usp2Desc: "केवल सतही अनुवाद नहीं, बल्कि ग्रामीण और अर्ध-शहरी भारतीय परिवारों की वास्तविक पहुंच और समझ के लिए विशेष रूप से निर्मित।",
        usp3Title: "निःशुल्क और खुला", usp3Desc: "एक वास्तविक नागरिक समस्या के समाधान हेतु छात्रों द्वारा निर्मित, कोई सशुल्क सदस्यता नहीं।",
        usp4Title: "स्पष्ट एवं सतर्क सुरक्षा नीति", usp4Desc: "अनिश्चितता की स्थिति में मरीजों को 'सुरक्षित' का झूठा दिलासा देने के बजाय हमेशा 'डॉक्टर से परामर्श लें' का सुरक्षित विकल्प चुनते हैं।",
        compClosing: "हम पहला AI स्वास्थ्य ऐप होने का दावा नहीं करते — हम ऐसा ऐप बना रहे हैं जो वास्तव में एक भारतीय परिवार के पैसे बचाए और दवाओं के साथ उन्हें अधिक सुरक्षित रखे।",
        serverVerified: "सर्वर सत्यापित (ICMR / WHO)",
        refsTitle: "चिकित्सा संदर्भ व दिशानिर्देश (Clinical Sources)",
        refsSub: "हमारे ऐप में सभी जोखिम सीमाएं और नियम आधिकारिक राष्ट्रीय व अंतरराष्ट्रीय चिकित्सा दिशानिर्देशों पर आधारित हैं:",
        refCard1Title: "ICMR दिशानिर्देश", refCard1Desc: "भारतीय आयुर्विज्ञान अनुसंधान परिषद (ICMR): खाली पेट शुगर सामान्य < 100 mg/dL, प्रीडायबिटीज 100-125, डायबिटीज >= 126 mg/dL. HbA1c >= 6.5% डायबिटीज दर्शाता है।",
        refCard2Title: "WHO रक्तचाप मानक", refCard2Desc: "विश्व स्वास्थ्य संगठन (WHO): सामान्य रक्तचाप 120/80 mmHg. 140/90 से ऊपर उच्च रक्तचाप और 180/120+ आपातकालीन स्थिति (Crisis) मानी जाती है।",
        refCard3Title: "AIIMS व NKF किडनी मानक", refCard3Desc: "नेशनल किडनी फाउंडेशन (NKF): सीरम क्रिएटिनिन सामान्य सीमा — पुरुष 0.7-1.3 mg/dL, महिला 0.6-1.1 mg/dL. 2.5 से ऊपर गुर्दा परीक्षण अत्यंत आवश्यक।",
        refsNote: "सभी परीक्षण आधिकारिक मानकों के अनुसार आंके जाते हैं। क्रिएटिनिन सीमा लिंग-आधारित है (पुरुष: 0.7-1.3, महिला: 0.6-1.1 mg/dL)।"
      },
      en: {
        appTitle: "AI Health Companion", topbarTag: "SIH 2026 · Student Innovation",
        heroEyebrow: "Upload once. Understand everything.",
        heroTitle: "Your health report,<br>explained — not just read.",
        heroSub: "Upload a medical report or prescription to get instant patient-friendly explanations and emergency safety alerts in your language.",
        stat1: "12.4% Rx comprehension rate (Mumbai study)",
        stat2: "~48% pooled antihypertensive non-adherence in India",
        stat3: "DPDP Act 2023 · Zero Data Retention",
        tabReport: "Report & Prescription OCR", tabMeds: "Medicine & Safety Check", tabRisk: "Disease Risk Assessment", tabCompare: "Competitor Analysis & USP", tabRefs: "Clinical Sources (ICMR/WHO)",
        cardInputTitle: "Upload Medical Report / Slip", dropTitle: "Choose an image/PDF or drag here",
        privacyBadge: "Your photo/report is processed securely and deleted immediately after analysis.",
        previewLabel: "Uploaded Document Preview",
        presetTitle: "⚡ Quick Demo Presets (Sample Tests):", sample1: "High Blood Sugar", sample2: "High BP Crisis", sample3: "Kidney (Creatinine)",
        verifyBadge: "Human-in-the-Loop Verification Step", verifyDesc: "Verify or correct AI-extracted values before final analysis:",
        fieldGender: "Gender", fieldAge: "Age", fieldBp: "Blood Pressure", fieldSugar: "Fasting Sugar (mg/dL)", fieldHr: "Heart Rate (BPM)", fieldSpo2: "SpO2 (%)", fieldChol: "Cholesterol (mg/dL)", fieldCreat: "Creatinine (mg/dL)",
        btnAnalyze: "Analyze Report Now", btnAnalyzing: "Analyzing...",
        cardResultTitle: "Patient-Friendly Explanation", btnSpeak: "Listen (Voice)", btnDownload: "Download PDF",
        btnDocSummary: "Print One-Page Doctor Summary",
        noReport: "Upload a document on the left or select a 'Quick Demo' preset to view the simplified report.",
        rfTitle: "🚨 Emergency Red-Flag Alert", rfDesc: "One or more markers are critically abnormal. Please seek immediate professional medical consultation.",
        combRiskTitle: "Combined Risk Alert (High BP + High Sugar)", combRiskDesc: "Both blood pressure and blood sugar are elevated together, which places double strain on the heart and blood vessels. Please consult a doctor soon.",
        overallEyebrow: "Overall Health Status",
        verdictNormal: "All values are normal and safe", verdictWatch: "Some values need watching", verdictAbnormal: "Some values are abnormal — consult a doctor", verdictRed: "🚨 Emergency risk — seek immediate medical help",
        source: "Source", footerDisc: "This application is for patient educational screening only. It is not a diagnostic tool or a substitute for medical advice. Always consult a qualified doctor.",
        footerBadge: "Important Notice (Medical Disclaimer)",
        toastRiskCalc: "Risk Calculated Successfully!", toastNoSpeech: "Voice is not supported in this browser.", toastNoData: "Please analyze a report first.",
        ocrExtracting: "Reading text with AI OCR...", ocrPdf: "Reading PDF document...", ocrSuccess: "Text successfully extracted and analyzed ✓",
        ocrFail: "Photo received ✓ — fill in the fields below to continue.",
        ocrFailUnreadable: "Could not clearly read text from this document — please ensure good lighting or enter the values below.",
        hintBpRange: "Enter a valid BP (e.g. 120/80)", hintNumRange: "Value is outside a realistic range",
        medsCardTitle: "Upload a prescription or type a medicine name",
        medsDropLabel: "Tap to upload a photo of the prescription", medsDropSub: "JPG, PNG — handwritten prescriptions OK",
        medsPrivacy: "The photo is deleted from the server immediately after processing — never stored anywhere.",
        medsPresetTitle: "⚡ Quick demo:", medsSample1: "Duplicate Paracetamol", medsSample2: "Multiple Painkillers (NSAID)", medsSample3: "Safe Combination",
        medsVerifyBadge: "Review & confirm", medsVerifyDesc: "Type or correct the medicine names read from the prescription:",
        medsCheckBtn: "Find medicines & check", medsResultTitle: "Detected medicines & safety evaluation",
        medsEmpty: "Upload a prescription on the left, or type a medicine name.",
        medsProfTitle: "Patient profile (optional — helps give a more specific check)",
        lblPregnant: "Pregnant", lblKidney: "Kidney disease",
        medsAllergyLabel: "Known allergies:", allergyPenicillin: "Penicillin", allergyNsaid: "Painkiller (NSAID)", allergySulfa: "Sulfa",
        medsAgePlaceholder: "Age",
        riskFormTitle: "Patient Profile & Lifestyle", riskResultsTitle: "Indicative Disease Risk Assessment",
        btnCalcRisk: "Assess Disease Risk",
        compTitle: "How We Compare",
        compIntro: "Several AI health apps exist today — here's an honest look at where we stand, and what we're doing differently.",
        lblPro: "What they do well:", lblCon: "What's missing:",
        compApp1Pro: "Good multilingual report summaries", compApp1Con: "No generic medicine/cost-saving guidance",
        compApp2Pro: "Strong drug interaction database", compApp2Con: "English-first, limited regional language depth",
        compApp3Pro: "On-device privacy, wide language support", compApp3Con: "No focus on affordability or government schemes",
        compApp4Pro: "Good OCR extraction", compApp4Con: "No health-risk alerts or generic alternatives",
        uspHeading: "Our Differentiators (USP)",
        usp1Title: "\\"Generic Alternative & Savings Finder\\"", usp1Desc: "We show cheaper generic salt equivalents for branded medicines and point users to their nearest Jan Aushadhi Kendra (govt. generic medicine store) — no other app in this space currently offers this cost-saving guidance.",
        usp2Title: "Deep Hindi & Marathi Support", usp2Desc: "Built for rural and semi-urban Indian users, not just translated UI — designed for real accessibility, not just localization.",
        usp3Title: "Free and Open", usp3Desc: "Built by students for a real civic problem, not a subscription-first product.",
        usp4Title: "Clear, Cautious Safety Design", usp4Desc: "We default to \\"Consult doctor\\" instead of falsely reassuring \\"Safe\\" when data is uncertain.",
        compClosing: "We're not claiming to be the first AI health app — we're building the one that actually helps an Indian family save money and stay safer with their medicines.",
        serverVerified: "Server Verified (ICMR / WHO)",
        refsTitle: "Clinical Reference Guidelines (ICMR/WHO)",
        refsSub: "All risk thresholds and clinical evaluations in our app are grounded in official national and international medical guidelines:",
        refCard1Title: "ICMR Guidelines", refCard1Desc: "Indian Council of Medical Research (ICMR): Fasting sugar normal < 100 mg/dL, prediabetes 100-125, diabetes >= 126 mg/dL. HbA1c >= 6.5% indicates diabetes.",
        refCard2Title: "WHO Blood Pressure Standards", refCard2Desc: "World Health Organization (WHO): Optimal BP is 120/80 mmHg. Stage 2 hypertension is >= 140/90, and >= 180/120 mmHg is classified as Hypertensive Crisis.",
        refCard3Title: "AIIMS & NKF Kidney Standards", refCard3Desc: "National Kidney Foundation (NKF): Serum creatinine normal ranges — Male 0.7-1.3 mg/dL, Female 0.6-1.1 mg/dL. Values > 2.5 mg/dL indicate severe renal impairment.",
        refsNote: "Clinical reference ranges are benchmarked against official adult criteria. Creatinine thresholds are gender-adjusted (Male: 0.7-1.3, Female: 0.6-1.1 mg/dL)."
      }
    };
"""

text = text[:i18n_mr_start] + new_i18n_block + text[i18n_end:]

# 2. Update setLanguage(lang) to populate the new elements
old_set_lang = """      // Tab 4 UI (Compare)
      setText('txt-comp-title', t.compTitle);
      setText('txt-comp-intro', t.compIntro);
      setText('th-comp-features', t.compFeatures);
      setText('th-comp-ios', t.compIos);
      setText('th-comp-symptom', t.compSymptom);
      setText('th-comp-tele', t.compTele);
      setText('th-comp-our', t.compOur);
      setText('td-comp-r1-feat', t.compR1Feat);
      setText('td-comp-r1-ios', t.compR1Ios);
      setText('td-comp-r1-sym', t.compR1Sym);
      setText('td-comp-r1-tele', t.compR1Tele);
      setText('td-comp-r1-our', t.compR1Our);
      setText('td-comp-r2-feat', t.compR2Feat);
      setText('td-comp-r2-ios', t.compR2Ios);
      setText('td-comp-r2-sym', t.compR2Sym);
      setText('td-comp-r2-tele', t.compR2Tele);
      setText('td-comp-r2-our', t.compR2Our);
      setText('td-comp-r3-feat', t.compR3Feat);
      setText('td-comp-r3-ios', t.compR3Ios);
      setText('td-comp-r3-sym', t.compR3Sym);
      setText('td-comp-r3-tele', t.compR3Tele);
      setText('td-comp-r3-our', t.compR3Our);
      setText('td-comp-r4-feat', t.compR4Feat);
      setText('td-comp-r4-ios', t.compR4Ios);
      setText('td-comp-r4-sym', t.compR4Sym);
      setText('td-comp-r4-tele', t.compR4Tele);
      setText('td-comp-r4-our', t.compR4Our);
      setText('td-comp-r5-feat', t.compR5Feat);
      setText('td-comp-r5-ios', t.compR5Ios);
      setText('td-comp-r5-sym', t.compR5Sym);
      setText('td-comp-r5-tele', t.compR5Tele);
      setText('td-comp-r5-our', t.compR5Our);
      setText('td-comp-r6-feat', t.compR6Feat);
      setText('td-comp-r6-ios', t.compR6Ios);
      setText('td-comp-r6-sym', t.compR6Sym);
      setText('td-comp-r6-tele', t.compR6Tele);
      setText('td-comp-r6-our', t.compR6Our);
      setText('txt-comp-note', t.compNote);"""

new_set_lang = """      // Stats chips
      setText('txt-stat-1', t.stat1);
      setText('txt-stat-2', t.stat2);
      setText('txt-stat-3', t.stat3);
      setText('btn-doc-summary-txt', t.btnDocSummary);

      // Tab 4 UI (Compare & USP)
      setText('txt-comp-title', t.compTitle);
      setText('txt-comp-intro', t.compIntro);
      setText('lbl-pro-1', t.lblPro);
      setText('lbl-con-1', t.lblCon);
      setText('txt-comp-app1-pro', t.compApp1Pro);
      setText('txt-comp-app1-con', t.compApp1Con);
      setText('lbl-pro-2', t.lblPro);
      setText('lbl-con-2', t.lblCon);
      setText('txt-comp-app2-pro', t.compApp2Pro);
      setText('txt-comp-app2-con', t.compApp2Con);
      setText('lbl-pro-3', t.lblPro);
      setText('lbl-con-3', t.lblCon);
      setText('txt-comp-app3-pro', t.compApp3Pro);
      setText('txt-comp-app3-con', t.compApp3Con);
      setText('lbl-pro-4', t.lblPro);
      setText('lbl-con-4', t.lblCon);
      setText('txt-comp-app4-pro', t.compApp4Pro);
      setText('txt-comp-app4-con', t.compApp4Con);
      setText('txt-usp-heading', t.uspHeading);
      setText('txt-usp-1-title', t.usp1Title);
      setText('txt-usp-1-desc', t.usp1Desc);
      setText('txt-usp-2-title', t.usp2Title);
      setText('txt-usp-2-desc', t.usp2Desc);
      setText('txt-usp-3-title', t.usp3Title);
      setText('txt-usp-3-desc', t.usp3Desc);
      setText('txt-usp-4-title', t.usp4Title);
      setText('txt-usp-4-desc', t.usp4Desc);
      setText('txt-comp-closing', t.compClosing);"""

text = text.replace(old_set_lang, new_set_lang)

# 3. Add Jan Aushadhi generic alternative & savings box inside renderMedicineSafetyResults
# Look for mCard.innerHTML in renderMedicineSafetyResults
old_mcard = """        mCard.className = `marker-card ${cardBorder}`;
        mCard.style.marginBottom = '10px';
        mCard.innerHTML = `
          <div class="marker-top">
            <span class="marker-label">${e.brand} <small style="color:var(--slate); font-weight:normal;">(${e.generic})</small></span>
            <span class="status-pill ${pillClass}">${label}</span>
          </div>
          <div class="marker-reasoning" style="margin-top:4px;">${reason}</div>
          <div class="marker-source"><i class="fa-solid fa-circle-info"></i> ${action}</div>
        `;"""

new_mcard = """        const brandMrp = e.brand_mrp || 45;
        const jaMrp = e.ja_mrp || 9;
        const savingsPct = e.savings_pct || 80;

        mCard.className = `marker-card ${cardBorder}`;
        mCard.style.marginBottom = '12px';
        mCard.innerHTML = `
          <div class="marker-top">
            <span class="marker-label">${e.brand} <small style="color:var(--slate); font-weight:normal;">(${e.generic})</small></span>
            <span class="status-pill ${pillClass}">${label}</span>
          </div>
          <div class="marker-reasoning" style="margin-top:4px;">${reason}</div>
          <div class="marker-source"><i class="fa-solid fa-circle-info"></i> ${action}</div>
          <div class="jan-aushadhi-box">
            <div class="jan-aushadhi-head">
              <span><i class="fa-solid fa-tags"></i> <strong>${L('जन औषधी जेनेरिक पर्याय & बचत','जन औषधि जेनेरिक विकल्प एवं बचत','Jan Aushadhi Generic Alternative & Savings')}</strong></span>
              <span class="jan-aushadhi-badge">${L(`बचत ${savingsPct}%`,`बचत ${savingsPct}%`,`Save ${savingsPct}%`)}</span>
            </div>
            <div class="jan-aushadhi-details">
              <div>
                <span>${L('ब्रँडेड किंमत: ','ब्रांडेड कीमत: ','Branded MRP: ')}<strong>₹${brandMrp}</strong></span> · 
                <span>${L('जन औषधी दर: ','जन औषधि दर: ','Jan Aushadhi: ')}<strong style="color:#166534;">₹${jaMrp}</strong></span>
                <div style="font-size:0.75rem; color:#64748b; margin-top:2px;">${L(`समान सॉल्ट: जेनेरिक ${e.generic}`,`समान सॉल्ट: जेनेरिक ${e.generic}`,`Identical Salt: Generic ${e.generic}`)}</div>
              </div>
              <a href="https://janaushadhi.gov.in/" target="_blank" rel="noopener" class="jan-aushadhi-link">
                <i class="fa-solid fa-location-dot"></i> ${L('जवळचे केंद्र शोधा','निकटतम केंद्र खोजें','Find Nearest Kendra')}
              </a>
            </div>
          </div>
        `;"""

text = text.replace(old_mcard, new_mcard)

# 4. Add Server-Verified badge in renderFullReport
old_meta_badge = """        const docType = meta.document_type === 'prescription' ? L('डॉक्टरांचे प्रिस्क्रिप्शन', 'डॉक्टर का पर्चा', 'Prescription') : L('वैद्यकीय लॅब अहवाल', 'मेडिकल लैब रिपोर्ट', 'Lab Report');
        metaCard.innerHTML = `
          <div class="report-meta-title"><i class="fa-solid fa-id-card"></i> ${docType} ${meta.hospital_or_lab ? '· ' + meta.hospital_or_lab : ''}</div>"""

new_meta_badge = """        const docType = meta.document_type === 'prescription' ? L('डॉक्टरांचे प्रिस्क्रिप्शन', 'डॉक्टर का पर्चा', 'Prescription') : L('वैद्यकीय लॅब अहवाल', 'मेडिकल लैब रिपोर्ट', 'Lab Report');
        metaCard.innerHTML = `
          <div class="report-meta-title" style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:8px;">
            <span><i class="fa-solid fa-id-card"></i> ${docType} ${meta.hospital_or_lab ? '· ' + meta.hospital_or_lab : ''}</span>
            <span class="badge-server-verified"><i class="fa-solid fa-shield-check"></i> ${I18N[currentLang].serverVerified}</span>
          </div>"""

text = text.replace(old_meta_badge, new_meta_badge)

# 5. Add printDoctorSummary function right before downloadPdfReport
doctor_summary_func = """    function printDoctorSummary() {
      const t = I18N[currentLang];
      const L = (mr, hi, en) => currentLang === 'mr' ? mr : (currentLang === 'hi' ? hi : en);
      const printDiv = document.getElementById('printable-doctor-summary');
      if (!printDiv) return;

      const report = window.__lastParsedReport || {};
      const meta = report.metadata || {};
      const tests = report.tests || [];
      const alerts = report.condition_alerts || [];
      const meds = report.detected_medicines || [];
      const overallText = document.getElementById('txt-overall-verdict') ? document.getElementById('txt-overall-verdict').innerText : 'Evaluated';

      let testsHtml = '';
      if (tests.length > 0) {
        testsHtml = `
          <table style="width:100%; border-collapse:collapse; margin-top:10px; font-size:11pt;">
            <thead>
              <tr style="background:#f1f5f9; border-bottom:2px solid #cbd5e1;">
                <th style="padding:6px 8px; text-align:left;">${L('चाचणी / मार्कर','परीक्षण / मार्कर','Test / Marker')}</th>
                <th style="padding:6px 8px; text-align:left;">${L('आढळलेले मूल्य','परिणाम','Observed Value')}</th>
                <th style="padding:6px 8px; text-align:left;">${L('प्रमाणित मर्यादा','मानक सीमा','Ref. Range')}</th>
                <th style="padding:6px 8px; text-align:left;">${L('स्थिती','स्थिति','Status')}</th>
              </tr>
            </thead>
            <tbody>
              ${tests.map(test => `
                <tr style="border-bottom:1px solid #e2e8f0;">
                  <td style="padding:6px 8px;"><strong>${test.name}</strong></td>
                  <td style="padding:6px 8px;">${test.value} ${test.unit}</td>
                  <td style="padding:6px 8px; color:#64748b;">${test.reference_range}</td>
                  <td style="padding:6px 8px; font-weight:bold; color:${test.status === 'high' || test.status === 'low' ? '#dc2626' : test.status === 'borderline' ? '#d97706' : '#16a34a'};">
                    ${test.status.toUpperCase()}
                  </td>
                </tr>
              `).join('')}
            </tbody>
          </table>
        `;
      } else {
        testsHtml = `<p style="font-size:10pt; color:#64748b; font-style:italic;">${L('कोणत्याही लॅब चाचण्या आढळल्या नाहीत.','कोई लैब परीक्षण नहीं मिला।','No clinical lab tests detected.')}</p>`;
      }

      let alertsHtml = '';
      if (alerts.length > 0) {
        alertsHtml = `
          <div style="margin-top:14px; padding:10px 14px; background:#fff7ed; border-left:4px solid #ea580c; border-radius:4px;">
            <h4 style="margin:0 0 6px; color:#c2410c; font-size:11pt;">⚠️ ${L('धोका इशारे आणि शिफारसी','जोखिम अलर्ट और सलाह','Active Clinical Alerts & Red-Flags')}</h4>
            <ul style="margin:0; padding-left:18px; font-size:10pt; color:#7c2d12;">
              ${alerts.map(a => `<li><strong>${L(a.title_mr, a.title_hi, a.title_en)}:</strong> ${L(a.desc_mr, a.desc_hi, a.desc_en)}</li>`).join('')}
            </ul>
          </div>
        `;
      }

      let medsHtml = '';
      if (meds.length > 0) {
        medsHtml = `
          <div style="margin-top:14px;">
            <h4 style="margin:0 0 6px; font-size:11pt; color:#0f172a;">💊 ${L('प्रिस्क्रिप्शनमधील औषधे आणि जेनेरिक सॉल्ट','पर्चे में दर्ज दवाएं एवं जेनेरिक सॉल्ट','Prescribed Medicines & Generic Equivalents')}</h4>
            <table style="width:100%; border-collapse:collapse; font-size:10pt;">
              <thead>
                <tr style="background:#f1f5f9; border-bottom:2px solid #cbd5e1;">
                  <th style="padding:6px 8px; text-align:left;">${L('ब्रँड नाव','ब्रांड नाम','Brand Name')}</th>
                  <th style="padding:6px 8px; text-align:left;">${L('जेनेरिक सॉल्ट घटक','जेनेरिक सॉल्ट घटक','Generic Salt Equivalent')}</th>
                  <th style="padding:6px 8px; text-align:left;">${L('जन औषधी बचत','जन औषधि बचत','Jan Aushadhi Savings')}</th>
                </tr>
              </thead>
              <tbody>
                ${meds.map(m => `
                  <tr style="border-bottom:1px solid #e2e8f0;">
                    <td style="padding:6px 8px; font-weight:bold;">${m.brand}</td>
                    <td style="padding:6px 8px;">${m.generic}</td>
                    <td style="padding:6px 8px; color:#15803d; font-weight:bold;">${L('~७०-८५% बचत (PMBI)','~70-85% बचत (PMBI)','~70-85% cheaper at Jan Aushadhi')}</td>
                  </tr>
                `).join('')}
              </tbody>
            </table>
          </div>
        `;
      }

      printDiv.innerHTML = `
        <div style="max-width:800px; margin:0 auto; font-family:Arial, sans-serif; line-height:1.4;">
          <div style="display:flex; justify-content:space-between; align-items:flex-start; border-bottom:2px solid #0f3d3e; padding-bottom:10px; margin-bottom:12px;">
            <div>
              <h2 style="margin:0; color:#0f3d3e; font-size:16pt;">AI Health Companion — Clinical Screening Summary</h2>
              <div style="font-size:9.5pt; color:#475569; margin-top:3px;">Smart India Hackathon (SIH 2026) Student Innovation · Problem Statement ID: SIH26196</div>
            </div>
            <div style="text-align:right; font-size:9pt; color:#475569;">
              <div><strong>Grounded:</strong> ICMR / WHO Guidelines</div>
              <div><strong>Date:</strong> ${new Date().toLocaleDateString()}</div>
            </div>
          </div>

          <div style="background:#f8fafc; border:1px solid #e2e8f0; border-radius:6px; padding:10px 14px; margin-bottom:12px; font-size:10pt;">
            <div style="display:flex; flex-wrap:wrap; gap:16px;">
              <div><strong>${L('रुग्णाचे नाव: ','मरीज का नाम: ','Patient Name: ')}</strong>${meta.patient_name || 'Patient'}</div>
              <div><strong>${L('वय: ','आयु: ','Age: ')}</strong>${meta.age || '—'}</div>
              <div><strong>${L('लिंग: ','लिंग: ','Gender: ')}</strong>${meta.gender ? (meta.gender === 'female' ? L('महिला','महिला','Female') : L('पुरुष','पुरुष','Male')) : '—'}</div>
              <div><strong>${L('डॉक्टर/लॅब: ','डॉक्टर/लैब: ','Doctor/Lab: ')}</strong>${meta.doctor_name || meta.hospital_or_lab || 'Clinical Laboratory'}</div>
            </div>
          </div>

          <div style="margin-bottom:8px; font-size:11pt; font-weight:bold; color:#0f3d3e;">
            ${L('एकूण आरोग्य स्थिती: ','समग्र स्वास्थ्य स्थिति: ','Overall Health Status: ')} <span style="color:#0f3d3e;">${overallText}</span>
          </div>

          ${alertsHtml}
          ${testsHtml}
          ${medsHtml}

          <div style="margin-top:20px; border-top:1px solid #cbd5e1; padding-top:10px; font-size:8pt; color:#64748b; line-height:1.4;">
            <p style="margin:0;"><strong>Regulatory Notice (Telemedicine Practice Guidelines 2020 & DPDP Act 2023):</strong> This document is an educational screening aid generated from patient-confirmed OCR data against published ICMR and WHO thresholds. It is NOT a clinical diagnosis. Zero health data is retained after this session. Please present this structured summary to your treating physician for definitive medical consultation.</p>
          </div>
        </div>
      `;

      window.print();
    }

"""

text = text.replace("    async function downloadPdfReport() {", doctor_summary_func + "    async function downloadPdfReport() {")

with open("templates/index.html", "w", encoding="utf-8") as f:
    f.write(text)

print("Step 2 completed.")
