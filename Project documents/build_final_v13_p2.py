"""
build_final_v13_p2.py — Chapter 5: System Design
Uses FRESH matplotlib-generated diagrams from fresh_diagrams/
"""
import os

FRESH = os.path.join(BASE, "fresh_diagrams")

def fresh(name):
    return os.path.join(FRESH, name)

chapter("5.  SYSTEM DESIGN")

subhead("5.1 Input Design:")
body(
    'Sign-to-Speech Input Pipeline: (1) The browser activates the user\'s webcam via the '
    'HTML5 getUserMedia() API; (2) MediaPipe Holistic JavaScript processes each video frame '
    'and outputs 33 body pose landmarks (x, y, z, visibility), 21 left-hand landmarks (x, y, z), '
    'and 21 right-hand landmarks (x, y, z), yielding a 258-dimensional vector per frame; '
    '(3) sign.js maintains a circular buffer of the latest 30 frames; (4) when the buffer '
    'is full, a (1, 30, 258) Float32 tensor is constructed and passed to the TF.js LSTM model; '
    '(5) the predicted class index is mapped to the ISL phrase label; (6) if confidence exceeds '
    '0.75, the phrase is submitted for further processing.'
)
body(
    'Speech-to-Sign Input Pipeline: (1) User initiates recording via the "Speak" button; '
    '(2) the browser records audio via MediaRecorder API into a WebM blob; (3) the blob is '
    'uploaded via POST /speech/upload as multipart form data; (4) speech.py receives the file, '
    'converts to 16 kHz mono WAV using pydub, and calls SpeechRecognition with '
    'recognize_google(audio_data, language="en-IN"); (5) the transcribed English string is '
    'pre-processed by grammar_helper.py; (6) sent to Gemini API with ISL OSV system prompt; '
    '(7) Gemini returns a JSON gloss token array.'
)

subhead("5.2 UML Diagrams:")

# ── 5.2.1 USE CASE DIAGRAM ─────────────────────────────────────────────────
body("5.2.1 Use Case Diagram", space_before=6)
body(
    'The Use Case Diagram illustrates interactions between two user actors — Deaf User and '
    'Hearing User — and the eight core use cases of the Saṁvāk system, along with the '
    'external Gemini API integration for ISL gloss generation.'
)
insert_image(fresh("uc_diagram.png"), width=6.5,
             caption="Figure 5.1: Use Case Diagram — 2 Actors, 8 Use Cases, Gemini API")
pb()

# ── 5.2.2 CLASS DIAGRAM ────────────────────────────────────────────────────
body("5.2.2 Class Diagram", space_before=6)
body(
    'The Class Diagram shows all six data model classes defined in models.py using '
    'SQLAlchemy ORM: User, Translation, UserProgress, UserPreference, ContactMessage, '
    'and the utility LSTMModel class. Attributes, data types, methods, and one-to-many '
    'relationships between User and its child tables are shown.'
)
insert_image(fresh("class_diagram.png"), width=6.5,
             caption="Figure 5.2: Class Diagram — 6 SQLAlchemy Model Classes and Relationships")
pb()

# ── 5.2.3 SEQUENCE DIAGRAM ────────────────────────────────────────────────
body("5.2.3 Sequence Diagram — Sign-to-Speech Flow", space_before=6)
body(
    'The Sequence Diagram shows 11 messages across 6 lifelines for the complete '
    'sign-to-speech prediction cycle: User → Browser → MediaPipe → TF.js LSTM → '
    'Flask API → SQLite DB, with activation boxes and return arrows clearly showing '
    'the asynchronous flow.'
)
insert_image(fresh("sequence_diagram.png"), width=6.5,
             caption="Figure 5.3: Sequence Diagram — Sign-to-Speech (6 Lifelines, 11 Messages)")
pb()

# ── 5.2.4 ACTIVITY DIAGRAM ────────────────────────────────────────────────
body("5.2.4 Activity Diagram — Complete System Flow", space_before=6)
body(
    'The Activity Diagram shows the complete decision flow from browser launch through '
    'authentication, mode selection, and both Sign-to-Speech and Speech-to-Sign parallel '
    'branches, including all decision diamonds (authentication check, confidence threshold, '
    'continue or exit) and terminal states.'
)
insert_image(fresh("activity_diagram.png"), width=5.5,
             caption="Figure 5.4: Activity Diagram — Saṁvāk Complete System Decision Flow")
