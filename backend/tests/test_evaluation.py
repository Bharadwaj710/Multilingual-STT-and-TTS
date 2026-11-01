from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from app.core.config import settings
from app.evaluation.benchmark import MODEL_SIZES, _write_output, run_benchmark, selected_model
from app.evaluation.import_vih_varnamala import import_subset
from app.evaluation.manifest import ManifestError, load_manifest
from app.evaluation.metrics import cer, normalize_text, real_time_factor, wer


def _manifest(tmp_path: Path, audio: Path, **overrides) -> Path:
    data = {
        "version": 1,
        "samples": [{
            "id": "one",
            "audio_path": audio.name,
            "checksum_sha256": hashlib.sha256(audio.read_bytes()).hexdigest(),
            "language": "en",
            "reference_transcript": "Hello, world!",
            "dataset": "test fixture",
            "license_or_consent": "synthetic test fixture",
        }],
    }
    data["samples"][0].update(overrides)
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


def test_metrics_normalize_and_calculate_error_rates():
    assert normalize_text(" Héllo,   WORLD! ") == "héllo world"
    assert wer("hello world", "hello there") == 0.5
    assert cer("abc", "adc") == pytest.approx(1 / 3)
    assert real_time_factor(2, 4) == 0.5


@pytest.mark.parametrize("text", [
    "मोहम्मद ने ग़ज़नी",
    "తెలుగు క్రమంలో",
    "മലയാളം കാർണിവോറുകൾ",
])
def test_normalization_preserves_indic_combining_marks(text):
    assert normalize_text(text) == text


def test_normalization_applies_nfkc_without_transliteration():
    assert normalize_text("ＡＢＣ") == "abc"
    assert normalize_text("हिन्दी") == "हिन्दी"


def test_normalization_removes_punctuation_and_collapses_whitespace():
    assert normalize_text(" one,\t two!\nthree — four ") == "one two three four"


def test_metrics_handle_empty_and_boundary_cases():
    assert wer("", "") == 0
    assert wer("", "text") == 1
    assert wer("text", "") == 1
    assert wer("same text", "same text") == 0
    assert wer("one", "different") == 1
    assert cer("", "") == 0
    assert cer("", "text") == 1
    assert cer("text", "") == 1
    assert cer("same", "same") == 0
    assert cer("a", "b") == 1


def test_manifest_validates_metadata_and_resolves_audio(tmp_path):
    audio = tmp_path / "sample.wav"
    audio.write_bytes(b"audio")
    sample = load_manifest(_manifest(tmp_path, audio))[0]
    assert sample.audio_path == audio.resolve()

    with pytest.raises(ManifestError, match="invalid checksum"):
        load_manifest(_manifest(tmp_path, audio, checksum_sha256="bad"))


def test_manifest_rejects_missing_audio(tmp_path):
    audio = tmp_path / "sample.wav"
    audio.write_bytes(b"audio")
    manifest = _manifest(tmp_path, audio)
    audio.unlink()
    with pytest.raises(ManifestError, match="does not exist"):
        run_benchmark(load_manifest(manifest), lambda *_args: {})


def test_benchmark_exports_observed_metrics_and_inference_failure(tmp_path):
    audio = tmp_path / "sample.wav"
    audio.write_bytes(b"audio")
    samples = load_manifest(_manifest(tmp_path, audio, duration_seconds=2))

    def fake_transcriber(path, language):
        assert path == audio.resolve()
        assert language == "en"
        return {
            "text": "hello world",
            "duration": 2,
            "language": "en",
            "language_probability": 0.99,
        }

    result = run_benchmark(samples, fake_transcriber)
    row = result["samples"][0]
    assert row["status"] == "ok"
    assert row["detected_language"] == "en"
    assert row["language_probability"] == 0.99
    assert row["wer"] == 0
    assert row["rtf"] >= 0
    assert result["summary"]["by_language"]["en"]["samples"] == 1

    failed = run_benchmark(samples, lambda *_args: (_ for _ in ()).throw(RuntimeError("inference failed")))
    assert failed["summary"]["failed"] == 1
    assert failed["samples"][0]["error"] == "inference failed"


def test_invalid_rtf_inputs_are_rejected():
    with pytest.raises(ValueError):
        real_time_factor(1, 0)


def test_model_selection_is_limited_and_restores_production_setting():
    original_size = settings.model_size
    with selected_model("tiny"):
        assert settings.model_size == "tiny"
    assert settings.model_size == original_size

    with pytest.raises(ValueError, match="model_size must be one of"):
        with selected_model("large"):
            pass


def test_supported_comparison_models_are_multilingual_sizes():
    assert MODEL_SIZES == ("tiny", "base", "small", "medium")


def test_benchmark_reports_model_and_environment_metadata(tmp_path):
    audio = tmp_path / "sample.wav"
    audio.write_bytes(b"audio")
    samples = load_manifest(_manifest(tmp_path, audio, duration_seconds=2))
    result = run_benchmark(
        samples,
        lambda *_args: {"text": "hello world", "duration": 2},
        metadata={
            "size": "tiny",
            "identifier": "Systran/faster-whisper-tiny",
            "device": "cpu",
            "compute_type": "int8",
            "model_load_seconds": 0.1,
        },
    )
    assert result["model"]["identifier"] == "Systran/faster-whisper-tiny"
    assert result["model"]["model_load_seconds"] == 0.1
    assert "python" in result["environment"]


def test_csv_output_includes_selected_model_metadata(tmp_path):
    audio = tmp_path / "sample.wav"
    audio.write_bytes(b"audio")
    samples = load_manifest(_manifest(tmp_path, audio, duration_seconds=2))
    result = run_benchmark(
        samples,
        lambda *_args: {"text": "hello world", "duration": 2},
        metadata={"size": "base", "identifier": "Systran/faster-whisper-base", "model_load_seconds": 0.2},
    )
    output = tmp_path / "results.csv"
    _write_output(result, output, "csv")
    header = output.read_text(encoding="utf-8").splitlines()[0]
    row = output.read_text(encoding="utf-8").splitlines()[1]
    assert "model_size,model_identifier,model_load_seconds" in header
    assert "base,Systran/faster-whisper-base,0.2" in row


def test_vih_import_refuses_training_split(tmp_path):
    with pytest.raises(ValueError, match="refusing to import train"):
        import_subset(
            split="train",
            revision="main",
            output_manifest=tmp_path / "manifest.json",
            output_audio=tmp_path / "audio",
            excluded_path=tmp_path / "excluded.json",
            token=None,
        )
