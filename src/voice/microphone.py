"""Microphone capture with voice activity detection (VAD).

Records 16 kHz mono int16 audio until the user stops speaking, or until a hard
timeout is reached.

Two detection backends:
- WebRTC VAD (preferred): Google's `webrtcvad` classifies each 30 ms frame as
  speech / non-speech. Far more robust to background noise and natural pauses
  than a raw energy threshold.
- RMS energy (fallback): used automatically if `webrtcvad` is not installed,
  so voice mode keeps working without the extra dependency.
"""

from __future__ import annotations

import numpy as np
import sounddevice as sd

try:  # optional dependency — fall back to RMS if missing
    import webrtcvad
    _HAS_WEBRTCVAD = True
except ImportError:  # pragma: no cover - exercised only without the dep
    webrtcvad = None  # type: ignore[assignment]
    _HAS_WEBRTCVAD = False


SAMPLE_RATE = 16000  # what Whisper expects
VAD_FRAME_MS = 30    # webrtcvad accepts 10 / 20 / 30 ms frames only


class Microphone:
    """Silence-aware microphone recorder (WebRTC VAD with RMS fallback)."""

    def __init__(
        self,
        sample_rate: int = SAMPLE_RATE,
        chunk_duration: float = 0.1,        # 100 ms blocks (RMS fallback only)
        silence_threshold: float = 0.012,   # RMS energy below this = "silent"
        silence_duration: float = 2.0,      # consecutive silence to stop
        min_recording: float = 1.5,         # min length before silence stops it
        max_recording: float = 30.0,        # hard cap
        warmup: float = 0.2,                # initial chunks always treated as voice
        vad_aggressiveness: int = 2,        # 0 (lenient) .. 3 (aggressive) for webrtcvad
        use_webrtcvad: bool = True,         # set False to force the RMS fallback
    ):
        self.sample_rate = sample_rate
        self.chunk_duration = chunk_duration
        self.silence_threshold = silence_threshold
        self.silence_duration = silence_duration
        self.min_recording = min_recording
        self.max_recording = max_recording
        self.warmup = warmup
        self.vad_aggressiveness = max(0, min(3, vad_aggressiveness))

        self._vad = None
        if use_webrtcvad and _HAS_WEBRTCVAD and sample_rate in (8000, 16000, 32000, 48000):
            self._vad = webrtcvad.Vad(self.vad_aggressiveness)

    @property
    def backend(self) -> str:
        """Which detector is active: 'webrtcvad' or 'rms'."""
        return "webrtcvad" if self._vad is not None else "rms"

    def record_until_silence(self) -> np.ndarray:
        """Capture from the default input device and return int16 mono audio."""
        if self._vad is not None:
            return self._record_webrtcvad()
        return self._record_rms()

    # ---- WebRTC VAD backend ----

    def _record_webrtcvad(self) -> np.ndarray:
        """Frame-based speech detection with a hangover before stopping."""
        frame_samples = int(self.sample_rate * VAD_FRAME_MS / 1000)
        frame_secs = VAD_FRAME_MS / 1000.0
        silence_frames_needed = int(self.silence_duration / frame_secs)
        min_frames = int(self.min_recording / frame_secs)
        max_frames = int(self.max_recording / frame_secs)
        warmup_frames = int(self.warmup / frame_secs)

        collected: list[np.ndarray] = []
        silent_count = 0
        speech_started = False

        with sd.InputStream(
            samplerate=self.sample_rate,
            channels=1,
            dtype="int16",
            blocksize=frame_samples,
        ) as stream:
            for i in range(max_frames):
                frame, _ = stream.read(frame_samples)
                frame = frame.flatten()
                collected.append(frame)

                # webrtcvad needs exactly frame_samples; pad the final short read.
                if len(frame) < frame_samples:
                    frame = np.pad(frame, (0, frame_samples - len(frame)))

                is_speech = self._vad.is_speech(frame.tobytes(), self.sample_rate)

                if i < warmup_frames:
                    continue
                if is_speech:
                    speech_started = True
                    silent_count = 0
                    continue

                # Non-speech frame. Don't start the silence countdown until the
                # user has actually begun speaking, and never below min length.
                if not speech_started or i < min_frames:
                    continue
                silent_count += 1
                if silent_count >= silence_frames_needed:
                    break

        if not collected:
            return np.zeros(0, dtype=np.int16)
        return np.concatenate(collected)

    # ---- RMS energy fallback ----

    def _record_rms(self) -> np.ndarray:
        """Capture from the default input device and return int16 mono audio."""
        chunk_samples = int(self.sample_rate * self.chunk_duration)
        silence_chunks_needed = int(self.silence_duration / self.chunk_duration)
        min_chunks = int(self.min_recording / self.chunk_duration)
        max_chunks = int(self.max_recording / self.chunk_duration)
        warmup_chunks = int(self.warmup / self.chunk_duration)

        collected: list[np.ndarray] = []
        silent_count = 0

        with sd.InputStream(
            samplerate=self.sample_rate,
            channels=1,
            dtype="int16",
            blocksize=chunk_samples,
        ) as stream:
            for i in range(max_chunks):
                chunk, _ = stream.read(chunk_samples)
                chunk = chunk.flatten()
                collected.append(chunk)

                # Compute RMS in float [0, 1] space.
                rms = float(np.sqrt(np.mean((chunk.astype(np.float32) / 32768.0) ** 2)))

                if i < warmup_chunks:
                    continue
                if i < min_chunks:
                    continue

                if rms < self.silence_threshold:
                    silent_count += 1
                    if silent_count >= silence_chunks_needed:
                        break
                else:
                    silent_count = 0

        if not collected:
            return np.zeros(0, dtype=np.int16)
        return np.concatenate(collected)
