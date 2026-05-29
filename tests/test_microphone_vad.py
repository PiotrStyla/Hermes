"""Tests for Microphone VAD backend selection and the RMS fallback.

These tests mock sounddevice so they run without any audio hardware.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from src.voice.microphone import Microphone


def _fake_stream(frames: list[np.ndarray]):
    """Build a context-manager mock whose .read() yields the given frames."""
    stream = MagicMock()
    stream.__enter__ = MagicMock(return_value=stream)
    stream.__exit__ = MagicMock(return_value=False)
    calls = {"i": 0}

    def read(n):
        i = calls["i"]
        calls["i"] += 1
        frame = frames[i] if i < len(frames) else np.zeros(n, dtype=np.int16)
        return frame.reshape(-1, 1), False

    stream.read.side_effect = read
    return stream


# ---- Backend selection ----

def test_backend_is_webrtcvad_when_available() -> None:
    mic = Microphone(use_webrtcvad=True)
    # webrtcvad-wheels is in requirements, so it should be the active backend.
    assert mic.backend == "webrtcvad"


def test_force_rms_backend() -> None:
    mic = Microphone(use_webrtcvad=False)
    assert mic.backend == "rms"


def test_unsupported_sample_rate_falls_back_to_rms() -> None:
    mic = Microphone(sample_rate=44100)  # not a webrtcvad rate
    assert mic.backend == "rms"


def test_aggressiveness_is_clamped() -> None:
    assert Microphone(vad_aggressiveness=9).vad_aggressiveness == 3
    assert Microphone(vad_aggressiveness=-5).vad_aggressiveness == 0


# ---- RMS fallback recording ----

def test_rms_stops_after_silence() -> None:
    mic = Microphone(
        use_webrtcvad=False,
        chunk_duration=0.1,
        silence_threshold=0.05,
        silence_duration=0.3,   # 3 silent chunks
        min_recording=0.1,
        max_recording=2.0,
        warmup=0.0,
    )
    loud = (np.ones(1600, dtype=np.int16) * 5000)   # high RMS
    quiet = np.zeros(1600, dtype=np.int16)          # silence
    frames = [loud, loud, quiet, quiet, quiet, quiet]
    with patch("sounddevice.InputStream", return_value=_fake_stream(frames)):
        audio = mic.record_until_silence()
    # Should have stopped around the 3rd consecutive silent chunk, not run to max.
    assert audio.size > 0
    assert audio.size < 1600 * len(frames)


def test_rms_empty_returns_zero_array() -> None:
    mic = Microphone(use_webrtcvad=False, max_recording=0.0)
    with patch("sounddevice.InputStream", return_value=_fake_stream([])):
        audio = mic.record_until_silence()
    assert audio.size == 0


# ---- WebRTC VAD recording (mock the Vad classifier) ----

def test_webrtcvad_stops_after_speech_then_silence() -> None:
    mic = Microphone(
        use_webrtcvad=True,
        silence_duration=0.09,   # 3 frames @30ms
        min_recording=0.03,
        max_recording=1.0,
        warmup=0.0,
    )
    if mic.backend != "webrtcvad":
        pytest.skip("webrtcvad not installed")

    frame_samples = int(mic.sample_rate * 0.03)
    blob = np.ones(frame_samples, dtype=np.int16)
    # speech, speech, silence, silence, silence -> should break on 3rd silence
    speech_flags = [True, True, False, False, False, False]
    frames = [blob for _ in speech_flags]

    flags = iter(speech_flags)
    mic._vad = MagicMock()
    mic._vad.is_speech.side_effect = lambda *a, **k: next(flags, False)

    with patch("sounddevice.InputStream", return_value=_fake_stream(frames)):
        audio = mic.record_until_silence()
    assert audio.size > 0


def test_webrtcvad_ignores_silence_before_speech() -> None:
    """Leading silence must not trigger an early stop before speech begins."""
    mic = Microphone(
        use_webrtcvad=True,
        silence_duration=0.06,   # 2 frames
        min_recording=0.0,
        max_recording=0.6,       # 20 frames cap
        warmup=0.0,
    )
    if mic.backend != "webrtcvad":
        pytest.skip("webrtcvad not installed")

    frame_samples = int(mic.sample_rate * 0.03)
    blob = np.ones(frame_samples, dtype=np.int16)
    # Many leading silence frames, then speech, then trailing silence.
    speech_flags = [False] * 10 + [True, True] + [False, False, False]
    frames = [blob for _ in range(len(speech_flags) + 5)]

    flags = iter(speech_flags)
    mic._vad = MagicMock()
    mic._vad.is_speech.side_effect = lambda *a, **k: next(flags, False)

    with patch("sounddevice.InputStream", return_value=_fake_stream(frames)):
        audio = mic.record_until_silence()
    # Captured well past the 2-frame silence window because speech hadn't begun.
    assert audio.size > frame_samples * 10
