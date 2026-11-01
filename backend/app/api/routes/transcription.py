"""Multipart audio transcription endpoint."""

from __future__ import annotations

import logging

from fastapi import APIRouter, File, Form, UploadFile
from starlette.concurrency import run_in_threadpool

from app.core.config import settings
from app.core.errors import AppError, ServiceBusyError, TranscriptionFailedError
from app.schemas.common import ErrorResponse
from app.schemas.transcription import TranscriptionResponse
from app.services.audio_validation import save_and_validate_audio_upload
from app.services.inference_admission import inference_admission
from app.services.speech_recognition import transcribe_audio_file
from app.utils.file_handling import remove_file

router = APIRouter(tags=["transcription"])
logger = logging.getLogger("multilingual.stt.transcription")


@router.post(
    "/api/transcribe",
    response_model=TranscriptionResponse,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid audio input."},
        413: {"model": ErrorResponse, "description": "Audio file exceeds the configured limit."},
        415: {"model": ErrorResponse, "description": "Unsupported audio extension."},
        422: {"model": ErrorResponse, "description": "Malformed multipart request."},
        503: {"model": ErrorResponse, "description": "Inference capacity is temporarily exhausted."},
        500: {"model": ErrorResponse, "description": "Transcription failure."},
    },
    summary="Transcribe one audio upload",
)
async def transcribe(
    audio: UploadFile = File(description="Audio file in a configured supported format."),
    language: str | None = Form(default=None, description="Optional Whisper language hint, such as `en` or `hi`."),
    sequence: int | None = Form(
        default=None,
        ge=0,
        description="Optional non-negative recording sequence for ordered client transcript assembly.",
    ),
) -> TranscriptionResponse:
    """Transcribe audio and return the supplied client sequence unchanged."""
    temp_path = None
    admitted = False
    try:
        temp_path, _file_size = await save_and_validate_audio_upload(audio)
        if not inference_admission.try_acquire():
            logger.warning(
                "inference_rejected_capacity_exhausted admitted=%d capacity=%d",
                inference_admission.admitted_count,
                settings.max_admitted_inference_requests,
            )
            raise ServiceBusyError()
        admitted = True
        logger.info(
            "inference_admitted admitted=%d capacity=%d",
            inference_admission.admitted_count,
            settings.max_admitted_inference_requests,
        )
        logger.info("inference_started")
        result = await run_in_threadpool(transcribe_audio_file, temp_path, language)
        logger.info("inference_completed")
        return {**result, "sequence": sequence}
    except AppError:
        raise
    except Exception:
        logger.exception("inference_failed")
        raise TranscriptionFailedError() from None
    finally:
        if admitted:
            inference_admission.release()
        if temp_path is not None:
            remove_file(temp_path)
