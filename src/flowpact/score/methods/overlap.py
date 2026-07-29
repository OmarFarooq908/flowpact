"""Token-overlap soft-field method (offline Jaccard on whitespace tokens)."""

from __future__ import annotations

import re
from typing import Any

_TOKEN = re.compile(r"[a-z0-9]+", re.IGNORECASE)


def _tokens(value: Any) -> set[str]:
    if value is None:
        return set()
    text = str(value).lower()
    return set(_TOKEN.findall(text))


def token_overlap(gold: Any, draft: Any) -> float:
    """Jaccard similarity of normalized alphanumeric tokens. Deterministic."""
    g = _tokens(gold)
    d = _tokens(draft)
    if not g and not d:
        return 1.0
    if not g or not d:
        return 0.0
    inter = len(g & d)
    union = len(g | d)
    return inter / union if union else 0.0
