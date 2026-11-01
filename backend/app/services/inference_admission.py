"""Process-local admission control for shared model inference."""

from __future__ import annotations

from threading import Lock

from app.core.config import settings


class InferenceAdmission:
    """Track admitted requests without making callers wait for capacity."""

    def __init__(self) -> None:
        self._lock = Lock()
        self._admitted = 0

    def try_acquire(self) -> bool:
        with self._lock:
            if self._admitted >= settings.max_admitted_inference_requests:
                return False
            self._admitted += 1
            return True

    def release(self) -> None:
        with self._lock:
            if self._admitted <= 0:
                raise RuntimeError("Inference admission released without an admitted request")
            self._admitted -= 1

    @property
    def admitted_count(self) -> int:
        with self._lock:
            return self._admitted


inference_admission = InferenceAdmission()
