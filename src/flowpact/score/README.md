"""Optional scoring: population DSL, field paths, methods."""

from __future__ import annotations

# Field paths use dotted segments and optional numeric indices:
#   answer_body          top-level key
#   meta.locale          nested object
#   items.0.id           list index (also items[0].id)
#
# Population / hard-gate ``rule`` executable subset:
#   equals <value>       field equality (normalized)
#   <bare-token>         same as equals (no whitespace)
#   in a, b, c           membership
#
# Hard gates (draft-vs-gold): draft field must be non-empty and equal gold.
# Prose rules that are not parseable DSL are ignored for execution (human-facing).
#
# Soft methods:
#   exact_match          offline
#   token_overlap        offline Jaccard on alphanumeric tokens
#   embedding_similarity requires flowpact[score-embed] (stub in MVP)
#   llm_judge            requires flowpact[score-llm] (stub; off by default)
