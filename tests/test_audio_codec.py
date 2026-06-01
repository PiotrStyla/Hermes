"""Tests for audio codec (μ-law ↔ PCM, resampling)."""
from __future__ import annotations

import numpy as np

from src.telephony.audio_codec import (
    mulaw_to_pcm,
    pcm_to_mulaw,
    resample_16k_to_8k,
    resample_8k_to_16k,
)


def test_mulaw_roundtrip_silence() -> None:
    pcm = np.zeros(160, dtype=np.int16)
    encoded = pcm_to_mulaw(pcm)
    decoded = mulaw_to_pcm(encoded)
    assert len(decoded) == len(pcm)
    assert np.all(np.abs(decoded) < 100)


def test_mulaw_roundtrip_speech_level() -> None:
    rng = np.random.RandomState(42)
    pcm = (rng.randn(800) * 4000).astype(np.int16)
    encoded = pcm_to_mulaw(pcm)
    decoded = mulaw_to_pcm(encoded)
    assert len(decoded) == len(pcm)
    # μ-law is lossy but preserves sign for non-tiny samples
    significant = np.abs(pcm) > 50
    assert np.all((pcm[significant] >= 0) == (decoded[significant] >= 0))


def test_resample_16k_to_8k_halves_length() -> None:
    pcm = np.arange(1600, dtype=np.int16)
    out = resample_16k_to_8k(pcm)
    assert len(out) == 800
    assert out[0] == pcm[0]
    assert out[1] == pcm[2]


def test_resample_8k_to_16k_doubles_length() -> None:
    pcm = np.arange(80, dtype=np.int16)
    out = resample_8k_to_16k(pcm)
    assert len(out) == 160
    assert out[0] == pcm[0]
    assert out[2] == pcm[1]


def test_mulaw_empty_input() -> None:
    pcm = np.zeros(0, dtype=np.int16)
    encoded = pcm_to_mulaw(pcm)
    assert encoded == b""
    decoded = mulaw_to_pcm(encoded)
    assert len(decoded) == 0
