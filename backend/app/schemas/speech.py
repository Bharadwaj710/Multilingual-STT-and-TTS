"""Text-to-speech request schema."""

from __future__ import annotations

from pydantic import BaseModel, Field

from app.core.config import settings


class TTSRequest(BaseModel):
    text: str = Field(description="Text to synthesize as MP3.", examples=["Hello from the Speech AI API."])
    voice: str = Field(
        default=settings.tts_default_voice,
        description="Configured Edge TTS voice identifier.",
        examples=["en-US-AvaNeural"],
    )
