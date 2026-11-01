"""Command-line benchmark for the existing speech recognition service."""

from __future__ import annotations

import argparse
import csv
import json
import platform
import sys
import time
from contextlib import contextmanager
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from statistics import median
from typing import Any, Callable

from app.core.config import settings
from app.evaluation.manifest import EvaluationSample, ManifestError, load_manifest, verify_sample_file
from app.evaluation.metrics import cer, real_time_factor, wer
from app.services import speech_recognition

MODEL_SIZES = ("tiny", "base", "small", "medium")


def _audio_duration(path: Path) -> float | None:
    try:
        import av
        with av.open(str(path), mode="r") as container:
            duration = container.duration
            return duration / 1_000_000 if duration is not None else None
    except Exception:
        return None


def run_benchmark(
    samples: tuple[EvaluationSample, ...],
    transcriber: Callable[[Path, str | None], dict[str, Any]] | None = None,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    transcriber = transcriber or speech_recognition.transcribe_audio_file
    results: list[dict[str, Any]] = []
    for sample in samples:
        verify_sample_file(sample)
        started = time.perf_counter()
        try:
            output = transcriber(sample.audio_path, sample.language)
            inference_seconds = time.perf_counter() - started
            audio_seconds = sample.duration_seconds or _audio_duration(sample.audio_path) or output.get("duration")
            if not isinstance(audio_seconds, (int, float)) or audio_seconds <= 0:
                raise ValueError("audio duration is unavailable or invalid")
            hypothesis = str(output.get("text", ""))
            results.append({
                "id": sample.sample_id,
                "language": sample.language,
                "detected_language": output.get("language"),
                "language_probability": output.get("language_probability"),
                "reference": sample.reference_transcript,
                "hypothesis": hypothesis,
                "wer": wer(sample.reference_transcript, hypothesis),
                "cer": cer(sample.reference_transcript, hypothesis),
                "audio_duration_seconds": audio_seconds,
                "inference_seconds": inference_seconds,
                "end_to_end_latency_seconds": inference_seconds,
                "rtf": real_time_factor(inference_seconds, float(audio_seconds)),
                "status": "ok",
            })
        except Exception as exc:
            results.append({"id": sample.sample_id, "language": sample.language, "status": "error", "error": str(exc)})
    successful = [item for item in results if item["status"] == "ok"]
    by_language: dict[str, dict[str, float | int]] = {}
    for language in sorted({item["language"] for item in successful}):
        group = [item for item in successful if item["language"] == language]
        latencies = sorted(item["end_to_end_latency_seconds"] for item in group)
        by_language[language] = {
            "samples": len(group),
            "wer": sum(item["wer"] for item in group) / len(group),
            "cer": sum(item["cer"] for item in group) / len(group),
            "latency_p50_seconds": median(latencies),
            "latency_p95_seconds": latencies[max(0, int(len(latencies) * 0.95) - 1)],
        }
    return {
        "model": metadata or {
            "size": settings.model_size,
            "identifier": f"Systran/faster-whisper-{settings.model_size}",
            "device": settings.device,
            "compute_type": settings.compute_type,
        },
        "environment": _environment_metadata(),
        "samples": results,
        "summary": {"total": len(results), "successful": len(successful), "failed": len(results) - len(successful), "by_language": by_language},
    }


def _environment_metadata() -> dict[str, Any]:
    try:
        faster_whisper_version = version("faster-whisper")
    except PackageNotFoundError:
        faster_whisper_version = "unknown"
    return {
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "processor": platform.processor() or "unknown",
        "faster_whisper": faster_whisper_version,
    }


def _peak_memory_mb() -> float | None:
    try:
        import resource
        value = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        return value / 1024 if sys.platform != "darwin" else value / (1024 * 1024)
    except (ImportError, AttributeError):
        return None


@contextmanager
def selected_model(model_size: str):
    """Temporarily select one multilingual model without changing production settings."""
    if model_size not in MODEL_SIZES:
        raise ValueError(f"model_size must be one of: {', '.join(MODEL_SIZES)}")
    original_size = settings.model_size
    settings.model_size = model_size
    speech_recognition.get_model.cache_clear()
    try:
        yield
    finally:
        speech_recognition.get_model.cache_clear()
        settings.model_size = original_size


def run_selected_model_benchmark(samples: tuple[EvaluationSample, ...], model_size: str) -> dict[str, Any]:
    """Load, benchmark, and release exactly one selected model."""
    with selected_model(model_size):
        load_started = time.perf_counter()
        speech_recognition.get_model()
        load_seconds = time.perf_counter() - load_started
        result = run_benchmark(
            samples,
            metadata={
                "size": model_size,
                "identifier": f"Systran/faster-whisper-{model_size}",
                "device": settings.device,
                "compute_type": settings.compute_type,
                "model_load_seconds": load_seconds,
            },
        )
        result["summary"]["peak_memory_mb"] = _peak_memory_mb()
        return result


def _write_output(result: dict[str, Any], path: Path, output_format: str) -> None:
    if output_format == "json":
        path.write_text(json.dumps(result, indent=2), encoding="utf-8")
        return
    fields = [
        "model_size",
        "model_identifier",
        "model_load_seconds",
        "id",
        "language",
        "detected_language",
        "language_probability",
        "status",
        "wer",
        "cer",
        "rtf",
        "audio_duration_seconds",
        "inference_seconds",
        "end_to_end_latency_seconds",
        "error",
    ]
    model = result.get("model", {})
    rows = [
        {
            **sample,
            "model_size": model.get("size"),
            "model_identifier": model.get("identifier"),
            "model_load_seconds": model.get("model_load_seconds"),
        }
        for sample in result["samples"]
    ]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--format", choices=("json", "csv"), default="json")
    parser.add_argument(
        "--model-size",
        choices=MODEL_SIZES,
        default=settings.model_size if settings.model_size in MODEL_SIZES else "small",
        help="One multilingual faster-whisper model to evaluate; production settings are restored afterward.",
    )
    args = parser.parse_args(argv)
    try:
        result = run_selected_model_benchmark(load_manifest(args.manifest), args.model_size)
        _write_output(result, args.output, args.format)
    except ManifestError as exc:
        parser.error(str(exc))
    print(f"Evaluated {result['summary']['successful']}/{result['summary']['total']} samples; results: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
