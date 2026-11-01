"""Health and model lifecycle response schemas."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class RootResponse(BaseModel):
    message: str


class HealthResponse(BaseModel):
    status: Literal["ok"]


class ReadinessResponse(BaseModel):
    status: Literal["ready", "not_ready"]
    model_loaded: bool
    model_size: str


class ModelWarmupResponse(BaseModel):
    status: Literal["ready"]
    model_size: str
    device: str
    compute_type: str
