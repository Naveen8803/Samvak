
# ═══════════════════════════════════════════════════════════════
# 5. SYSTEM DESIGN
# ═══════════════════════════════════════════════════════════════
add_para("5. SYSTEM DESIGN", True, WD_ALIGN_PARAGRAPH.LEFT, 16)
add_empty()

add_para("5.1 Input and Output Design", True, WD_ALIGN_PARAGRAPH.LEFT, 13)
add_para("The input and output design of the system focuses on user-friendliness, accessibility, and real-time responsiveness. Below are the key design specifications:", False, WD_ALIGN_PARAGRAPH.JUSTIFY, 13)
add_empty()

add_para("Input Design Specification:", True, size=13)
add_para('• Webcam Feed: Continuous 30 FPS RGB video stream captured via HTML5 <video> element.\n• Speech/Voice Input: Captured via the device microphone using the Web Speech API and processed by Google STT engine.\n• UI Controls: Intuitive buttons for toggling modes (Sign-to-Text / Speech-to-Sign), language selection dropdowns, and recording triggers.', False, WD_ALIGN_PARAGRAPH.JUSTIFY, 13)

add_empty()
add_para("Output Design Specification:", True, size=13)
add_para('• Visual Translations: Real-time display of predicted text with high-contrast, readable font overlays.\n• Audio Output: Synthesized speech generated dynamically using Google Text-to-Speech (gTTS) mapped to the selected regional language.\n• 3D Avatar Rendering: A Three.js WebGL canvas displaying a humanoid avatar animating precise Indian Sign Language gestures based on the processed ISL gloss grammar.', False, WD_ALIGN_PARAGRAPH.JUSTIFY, 13)

doc.add_page_break()

add_para("5.2 UML Diagrams", True, WD_ALIGN_PARAGRAPH.LEFT, 13)
uml_diagrams = [
    ("Use Case Diagram", "use_case_diagram.png", "Figure 5.1: Use Case Diagram"),
    ("Class Diagram", "class_diagram.png", "Figure 5.2: Class Diagram"),
    ("Activity Diagram", "activity_diagram.png", "Figure 5.3: Activity Diagram"),
    ("Sequence Diagram: Sign-to-Text", "sequence_sign.png", "Figure 5.4: Sequence Diagram (Sign-to-Text)"),
    ("Sequence Diagram: Speech-to-Sign", "sequence_speech.png", "Figure 5.5: Sequence Diagram (Speech-to-Sign)"),
    ("Entity Relationship (ER) Diagram", "er_diagram.png", "Figure 5.6: ER Diagram"),
]

for title, filename, caption in uml_diagrams:
    add_para(title, True, WD_ALIGN_PARAGRAPH.LEFT, 13)
    img_path = os.path.join(DIAGRAM_DIR, filename)
    if os.path.exists(img_path):
        doc.add_picture(img_path, width=Inches(6.0))
        doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER
    add_para(caption, False, WD_ALIGN_PARAGRAPH.CENTER, 11)
    doc.add_page_break()

add_para("5.3 DFD Diagrams", True, WD_ALIGN_PARAGRAPH.LEFT, 13)
dfd_diagrams = [
    ("Level 0 DFD (Context Diagram)", "dfd_level0.png", "Figure 5.7: Level 0 DFD"),
    ("Level 1 DFD", "dfd_level1.png", "Figure 5.8: Level 1 DFD"),
    ("Level 2 DFD (Translation Processes)", "dfd_level2.png", "Figure 5.9: Level 2 DFD"),
]
for title, filename, caption in dfd_diagrams:
    add_para(title, True, WD_ALIGN_PARAGRAPH.LEFT, 13)
    img_path = os.path.join(DIAGRAM_DIR, filename)
    if os.path.exists(img_path):
        doc.add_picture(img_path, width=Inches(6.0))
        doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER
    add_para(caption, False, WD_ALIGN_PARAGRAPH.CENTER, 11)
    if title != dfd_diagrams[-1][0]:
        doc.add_page_break()


# ═══════════════════════════════════════════════════════════════
# 6. CODE, IMPLEMENTATION AND RESULT
# ═══════════════════════════════════════════════════════════════
doc.add_page_break()
add_para("6. CODE, IMPLEMENTATION AND RESULT", True, WD_ALIGN_PARAGRAPH.LEFT, 16)
add_empty()

