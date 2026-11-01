"""Stable public errors that do not reveal internal exception details."""

from __future__ import annotations


class AppError(Exception):
    def __init__(self, code: str, message: str, status_code: int) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code


class InvalidAudioError(AppError):
    def __init__(self, message: str = "The uploaded file is not valid audio.") -> None:
        super().__init__("INVALID_AUDIO", message, 400)


class FileTooLargeError(AppError):
    def __init__(self) -> None:
        super().__init__("FILE_TOO_LARGE", "The uploaded audio file exceeds the allowed size.", 413)


class UnsupportedAudioFormatError(AppError):
    def __init__(self) -> None:
        super().__init__("UNSUPPORTED_AUDIO_FORMAT", "The uploaded audio format is not supported.", 415)


class ModelNotReadyError(AppError):
    def __init__(self) -> None:
        super().__init__("MODEL_NOT_READY", "The speech recognition model is unavailable.", 503)


class TranscriptionFailedError(AppError):
    def __init__(self) -> None:
        super().__init__("TRANSCRIPTION_FAILED", "Transcription could not be completed.", 500)


class ServiceBusyError(AppError):
    def __init__(self) -> None:
        super().__init__(
            "SERVICE_BUSY",
            "The transcription service is busy. Please retry shortly.",
            503,
        )


class TTSGenerationFailedError(AppError):
    def __init__(self) -> None:
        super().__init__("TTS_GENERATION_FAILED", "Speech generation could not be completed.", 502)


class InvalidTTSRequestError(AppError):
    def __init__(self, message: str) -> None:
        super().__init__("INVALID_TTS_REQUEST", message, 400)
