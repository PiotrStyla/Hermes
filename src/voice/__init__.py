"""Voice mode — ElevenLabs TTS + OpenAI Whisper STT + microphone capture.

All voice dependencies (elevenlabs, sounddevice, numpy) are imported lazily
so the rest of the system continues to work in pure-text mode without them.
"""

from .tts import ElevenLabsTTS
from .stt import WhisperSTT
from .microphone import Microphone

__all__ = ["ElevenLabsTTS", "WhisperSTT", "Microphone"]
