"""Safe temporary-file helpers used by audio and speech services."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

from app.core.config import settings


def create_temporary_file(category: str, suffix: str) -> Path:
    directory = settings.temp_directory / category
    directory.mkdir(parents=True, exist_ok=True)
    descriptor, filename = tempfile.mkstemp(prefix="speech-", suffix=suffix, dir=directory)
    os.close(descriptor)
    return Path(filename)


def remove_file(path: Path) -> None:
    try:
        path.unlink(missing_ok=True)
    except OSError:
        pass
