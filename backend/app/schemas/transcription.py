"""Multipart transcription response schema."""

from __future__ import annotations

from pydantic import BaseModel, Field


class TranscriptionResponse(BaseModel):
    text: str
    language: str | None
    language_probability: float
    duration: float
    no_speech_probability: float
    skipped: str | None
    sequence: int | None = Field(
        default=None,
        ge=0,
        description="Client recording sequence when supplied; omitted for legacy callers.",
    )
