"""Shared severity patterns and compatibility parsing rules from CP1."""

from __future__ import annotations

import re
from typing import Optional


WARN_RE = re.compile(r"\bWARN(?:ING)?\b", re.IGNORECASE)
ERROR_RE = re.compile(r"\b(?:ERROR|ERR|SEVERE)\b", re.IGNORECASE)
INFO_RE = re.compile(r"\bINFO\b", re.IGNORECASE)
DEBUG_RE = re.compile(r"\bDEBUG\b", re.IGNORECASE)
LOG4J_LEVEL_RE = re.compile(
    r"^\s*\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}:\d{2}[.,]\d+\s+(TRACE|DEBUG|INFO|WARN|WARNING|ERROR|FATAL)\b",
    re.IGNORECASE,
)
ERR_NULL_RE = re.compile(r"\berr=(?:null|nil|<nil>|\"\"|'')\b", re.IGNORECASE)


def is_warning(message: object) -> bool:
    return isinstance(message, str) and bool(WARN_RE.search(message))


def is_error(message: object) -> bool:
    if not isinstance(message, str):
        return False
    header = LOG4J_LEVEL_RE.search(message)
    if header and header.group(1).upper() in {"ERROR", "FATAL"}:
        return True
    cleaned = ERR_NULL_RE.sub("", message)
    return bool(ERROR_RE.search(cleaned))


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
    cleaned = ERR_NULL_RE.sub("", message)
    if ERROR_RE.search(cleaned):
        return "ERROR"
    if DEBUG_RE.search(message):
        return "DEBUG"
    if INFO_RE.search(message):
        return "INFO"
    return "INFO"
