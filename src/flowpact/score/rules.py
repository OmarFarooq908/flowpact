"""Executable population / gate rule DSL.

Supported forms (case-insensitive keywords):

- bare token / ``equals <value>`` → field equality
- ``in a, b, c`` → membership

Anything else is unparseable prose (human-facing only).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Literal

from flowpact.score.io import get_path, normalize_value

RuleKind = Literal["equals", "in", "unparseable"]


@dataclass(frozen=True)
class ParsedRule:
    kind: RuleKind
    value: Any = None
    values: tuple[Any, ...] = ()
    raw: str = ""


_EQUALS_RE = re.compile(r"^\s*equals\s+(.+?)\s*$", re.IGNORECASE)
_IN_RE = re.compile(r"^\s*in\s+(.+?)\s*$", re.IGNORECASE)


def parse_rule(rule: str | None) -> ParsedRule:
    raw = "" if rule is None else str(rule).strip()
    if not raw:
        return ParsedRule(kind="unparseable", raw=raw)

    m_eq = _EQUALS_RE.match(raw)
    if m_eq:
        return ParsedRule(kind="equals", value=_coerce_literal(m_eq.group(1).strip()), raw=raw)

    m_in = _IN_RE.match(raw)
    if m_in:
        parts = tuple(_coerce_literal(p.strip()) for p in m_in.group(1).split(",") if p.strip())
        if not parts:
            return ParsedRule(kind="unparseable", raw=raw)
        return ParsedRule(kind="in", values=parts, raw=raw)

    # Bare token: no spaces → equals; otherwise unparseable prose
    if re.fullmatch(r"[^\s,]+", raw):
        return ParsedRule(kind="equals", value=_coerce_literal(raw), raw=raw)

    return ParsedRule(kind="unparseable", raw=raw)


def _coerce_literal(text: str) -> Any:
    lower = text.lower()
    if lower == "true":
        return True
    if lower == "false":
        return False
    if lower == "null" or lower == "none":
        return None
    try:
        if re.fullmatch(r"-?\d+", text):
            return int(text)
        if re.fullmatch(r"-?\d+\.\d+", text):
            return float(text)
    except ValueError:
        pass
    return text


def rule_matches(field_value: Any, parsed: ParsedRule) -> bool:
    if parsed.kind == "unparseable":
        raise ValueError(f"Cannot evaluate unparseable rule: {parsed.raw!r}")
    norm = normalize_value(field_value)
    if parsed.kind == "equals":
        return norm == normalize_value(parsed.value)
    if parsed.kind == "in":
        allowed = {normalize_value(v) for v in parsed.values}
        return norm in allowed
    return False


def field_matches_rule(record: dict[str, Any], field: str, rule: str | None) -> bool:
    parsed = parse_rule(rule)
    return rule_matches(get_path(record, field), parsed)
