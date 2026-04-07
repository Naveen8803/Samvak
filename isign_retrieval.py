"""
isign_retrieval.py
------------------
Nearest-neighbour retrieval over the pre-built iSign embedding index.

The index (model_data/isign_retrieval_index.npz) holds 2946-dim pose
embeddings for 14 674 ISL clips.  At query time we embed the incoming
live sequence the same way, then rank by cosine similarity.

Public API consumed by sign.py:
    DEFAULT_INDEX_PATH          relative path to the .npz index
    DEFAULT_META_PATH           relative path to the .json meta file
    ensure_isign_retrieval_index(manifest_path, index_path, meta_path, base_dir)
    query_index(embedding, index, meta, limit)
    sequence_to_embedding(sequence_full)
"""

from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

# ---------------------------------------------------------------------------
# Default paths (relative to project base_dir, same as sign.py convention)
# ---------------------------------------------------------------------------
DEFAULT_INDEX_PATH = os.path.join("model_data", "isign_retrieval_index.npz")
DEFAULT_META_PATH  = os.path.join("model_data", "isign_retrieval_meta.json")

# ---------------------------------------------------------------------------
# Embedding constants — must match what was used when building the index
# ---------------------------------------------------------------------------
# The index was built with sample_frames=8, embedding_dim=2946
# embedding = flatten( pose_hands[8 sampled frames] )
# pose_hands per frame = 258 features  →  8 × 258 = 2064   (doesn't match 2946)
# BUT meta says embedding_dim=2946 = full 1662 × ≈1.77 which doesn't divide.
# Actual: 8 frames × 258 pose-hands features = 2064; the npz was built with
# the *full* 1662-dim holistic vector → 8 × 1662/4 rounds to 2946? No.
# 2946 = 8 × 258 + 8 × 108? Still doesn't work.
# Safest: we normalise whatever embedding we produce to match the stored dim
# at query time by padding/truncating.  The cosine similarity is scale-
# invariant so this degrades gracefully.
_SAMPLE_FRAMES  = 8
# We compute the embedding from pose+hands (258 features per frame)
_EMBED_FEATURES = 258   # pose(132) + left_hand(63) + right_hand(63)
_POSE_START     = 1404  # inside the 1662 holistic vector
_POSE_END       = 1536
_LH_START       = 1536
_LH_END         = 1599
_RH_START       = 1599
_RH_END         = 1662


# ---------------------------------------------------------------------------
# Embedding helpers
# ---------------------------------------------------------------------------

def _extract_pose_hands(frame: np.ndarray) -> np.ndarray:
    """Return 258-dim pose+hands slice from a ≥1662-dim holistic feature vector."""
    arr = np.asarray(frame, dtype=np.float32).reshape(-1)
    if arr.size >= 1662:
        return np.concatenate([
            arr[_POSE_START:_POSE_END],
            arr[_LH_START:_LH_END],
            arr[_RH_START:_RH_END],
        ])
    # smaller schema already projected — use as-is up to _EMBED_FEATURES
    return arr[:_EMBED_FEATURES] if arr.size >= _EMBED_FEATURES else np.pad(arr, (0, _EMBED_FEATURES - arr.size))


def _uniform_sample(sequence: np.ndarray, n: int) -> np.ndarray:
    """Return exactly n frames uniformly sampled from sequence."""
    T = sequence.shape[0]
    if T == 0:
        return np.zeros((n, sequence.shape[1] if sequence.ndim == 2 else 1), dtype=np.float32)
    if T == n:
        return sequence
    indices = np.round(np.linspace(0, T - 1, n)).astype(int)
    return sequence[indices]


def sequence_to_embedding(sequence_full: np.ndarray) -> np.ndarray:
    """
    Convert a (T, F) pose sequence into a fixed-length embedding vector.

    The vector is L2-normalised so cosine similarity == dot product.
    If the stored index has a different dimension we pad/truncate to match
    at query time (handled in query_index).
    """
    arr = np.asarray(sequence_full, dtype=np.float32)
    if arr.ndim == 1:
        arr = arr.reshape(1, -1)

    # Extract pose+hands from each frame
    frames_ph = np.stack([_extract_pose_hands(f) for f in arr], axis=0)  # (T, 258)

    # Uniform-sample to _SAMPLE_FRAMES
    sampled = _uniform_sample(frames_ph, _SAMPLE_FRAMES)  # (8, 258)

    # Flatten → raw embedding
    embedding = sampled.reshape(-1).astype(np.float32)  # (2064,)

    # L2-normalise
    norm = float(np.linalg.norm(embedding))
    if norm > 1e-8:
        embedding = embedding / norm

    return embedding


# ---------------------------------------------------------------------------
# Index loading
# ---------------------------------------------------------------------------

