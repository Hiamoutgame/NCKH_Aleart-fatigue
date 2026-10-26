"""Drain online log parser (He et al., ICWS 2017, Section III), one tree per incident.

Step 1 (domain-knowledge preprocessing) is `normalize_message` plus
`split_header`: the paper's parsers read the message content, so known headers
are split off first (Spring Boot "LEVEL <N> --- [thread] logger :", Nezha
TrainTicket "<N>:<N>:<N> LEVEL logger TraceID: .. SpanID: ..", and the
variable-only prefixes go-kit "ts=" and Nezha "TraceID: .. SpanID: .."). Left in,
a header fills the leading tokens that Step 3 routes on and makes unrelated
messages look similar in Step 4. "LEVEL logger" is kept as a fixed template
prefix with its own tree, so loggers never merge. The content is then split on
whitespace and runs Steps 2-5:

  2. pick the first-layer node by message length (number of tokens);
  3. walk (depth - 2) internal layers by the leading tokens; a token with a
     digit, or any new token once a node has `max_child` children, goes to "<*>";
  4. in the leaf, take the log group with the highest simSeq (share of
     positions whose tokens are equal) and accept it if simSeq >= st;
  5. add the log ID to that group and wildcard the template positions that
     differ, or else start a new group from the message.

Each log ID lands in exactly one group. A group's template keeps changing
while logs arrive, so the template reported for every member is the one the
group has after the whole incident is parsed.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field, replace
from typing import Iterable, Optional, Sequence

from src.shared.domain.canonical import LogEvent

WILDCARD = "<*>"
# Matched on normalize_message output, where the PID is already "<N>".
SPRING_HEADER_RE = re.compile(
    r"^(?P<level>[A-Z]+)\s+(?:\[[^\]]*\]\s+)?<N>\s+---\s+(?:\[[^\]]*\]|<THREAD>)\s+"
    r"(?P<logger>\S+)\s+:\s?(?P<content>.*)$"
)
NEZHA_HEADER_RE = re.compile(
    r"^<N>:<N>:<N>\s+(?P<level>[A-Z]+)\s+(?P<logger>\S+)\s+TraceID:\s+\S+\s+SpanID:\s+\S+\s*(?P<content>.*)$"
)
VARIABLE_PREFIX_RE = re.compile(r"^(?:ts=\S+|TraceID:\s+\S+\s+SpanID:\s+\S+)\s*")


@dataclass(frozen=True)
class DrainConfig:
    """Drain parameters. The paper uses depth 3-4 and st 0.3-0.5 (Table II), max_child 100."""

    depth: int = 4
    st: float = 0.4
    max_child: int = 100

    def __post_init__(self) -> None:
        if self.depth < 2:
            raise ValueError("depth must be >= 2 (root and length layer)")
        if not 0.0 <= self.st <= 1.0:
            raise ValueError("st must be within [0, 1]")
        if self.max_child < 1:
            raise ValueError("max_child must be >= 1")


@dataclass
class LogGroup:
    """Log event (template tokens) plus the IDs of the logs it holds."""

    template: list[str]
    log_ids: list[str] = field(default_factory=list)

    @property
    def template_text(self) -> str:
        return " ".join(self.template)


class _Node:
    __slots__ = ("children", "groups")

    def __init__(self) -> None:
        self.children: dict[str, _Node] = {}
        self.groups: list[LogGroup] = []


def _has_digit(token: str) -> bool:
    return any(char.isdigit() for char in token)


def sim_seq(template: Sequence[str], tokens: Sequence[str]) -> float:
    """Equation (1): equal tokens at the same position / message length."""
    return sum(a == b for a, b in zip(template, tokens)) / len(tokens)


class DrainParser:
    def __init__(self, config: DrainConfig = DrainConfig()) -> None:
        self.config = config
        self.length_layer: dict[int, _Node] = {}
        self.groups: list[LogGroup] = []

    def _child(self, node: _Node, token: str) -> _Node:
        if token in node.children:
            return node.children[token]
        if _has_digit(token) or len(node.children) >= self.config.max_child:
            # The "<*>" child may be the (max_child + 1)-th child of a full node.
            return node.children.setdefault(WILDCARD, _Node())
        return node.children.setdefault(token, _Node())

    def _leaf(self, tokens: Sequence[str]) -> _Node:
        node = self.length_layer.setdefault(len(tokens), _Node())
        for token in tokens[: self.config.depth - 2]:
            node = self._child(node, token)
        return node

    def _most_similar(self, groups: Sequence[LogGroup], tokens: Sequence[str]) -> Optional[LogGroup]:
        best: Optional[LogGroup] = None
        best_sim = -1.0
        for group in groups:  # ties keep the oldest group, so runs are reproducible
            similarity = sim_seq(group.template, tokens)
            if similarity > best_sim:
                best, best_sim = group, similarity
        return best if best is not None and best_sim >= self.config.st else None

    def add(self, log_id: str, tokens: Sequence[str]) -> LogGroup:
        """Parse one log message (already tokenized) and return its group."""
        if not tokens:
            raise ValueError("Drain needs at least one token")
        leaf = self._leaf(tokens)
        group = self._most_similar(leaf.groups, tokens)
        if group is None:
            group = LogGroup(template=list(tokens))
            leaf.groups.append(group)
            self.groups.append(group)
        else:
            group.template = [t if t == m else WILDCARD for t, m in zip(group.template, tokens)]
        group.log_ids.append(log_id)
        return group


def split_header(parsed_message: str) -> tuple[str, list[str]]:
    """Return (fixed header prefix, content tokens) for one normalized message."""
    match = SPRING_HEADER_RE.match(parsed_message)
    if match:
        return f"{match['level']} {match['logger']} :", match["content"].split()
    match = NEZHA_HEADER_RE.match(parsed_message)
    if match:
        return f"{match['level']} {match['logger']}", match["content"].split()
    return "", VARIABLE_PREFIX_RE.sub("", parsed_message).split()


def template_hash(template: str) -> str:
    return hashlib.md5(template.encode("utf-8")).hexdigest()[:12]


def drain_columns(
    incident_ids: Iterable[str],
    log_ids: Iterable[str],
    parsed_messages: Iterable[Optional[str]],
    config: DrainConfig = DrainConfig(),
) -> tuple[list[Optional[str]], list[Optional[str]]]:
    """Drain template and template ID per message, parsing each incident in the given order.

    Messages that are empty after preprocessing get None, like template_id.
    """
    parsers: dict[tuple[str, str], DrainParser] = {}
    parsed: list[tuple[str, Optional[LogGroup]]] = []
    for incident_id, log_id, message in zip(incident_ids, log_ids, parsed_messages):
        header, tokens = split_header(message or "")
        group = None
        if tokens:
            parser = parsers.setdefault((incident_id, header), DrainParser(config))
            group = parser.add(log_id, tokens)
        parsed.append((header, group))

    templates: list[Optional[str]] = []
    template_ids: list[Optional[str]] = []
    hashes: dict[str, str] = {}
    for header, group in parsed:
        # Read only now: a group's template is final once the whole incident is parsed.
        text = " ".join(part for part in (header, group.template_text if group else "") if part)
        if text and text not in hashes:
            hashes[text] = template_hash(text)
        templates.append(text or None)
        template_ids.append(hashes[text] if text else None)
    return templates, template_ids


def assign_drain_templates(events: Sequence[LogEvent], config: DrainConfig = DrainConfig()) -> list[LogEvent]:
    """Fill drain_template/drain_template_id on events, see drain_columns."""
    templates, template_ids = drain_columns(
        (event.incident_id for event in events),
        (event.log_id for event in events),
        (event.parsed_message for event in events),
        config,
    )
    return [
        replace(event, drain_template=template, drain_template_id=template_id)
        for event, template, template_id in zip(events, templates, template_ids)
    ]
