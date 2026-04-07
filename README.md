# Saṁvāk (Samvak) — Where Signs Speak

> Real-time multilingual translation between Indian Sign Language (ISL) and speech, powered by deep learning and the [iSign dataset](https://huggingface.co/datasets/Exploration-Lab/iSign).

## ✨ Features

| Feature | Description |
|---|---|
| **Sign-to-Text** | Real-time ISL recognition via webcam using LSTM + iSign retrieval (40 ISL phrases, 94.6% accuracy) |
| **Speech-to-Sign** | Voice/text input → 3D avatar performs ISL signs with Gemini-powered gloss conversion |
| **Dictionary** | Browse ISL signs with image sequences from the ISL CSLRT Corpus |
| **Learn** | Interactive sign learning with progress tracking and XP gamification |
| **Multilingual** | Output in 8 languages: English, Hindi, Telugu, Tamil, Kannada, Malayalam, Spanish, French |
| **Dashboard** | User progress tracking with XP, levels, and translation history |
| **Text-to-Speech** | Speak recognized signs aloud via gTTS (or browser TTS fallback) |

## 🏗️ Architecture

```
┌──────────────┐     WebSocket / REST      ┌──────────────────┐
│   Browser    │ ◄────────────────────────► │   Flask + WSGI   │
│              │                            │   (app.py)       │
│  TFJS LSTM   │                            ├──────────────────┤
│  MediaPipe   │                            │  sign.py         │ ← LSTM, iSign retrieval, translation model
│  3D Avatar   │                            │  speech.py       │ ← STT + ISL gloss + avatar tokens
│  speech.js   │                            │  grammar_helper  │ ← Gemini ISL gloss conversion
│  sign.js     │                            │  dictionary.py   │ ← Dataset browser
└──────────────┘                            │  auth.py         │ ← Registration, login, settings
                                            └──────────────────┘
                                                    │
                                            ┌───────┴────────┐
                                            │   SQLite DB    │
                                            │   (database.db)│
                                            └────────────────┘
```

## 📋 Prerequisites

- **Python** 3.10 or higher
- **ffmpeg** installed and on PATH (required by `pydub` for audio conversion)
- **Webcam** for Sign-to-Text feature
- **Microphone** for Speech-to-Sign feature (optional — text input also works)

## 🚀 Quick Start

### 1. Clone & Install

```bash
# Install Python dependencies
pip install -r requirements.txt

# Download spaCy English model (for speech tokenization)
python -m spacy download en_core_web_sm
```

### 2. Configure Environment

```bash
# Copy the environment template
cp .env.template .env
```

Edit `.env` and set your **Gemini API key** (get one at [Google AI Studio](https://aistudio.google.com/app/apikey)):

```
GEMINI_API_KEY=your_key_here
```

> **Note:** Without a Gemini API key, Speech-to-Sign still works but uses naive word-order instead of proper ISL grammar (OSV structure).

### 3. Run

```bash
python run.py
```

Open [http://127.0.0.1:5000](http://127.0.0.1:5000) in your browser.

## 🧠 ML Models (Pre-trained on iSign)

All models are trained on the [Exploration-Lab/iSign](https://huggingface.co/datasets/Exploration-Lab/iSign) dataset:

| Model | File | Description |
|---|---|---|
| LSTM Sign Classifier | `sign_language.h5` | 40 ISL phrases, 94.6% top-1 accuracy, pose+hands (258 features) |
| TFJS Browser Model | `static/models/tfjs_lstm/` | Same LSTM exported for in-browser inference via TensorFlow.js |
| Translation Model | `translation_model.keras` | Sequence classification on iSign pose features |
| iSign Retrieval Index | `model_data/isign_retrieval_index.npz` | 14,674 ISL clip embeddings for nearest-neighbor lookup |
| Geometry Classifier | `geometry_brain.py` | Rule-based fallback: YES, NO, HELLO, I LOVE YOU |

### Model Data

The `model_data/` directory contains 101 ISL phrase folders with extracted pose features (`.npy` files) from the iSign dataset, covering phrases like:
- *"how old are you"*, *"i am fine thank you sir"*, *"take care of yourself"*
- *"what is your phone number"*, *"which college/school are you from"*
- *"he would be coming today"*, *"pour some more water into the glass"*

## 📁 Project Structure

```
e:\sam\
├── app.py                  # Flask app, routes, API endpoints
├── run.py                  # Server startup with health checks
├── config.py               # App configuration
├── extensions.py            # SQLAlchemy + SocketIO instances
├── models.py               # DB models (User, Translation, Progress, etc.)
├── sign.py                 # Sign-to-Text pipeline (3700+ lines)
├── speech.py               # Speech-to-Sign pipeline
├── grammar_helper.py       # Gemini ISL gloss conversion
├── geometry_brain.py       # Heuristic sign classifier
├── fingerspell_recognizer.py # Fingerspell scaffold
├── dictionary.py           # Dictionary browser API
├── isign_retrieval.py      # iSign nearest-neighbor retrieval
├── model_assets.py         # Feature schema + model utilities
├── auth.py                 # Authentication (register/login/settings)
├── .env                    # Environment variables (not in git)
├── requirements.txt        # Python dependencies
├── sign_language.h5        # Trained LSTM model
├── translation_model.keras # Translation model
├── database.db             # SQLite database
├── static/
│   ├── css/styles.css      # Global styles
│   ├── js/
│   │   ├── app.js          # Navigation, auth menu
│   │   ├── sign.js         # Sign-to-Text frontend (1600+ lines)
│   │   ├── speech.js       # Speech-to-Sign + 3D avatar
│   │   └── hand_avatar.js  # Hand avatar renderer
│   └── models/
│       ├── tfjs_lstm/      # TF.js model for browser inference
│       ├── model_registry.json
│       └── translation_registry.json
├── templates/              # Jinja2 HTML templates
│   ├── base.html           # Base layout
│   ├── index.html          # Homepage
│   ├── sign_to_text.html   # Sign-to-Text page
│   ├── speech_to_sign.html # Speech-to-Sign page
│   ├── learn.html          # Interactive learning
│   ├── dictionary.html     # Sign dictionary
│   ├── dashboard.html      # User dashboard
│   ├── history.html        # Translation history
│   ├── contact.html        # Contact form
│   ├── settings.html       # User settings
│   ├── login.html          # Login page
│   └── register.html       # Registration page
└── model_data/             # 101 ISL phrase folders with pose data
    ├── isign_retrieval_index.npz   # 132MB retrieval index
    ├── isign_retrieval_meta.json   # Retrieval metadata
    ├── production_classes.json     # 40 production classes
    └── [101 phrase folders]/       # Pose .npy + metadata .json
```

## 🔧 Environment Variables

| Variable | Required | Description |
|---|---|---|
| `SECRET_KEY` | Yes | Flask session secret key |
| `GEMINI_API_KEY` | Recommended | Google Gemini API key for ISL gloss conversion |
| `HYBRID_SEQUENCE_PRIORITY` | No | `translation_first` (default) or `hf_first` |
| `ISIGN_RETRIEVAL_MIN_CONFIDENCE` | No | Minimum cosine similarity for retrieval (default: 0.82) |
| `FLASK_SECURE_COOKIE` | No | Set to `1` for HTTPS deployments |

## 📚 External Data (Optional)

### ISL CSLRT Corpus

The Dictionary and Learn pages can display sign image sequences from the ISL CSLRT Corpus. Place it at:

```
e:\sam\ISL_CSLRT_Corpus\Frames_Word_Level\
```

Without this dataset, the Dictionary and Learn "Watch" features show no image sequences. All other features (Sign-to-Text, Speech-to-Sign, etc.) work without it.

## 🙏 Acknowledgments

- **iSign Dataset**: [Exploration-Lab/iSign](https://huggingface.co/datasets/Exploration-Lab/iSign) — Indian Sign Language benchmark (ACL 2024)
- **MediaPipe**: Google's real-time pose estimation
- **TensorFlow / TensorFlow.js**: Model training and browser inference
- **Gemini API**: ISL grammar conversion
- **ISL CSLRT Corpus**: Sign video frames for dictionary

## 📄 License

This project uses the iSign dataset which is free for research use but not for commercial purposes. See the [iSign license](https://huggingface.co/datasets/Exploration-Lab/iSign) for details.
