from __future__ import annotations

from app.api.routes import speech

from .conftest import temp_files


async def _write_fake_mp3(_text, _voice, output_path):
    output_path.write_bytes(b"fake-mp3")


def test_tts_returns_mp3_and_cleans_temp_file(client, monkeypatch):
    monkeypatch.setattr(speech, "synthesize_speech", _write_fake_mp3)
    before = temp_files()

    response = client.post("/api/speak", json={"text": "Hello", "voice": "en-US-AvaNeural"})

    assert response.status_code == 200
    assert response.headers["content-type"] == "audio/mpeg"
    assert response.content == b"fake-mp3"
    assert temp_files() == before


def test_tts_rejects_empty_text_and_unsupported_voice(client):
    empty_response = client.post("/api/speak", json={"text": "  "})
    voice_response = client.post("/api/speak", json={"text": "Hello", "voice": "invalid"})

    assert empty_response.status_code == 400
    assert empty_response.json()["error"]["code"] == "INVALID_TTS_REQUEST"
    assert voice_response.status_code == 400
    assert voice_response.json()["error"]["code"] == "INVALID_TTS_REQUEST"


def test_tts_hides_provider_exception_and_cleans_temp_file(client, monkeypatch):
    async def fail_synthesis(_text, _voice, _output_path):
        raise RuntimeError("provider internals")

    monkeypatch.setattr(speech, "synthesize_speech", fail_synthesis)
    before = temp_files()
    response = client.post("/api/speak", json={"text": "Hello"})

    assert response.status_code == 502
    assert response.json()["error"]["code"] == "TTS_GENERATION_FAILED"
    assert "provider internals" not in response.json()["detail"]
    assert temp_files() == before
