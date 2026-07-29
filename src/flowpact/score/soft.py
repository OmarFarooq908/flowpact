"""Soft-field method registry."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from flowpact.score.io import ScoreInputError, get_path
from flowpact.score.methods.exact import exact_match
from flowpact.score.methods.overlap import token_overlap

ScoreFn = Callable[[Any, Any], float]

_OFFLINE: dict[str, ScoreFn] = {
    "exact_match": exact_match,
    "token_overlap": token_overlap,
}


def _load_optional(name: str) -> ScoreFn:
    if name == "embedding_similarity":
        from flowpact.score.methods.embedding import embedding_similarity

        return embedding_similarity
    if name == "llm_judge":
        from flowpact.score.methods.llm_judge import llm_judge

        return llm_judge
    raise ScoreInputError(f"Unknown soft-field method: {name!r}")


def resolve_method(name: str) -> ScoreFn:
    if name in _OFFLINE:
        return _OFFLINE[name]
    return _load_optional(name)


def score_soft_fields(
    gold: dict[str, Any],
    draft: dict[str, Any],
    soft_fields: list[dict[str, Any]] | None,
) -> tuple[float, list[dict[str, Any]]]:
    """Return (weighted_score, per-field breakdown). Weights need not sum to 1;
    if total weight is 0, score is 0.
    """
    breakdown: list[dict[str, Any]] = []
    weighted_sum = 0.0
    weight_total = 0.0

    for spec in soft_fields or []:
        field = str(spec.get("field") or "")
        method = str(spec.get("method") or "")
        weight = float(spec.get("weight") or 0.0)
        fn = resolve_method(method)
        gold_val = get_path(gold, field)
        draft_val = get_path(draft, field)
        field_score = float(fn(gold_val, draft_val))
        breakdown.append(
            {
                "field": field,
                "method": method,
                "weight": weight,
                "score": field_score,
                "gold": _snippet(gold_val),
                "draft": _snippet(draft_val),
            }
        )
        weighted_sum += weight * field_score
        weight_total += weight

    if weight_total <= 0:
        return 0.0, breakdown
    return weighted_sum / weight_total, breakdown


def _snippet(value: Any, limit: int = 120) -> Any:
    if isinstance(value, str) and len(value) > limit:
        return value[: limit - 1] + "…"
    return value