pb()

# ── 5.2.5 ER DIAGRAM ──────────────────────────────────────────────────────
body("5.2.5 Entity-Relationship (ER) Diagram", space_before=6)
body(
    'The ER Diagram shows all five database tables with primary keys (PK), foreign keys (FK), '
    'attribute names, data types, and cardinality notation. The USERS table has 1:N '
    'relationships with TRANSLATIONS and USER_PROGRESS, and a 1:1 relationship with '
    'USER_PREFERENCES. CONTACT_MESSAGES is a standalone table with no FK.'
)
insert_image(fresh("er_diagram.png"), width=6.5,
             caption="Figure 5.5: ER Diagram — Saṁvāk Database Schema (5 Tables, 3 Relationships)")
pb()

# ── 5.2.6 COMPONENT DIAGRAM ───────────────────────────────────────────────
body("5.2.6 Component Diagram", space_before=6)
body(
    'The Component Diagram shows four architectural layers (Frontend, REST API Interface, '
    'Backend Modules, Data & External Services) with all component boxes showing their roles. '
    'Bidirectional arrows between layers indicate HTTP/WebSocket communication protocols.'
)
insert_image(fresh("component_diagram.png"), width=6.5,
             caption="Figure 5.6: Component Diagram — 4-Layer Saṁvāk Architecture")
pb()

# ── 5.2.7 DEPLOYMENT DIAGRAM ──────────────────────────────────────────────
body("5.2.7 Deployment Diagram", space_before=6)
body(
    'The Deployment Diagram shows three hardware/service nodes: User Device (Browser) '
    'containing the browser-side ML stack, Render.com Cloud Server running Flask + '
    'Gunicorn + SQLite, and Google Cloud Services hosting the Gemini API and gTTS. '
    'Communication protocols (HTTPS/WSS, REST/JSON TLS) are labeled on each connection.'
)
insert_image(fresh("deployment_diagram.png"), width=6.5,
             caption="Figure 5.7: Deployment Diagram — Render.com + Google Cloud Nodes")
pb()

# ── 5.2.8 COLLABORATIVE DIAGRAM ───────────────────────────────────────────
body("5.2.8 Collaborative (Communication) Diagram", space_before=6)
body(
    'The Communication Diagram shows 7 object instances with 12 sequentially numbered '
    'messages flowing between :User, :Browser (JS), :MediaPipe Holistic, :TF.js LSTM, '
    ':Flask API, :iSign Retrieval, and :SQLite DB. Blue arrows indicate requests; '
    'red arrows indicate return messages.'
)
insert_image(fresh("collab_diagram.png"), width=6.5,
             caption="Figure 5.8: Collaborative Diagram — 7 Objects, 12 Numbered Messages")
pb()

# ═══════════════════════════════════════════════════════════════════════════
# 5.3 DFD DIAGRAMS
# ═══════════════════════════════════════════════════════════════════════════
subhead("5.3 DFD Diagrams:")

body("5.3.1 Data Flow Diagram — Level 0 (Context Diagram)", space_before=6)
body(
    'The Level 0 DFD shows the Saṁvāk system as a single central process (Process 0) '
    'with three external entities: User, Gemini API, and iSign Dataset. All data flows '
    'in and out of the system boundary are labeled with their data type.'
)
insert_image(fresh("dfd_level0.png"), width=6.0,
             caption="Figure 5.9: DFD Level 0 — Context Diagram (3 External Entities)")
pb()

body("5.3.2 Data Flow Diagram — Level 1 (Sub-Processes)", space_before=6)
body(
    'The Level 1 DFD decomposes the system into 7 numbered sub-processes: (1.0) Pose '
    'Extraction via MediaPipe, (2.0) LSTM Classification, (3.0) Language Translation, '
    '(4.0) gTTS Speech Synthesis, (5.0) STT Transcription, (6.0) ISL Gloss Conversion '
    'via Gemini API, and (7.0) Three.js Avatar Animation. Two data stores — D1: SQLite '
    'DB and D2: iSign cosine index — are shown with their read/write data flows.'
)
insert_image(fresh("dfd_level1.png"), width=6.5,
             caption="Figure 5.10: DFD Level 1 — 7 Sub-Processes, 2 Data Stores")
pb()

doc.save(OUT)
print(f"Chapter 5 (fresh diagrams) saved: {OUT}")
