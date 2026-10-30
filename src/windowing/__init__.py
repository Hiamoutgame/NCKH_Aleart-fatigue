"""Time windowing module relative to fault injection timestamps."""

from .windows import WindowConfig, assign_windows, offset_seconds

__all__ = [
    "WindowConfig",
    "assign_windows",
    "offset_seconds",
]
