"""Validated Edge TTS integration."""

from __future__ import annotations

from pathlib import Path

import edge_tts

from app.core.config import settings
from app.core.errors import InvalidTTSRequestError


def validate_tts_request(text: str, voice: str) -> tuple[str, str]:
    normalized_text = text.strip()
    if not normalized_text:
        raise InvalidTTSRequestError("Text cannot be empty.")
    if len(normalized_text) > settings.tts_max_text_characters:
        raise InvalidTTSRequestError("Text exceeds the maximum allowed length.")
    if voice not in settings.tts_allowed_voices:
        raise InvalidTTSRequestError("The requested voice is not supported.")
    return normalized_text, voice


async def synthesize_speech(text: str, voice: str, output_path: Path) -> None:
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(str(output_path))
