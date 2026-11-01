from __future__ import annotations

import io
import sys
import wave
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

BACKEND_DIRECTORY = Path(__file__).resolve().parents[1]
if str(BACKEND_DIRECTORY) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIRECTORY))

from app.core.config import settings
from app.main import app
from app.services.speech_recognition import get_model


@pytest.fixture(autouse=True)
def isolated_runtime(tmp_path: Path):
    original_directory = settings.temp_directory
    original_max_size = settings.max_upload_size_bytes
    settings.temp_directory = tmp_path / "speech-temp"
    get_model.cache_clear()
    yield
    get_model.cache_clear()
    settings.temp_directory = original_directory
    settings.max_upload_size_bytes = original_max_size


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture
def wav_bytes() -> bytes:
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as writer:
        writer.setnchannels(1)
        writer.setsampwidth(2)
        writer.setframerate(16_000)
        writer.writeframes(b"\x00\x00" * 1_600)
    return buffer.getvalue()


def temp_files() -> set[Path]:
    if not settings.temp_directory.exists():
        return set()
    return {path for path in settings.temp_directory.rglob("speech-*") if path.is_file()}
