"""Import a small test-only Indic_ASR_Eval Kathbath subset.

The importer uses the Hugging Face dataset-server row API so Parquet shards are
not downloaded. It downloads audio only after selecting valid rows.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

DATASET_ID = "ayush-shunyalabs/Indic_ASR_Eval"
REVISION = "7c1d7dde6aee30d98075522bc9ec9eb26898f6ab"
CONFIG = "kathbath"
SPLIT = "test"
LANGUAGES = {"Hindi": "hi", "Telugu": "te", "Malayalam": "ml"}
SAMPLES_PER_LANGUAGE = 5
ROWS_ENDPOINT = "https://datasets-server.huggingface.co/rows"
API_ENDPOINT = "https://huggingface.co/api/datasets/ayush-shunyalabs/Indic_ASR_Eval"


def _json_get(url: str) -> dict:
    with urlopen(Request(url, headers={"User-Agent": "multilingual-evaluation-importer"}), timeout=60) as response:
        return json.load(response)


def _download(url: str) -> bytes:
    with urlopen(Request(url, headers={"User-Agent": "multilingual-evaluation-importer"}), timeout=120) as response:
        return response.read()


def _extension(audio: dict) -> str:
    content_type = str(audio.get("type", "")).lower()
    if "wav" in content_type:
        return ".wav"
    if "flac" in content_type:
        return ".flac"
    if "mp3" in content_type or "mpeg" in content_type:
        return ".mp3"
    return ".audio"


def import_subset(manifest_path: Path, audio_dir: Path, excluded_path: Path) -> dict[str, int]:
    metadata = _json_get(API_ENDPOINT)
    if metadata.get("sha") != REVISION:
        raise RuntimeError(f"dataset revision changed: expected {REVISION}, got {metadata.get('sha')}")

    counts = {code: 0 for code in LANGUAGES.values()}
    excluded: list[dict[str, str]] = []
    selected: list[dict] = []
    seen_sources: set[str] = set()
    offset = 0
    page_length = 100
    audio_dir.mkdir(parents=True, exist_ok=True)

    while not all(count == SAMPLES_PER_LANGUAGE for count in counts.values()):
        query = urlencode({
            "dataset": DATASET_ID,
            "config": CONFIG,
            "split": SPLIT,
            "offset": offset,
            "length": page_length,
        })
        payload = _json_get(f"{ROWS_ENDPOINT}?{query}")
        rows = payload.get("rows", [])
        if not rows:
            break
        for item in rows:
            row_index = str(item.get("row_idx", offset))
            row = item.get("row", {})
            language = LANGUAGES.get(str(row.get("language", "")).strip())
            if language is None:
                excluded.append({"row": row_index, "reason": "not Hindi, Telugu, or Malayalam"})
                continue
            if counts[language] >= SAMPLES_PER_LANGUAGE:
                continue
            transcript = row.get("transcript")
            audio_values = row.get("audio")
            if not isinstance(transcript, str) or not transcript.strip():
                excluded.append({"row": row_index, "reason": "missing or empty transcript"})
                continue
            if not isinstance(audio_values, list) or not audio_values or not isinstance(audio_values[0], dict):
                excluded.append({"row": row_index, "reason": "missing audio resource"})
                continue
            audio = audio_values[0]
            source_url = audio.get("src")
            if not isinstance(source_url, str) or not source_url:
                excluded.append({"row": row_index, "reason": "missing audio URL"})
                continue
            source_identity = f"{CONFIG}/{SPLIT}/row-{row_index}"
            if source_identity in seen_sources:
                excluded.append({"row": row_index, "reason": "duplicate source identity"})
                continue
            try:
                content = _download(source_url)
            except Exception as exc:
                excluded.append({"row": row_index, "reason": f"audio download failed: {exc}"})
                continue
            if not content:
                excluded.append({"row": row_index, "reason": "downloaded audio is empty"})
                continue
            ordinal = counts[language] + 1
            filename = f"kathbath-{language}-{ordinal:02d}-row-{row_index}{_extension(audio)}"
            (audio_dir / filename).write_bytes(content)
            counts[language] += 1
            seen_sources.add(source_identity)
            selected.append({
                "id": f"indic-asr-eval-kathbath-{language}-{ordinal:02d}",
                "audio_path": f"../audio/{filename}",
                "checksum_sha256": hashlib.sha256(content).hexdigest(),
                "language": language,
                "reference_transcript": transcript,
                "duration_seconds": row.get("duration"),
                "dataset": (
                    f"{DATASET_ID}@{REVISION} config={CONFIG} split={SPLIT} "
                    f"source_identity={source_identity}"
                ),
                "license_or_consent": (
                    "Compilation CC BY 4.0; attribute ayush-shunyalabs and ViH Research Labs. "
                    "Kathbath source attributed to AI4Bharat; verify upstream terms before redistribution."
                ),
                "tags": [
                    "public-dataset",
                    "kathbath",
                    f"source-row:{row_index}",
                    f"source-dataset:{row.get('dataset', CONFIG)}",
                ],
            })
        offset += len(rows)
        if offset >= int(payload.get("num_rows_total", offset)):
            break

    if not all(count == SAMPLES_PER_LANGUAGE for count in counts.values()):
        raise RuntimeError(f"could not select five samples per language: {counts}")
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps({
        "version": 1,
        "metadata": {
            "dataset": DATASET_ID,
            "revision": REVISION,
            "config": CONFIG,
            "split": SPLIT,
            "license": "CC BY 4.0 compilation; upstream Kathbath terms also apply",
            "attribution": "ayush-shunyalabs, ViH Research Labs, AI4Bharat",
            "samples_per_language": SAMPLES_PER_LANGUAGE,
        },
        "samples": selected,
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    excluded_path.parent.mkdir(parents=True, exist_ok=True)
    excluded_path.write_text(json.dumps(excluded, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Imported {len(selected)} samples: {counts}")
    return counts


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--audio-dir", type=Path, required=True)
    parser.add_argument("--excluded", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        import_subset(args.manifest, args.audio_dir, args.excluded)
    except (OSError, RuntimeError, ValueError) as exc:
        print(f"Import failed: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