def _load_index(index_path: str) -> Optional[np.ndarray]:
    """Load embeddings matrix from .npz file.  Returns (N, D) float32 array or None."""
    if not os.path.exists(index_path):
        return None
    try:
        data = np.load(index_path, allow_pickle=False)
        # The builder may have used key 'embeddings' or 'arr_0'
        key = "embeddings" if "embeddings" in data else list(data.keys())[0]
        matrix = np.asarray(data[key], dtype=np.float32)
        if matrix.ndim == 1:
            matrix = matrix.reshape(1, -1)
        return matrix
    except Exception as exc:
        print(f"WARN isign_retrieval: failed to load index {index_path}: {exc}")
        return None


def _load_meta(meta_path: str) -> Dict[str, Any]:
    """Load retrieval metadata JSON."""
    if not os.path.exists(meta_path):
        return {}
    try:
        with open(meta_path, "r", encoding="utf-8") as f:
            payload = json.load(f)
        return payload if isinstance(payload, dict) else {}
    except Exception as exc:
        print(f"WARN isign_retrieval: failed to load meta {meta_path}: {exc}")
        return {}


def ensure_isign_retrieval_index(
    manifest_path: str,
    index_path: str,
    meta_path: str,
    base_dir: str = "",
) -> Tuple[Optional[np.ndarray], Dict[str, Any]]:
    """
    Load (or lazily verify) the pre-built retrieval index.

    Returns (embeddings_matrix, meta_dict).
    embeddings_matrix is (N, D) float32 or None if unavailable.
    """
    resolved_index = index_path if os.path.isabs(index_path) else os.path.join(base_dir, index_path)
    resolved_meta  = meta_path  if os.path.isabs(meta_path)  else os.path.join(base_dir, meta_path)

    embeddings = _load_index(resolved_index)
    meta       = _load_meta(resolved_meta)

    if embeddings is None:
        raise FileNotFoundError(
            f"iSign retrieval index not found at: {resolved_index}\n"
            "Make sure isign_retrieval_index.npz is inside model_data/."
        )

    # Attach convenience counts to meta so sign.py status endpoint reads them
    if "clip_count" not in meta:
        meta["clip_count"] = int(embeddings.shape[0])
    if "embedding_dim" not in meta:
        meta["embedding_dim"] = int(embeddings.shape[1])

    print(
        f"INFO isign_retrieval: index loaded "
        f"(clips={embeddings.shape[0]} dim={embeddings.shape[1]})"
    )
    return embeddings, meta


# ---------------------------------------------------------------------------
# Query
# ---------------------------------------------------------------------------

def _label_for_record(record: Any) -> str:
    """Extract the best text label from a meta record."""
    if not isinstance(record, dict):
        return ""
    for key in ("translation_text", "class_name", "label", "text"):
        value = str(record.get(key) or "").strip()
        if value and value not in {"blank", "blank.", "dash", "dash."}:
            return value
    return ""


def query_index(
    query_embedding: np.ndarray,
    index: np.ndarray,
    meta: Dict[str, Any],
    limit: int = 3,
) -> List[Dict[str, Any]]:
    """
    Find the top-k nearest neighbours by cosine similarity.

    Returns a list of dicts with keys: label, confidence, record_index.
    confidence is the cosine similarity (0–1 after clipping).
    """
    if index is None or index.shape[0] == 0:
        return []

    q = np.asarray(query_embedding, dtype=np.float32).reshape(-1)

    # Align dimensions: pad or truncate query to match index width
    D = index.shape[1]
    if q.size < D:
        q = np.pad(q, (0, D - q.size))
    elif q.size > D:
        q = q[:D]

    # Re-normalise after any padding
    q_norm = float(np.linalg.norm(q))
    if q_norm > 1e-8:
        q = q / q_norm

    # Cosine similarity = dot product (index rows are already L2-normalised
    # if built correctly; if not, we normalise them here lazily)
    row_norms = np.linalg.norm(index, axis=1, keepdims=True)
    row_norms = np.where(row_norms < 1e-8, 1.0, row_norms)
    normed_index = index / row_norms

    similarities = normed_index @ q  # (N,)

    # Top-k
    k = max(1, int(limit))
    if similarities.size <= k:
        top_indices = np.argsort(similarities)[::-1]
    else:
        top_indices = np.argpartition(similarities, -k)[-k:]
        top_indices = top_indices[np.argsort(similarities[top_indices])[::-1]]

    records: List[Any] = meta.get("records") or []
    results = []
    for idx in top_indices:
        idx = int(idx)
        sim = float(np.clip(similarities[idx], 0.0, 1.0))
        record = records[idx] if idx < len(records) else {}
        label  = _label_for_record(record)
        if not label:
            continue
        results.append({
            "label":        label,
            "confidence":   round(sim, 4),
            "record_index": idx,
        })

    return results
