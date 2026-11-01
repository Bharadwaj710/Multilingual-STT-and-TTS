"""Shared OpenAPI response schemas."""

from __future__ import annotations

from pydantic import BaseModel, Field


class ErrorDetail(BaseModel):
    code: str = Field(examples=["INVALID_AUDIO"])
    message: str = Field(examples=["The uploaded audio could not be decoded."])
    request_id: str = Field(examples=["6b8f208e1d834d9388b1ca5a4c751593"])


class ErrorResponse(BaseModel):
    # `detail` is retained for compatibility with the original React client.
    detail: str
    error: ErrorDetail
