"""Bounded upload handling and lightweight media validation."""

from __future__ import annotations

from pathlib import Path

import av
from fastapi import UploadFile

from app.core.config import settings
from app.core.errors import FileTooLargeError, InvalidAudioError, UnsupportedAudioFormatError
from app.utils.file_handling import create_temporary_file, remove_file

_COPY_CHUNK_BYTES = 1024 * 1024


def _safe_suffix(filename: str | None) -> str:
    suffix = Path(filename or "audio.webm").suffix.lower().lstrip(".")
    if not suffix or suffix not in settings.supported_audio_extensions:
        raise UnsupportedAudioFormatError()
    return f".{suffix}"


def _verify_decodable_audio(path: Path) -> None:
    """Confirm an audio stream exists and decode one frame when available."""
    try:
        with av.open(str(path), mode="r") as container:
            audio_streams = [stream for stream in container.streams if stream.type == "audio"]
            if not audio_streams:
                raise InvalidAudioError("The uploaded file does not contain an audio stream.")
            decoded_frame = False
            for packet in container.demux(audio_streams[0]):
                for _frame in packet.decode():
                    decoded_frame = True
                    break
                if decoded_frame:
                    break
            if not decoded_frame:
                raise InvalidAudioError("The uploaded audio could not be decoded.")
    except InvalidAudioError:
        raise
    except Exception as exc:
        raise InvalidAudioError("The uploaded audio could not be decoded.") from exc


async def save_and_validate_audio_upload(upload: UploadFile) -> tuple[Path, int]:
    """Stream an upload to a private temp path, enforce size, then decode-check it."""
    path: Path | None = None
    total_bytes = 0
    try:
        suffix = _safe_suffix(upload.filename)
        path = create_temporary_file("uploads", suffix)
        with path.open("wb") as destination:
            while chunk := await upload.read(_COPY_CHUNK_BYTES):
                total_bytes += len(chunk)
                if total_bytes > settings.max_upload_size_bytes:
                    raise FileTooLargeError()
                destination.write(chunk)
        if total_bytes == 0:
            raise InvalidAudioError("The uploaded audio file is empty.")
        _verify_decodable_audio(path)
        return path, total_bytes
    except Exception:
        if path is not None:
            remove_file(path)
        raise
    finally:
        await upload.close()
