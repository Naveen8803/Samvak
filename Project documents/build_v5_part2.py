
# ═══════════════════════════════════════════════════════════════
# 1. INTRODUCTION
# ═══════════════════════════════════════════════════════════════
add_para("1. INTRODUCTION", True, WD_ALIGN_PARAGRAPH.LEFT, 16)
add_empty()

add_para("1.1 Motivation", True, WD_ALIGN_PARAGRAPH.LEFT, 13)
add_para('According to the World Health Organization, over 430 million people worldwide suffer from disabling hearing loss, with approximately 63 million individuals in India alone classified as hearing-impaired. The primary mode of communication for the Deaf and hard-of-hearing community is sign language, yet the vast majority of the hearing population does not understand sign language. This communication barrier leads to social isolation, limited access to education, healthcare, and employment opportunities for the hearing-impaired.', False, WD_ALIGN_PARAGRAPH.JUSTIFY, 13)
add_para('While interpreters serve as intermediaries, their availability is severely limited, especially in rural India. Moreover, Indian Sign Language (ISL) has its own grammar, syntax, and vocabulary that differ significantly from spoken languages, making direct translation non-trivial. Existing assistive technologies are either expensive, require specialized hardware (such as sensor gloves), or are restricted to a single language. These challenges motivated the development of a software-based, hardware-minimal, multilingual solution that can run on any device with a webcam and microphone.', False, WD_ALIGN_PARAGRAPH.JUSTIFY, 13)

add_para("1.2 Problem Statement", True, WD_ALIGN_PARAGRAPH.LEFT, 13)
add_para('The core problem addressed is the absence of an affordable, real-time, bidirectional translation system between Indian Sign Language and spoken/written languages. Existing sign language recognition systems are predominantly designed for American Sign Language (ASL), provide only one-way translation, require specialized hardware, do not support multilingual output, and do not account for ISL grammar (Object-Subject-Verb order) during speech-to-sign translation.', False, WD_ALIGN_PARAGRAPH.JUSTIFY, 13)

add_para("1.3 Objective of the Project", True, WD_ALIGN_PARAGRAPH.LEFT, 13)
add_para('1. Develop a real-time sign language recognition system using webcam, MediaPipe, and LSTM-TCN deep learning model.\n2. Implement a speech-to-sign translation pipeline with NLP-based ISL grammar transformation and 3D avatar animation.\n3. Support multilingual input and output in eight languages.\n4. Build a web-based, mobile-responsive application requiring no specialized hardware.\n5. Incorporate interactive learning features with ISL dictionary, gamified learning, and progress tracking.', False, WD_ALIGN_PARAGRAPH.JUSTIFY, 13)

add_para("1.4 Scope", True, WD_ALIGN_PARAGRAPH.LEFT, 13)
add_para('The scope encompasses: (a) Real-time recognition of 40 ISL phrases via webcam; (b) Speech-to-sign conversion with ISL grammar rules and 3D avatar; (c) ISL dictionary and learning module; (d) User management with authentication, preferences, and history; (e) Cloud deployment on Render. The system does not currently cover continuous sign language recognition or ISL dialects beyond the standard iSign dataset vocabulary.', False, WD_ALIGN_PARAGRAPH.JUSTIFY, 13)

add_para("1.5 Project Introduction", True, WD_ALIGN_PARAGRAPH.LEFT, 13)
add_para('Samvak (Sanskrit for "dialogue") is a web-based, real-time, bidirectional translation application. For Sign-to-Text, MediaPipe extracts 258-dimensional pose/hand features from webcam frames, and an LSTM-TCN model classifies gestures into ISL phrases with 94.6% accuracy. A geometry-based classifier provides fallback recognition for basic static signs. For Speech-to-Sign, the SpeechRecognition library transcribes voice input, spaCy tokenizes the text, and a local ISL grammar engine applies OSV reordering, article/be-verb dropping, and WH-word repositioning. The resulting gloss sequence drives a Three.js 3D avatar. The architecture uses Flask + SQLAlchemy backend, TensorFlow.js for in-browser inference, and Flask-SocketIO for real-time streaming.', False, WD_ALIGN_PARAGRAPH.JUSTIFY, 13)

doc.add_page_break()

# ═══════════════════════════════════════════════════════════════
# 2. LITERATURE SURVEY
# ═══════════════════════════════════════════════════════════════
add_para("2. LITERATURE SURVEY", True, WD_ALIGN_PARAGRAPH.LEFT, 16)
add_empty()
add_para("2.1 Related Work", True, WD_ALIGN_PARAGRAPH.LEFT, 13)

