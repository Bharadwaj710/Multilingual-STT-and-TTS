from __future__ import annotations

from app.api.routes import transcription
from app.core.config import settings

from .conftest import temp_files


def _mock_result(_path, language):
    return {
        "text": "mock transcript",
        "language": language or "en",
        "language_probability": 0.97,
        "duration": 0.1,
        "no_speech_probability": 0.02,
        "skipped": None,
    }


def test_transcription_returns_sequence_and_cleans_temp_file(client, monkeypatch, wav_bytes):
    monkeypatch.setattr(transcription, "transcribe_audio_file", _mock_result)
    before = temp_files()

    response = client.post(
        "/api/transcribe",
        files={"audio": ("sample.wav", wav_bytes, "audio/wav")},
        data={"language": "en", "sequence": "4"},
    )

    assert response.status_code == 200
    assert response.json()["text"] == "mock transcript"
    assert response.json()["sequence"] == 4
    assert len(response.headers["X-Request-ID"]) == 32
    assert temp_files() == before


def test_transcription_rejects_unsupported_extension_with_stable_error(client):
    response = client.post(
        "/api/transcribe",
        files={"audio": ("sample.txt", b"not-audio", "text/plain")},
    )

    assert response.status_code == 415
    assert response.json()["error"]["code"] == "UNSUPPORTED_AUDIO_FORMAT"


def test_transcription_rejects_corrupt_audio_and_cleans_temp_file(client):
    before = temp_files()
    response = client.post(
        "/api/transcribe",
        files={"audio": ("sample.webm", b"not-audio", "audio/webm")},
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "INVALID_AUDIO"
    assert temp_files() == before


def test_transcription_enforces_upload_limit(client):
    settings.max_upload_size_bytes = 4
    response = client.post(
        "/api/transcribe",
        files={"audio": ("sample.wav", b"12345", "audio/wav")},
    )

    assert response.status_code == 413
    assert response.json()["error"]["code"] == "FILE_TOO_LARGE"


def test_transcription_hides_inference_exception_and_cleans_temp_file(client, monkeypatch, wav_bytes):
    def fail_inference(_path, _language):
        raise RuntimeError("model implementation detail")

    monkeypatch.setattr(transcription, "transcribe_audio_file", fail_inference)
    before = temp_files()
    response = client.post(
        "/api/transcribe",
        files={"audio": ("sample.wav", wav_bytes, "audio/wav")},
    )

    assert response.status_code == 500
    assert response.json()["error"]["code"] == "TRANSCRIPTION_FAILED"
    assert "model implementation detail" not in response.json()["detail"]
    assert temp_files() == before


def test_transcription_rejects_negative_sequence(client, wav_bytes):
    response = client.post(
        "/api/transcribe",
        files={"audio": ("sample.wav", wav_bytes, "audio/wav")},
        data={"sequence": "-1"},
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "INVALID_REQUEST"
