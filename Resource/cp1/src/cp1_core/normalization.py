"""Canonical CP1 message normalization, based on final_verification.py."""

from __future__ import annotations

import re


RE_TS = re.compile(r"^\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}:\d{2}[.,]\d+\s*")
RE_UUID = re.compile(r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}")
RE_HEX = re.compile(r"\b[0-9a-f]{8,}\b")
RE_THREAD = re.compile(r"\[\s*[-\w]*nio-\d+-exec-\d+\s*\]|\[\s*\w*Container-\d+\s*\]|\[\s*main\s*\]")
RE_LOG4J_HDR = re.compile(r"^(\d{4}-\d{2}-\d{2}[ T][\d:.,]+)\s+(\w+)\s+(\[[^\]]*\])\s+(\d+)\s+---\s+(\[[^\]]*\])\s*")
RE_NUM = re.compile(r"\b\d+(?:\.\d+)?\b")


def normalize_message(message: object) -> str:
    if not isinstance(message, str):
        return ""
    normalized = RE_TS.sub("", message)
    normalized = RE_UUID.sub("<UUID>", normalized)
    normalized = RE_LOG4J_HDR.sub(
        lambda match: f"<TS> {match.group(2)} {match.group(3)} <PID> --- {match.group(5)} ",
        normalized,
    )
    normalized = RE_THREAD.sub("<THREAD>", normalized)
    normalized = RE_HEX.sub("<HEX>", normalized)
    normalized = RE_NUM.sub("<N>", normalized)
    return normalized.strip()
