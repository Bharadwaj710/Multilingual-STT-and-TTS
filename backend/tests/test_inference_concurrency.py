from __future__ import annotations

import asyncio
import threading
from pathlib import Path

import pytest

from app.api.routes import transcription
from app.core.config import settings
from app.services.inference_admission import InferenceAdmission, inference_admission
from app.services import speech_recognition


@pytest.fixture(autouse=True)
def reset_admission():
    original_capacity = settings.max_admitted_inference_requests
    while inference_admission.admitted_count:
        inference_admission.release()
    yield
    while inference_admission.admitted_count:
        inference_admission.release()
    settings.max_admitted_inference_requests = original_capacity


def test_admission_rejects_beyond_capacity_and_releases():
    admission = InferenceAdmission()
    settings.max_admitted_inference_requests = 1

    assert admission.try_acquire()
    assert not admission.try_acquire()
    assert admission.admitted_count == 1
    admission.release()
    assert admission.try_acquire()
    admission.release()


def test_inference_exception_releases_api_admission(client, monkeypatch, wav_bytes):
    settings.max_admitted_inference_requests = 1

    def fail(_path, _language):
        raise RuntimeError("inference failed")

    monkeypatch.setattr(transcription, "transcribe_audio_file", fail)
    response = client.post("/api/transcribe", files={"audio": ("sample.wav", wav_bytes, "audio/wav")})

    assert response.status_code == 500
    assert inference_admission.admitted_count == 0


def test_busy_api_response_is_predictable(client, monkeypatch, wav_bytes):
    settings.max_admitted_inference_requests = 1
    entered = threading.Event()
    release = threading.Event()

    def blocked(_path, _language):
        entered.set()
        release.wait(timeout=5)
        return {
            "text": "mock transcript",
            "language": "en",
            "language_probability": 1,
            "duration": 1,
            "no_speech_probability": 0,
            "skipped": None,
        }

    monkeypatch.setattr(transcription, "transcribe_audio_file", blocked)
    first = threading.Thread(
        target=lambda: client.post("/api/transcribe", files={"audio": ("one.wav", wav_bytes, "audio/wav")})
    )
    first.start()
    assert entered.wait(timeout=5)

    second = client.post("/api/transcribe", files={"audio": ("two.wav", wav_bytes, "audio/wav")})
    release.set()
    first.join(timeout=5)

    assert second.status_code == 503
    assert second.json()["error"]["code"] == "SERVICE_BUSY"


def test_cancellation_releases_api_admission(monkeypatch, tmp_path: Path):
    async def scenario():
        settings.max_admitted_inference_requests = 1
        started = asyncio.Event()
        stopped = asyncio.Event()

        async def save(_audio):
            return tmp_path / "sample.wav", 1

        async def blocked(*_args):
            started.set()
            await stopped.wait()

        monkeypatch.setattr(transcription, "save_and_validate_audio_upload", save)
        monkeypatch.setattr(transcription, "run_in_threadpool", blocked)
        monkeypatch.setattr(transcription, "remove_file", lambda _path: None)

        task = asyncio.create_task(transcription.transcribe(None))
        await started.wait()
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task

        assert inference_admission.admitted_count == 0

    asyncio.run(scenario())


def test_model_initialization_is_single_flight(monkeypatch):
    created = []
    started = threading.Event()
    continue_loading = threading.Event()

    class FakeModel:
        def __init__(self, *_args, **_kwargs):
            created.append(self)
            started.set()
            continue_loading.wait(timeout=5)

    monkeypatch.setattr(speech_recognition, "WhisperModel", FakeModel)
    speech_recognition.get_model.cache_clear()
    results = []

    first = threading.Thread(target=lambda: results.append(speech_recognition.get_model()))
    second = threading.Thread(target=lambda: results.append(speech_recognition.get_model()))
    first.start()
    assert started.wait(timeout=5)
    second.start()
    continue_loading.set()
    first.join(timeout=5)
    second.join(timeout=5)

    assert len(created) == 1
    assert results[0] is results[1]
    speech_recognition.get_model.cache_clear()
