"""Population include/exclude filtering and audit."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from typing import Any

from flowpact.score.io import ScoreInputError, get_path
from flowpact.score.rules import parse_rule, rule_matches


@dataclass
class PopulationAudit:
    n_gold: int = 0
    n_drafts: int = 0
    n_paired: int = 0
    n_scored: int = 0
    n_excluded: int = 0
    reason_histogram: dict[str, int] = field(default_factory=dict)
    exclude_reasons: dict[str, list[str]] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "n_gold": self.n_gold,
            "n_drafts": self.n_drafts,
            "n_paired": self.n_paired,
            "n_scored": self.n_scored,
            "n_excluded": self.n_excluded,
            "reason_histogram": dict(sorted(self.reason_histogram.items())),
            "exclude_reasons": {k: self.exclude_reasons[k] for k in sorted(self.exclude_reasons)},
        }


def _eval_clause(
    record: dict[str, Any],
    clause: dict[str, Any],
    *,
    lenient: bool,
    warnings: list[str],
) -> bool | None:
    """Return True/False if evaluable; None if skipped under lenient mode."""
    field_name = clause.get("field")
    rule = clause.get("rule")
    if not field_name:
        raise ScoreInputError("Population clause missing 'field'")
    parsed = parse_rule(rule)
    if parsed.kind == "unparseable":
        msg = (
            f"Unparseable population rule for field {field_name!r}: {rule!r}. "
            "Use 'equals <value>', 'in a, b, c', or a bare token."
        )
        if lenient:
            warnings.append(msg)
            return None
        raise ScoreInputError(msg)
    return rule_matches(get_path(record, str(field_name)), parsed)


def filter_population(
    paired: dict[str, tuple[dict[str, Any], dict[str, Any]]],
    population: dict[str, Any] | None,
    *,
    lenient_rules: bool = False,
) -> tuple[dict[str, tuple[dict[str, Any], dict[str, Any]]], PopulationAudit, list[str]]:
    """Filter paired gold/draft records. Returns scored map, audit stub, warnings.

    Include: all include clauses that are evaluable must match (AND).
    If there are no evaluable includes, all paired records are candidates.
    Exclude: any matching exclude clause removes the record.
    Population filters use the **gold** record.
    """
    warnings: list[str] = []
    includes = list((population or {}).get("include") or [])
    excludes = list((population or {}).get("exclude") or [])

    scored: dict[str, tuple[dict[str, Any], dict[str, Any]]] = {}
    exclude_reasons: dict[str, list[str]] = {}
    reason_counter: Counter[str] = Counter()

    for key in sorted(paired):
        gold, draft = paired[key]
        reasons: list[str] = []

        include_results: list[bool] = []
        for clause in includes:
            result = _eval_clause(gold, clause, lenient=lenient_rules, warnings=warnings)
            if result is None:
                continue
            include_results.append(result)
            if not result:
                reason = f"include_miss:{clause.get('field')}"
                reasons.append(reason)

        if include_results and not all(include_results):
            # already collected reasons
            pass
        else:
            for clause in excludes:
                result = _eval_clause(gold, clause, lenient=lenient_rules, warnings=warnings)
                if result is None:
                    continue
                if result:
                    reason = f"exclude_hit:{clause.get('field')}"
                    reasons.append(reason)

        if reasons:
            # Deduplicate while preserving order
            uniq = list(dict.fromkeys(reasons))
            exclude_reasons[key] = uniq
            for r in uniq:
                reason_counter[r] += 1
        else:
            scored[key] = (gold, draft)

    audit = PopulationAudit(
        n_excluded=len(exclude_reasons),
        n_scored=len(scored),
        reason_histogram=dict(reason_counter),
        exclude_reasons=exclude_reasons,
    )
    return scored, audit, warnings
