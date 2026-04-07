#!/usr/bin/env python3
"""
Quick Start Script for Saṁvāk
This script helps verify setup and provides quick installation checks.
"""

import sys
import subprocess
import os

def check_python_version():
    """Check if Python version is 3.8+"""
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 8):
        print("❌ Python 3.8+ required. Current version:", sys.version)
        return False
    print(f"✅ Python {version.major}.{version.minor}.{version.micro}")
    return True

def check_dependencies():
    """Check if required packages are installed"""
    required = [
        'flask', 'flask_login', 'flask_sqlalchemy', 'opencv-python',
        'mediapipe', 'numpy', 'speech_recognition', 'pydub', 'scipy',
        'deep_translator', 'gtts'
    ]
    
    missing = []
    for package in required:
        try:
            if package == 'opencv-python':
                __import__('cv2')
            elif package == 'flask_login':
                __import__('flask_login')
            elif package == 'flask_sqlalchemy':
                __import__('flask_sqlalchemy')
            elif package == 'speech_recognition':
                __import__('speech_recognition')
            elif package == 'deep_translator':
                __import__('deep_translator')
            else:
                __import__(package.replace('-', '_'))
            print(f"✅ {package}")
        except ImportError:
            print(f"❌ {package} - MISSING")
            missing.append(package)
    
    return missing

def check_spacy_model():
    """Check if spaCy model is installed"""
    try:
        import spacy
        nlp = spacy.load("en_core_web_sm")
        print("✅ spaCy model 'en_core_web_sm' installed")
        return True
    except OSError:
        print("❌ spaCy model 'en_core_web_sm' not found")
        print("   Run: python -m spacy download en_core_web_sm")
        return False

def check_ffmpeg():
    """Check if ffmpeg is installed"""
    try:
        result = subprocess.run(['ffmpeg', '-version'], 
                              capture_output=True, 
                              text=True,
                              timeout=5)
        if result.returncode == 0:
            print("✅ ffmpeg installed")
            return True
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    
    print("❌ ffmpeg not found in PATH")
    print("   Install from: https://ffmpeg.org/download.html")
    return False

def check_model_file():
    """Check if model file exists"""
    from config import Config
    model_file = os.path.join(Config.ML_MODELS_DIR, "reference_data.pkl")
    if os.path.exists(model_file):
        print(f"✅ Model file found: {model_file}")
        return True
    else:
        print(f"⚠️  Model file not found: {model_file}")
        print("   Run: python train_model.py")
        return False

def main():
    print("=" * 50)
    print("Samvak Setup Verification")
    print("=" * 50)
    print()
    
    all_ok = True
    
    print("1. Checking Python version...")
    if not check_python_version():
        all_ok = False
    print()
    
    print("2. Checking Python dependencies...")
    missing = check_dependencies()
    if missing:
        print(f"\n   Install missing packages: pip install {' '.join(missing)}")
        all_ok = False
    print()
    
    print("3. Checking spaCy model...")
    if not check_spacy_model():
        all_ok = False
    print()
    
    print("4. Checking ffmpeg...")
    if not check_ffmpeg():
        all_ok = False
    print()
    
    print("5. Checking model file...")
    model_exists = check_model_file()
    if not model_exists:
        print("   (Warning: Model training recommended but not required for basic functionality)")
    print()
    
    print("=" * 50)
    if all_ok and model_exists:
        print("✅ All checks passed! You're ready to run the application.")
        print("\nStart the server with: python app.py")
    elif all_ok:
        print("⚠️  Basic setup complete, but model training recommended.")
        print("\nStart the server with: python app.py")
        print("Train the model with: python train_model.py")
    else:
        print("❌ Some checks failed. Please fix the issues above.")
        print("\nInstall dependencies: pip install -r requirements.txt")
    print("=" * 50)

if __name__ == "__main__":
    main()
