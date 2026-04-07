import argparse
import os
import sys


def load_dotenv_if_available():
    try:
        from dotenv import load_dotenv
        env_path = os.path.join(os.path.dirname(__file__), '.env')
        if os.path.exists(env_path):
            load_dotenv(env_path)
            print(f'INFO: Loaded environment from {env_path}')
        else:
            print('INFO: No .env file found - using system environment variables.')
    except ImportError:
        print('INFO: python-dotenv not installed; skipping .env load.')


def check_critical_imports():
    missing = []
    checks = [
        ('flask', 'flask'),
        ('flask_socketio', 'flask-socketio'),
        ('flask_login', 'flask-login'),
        ('flask_sqlalchemy', 'flask-sqlalchemy'),
        ('numpy', 'numpy'),
        ('eventlet', 'eventlet'),
    ]
    for module, package in checks:
        try:
            __import__(module)
        except ImportError:
            missing.append(package)

    if missing:
        print('\nERROR: Missing packages - run:\n')
        print(f"    pip install {' '.join(missing)}\n")
        sys.exit(1)


def check_model_files():
    base = os.path.dirname(os.path.abspath(__file__))
    checks = {
        'LSTM sign model': os.path.join(base, 'sign_language.h5'),
        'Translation model': os.path.join(base, 'translation_model.keras'),
        'TF.js labels': os.path.join(base, 'static', 'models', 'tfjs_lstm', 'labels.json'),
        'TF.js model.json': os.path.join(base, 'static', 'models', 'tfjs_lstm', 'model.json'),
        'iSign retrieval index': os.path.join(base, 'model_data', 'isign_retrieval_index.npz'),
        'iSign retrieval meta': os.path.join(base, 'model_data', 'isign_retrieval_meta.json'),
    }
    all_ok = True
    for label, path in checks.items():
        exists = os.path.exists(path)
        status = 'OK' if exists else 'MISSING'
        print(f'  {status}  {label}: {os.path.relpath(path, base)}')
        if not exists:
            all_ok = False

    if not all_ok:
        print('\n  Some model files are missing. The server will start but inference will fall back to geometry heuristics.\n')

    print('  OK  ISL gloss conversion: local iSign vocabulary (no API required)')


def main():
    parser = argparse.ArgumentParser(description='Samvak real-time server')
    parser.add_argument('--host', default='127.0.0.1', help='Bind host (default: 127.0.0.1)')
    parser.add_argument('--port', type=int, default=5000, help='Bind port (default: 5000)')
    parser.add_argument('--debug', action='store_true', help='Enable Flask debug mode')
    args = parser.parse_args()

    load_dotenv_if_available()
    check_critical_imports()

    print('\nINFO: Checking model files...')
    check_model_files()

    print('\nINFO: Starting Samvak...')
    try:
        from app import app, socketio
    except ImportError as exc:
        print(f'\nERROR: Could not import app: {exc}')
        print('    Make sure isign_retrieval.py is in the same directory as app.py')
        sys.exit(1)

    print(f'    Listening on http://{args.host}:{args.port}/\n')

    socketio.run(
        app,
        host=args.host,
        port=args.port,
        debug=args.debug,
        use_reloader=False,
    )


if __name__ == '__main__':
    main()
