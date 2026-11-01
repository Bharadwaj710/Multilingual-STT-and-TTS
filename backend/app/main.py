"""FastAPI application assembly for the self-hostable multilingual STT/TTS API."""

from __future__ import annotations

import logging
import json
from time import perf_counter
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response

from app.api.routes import health, speech, transcription
from app.core.config import settings
from app.core.errors import AppError
from app.core.logging import configure_logging

configure_logging()
logger = logging.getLogger("multilingual.stt")

app = FastAPI(
    title="Multilingual STT/TTS API",
    version="1.0.0",
    description=(
        "Chunk-based multilingual transcription using faster-whisper and "
        "text-to-speech generation through a configured Edge TTS voice."
    ),
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID"],
)


def _request_id(request: Request) -> str:
    return getattr(request.state, "request_id", "unknown")


def _error_body(code: str, message: str, request: Request) -> dict:
    # Preserve `detail` for the existing React client's error extraction while
    # giving API consumers a stable machine-readable error shape.
    return {
        "detail": message,
        "error": {"code": code, "message": message, "request_id": _request_id(request)},
    }


@app.middleware("http")
async def request_context_and_logging(request: Request, call_next) -> Response:
    """Attach a safe request identifier and emit one structured completion log."""
    request_id = uuid4().hex
    request.state.request_id = request_id
    started_at = perf_counter()
    status_code = 500
    try:
        response = await call_next(request)
        status_code = response.status_code
        response.headers["X-Request-ID"] = request_id
        return response
    finally:
        logger.info(
            "request_complete %s",
            json.dumps(
                {
                    "event": "request_complete",
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": status_code,
                    "duration_ms": round((perf_counter() - started_at) * 1000, 2),
                },
                separators=(",", ":"),
            ),
        )


@app.exception_handler(AppError)
async def app_error_handler(_request: Request, exc: AppError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content=_error_body(exc.code, exc.message, _request),
    )


@app.exception_handler(RequestValidationError)
async def request_validation_error_handler(
    _request: Request, _exc: RequestValidationError
) -> JSONResponse:
    validation_details = [
        {
            "location": ".".join(str(part) for part in error.get("loc", ())),
            "type": error.get("type", "unknown"),
        }
        for error in _exc.errors()
    ]
    logger.warning(
        "request_validation_failed %s",
        json.dumps(
            {
                "event": "request_validation_failed",
                "request_id": _request_id(_request),
                "method": _request.method,
                "path": _request.url.path,
                "details": validation_details,
            },
            separators=(",", ":"),
        ),
    )
    return JSONResponse(
        status_code=422,
        content=_error_body("INVALID_REQUEST", "The request payload is invalid.", _request),
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(_request: Request, _exc: Exception) -> JSONResponse:
    logger.exception("Unhandled application error")
    return JSONResponse(
        status_code=500,
        content=_error_body("INTERNAL_ERROR", "An unexpected server error occurred.", _request),
    )


app.include_router(health.router)
app.include_router(transcription.router)
app.include_router(speech.router)
