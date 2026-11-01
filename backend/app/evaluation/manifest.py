"""Manifest loading and validation for speech evaluation datasets."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

_SHA256 = re.compile(r"^[0-9a-f]{64}$")


@dataclass(frozen=True)
class EvaluationSample:
    sample_id: str
    audio_path: Path
    checksum_sha256: str
    language: str
    reference_transcript: str
    duration_seconds: float | None
    dataset: str
    license_or_consent: str
    tags: tuple[str, ...]


class ManifestError(ValueError):
    """Raised when a manifest is malformed or contains unusable metadata."""


def _required_string(data: dict[str, Any], key: str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ManifestError(f"sample field '{key}' must be a non-empty string")
    return value.strip()


def _sample(raw: Any, index: int, root: Path) -> EvaluationSample:
    if not isinstance(raw, dict):
        raise ManifestError(f"sample {index} must be an object")
    sample_id = _required_string(raw, "id")
    audio_value = _required_string(raw, "audio_path")
    checksum = _required_string(raw, "checksum_sha256").lower()
    if not _SHA256.fullmatch(checksum):
        raise ManifestError(f"sample {sample_id} has an invalid checksum_sha256")
    language = _required_string(raw, "language")
    reference = _required_string(raw, "reference_transcript")
    dataset = _required_string(raw, "dataset")
    provenance = _required_string(raw, "license_or_consent")
    duration = raw.get("duration_seconds")
    if duration is not None and (isinstance(duration, bool) or not isinstance(duration, (int, float)) or duration <= 0):
        raise ManifestError(f"sample {sample_id} has invalid duration_seconds")
    tags = raw.get("tags", [])
    if not isinstance(tags, list) or any(not isinstance(tag, str) or not tag.strip() for tag in tags):
        raise ManifestError(f"sample {sample_id} tags must be a list of non-empty strings")
    audio_path = Path(audio_value)
    if not audio_path.is_absolute():
        audio_path = root / audio_path
    return EvaluationSample(
        sample_id=sample_id,
        audio_path=audio_path.resolve(),
        checksum_sha256=checksum,
        language=language,
        reference_transcript=reference,
        duration_seconds=float(duration) if duration is not None else None,
        dataset=dataset,
        license_or_consent=provenance,
        tags=tuple(tag.strip() for tag in tags),
    )


def load_manifest(path: Path) -> tuple[EvaluationSample, ...]:
    """Load and validate a JSON manifest; paths are relative to its directory."""
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ManifestError(f"could not read manifest {path}: {exc}") from exc
    if not isinstance(payload, dict) or payload.get("version") != 1:
        raise ManifestError("manifest must be an object with version 1")
    samples = payload.get("samples")
    if not isinstance(samples, list) or not samples:
        raise ManifestError("manifest samples must be a non-empty list")
    parsed = tuple(_sample(item, index, path.parent) for index, item in enumerate(samples, 1))
    ids = [sample.sample_id for sample in parsed]
    if len(ids) != len(set(ids)):
        raise ManifestError("sample ids must be unique")
    return parsed


def verify_sample_file(sample: EvaluationSample) -> None:
    """Verify that an audio file exists and matches the manifest checksum."""
    if not sample.audio_path.is_file():
        raise ManifestError(f"audio file does not exist: {sample.audio_path}")
    digest = hashlib.sha256(sample.audio_path.read_bytes()).hexdigest()
    if digest != sample.checksum_sha256:
        raise ManifestError(f"checksum mismatch for sample {sample.sample_id}")
