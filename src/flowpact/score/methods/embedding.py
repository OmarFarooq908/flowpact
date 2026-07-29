"""Embedding similarity — requires ``flowpact[score-embed]``."""

from __future__ import annotations

from typing import Any

from flowpact.score.io import ScoreInputError


def embedding_similarity(gold: Any, draft: Any) -> float:
    try:
        import numpy  # noqa: F401
    except ImportError as exc:
        raise ScoreInputError(
            "Method 'embedding_similarity' requires optional deps. "
            "Install with: pip install 'flowpact[score-embed]'"
        ) from exc
    # Stub: deps present but no model wired in MVP — still fail clearly.
    raise ScoreInputError(
        "Method 'embedding_similarity' is not fully configured in this MVP. "
        "Use 'token_overlap' or 'exact_match' offline, or contribute a model backend."
    )
