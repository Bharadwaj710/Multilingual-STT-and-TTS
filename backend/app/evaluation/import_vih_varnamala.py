"""Import a small, authenticated ViH Varnamala evaluation subset.

This is an optional evaluation tool. It intentionally refuses the ``train``
split because evaluation data must not be sampled from training data.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path
from typing import Any

DATASET_ID = "ViH-research-labs/ViH-Varnamala"
LANGUAGES = ("en", "hi", "te", "ml")
SAMPLES_PER_LANGUAGE = 5


def _audio_bytes(audio: Any) -> bytes | None:
    if isinstance(audio, dict):
        value = audio.get("bytes")
        if isinstance(value, bytes):
            return value
        path = audio.get("path")
        if isinstance(path, str) and Path(path).is_file():
            return Path(path).read_bytes()
    return None


def _safe_id(value: str) -> str:
    return "".join(character if character.isalnum() or character in "-_" else "_" for character in value)


def import_subset(
    *,
    split: str,
    revision: str,
    output_manifest: Path,
    output_audio: Path,
    excluded_path: Path,
    token: str | None,
) -> None:
    if split == "train":
        raise ValueError("refusing to import train: this tool requires a dedicated evaluation split")
    try:
        from datasets import Audio, load_dataset
    except ImportError as exc:
        raise RuntimeError(
            "optional dependency missing; install backend/requirements-evaluation.txt"
        ) from exc

    dataset = load_dataset(
        DATASET_ID,
        split=split,
        streaming=True,
        revision=revision,
        token=token,
    )
    dataset = dataset.cast_column("audio", Audio(decode=False))
    counts = {language: 0 for language in LANGUAGES}
    seen_ids: set[str] = set()
    samples: list[dict[str, Any]] = []
    excluded: list[dict[str, str]] = []
    output_audio.mkdir(parents=True, exist_ok=True)

    for row_index, row in enumerate(dataset):
        language = str(row.get("language", "")).strip().lower()
        if language not in counts:
            excluded.append({"row": str(row_index), "reason": f"unsupported language: {language or 'missing'}"})
            continue
        if counts[language] >= SAMPLES_PER_LANGUAGE:
            if all(count == SAMPLES_PER_LANGUAGE for count in counts.values()):
                break
            continue
        transcript = row.get("transcript")
        audio_name = row.get("audio_name")
        if not isinstance(transcript, str) or not transcript.strip():
            excluded.append({"row": str(row_index), "reason": "missing or empty transcript"})
            continue
        if not isinstance(audio_name, str) or not audio_name.strip():
            excluded.append({"row": str(row_index), "reason": "missing audio_name"})
            continue
        source_id = audio_name.strip()
        if source_id in seen_ids:
            excluded.append({"row": str(row_index), "reason": f"duplicate sample ID: {source_id}"})
            continue
        content = _audio_bytes(row.get("audio"))
        if not content:
            excluded.append({"row": str(row_index), "reason": "audio bytes unavailable"})
            continue
        digest = hashlib.sha256(content).hexdigest()
        suffix = Path(source_id).suffix.lower() or ".audio"
        filename = f"{language}-{counts[language] + 1:02d}-{_safe_id(Path(source_id).stem)}{suffix}"
        (output_audio / filename).write_bytes(content)
        seen_ids.add(source_id)
        counts[language] += 1
        samples.append({
            "id": f"vih-varnamala-{language}-{counts[language]:02d}",
            "audio_path": f"../audio/{filename}",
            "checksum_sha256": digest,
            "language": language,
            "reference_transcript": transcript,
            "dataset": f"{DATASET_ID}@{revision} split={split} sample_id={source_id}",
            "license_or_consent": "CC BY 4.0; attribution to ViH Research Labs required",
            "tags": ["public-dataset", "human-recorded", f"source-id:{source_id}"],
        })

    if any(count < SAMPLES_PER_LANGUAGE for count in counts.values()):
        raise RuntimeError(f"could not collect five samples per language: {counts}")
    output_manifest.parent.mkdir(parents=True, exist_ok=True)
    output_manifest.write_text(json.dumps({
        "version": 1,
        "metadata": {
            "dataset": DATASET_ID,
            "revision": revision,
            "split": split,
            "license": "cc-by-4.0",
            "attribution": "ViH Research Labs",
            "samples_per_language": SAMPLES_PER_LANGUAGE,
        },
        "samples": samples,
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    excluded_path.parent.mkdir(parents=True, exist_ok=True)
    excluded_path.write_text(json.dumps(excluded, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Imported {len(samples)} samples: {counts}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--split", default="validation", help="Dedicated evaluation split; train is refused")
    parser.add_argument("--revision", default="main")
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--audio-dir", type=Path, required=True)
    parser.add_argument("--excluded", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        import_subset(
            split=args.split,
            revision=args.revision,
            output_manifest=args.manifest,
            output_audio=args.audio_dir,
            excluded_path=args.excluded,
            token=os.getenv("HF_TOKEN"),
        )
    except (RuntimeError, ValueError) as exc:
        print(f"Import failed: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