refs = [
    ('[1] Wadhawan & Kumar (2021) — "Sign Language Recognition Systems: A Decade Systematic Literature Review"',
     'This survey covers SLR systems, classifying approaches into vision-based and sensor-based methods. Vision-based approaches using deep learning (CNN, LSTM) showed most promise. Most systems focused on ASL, highlighting the gap in ISL-specific recognition. This motivated our choice of LSTM with MediaPipe pose features for Samvak.'),
    ('[2] Lugaresi et al. (2019) — "MediaPipe: A Framework for Building Perception Pipelines"',
     'MediaPipe provides real-time detection of 33 pose and 21 per-hand landmarks from a single RGB camera. Samvak uses MediaPipe Holistic to extract a 258-dimensional feature vector per frame (33×4 pose + 21×3×2 hand coordinates). MediaPipe\'s browser-side JavaScript API enables the client-side inference architecture.'),
    ('[3] Hochreiter & Schmidhuber (1997) — "Long Short-Term Memory"',
     'The foundational LSTM paper addresses the vanishing gradient problem with gating mechanisms. Samvak employs an LSTM-TCN to classify 30-frame sequences of landmarks into ISL phrases, capturing temporal dependencies in dynamic signs like "Hello" (waving motion) and "Thank You" (mouth-to-outward sweep).'),
    ('[4] Saunders, Camgoz & Bowden (2020) — "Progressive Transformers for Sign Language Production"',
     'This work on sign language production informed Samvak\'s speech-to-sign pipeline design — converting English text into ISL gloss sequences as intermediate representation before driving the 3D avatar.'),
    ('[5] Paudyal, Lee & Banerjee (2023) — "A Survey on Sign Language Translation"',
     'The survey identifies that rule-based ISL grammar transformation achieves comparable accuracy to neural approaches for gloss generation in resource-limited scenarios. Samvak adopts a local rule-based ISL grammar engine.')
]

for title, desc in refs:
    add_para(title, True, size=13)
    add_para(desc, size=13, align=WD_ALIGN_PARAGRAPH.JUSTIFY)
    add_empty()

doc.add_page_break()

# ═══════════════════════════════════════════════════════════════
# 3. SYSTEM ANALYSIS
# ═══════════════════════════════════════════════════════════════
add_para("3. SYSTEM ANALYSIS", True, WD_ALIGN_PARAGRAPH.LEFT, 16)
add_empty()

add_para("3.1 Existing System", True, WD_ALIGN_PARAGRAPH.LEFT, 13)
add_para('Existing sign language translation systems are either hardware-based (CyberGlove, Kinect) requiring expensive specialized devices, or software-based systems primarily focused on American Sign Language (ASL). Open-source alternatives typically support only one-way translation, operate in a single language, and do not handle ISL grammar.', False, WD_ALIGN_PARAGRAPH.JUSTIFY, 13)

add_para("3.2 Disadvantages of Existing System", True, WD_ALIGN_PARAGRAPH.LEFT, 13)
add_para('1. Hardware Dependency: Require expensive sensor gloves or depth cameras ($500–$5,000).\n2. Limited Language Support: Work only with ASL, producing output only in English.\n3. Unidirectional: Support only sign-to-text, lacking speech-to-sign.\n4. No ISL Grammar: Perform naive word-by-word mapping without OSV reordering.\n5. Desktop-Bound: Cannot be accessed via web or mobile.\n6. No Learning Component: Focus solely on translation without teaching ISL.', False, WD_ALIGN_PARAGRAPH.JUSTIFY, 13)

add_para("3.3 Proposed System", True, WD_ALIGN_PARAGRAPH.LEFT, 13)
add_para('Samvak addresses all limitations: uses only webcam/microphone via MediaPipe; custom LSTM-TCN trained on iSign (40 ISL phrases, 94.6% accuracy); bidirectional translation; rule-based ISL grammar engine (OSV, article dropping, WH repositioning); 8 languages; Three.js 3D avatar; web-based with mobile responsiveness; gamified learning module.', False, WD_ALIGN_PARAGRAPH.JUSTIFY, 13)

add_para("3.4 Advantages of Proposed System", True, WD_ALIGN_PARAGRAPH.LEFT, 13)
add_para('1. Zero hardware cost — runs on any device with webcam.\n2. Real-time in-browser inference via TensorFlow.js (sub-200ms).\n3. Grammatically correct ISL gloss output.\n4. Multilingual support across 8 languages.\n5. Bidirectional communication for both hearing and Deaf users.\n6. Cloud-deployed on Render for universal accessibility.', False, WD_ALIGN_PARAGRAPH.JUSTIFY, 13)

add_para("3.5 Workflow of Proposed System", True, WD_ALIGN_PARAGRAPH.LEFT, 13)
add_para('The complete workflow of the proposed system handles both Sign-to-Text and Speech-to-Sign processes as well as the dictionary and gamified learning features. Below is the system workflow diagram:', False, WD_ALIGN_PARAGRAPH.JUSTIFY, 13)

wf_img = os.path.join(DIAGRAM_DIR, "workflow_diagram.png")
if os.path.exists(wf_img):
    doc.add_picture(wf_img, width=Inches(6.0))
    doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER
add_para("Figure 3.1: System Workflow", False, align=WD_ALIGN_PARAGRAPH.CENTER, size=11)
add_empty()

doc.add_page_break()

