"""Text normalization and error-rate metrics."""

from __future__ import annotations

import unicodedata


def normalize_text(text: str) -> str:
    """Normalize text without removing Unicode combining marks.

    Punctuation and symbols become spaces, while letters, numbers, marks, and
    other non-punctuation characters are preserved. This keeps Indic vowel
    signs and viramas intact for both WER and CER.
    """
    normalized = unicodedata.normalize("NFKC", text).casefold()
    cleaned = []
    for character in normalized:
        category = unicodedata.category(character)
        if character.isspace():
            cleaned.append(" ")
        elif category.startswith(("P", "S")):
            cleaned.append(" ")
        else:
            cleaned.append(character)
    return " ".join("".join(cleaned).split())


def _edit_distance(reference: list[str], hypothesis: list[str]) -> int:
    previous = list(range(len(hypothesis) + 1))
    for row, reference_token in enumerate(reference, 1):
        current = [row]
        for column, hypothesis_token in enumerate(hypothesis, 1):
            current.append(min(
                current[-1] + 1,
                previous[column] + 1,
                previous[column - 1] + (reference_token != hypothesis_token),
            ))
        previous = current
    return previous[-1]


def wer(reference: str, hypothesis: str) -> float:
    """Return whitespace-token WER; an empty reference is only valid if empty."""
    reference_tokens = normalize_text(reference).split()
    hypothesis_tokens = normalize_text(hypothesis).split()
    if not reference_tokens:
        return 0.0 if not hypothesis_tokens else 1.0
    return _edit_distance(reference_tokens, hypothesis_tokens) / len(reference_tokens)


def cer(reference: str, hypothesis: str) -> float:
    """Return code-point CER after the same Unicode-safe normalization."""
    reference_chars = list(normalize_text(reference).replace(" ", ""))
    hypothesis_chars = list(normalize_text(hypothesis).replace(" ", ""))
    if not reference_chars:
        return 0.0 if not hypothesis_chars else 1.0
    return _edit_distance(reference_chars, hypothesis_chars) / len(reference_chars)


def real_time_factor(inference_seconds: float, audio_seconds: float) -> float:
    if inference_seconds < 0 or audio_seconds <= 0:
        raise ValueError("inference_seconds must be non-negative and audio_seconds must be positive")
    return inference_seconds / audio_seconds