add_para("6.1 Implementation Details", True, WD_ALIGN_PARAGRAPH.LEFT, 13)
add_para("The implementation consists of the following key modules:", False, WD_ALIGN_PARAGRAPH.JUSTIFY, 13)
add_para(
    "1. MediaPipe Integration: Hand and pose landmarks are extracted iteratively using MediaPipe Holistic API across a 30-frame temporal window.\n"
    "2. Deep Learning Pipeline: Captured landmark features (258 dimensions per frame) are scaled and passed to a trained Keras Sequential model comprising Temporal Convolutional Network (TCN) blocks and LSTM layers to classify gestures into one of 40 potential ISL classes.\n"
    "3. NLP Grammar Engine: For the Speech-to-Sign mechanism, spaCy handles dependency parsing to reorganize English Subject-Verb-Object (SVO) structures into Indian Sign Language Object-Subject-Verb (OSV) semantic formats, omitting articles and auxiliary 'be' verbs.\n"
    "4. Web Integration: Flask governs the core routing logic, SQLAlchemy manages user session state (SQLite), and Flask-SocketIO binds the front-end Three.js web-worker events back to the server in real-time.",
    False, WD_ALIGN_PARAGRAPH.JUSTIFY, 13
)
add_empty()

add_para("6.2 Screenshots", True, WD_ALIGN_PARAGRAPH.LEFT, 13)
screenshots = [
    ("Login / Register Page", "login.png"),
    ("User Dashboard", "dashboard.png"),
    ("Sign-to-Text Mode", "sign.png"),
    ("Speech-to-Sign Mode", "speech.png"),
    ("ISL Dictionary", "dict.png"),
    ("Gamified Learning Module", "learn.png")
]

fig_num = 1
for title, filename in screenshots:
    add_para(f"6.2.{fig_num} {title}", True, WD_ALIGN_PARAGRAPH.LEFT, 13)
    img_path = os.path.join(SCREENSHOT_DIR, filename)
    if os.path.exists(img_path):
        doc.add_picture(img_path, width=Inches(6.0))
        doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER
    add_para(f"Figure 6.{fig_num}: {title}", False, WD_ALIGN_PARAGRAPH.CENTER, 11)
    add_empty()
    fig_num += 1


# ═══════════════════════════════════════════════════════════════
# 7. SYSTEM STUDY AND TESTING
# ═══════════════════════════════════════════════════════════════
doc.add_page_break()
add_para("7. SYSTEM STUDY AND TESTING", True, WD_ALIGN_PARAGRAPH.LEFT, 16)
add_empty()

add_para("7.1 Feasibility Study", True, WD_ALIGN_PARAGRAPH.LEFT, 13)
add_para("The feasibility study investigates the viability of the system under technical, economic, and operational standards.", False, WD_ALIGN_PARAGRAPH.JUSTIFY, 13)
add_para("• Technical Feasibility: The implementation capitalizes on open-source ML frameworks (TensorFlow) and web APIs (MediaPipe), making hardware acceleration unnecessary for inference. High performance is maintained using client-side WebGL.\n• Economic Feasibility: Since the target solution is software-deployed requiring only a built-in webcam, the cost barrier is virtually zero.\n• Operational Feasibility: The gamified dictionary helps flatten the learning curve for users unfamiliar with ISL, solidifying high operational viability.", False, WD_ALIGN_PARAGRAPH.JUSTIFY, 13)
add_empty()

add_para("7.2 System Testing", True, WD_ALIGN_PARAGRAPH.LEFT, 13)
add_para("Testing was conducted to ensure robustness, precision in detection, and minimal latency handling during real-time video streaming.", False, WD_ALIGN_PARAGRAPH.JUSTIFY, 13)
add_empty()

