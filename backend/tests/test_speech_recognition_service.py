from __future__ import annotations

from pathlib import Path

import pytest

from app.services import speech_recognition


class FakeSegment:
    text = "  hello  "
    no_speech_prob = 0.1


class FakeInfo:
    language = "en"
    language_probability = 0.91
    duration = 1.25


def test_model_is_cached_and_transcription_result_is_normalized(monkeypatch, tmp_path):
    created_models = []

    class FakeModel:
        def __init__(self, *args, **kwargs):
            created_models.append((args, kwargs))

        def transcribe(self, *_args, **_kwargs):
            return iter([FakeSegment()]), FakeInfo()

    monkeypatch.setattr(speech_recognition, "WhisperModel", FakeModel)
    speech_recognition.get_model.cache_clear()
    try:
        assert speech_recognition.get_model() is speech_recognition.get_model()
        result = speech_recognition.transcribe_audio_file(tmp_path / "sample.wav", "en")
    finally:
        speech_recognition.get_model.cache_clear()

    assert len(created_models) == 1
    assert result["text"] == "hello"
    assert result["language"] == "en"
    assert result["duration"] == 1.25


def test_transcription_service_propagates_model_failure(monkeypatch, tmp_path):
    class FailingModel:
        def __init__(self, *_args, **_kwargs):
            pass

        def transcribe(self, *_args, **_kwargs):
            raise RuntimeError("model failure")

    monkeypatch.setattr(speech_recognition, "WhisperModel", FailingModel)
    speech_recognition.get_model.cache_clear()
    try:
        with pytest.raises(RuntimeError, match="model failure"):
            speech_recognition.transcribe_audio_file(tmp_path / "sample.wav")
    finally:
        speech_recognition.get_model.cache_clear()
