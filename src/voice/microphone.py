"""Microphone capture with simple energy-based voice activity detection (VAD).

Records 16 kHz mono int16 audio until the user stops speaking (configurable
silence threshold and duration), or until a hard timeout is reached.
"""

from __future__ import annotations

import numpy as np
import sounddevice as sd


SAMPLE_RATE = 16000  # what Whisper expects


class Microphone:
    """Simple silence-aware microphone recorder."""

    def __init__(
        self,
        sample_rate: int = SAMPLE_RATE,
        chunk_duration: float = 0.1,        # 100 ms blocks
        silence_threshold: float = 0.012,   # RMS energy below this = "silent"
        silence_duration: float = 1.6,      # consecutive silence to stop
        min_recording: float = 0.8,         # min length before silence stops it
        max_recording: float = 30.0,        # hard cap
        warmup: float = 0.2,                # initial chunks always treated as voice
    ):
        self.sample_rate = sample_rate
        self.chunk_duration = chunk_duration
        self.silence_threshold = silence_threshold
        self.silence_duration = silence_duration
        self.min_recording = min_recording
        self.max_recording = max_recording
        self.warmup = warmup

    def record_until_silence(self) -> np.ndarray:
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
