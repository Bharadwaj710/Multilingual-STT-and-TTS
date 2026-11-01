"""Environment-driven application configuration.

The module intentionally uses the standard library rather than adding a new
runtime dependency solely for settings management. Invalid numeric settings
fail fast during startup instead of failing in the request path.
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path


def _csv_setting(name: str, default: str) -> tuple[str, ...]:
    values = tuple(value.strip() for value in os.getenv(name, default).split(",") if value.strip())
    if not values:
        raise ValueError(f"{name} must contain at least one value")
    return values


def _positive_int_setting(name: str, default: int) -> int:
    value = os.getenv(name, str(default))
    try:
        parsed = int(value)
    except ValueError as exc:
        raise ValueError(f"{name} must be an integer") from exc
    if parsed <= 0:
        raise ValueError(f"{name} must be greater than zero")
    return parsed


class Settings:
    """Centralized, immutable-at-runtime settings for the API process."""

    def __init__(self) -> None:
        self.app_environment = os.getenv("APP_ENV", "development")
        self.log_level = os.getenv("LOG_LEVEL", "INFO").upper()
        self.model_size = os.getenv("WHISPER_MODEL_SIZE", "small")
        self.device = os.getenv("WHISPER_DEVICE", "cpu")
        self.compute_type = os.getenv("WHISPER_COMPUTE_TYPE", "int8")
        self.cors_origins = list(_csv_setting("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173"))
        self.max_upload_size_bytes = _positive_int_setting("MAX_UPLOAD_SIZE_BYTES", 15 * 1024 * 1024)
        self.max_admitted_inference_requests = _positive_int_setting(
            "MAX_ADMITTED_INFERENCE_REQUESTS",
            2,
        )
        self.supported_audio_extensions = frozenset(
            extension.lower().lstrip(".")
            for extension in _csv_setting("SUPPORTED_AUDIO_EXTENSIONS", "webm,wav,mp3,m4a,ogg,mp4,aac,flac")
        )
        self.temp_directory = Path(os.getenv("TEMP_DIRECTORY", str(Path(tempfile.gettempdir()) / "multilingual-speech-api")))
        self.tts_default_voice = os.getenv("TTS_DEFAULT_VOICE", "en-US-AvaNeural")
        self.tts_allowed_voices = frozenset(_csv_setting(
            "TTS_ALLOWED_VOICES",
            "hi-IN-SwaraNeural,en-US-AvaNeural,mr-IN-AarohiNeural,ta-IN-PallaviNeural,te-IN-ShrutiNeural",
        ))
        self.tts_max_text_characters = _positive_int_setting("TTS_MAX_TEXT_CHARACTERS", 5000)


settings = Settings()
