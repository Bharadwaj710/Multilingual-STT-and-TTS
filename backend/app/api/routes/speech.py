"""Text-to-speech endpoint."""

from __future__ import annotations

import logging

from fastapi import APIRouter, BackgroundTasks
from fastapi.responses import FileResponse

from app.core.errors import AppError, TTSGenerationFailedError
from app.schemas.common import ErrorResponse
from app.schemas.speech import TTSRequest
from app.services.text_to_speech import synthesize_speech, validate_tts_request
from app.utils.file_handling import create_temporary_file, remove_file

router = APIRouter(tags=["speech"])
logger = logging.getLogger("pelocal.stt.tts")


@router.post(
    "/api/speak",
    response_class=FileResponse,
    responses={
        200: {"content": {"audio/mpeg": {}}, "description": "Generated MP3 audio."},
        400: {"model": ErrorResponse, "description": "Invalid text or unsupported voice."},
        422: {"model": ErrorResponse, "description": "Malformed JSON request."},
        502: {"model": ErrorResponse, "description": "Speech provider generation failure."},
    },
    summary="Generate MP3 speech from text",
)
async def speak(request: TTSRequest, background_tasks: BackgroundTasks):
    """Generate an MP3 response for validated text and a configured voice."""
    temp_path = create_temporary_file("tts", ".mp3")
    try:
        text, voice = validate_tts_request(request.text, request.voice)
        await synthesize_speech(text, voice, temp_path)
        background_tasks.add_task(remove_file, temp_path)
        return FileResponse(path=temp_path, media_type="audio/mpeg", filename="tts_output.mp3")
    except AppError:
        remove_file(temp_path)
        raise
    except Exception:
        logger.exception("TTS generation failed")
        remove_file(temp_path)
        raise TTSGenerationFailedError() from None
