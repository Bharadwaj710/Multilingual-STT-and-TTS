"""Validate an evaluation manifest and all referenced audio checksums."""

from __future__ import annotations

import argparse
from pathlib import Path

from app.evaluation.manifest import ManifestError, load_manifest, verify_sample_file


def validate_manifest(path: Path) -> int:
    samples = load_manifest(path)
    for sample in samples:
        verify_sample_file(sample)
    print(f"Validated {len(samples)} samples: {path}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    args = parser.parse_args(argv)
    try:
        return validate_manifest(args.manifest)
    except ManifestError as exc:
        parser.error(str(exc))
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
