from __future__ import annotations

from app.core.config import Settings


def test_settings_use_expected_defaults(monkeypatch):
    for name in (
        "WHISPER_MODEL_SIZE",
        "MAX_UPLOAD_SIZE_BYTES",
        "TTS_MAX_TEXT_CHARACTERS",
        "MAX_ADMITTED_INFERENCE_REQUESTS",
    ):
        monkeypatch.delenv(name, raising=False)

    configured = Settings()

    assert configured.model_size == "small"
    assert configured.max_upload_size_bytes == 15 * 1024 * 1024
    assert configured.tts_max_text_characters == 5000
    assert configured.max_admitted_inference_requests == 2
    assert "webm" in configured.supported_audio_extensions


def test_settings_honor_environment_overrides(monkeypatch):
    monkeypatch.setenv("WHISPER_MODEL_SIZE", "base")
    monkeypatch.setenv("MAX_UPLOAD_SIZE_BYTES", "2048")
    monkeypatch.setenv("CORS_ORIGINS", "https://example.test,https://app.example.test")
    monkeypatch.setenv("MAX_ADMITTED_INFERENCE_REQUESTS", "3")

    configured = Settings()

    assert configured.model_size == "base"
    assert configured.max_upload_size_bytes == 2048
    assert configured.cors_origins == ["https://example.test", "https://app.example.test"]
    assert configured.max_admitted_inference_requests == 3
