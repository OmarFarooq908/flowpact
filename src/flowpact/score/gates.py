"""Hard-gate evaluation for draft-vs-gold scoring."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from flowpact.score.io import get_path, normalize_value
from flowpact.score.rules import parse_rule, rule_matches


@dataclass(frozen=True)
class GateResult:
    field: str
    passed: bool
    on_fail: str
    detail: str


def evaluate_hard_gates(
    gold: dict[str, Any],
    draft: dict[str, Any],
    hard_gates: list[dict[str, Any]] | None,
) -> list[GateResult]:
    """Evaluate hard gates.

    Executable semantics (draft-vs-gold):
    - Draft field must be non-empty.
    - Draft field must equal gold field (normalized).
    - If the rule string is a parseable DSL and does not look like prose about
      matching gold, also require the draft field to satisfy the DSL.
    - ``on_fail`` defaults to ``zero_score``.
    """
    results: list[GateResult] = []
    for gate in hard_gates or []:
        field = str(gate.get("field") or "")
        on_fail = str(gate.get("on_fail") or "zero_score")
        rule = gate.get("rule")
        gold_val = get_path(gold, field)
        draft_val = get_path(draft, field)

        if draft_val is None or draft_val == "":
            results.append(
                GateResult(
                    field=field,
                    passed=False,
                    on_fail=on_fail,
                    detail="draft field missing or empty",
                )
            )
            continue

        if normalize_value(draft_val) != normalize_value(gold_val):
            results.append(
                GateResult(
                    field=field,
                    passed=False,
                    on_fail=on_fail,
                    detail="draft does not match gold",
                )
            )
            continue

        parsed = parse_rule(rule if isinstance(rule, str) else None)
        if parsed.kind != "unparseable":
            # Optional extra constraint on draft value from DSL
            if not rule_matches(draft_val, parsed):
                results.append(
                    GateResult(
                        field=field,
                        passed=False,
                        on_fail=on_fail,
                        detail=f"draft failed rule {parsed.raw!r}",
                    )
                )
                continue

        results.append(GateResult(field=field, passed=True, on_fail=on_fail, detail="ok"))
    return results


def case_zeroed(gate_results: list[GateResult]) -> bool:
    return any((not g.passed) and g.on_fail == "zero_score" for g in gate_results)
