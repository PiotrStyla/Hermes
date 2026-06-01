"""μ-law codec + resampling for Twilio Media Streams.

Uses Python's built-in audioop for correct ITU-T G.711 μ-law encoding.
"""

from __future__ import annotations

import audioop

import numpy as np


def pcm_to_mulaw(pcm: np.ndarray) -> bytes:
    """Encode int16 PCM → μ-law bytes (ITU-T G.711)."""
    return audioop.lin2ulaw(pcm.tobytes(), 2)


def mulaw_to_pcm(data: bytes) -> np.ndarray:
    """Decode μ-law bytes → int16 PCM."""
    raw = audioop.ulaw2lin(data, 2)
    return np.frombuffer(raw, dtype=np.int16)


def resample_16k_to_8k(pcm_16k: np.ndarray) -> np.ndarray:
    return pcm_16k[::2].copy()


def resample_8k_to_16k(pcm_8k: np.ndarray) -> np.ndarray:
    n = len(pcm_8k)
    out = np.zeros(n * 2, dtype=np.int16)
    out[::2] = pcm_8k
    if n > 1:
        out[1:-1:2] = ((pcm_8k[:-1].astype(np.int32) + pcm_8k[1:].astype(np.int32)) // 2).astype(np.int16)
    return out
