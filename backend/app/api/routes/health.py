"""Liveness, readiness, and explicit model warmup endpoints."""

from __future__ import annotations

import logging

from fastapi import APIRouter

from app.core.config import settings
from app.core.errors import ModelNotReadyError
from app.schemas.common import ErrorResponse
from app.schemas.health import HealthResponse, ModelWarmupResponse, ReadinessResponse, RootResponse
from app.services.speech_recognition import is_model_loaded, warmup_model

router = APIRouter(tags=["health"])
logger = logging.getLogger("multilingual.stt.health")


@router.get("/", response_model=RootResponse, summary="API service information")
def read_root() -> RootResponse:
    return {"message": "Multilingual Speech API is running."}


@router.get("/health", response_model=HealthResponse, summary="Liveness check")
def health() -> HealthResponse:
    """Lightweight liveness check; it never loads the Whisper model."""
    return {"status": "ok"}


@router.get("/ready", response_model=ReadinessResponse, summary="Model readiness check")
def ready() -> ReadinessResponse:
    """Report model cache state without triggering initialization."""
    loaded = is_model_loaded()
    return {
        "status": "ready" if loaded else "not_ready",
        "model_loaded": loaded,
        "model_size": settings.model_size,
    }


@router.post(
    "/api/model/warmup",
    response_model=ModelWarmupResponse,
    responses={503: {"model": ErrorResponse, "description": "The model could not be loaded."}},
    summary="Load the configured Whisper model",
)
def warmup() -> ModelWarmupResponse:
    try:
        return warmup_model()
    except Exception:
        logger.exception("Model warmup failed")
        raise ModelNotReadyError() from None
