"""Compatibility import for callers using the original module path."""

from app.services.speech_recognition import (
    get_model,
    is_model_loaded,
    transcribe_audio_file,
    warmup_model,
)

__all__ = ["get_model", "is_model_loaded", "transcribe_audio_file", "warmup_model"]
