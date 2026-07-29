"""Aggregate threshold parsing and claim pass/fail."""

from __future__ import annotations

import re
from dataclasses import dataclass

from flowpact.score.io import ScoreInputError

_MEAN_GE = re.compile(
    r"^\s*mean_score\s*>=\s*([+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?)\s*$",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class AggregateSpec:
    expression: str
    threshold: float | None
    unbounded: bool = False


def parse_aggregate(expression: str | None, *, allow_unbounded: bool = False) -> AggregateSpec:
    raw = "" if expression is None else str(expression).strip()
    if not raw:
        if allow_unbounded:
            return AggregateSpec(expression=raw, threshold=None, unbounded=True)
        raise ScoreInputError(
            "Missing aggregate expression. Provide mean_score >= <float> or pass --allow-unbounded."
        )
    m = _MEAN_GE.match(raw)
    if m:
        return AggregateSpec(expression=raw, threshold=float(m.group(1)))
    if allow_unbounded:
        return AggregateSpec(expression=raw, threshold=None, unbounded=True)
    raise ScoreInputError(
        f"Unparseable aggregate {raw!r}. Supported: 'mean_score >= <float>'. "
        "Pass --allow-unbounded to skip the claim threshold check."
    )


def claim_passes(mean_score: float, spec: AggregateSpec) -> bool:
    if spec.unbounded or spec.threshold is None:
        return True
    return mean_score >= spec.threshold
