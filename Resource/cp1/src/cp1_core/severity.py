"""Compatibility exports; implementation lives in exploration shared infrastructure."""

from src.shared.infrastructure.severity import (
    WARN_RE,
    ERROR_RE,
    INFO_RE,
    DEBUG_RE,
    LOG4J_LEVEL_RE,
    is_warning,
    infer_severity,
)

__all__ = ['WARN_RE', 'ERROR_RE', 'INFO_RE', 'DEBUG_RE', 'LOG4J_LEVEL_RE', 'is_warning', 'infer_severity']
