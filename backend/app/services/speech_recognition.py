"""Lifecycle and inference wrapper for the process-local Whisper model."""

from __future__ import annotations

from collections import namedtuple
from pathlib import Path
from threading import Lock

from faster_whisper import WhisperModel

from app.core.config import settings

_model_lock = Lock()
_transcribe_lock = Lock()
_model: WhisperModel | None = None
_CacheInfo = namedtuple("CacheInfo", "hits misses maxsize currsize")
_SHORT_HALLUCINATIONS = {
    "thank you",
    "thanks for watching",
    "subscribe",
    "follow",
    "follow follow follow",
    "i'll hold you",
}


def get_model() -> WhisperModel:
    global _model
    if _model is None:
        with _model_lock:
            if _model is None:
                _model = WhisperModel(
                    settings.model_size,
                    device=settings.device,
                    compute_type=settings.compute_type,
                )
    return _model


def is_model_loaded() -> bool:
    """Report cache state without loading/downloading a model."""
    return _model is not None


def _clear_model_cache() -> None:
    global _model
    with _model_lock:
        _model = None


def _model_cache_info() -> _CacheInfo:
    return _CacheInfo(0, 0, 1, int(_model is not None))


get_model.cache_clear = _clear_model_cache
get_model.cache_info = _model_cache_info


def warmup_model() -> dict:
    get_model()
    return {
        "status": "ready",
        "model_size": settings.model_size,
        "device": settings.device,
        "compute_type": settings.compute_type,
    }


def transcribe_audio_file(audio_path: Path, language: str | None = None) -> dict:
    # Admission is handled by the API route; this lock still serializes access
    # to the shared process-local Whisper model.
    with _transcribe_lock:
        segments, info = get_model().transcribe(
            str(audio_path),
            language=language or None,
            task="transcribe",
            vad_filter=True,
            vad_parameters={
                "min_silence_duration_ms": 700,
                "speech_pad_ms": 300,
            },
            beam_size=1,
            condition_on_previous_text=False,
        )

        segment_list = list(segments)
        text = " ".join(segment.text.strip() for segment in segment_list if segment.text.strip())
        normalized = " ".join(text.lower().replace(".", "").replace(",", "").split())
        no_speech_values = [
            getattr(segment, "no_speech_prob", 0)
            for segment in segment_list
            if getattr(segment, "no_speech_prob", None) is not None
        ]
        avg_no_speech_prob = sum(no_speech_values) / len(no_speech_values) if no_speech_values else 0
        skipped = None
        if not text:
            skipped = "no speech detected"
        elif normalized in _SHORT_HALLUCINATIONS and avg_no_speech_prob > 0.35:
            text = ""
            skipped = "likely silence hallucination"

        return {
            "text": text,
            "language": info.language,
            "language_probability": info.language_probability,
            "duration": info.duration,
            "no_speech_probability": avg_no_speech_prob,
            "skipped": skipped,
        }
