"""Compatibility import for callers using the original module path."""

from app.core.config import Settings, settings

__all__ = ["Settings", "settings"]
