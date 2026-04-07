import os
import sys
import time

import numpy as np

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)


def section(title):
    bar = '-' * 55
    print(f'\n{bar}')
    print(f'  {title}')
    print(bar)


def ok(msg):
    print(f'  OK   {msg}')


def warn(msg):
    print(f'  WARN {msg}')


def fail(msg):
    print(f'  FAIL {msg}')


section('1. isign_retrieval module')
try:
    from isign_retrieval import (
        DEFAULT_INDEX_PATH,
        DEFAULT_META_PATH,
        ensure_isign_retrieval_index,
        query_index,
        sequence_to_embedding,
    )
    ok('isign_retrieval imported successfully')
except ImportError as exc:
    fail(f'Import failed: {exc}')
    fail('Copy isign_retrieval.py into the project root and retry.')
    sys.exit(1)

section('2. iSign retrieval index')
index_path = os.path.join(BASE_DIR, DEFAULT_INDEX_PATH)
meta_path = os.path.join(BASE_DIR, DEFAULT_META_PATH)

try:
    embeddings, meta = ensure_isign_retrieval_index(
        manifest_path='model_data/data_manifest.json',
        index_path=index_path,
        meta_path=meta_path,
        base_dir=BASE_DIR,
    )
    ok(f'Index loaded: {embeddings.shape[0]} clips, dim={embeddings.shape[1]}')
    ok(f"Unique texts: {meta.get('unique_text_count', '?')}")
except Exception as exc:
    fail(f'Index load failed: {exc}')
    sys.exit(1)

section('3. Embedding function')
dummy_sequence = np.random.randn(30, 1662).astype(np.float32)
dummy_sequence[:, 1536:1599] = np.random.randn(30, 63).astype(np.float32) * 0.3
embedding = sequence_to_embedding(dummy_sequence)
ok(f'Embedding shape: {embedding.shape} norm={np.linalg.norm(embedding):.4f}')

section('4. Nearest-neighbour query')
t0 = time.perf_counter()
results = query_index(embedding, embeddings, meta, limit=3)
latency = (time.perf_counter() - t0) * 1000
if results:
    ok(f'Query returned {len(results)} results in {latency:.1f} ms')
    for result in results:
        print(f"      label='{result['label']}' confidence={result['confidence']:.3f}")
else:
    warn('Query returned no results')

section('5. LSTM sign model')
lstm_path = os.path.join(BASE_DIR, 'sign_language.h5')
if not os.path.exists(lstm_path):
    warn(f'Model file not found: {lstm_path}')
else:
    try:
        import tensorflow as tf
        model = tf.keras.models.load_model(lstm_path, compile=False)
        ok(f'LSTM loaded: input_shape={model.input_shape}')
        dummy = np.zeros((1, 30, model.input_shape[-1]), dtype=np.float32)
        probs = model.predict(dummy, verbose=0)[0]
        ok(f'Warm-up predict OK: output classes={len(probs)}')
    except Exception as exc:
        warn(f'LSTM load failed: {exc}')

section('6. POST /predict-sign via test client')
try:
    try:
        from dotenv import load_dotenv
        load_dotenv(os.path.join(BASE_DIR, '.env'))
    except ImportError:
        pass

    from app import app as flask_app

    with flask_app.test_client() as client:
        payload = {
            'prediction': 'i am fine thank you sir',
            'confidence': 0.85,
            'sequence': dummy_sequence.tolist(),
            'target_language': 'english',
            'mode': 'accuracy',
        }
        resp = client.post('/predict-sign', json=payload, content_type='application/json')
        data = resp.get_json() or {}
        if resp.status_code == 200:
            ok(
                f"Status 200 - engine='{data.get('engine')}' prediction='{data.get('prediction')}' "
                f"confidence={data.get('confidence', 0):.2f}"
            )
        else:
            warn(f'Status {resp.status_code}: {data}')
except Exception as exc:
    warn(f'Test client error: {exc}')

section('7. POST /api/speech-to-sign via test client')
try:
    with flask_app.test_client() as client:
        payload = {
            'text': 'How are you?',
            'input_language': 'en-IN',
            'sign_language': 'ISL',
            'render_mode': '3d_avatar_only',
            'realtime_mode': 'final',
        }
        resp = client.post('/api/speech-to-sign', json=payload, content_type='application/json')
        data = resp.get_json() or {}
        if resp.status_code == 200:
            ok(f"Status 200 - sign_text='{data.get('sign_text')}'")
            tokens = data.get('sign_tokens', [])
            ok(f"Tokens ({len(tokens)}): {[t.get('gesture') for t in tokens[:5]]}")
        else:
            warn(f'Status {resp.status_code}: {data}')
except Exception as exc:
    warn(f'Test client error: {exc}')

section('8. grammar_helper ISL gloss conversion')
try:
    from grammar_helper import english_to_isl_glosses

    test_sentence = 'How are you doing today?'
    t0 = time.perf_counter()
    glosses = english_to_isl_glosses(test_sentence)
    latency = (time.perf_counter() - t0) * 1000
    if glosses:
        ok(f'ISL glosses ({latency:.0f} ms): {glosses}')
    else:
        warn('Returned empty glosses - check GEMINI_API_KEY')
except Exception as exc:
    warn(f'grammar_helper error: {exc}')

section('Summary')
print('  Real-time pipeline check complete.')
print('  Start the server with:')
print('      python run.py')
print('  Then open http://127.0.0.1:5000/sign-to-text or /speech-to-sign')
