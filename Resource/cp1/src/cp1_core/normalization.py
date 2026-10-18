"""Compatibility exports; implementation lives in exploration shared infrastructure."""

from src.shared.infrastructure.normalization import (
    RE_TS,
    RE_UUID,
    RE_HEX,
    RE_THREAD,
    RE_LOG4J_HDR,
    RE_NUM,
    normalize_message,
)

__all__ = ['RE_TS', 'RE_UUID', 'RE_HEX', 'RE_THREAD', 'RE_LOG4J_HDR', 'RE_NUM', 'normalize_message']