# ═══════════════════════════════════════════════════════════════
# 4. REQUIREMENT ANALYSIS
# ═══════════════════════════════════════════════════════════════
add_para("4. REQUIREMENT ANALYSIS", True, WD_ALIGN_PARAGRAPH.LEFT, 16)
add_empty()

add_para("4.1 Functional and Non-Functional Requirements", True, WD_ALIGN_PARAGRAPH.LEFT, 13)
add_para("Functional Requirements:", True, size=13)
add_para('1. Capture live video and detect hand/pose landmarks in real time using MediaPipe.\n2. Classify ISL gestures into 40 phrases using LSTM-TCN with ≥90% accuracy.\n3. Convert recognized text to speech using gTTS in the selected language.\n4. Accept voice input and transcribe using Google Speech-to-Text.\n5. Translate speech to ISL gloss sequences and animate via 3D avatar.\n6. Support 8 languages for input/output.\n7. Provide user registration, login, and session management.\n8. Maintain translation history for authenticated users.\n9. Provide an ISL dictionary with browsable sign image sequences.\n10. Implement gamified learning with XP tracking.', False, WD_ALIGN_PARAGRAPH.JUSTIFY, 13)

add_para("Non-Functional Requirements:", True, size=13)
add_para('• Performance: Predictions within 200ms per frame sequence.\n• Security: PBKDF2-SHA256 password hashing; secure sessions.\n• Portability: Runs on all modern browsers across desktop and mobile.\n• Reliability: Graceful handling of camera/microphone unavailability.\n• Maintainability: Modular Flask blueprint architecture.', False, WD_ALIGN_PARAGRAPH.JUSTIFY, 13)

add_para("4.2 Hardware Requirements", True, WD_ALIGN_PARAGRAPH.LEFT, 13)
hw_table = doc.add_table(rows=8, cols=2, style='Table Grid')
hw_data = [
    ("Component", "Specification"),
    ("Processor", "Intel i3 / AMD Ryzen 3 or above"),
    ("RAM", "8 GB minimum"),
    ("Hard Disk", "256 GB SSD"),
    ("Webcam", "720p resolution minimum"),
    ("Microphone", "Standard built-in or external"),
    ("Monitor", "1366×768 resolution minimum"),
    ("Network", "Broadband Internet connection"),
]
for i, (c1, c2) in enumerate(hw_data):
    hw_table.rows[i].cells[0].text = c1
    hw_table.rows[i].cells[1].text = c2
    for cell in hw_table.rows[i].cells:
        for p in cell.paragraphs:
            for r in p.runs:
                r.font.name = 'Times New Roman'
                r.font.size = Pt(12)
                if i == 0: r.bold = True

add_empty()

add_para("4.3 Software Requirements", True, WD_ALIGN_PARAGRAPH.LEFT, 13)
sw_table = doc.add_table(rows=17, cols=2, style='Table Grid')
sw_data = [
    ("Component", "Specification"),
    ("Operating System", "Windows 10/11, macOS, or Linux"),
    ("Programming Language", "Python 3.10+"),
    ("Web Framework", "Flask 3.x with Jinja2"),
    ("Frontend", "HTML5, CSS3, JavaScript ES6+"),
    ("ML Framework", "TensorFlow 2.15+, TensorFlow.js 4.x"),
    ("Pose Estimation", "MediaPipe Holistic 0.10+"),
    ("Speech Recognition", "SpeechRecognition + Google STT"),
    ("NLP", "spaCy 3.x (en_core_web_sm)"),
    ("Translation", "deep-translator (Google Translate)"),
    ("Text-to-Speech", "gTTS (Google TTS)"),
    ("3D Rendering", "Three.js r160+"),
    ("Database", "SQLite 3 with SQLAlchemy ORM"),
    ("Authentication", "Flask-Login + Werkzeug"),
    ("Real-time", "Flask-SocketIO + Eventlet"),
    ("Deployment", "Render (Cloud PaaS)"),
    ("Version Control", "Git + GitHub"),
]
for i, (c1, c2) in enumerate(sw_data):
    sw_table.rows[i].cells[0].text = c1
    sw_table.rows[i].cells[1].text = c2
    for cell in sw_table.rows[i].cells:
        for p in cell.paragraphs:
            for r in p.runs:
                r.font.name = 'Times New Roman'
                r.font.size = Pt(12)
                if i == 0: r.bold = True

add_empty()
add_para("4.4 Architecture", True, WD_ALIGN_PARAGRAPH.LEFT, 13)
add_para('The system follows a client-server architecture. The browser handles real-time inference (TF.js, MediaPipe, Three.js) while the Flask backend manages authentication, translation, grammar processing, and database operations.', False, WD_ALIGN_PARAGRAPH.JUSTIFY, 13)
arch_img = os.path.join(DIAGRAM_DIR, "deployment_diagram.png")
if os.path.exists(arch_img):
    doc.add_picture(arch_img, width=Inches(6.0))
    doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER
add_para("Figure 4.1: System Architecture — Client-Server Deployment", False, align=WD_ALIGN_PARAGRAPH.CENTER, size=11)

doc.add_page_break()

