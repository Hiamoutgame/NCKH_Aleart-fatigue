"""Severity parsing rules used consistently by CP1."""

from __future__ import annotations

import re


WARN_RE = re.compile(r"\bWARN(?:ING)?\b", re.IGNORECASE)
ERROR_RE = re.compile(r"\b(?:ERROR|ERR|SEVERE)\b", re.IGNORECASE)
INFO_RE = re.compile(r"\bINFO\b", re.IGNORECASE)
DEBUG_RE = re.compile(r"\bDEBUG\b", re.IGNORECASE)
LOG4J_LEVEL_RE = re.compile(
    r"^\s*\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}:\d{2}[.,]\d+\s+(TRACE|DEBUG|INFO|WARN|WARNING|ERROR|FATAL)\b",
    re.IGNORECASE,
)


def is_warning(message: object) -> bool:
    return isinstance(message, str) and bool(WARN_RE.search(message))


def infer_severity(message: object) -> str:
    """Return a conservative parsed level; unknown messages remain INFO."""
    if not isinstance(message, str):
        return "INFO"
    header = LOG4J_LEVEL_RE.search(message)
    if header:
        level = header.group(1).upper()
        return "WARNING" if level in {"WARN", "WARNING"} else level
    if WARN_RE.search(message):
        return "WARNING"
    if ERROR_RE.search(message):
        return "ERROR"
    if DEBUG_RE.search(message):
        return "DEBUG"
    if INFO_RE.search(message):
        return "INFO"
    return "INFO"
