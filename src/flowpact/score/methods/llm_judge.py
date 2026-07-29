"""LLM judge soft-field method — requires ``flowpact[score-llm]``. Off by default."""

from __future__ import annotations

from typing import Any

from flowpact.score.io import ScoreInputError


def llm_judge(gold: Any, draft: Any) -> float:
    try:
        import openai  # noqa: F401
    except ImportError as exc:
        raise ScoreInputError(
            "Method 'llm_judge' requires optional deps. "
            "Install with: pip install 'flowpact[score-llm]'"
        ) from exc
    raise ScoreInputError(
        "Method 'llm_judge' is not fully configured in this MVP and is off by default. "
        "Use 'token_overlap' or 'exact_match' for offline scoring."
    )