add_para("7.3 Types of Tests", True, WD_ALIGN_PARAGRAPH.LEFT, 13)
add_para("Unit Testing: Model validation tests confirmed that the LSTM-TCN accurately identified targeted phrases (e.g., 'Hello', 'Thank You') under diverse lighting conditions.\nIntegration Testing: Validation between the Flask backend text generation and Google STT confirmed that language switching worked continuously without socket disconnects.\nSystem Testing: The comprehensive end-to-end flow was tested; the avatar matched the grammatical outputs strictly defined by the NLP OSV parser without desynchronization.", False, WD_ALIGN_PARAGRAPH.JUSTIFY, 13)


# ═══════════════════════════════════════════════════════════════
# 8. CONCLUSION
# ═══════════════════════════════════════════════════════════════
doc.add_page_break()
add_para("8. CONCLUSION", True, WD_ALIGN_PARAGRAPH.LEFT, 16)
add_empty()
add_para('The "Multi-Lingual Sign Language to Speech and Speech to Sign Translator" establishes a critical, scalable framework for real-time human-to-human interaction breaking typical accessibility barriers. By abstracting the need for advanced hardware gloves via an accurate MediaPipe and LSTM-TCN integrated architecture, this project delivers high-accuracy sign classification directly to the browser. The addition of the Speech-to-Sign mechanism paired with the rule-based Indian Sign Language semantic generator successfully demonstrates that conversational continuity can be preserved between standard vocal languages and non-vocal ISL.', False, WD_ALIGN_PARAGRAPH.JUSTIFY, 13)
add_para('Furthermore, expanding beyond simple English translations into a fully localized multi-lingual solution extends the system’s usability to a massive population sector. Given its high prediction accuracy and low operational latency, Samvak proves to be an effective, responsive, and innovative technological intervention serving the Deaf community.', False, WD_ALIGN_PARAGRAPH.JUSTIFY, 13)


# ═══════════════════════════════════════════════════════════════
# 9. FUTURE ENHANCEMENT
# ═══════════════════════════════════════════════════════════════
doc.add_page_break()
add_para("9. FUTURE ENHANCEMENT", True, WD_ALIGN_PARAGRAPH.LEFT, 16)
add_empty()
add_para("While the current prototype validates the efficacy of bidrectional translation, multiple enhancements could scale its applicability in future versions:", False, WD_ALIGN_PARAGRAPH.JUSTIFY, 13)
add_para("1. Continuous Sign Recognition: Expanding from isolated phrases to connected sign language sequences by integrating Transformer-based architectures.\n2. Generative Avatar Motions: Shifting from predefined Three.js skeletal animations to Generative Adversarial Networks (GANs) that can organically render smooth, human-like avatar transitions.\n3. Regional Dialect Implementation: Collecting additional real-world data to expand the ISL datasets enabling recognition of region-specific linguistic differences.\n4. Mobile Application: Compiling the architecture into native iOS and Android build environments for improved mobile GPU performance optimization.", False, WD_ALIGN_PARAGRAPH.JUSTIFY, 13)


# ═══════════════════════════════════════════════════════════════
# REFERENCES
# ═══════════════════════════════════════════════════════════════
doc.add_page_break()
add_para("REFERENCES", True, WD_ALIGN_PARAGRAPH.LEFT, 16)
add_empty()

references = [
    "[1] Wadhawan, A., & Kumar, P. (2021). Sign Language Recognition Systems: A Decade Systematic Literature Review. Archives of Computational Methods in Engineering, 28(3), 785-813.",
    "[2] Lugaresi, C. et al. (2019). MediaPipe: A Framework for Building Perception Pipelines. arXiv preprint arXiv:1906.08172.",
    "[3] Hochreiter, S., & Schmidhuber, J. (1997). Long Short-Term Memory. Neural Computation, 9(8), 1735-1780.",
    "[4] Exploration Lab, IIT Kharagpur (2024). iSign: A Benchmark for Indian Sign Language Processing. Proceedings of IEEE CVPR.",
    "[5] Paudyal, P., Lee, J., & Banerjee, S. (2023). A Survey on Sign Language Translation: Neural and Rule-based Approaches. ACM Computing Surveys."
]

for ref in references:
    add_para(ref, False, WD_ALIGN_PARAGRAPH.JUSTIFY, 13)
    add_empty()

doc.save(r"E:\sam\Project documents\Samvak_ProjectReview_Final.docx")
print("Successfully generated final Word document!")
