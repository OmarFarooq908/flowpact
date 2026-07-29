"""Exact-match soft-field method."""

from __future__ import annotations

from typing import Any

from flowpact.score.io import normalize_value


def exact_match(gold: Any, draft: Any) -> float:
    if gold is None and draft is None:
        return 1.0
    return 1.0 if normalize_value(gold) == normalize_value(draft) else 0.0
