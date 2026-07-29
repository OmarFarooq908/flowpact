"""Score run orchestration."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from flowpact import __version__
from flowpact.score.aggregate import AggregateSpec, claim_passes, parse_aggregate
from flowpact.score.gates import case_zeroed, evaluate_hard_gates
from flowpact.score.io import (
    ScoreInputError,
    canonical_json,
    load_json,
    load_jsonl,
    sha256_file,
    sha256_keys,
    sha256_records,
    sha256_text,
)
from flowpact.score.population import PopulationAudit, filter_population
from flowpact.score.soft import score_soft_fields


@dataclass
class CaseScore:
    id: str
    score: float
    hard_gate_failed: bool
    failed_gates: list[str]
    soft_fields: list[dict[str, Any]]
    passed_case: bool  # soft aggregate contribution usable; gates may still zero

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "score": self.score,
            "hard_gate_failed": self.hard_gate_failed,
            "failed_gates": self.failed_gates,
            "soft_fields": self.soft_fields,
        }


@dataclass
class ScoreRunResult:
    claim_id: str | None
    claim_result: str  # PASS | FAIL
    mean_score: float
    aggregate: AggregateSpec
    cases: list[CaseScore]
    audit: PopulationAudit
    manifest: dict[str, Any]
    scorecard: dict[str, Any]
    warnings: list[str] = field(default_factory=list)


def pair_records(
    gold: dict[str, dict[str, Any]],
    drafts: dict[str, dict[str, Any]],
) -> dict[str, tuple[dict[str, Any], dict[str, Any]]]:
    common = sorted(set(gold) & set(drafts))
    return {k: (gold[k], drafts[k]) for k in common}


def run_score(
    *,
    export_eng_path: Path,
    gold_path: Path,
    drafts_path: Path,
    id_field: str = "id",
    allow_unbounded: bool = False,
    lenient_rules: bool = False,
) -> ScoreRunResult:
    export_eng = load_json(export_eng_path)
    if not isinstance(export_eng, dict):
        raise ScoreInputError("export-eng.json must be a JSON object")

    gold = load_jsonl(gold_path, id_field)
    drafts = load_jsonl(drafts_path, id_field)
    paired = pair_records(gold, drafts)

    population = export_eng.get("population")
    scored_map, audit, warnings = filter_population(
        paired, population if isinstance(population, dict) else None, lenient_rules=lenient_rules
    )
    audit.n_gold = len(gold)
    audit.n_drafts = len(drafts)
    audit.n_paired = len(paired)
    audit.n_scored = len(scored_map)
    audit.n_excluded = len(audit.exclude_reasons)

    hard_gates = export_eng.get("hard_gates")
    soft_fields = export_eng.get("soft_fields")
    aggregate_spec = parse_aggregate(
        export_eng.get("aggregate") if isinstance(export_eng.get("aggregate"), str) else None,
        allow_unbounded=allow_unbounded,
    )

    cases: list[CaseScore] = []
    for key in sorted(scored_map):
        g, d = scored_map[key]
        gate_results = evaluate_hard_gates(
            g, d, hard_gates if isinstance(hard_gates, list) else None
        )
        soft_score, breakdown = score_soft_fields(
            g, d, soft_fields if isinstance(soft_fields, list) else None
        )
        failed = [gr.field for gr in gate_results if not gr.passed]
        zeroed = case_zeroed(gate_results)
        case_score = 0.0 if zeroed else soft_score
        cases.append(
            CaseScore(
                id=key,
                score=case_score,
                hard_gate_failed=zeroed,
                failed_gates=failed,
                soft_fields=breakdown,
                passed_case=not zeroed and case_score > 0,
            )
        )

    mean = sum(c.score for c in cases) / len(cases) if cases else 0.0
    passed = claim_passes(mean, aggregate_spec)
    claim_result = "PASS" if passed else "FAIL"

    recipe_slice = {
        "claim_id": export_eng.get("claim_id"),
        "population": export_eng.get("population"),
        "hard_gates": export_eng.get("hard_gates"),
        "soft_fields": export_eng.get("soft_fields"),
        "aggregate": export_eng.get("aggregate"),
    }
    method_config = [
        {"field": s.get("field"), "method": s.get("method"), "weight": s.get("weight")}
        for s in (soft_fields if isinstance(soft_fields, list) else [])
    ]
    scored_ids = [c.id for c in cases]
    population_hash = sha256_keys(scored_ids)

    timestamp = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    manifest = {
        "flowpact_score_version": __version__,
        "timestamp": timestamp,
        "claim_id": export_eng.get("claim_id"),
        "id_field": id_field,
        "aggregate": aggregate_spec.expression,
        "claim_result": claim_result,
        "mean_score": mean,
        "hashes": {
            "export_eng": sha256_file(export_eng_path),
            "gold_keys": sha256_keys(sorted(gold.keys())),
            "drafts": sha256_records(drafts),
            "recipe": sha256_text(canonical_json(recipe_slice)),
            "method_config": sha256_text(canonical_json(method_config)),
            "population": population_hash,
        },
        "n_scored": len(cases),
    }

    scorecard = {
        "claim_id": export_eng.get("claim_id"),
        "claim_result": claim_result,
        "mean_score": mean,
        "aggregate": aggregate_spec.expression,
        "threshold": aggregate_spec.threshold,
        "cases": [c.to_dict() for c in cases],
    }

    return ScoreRunResult(
        claim_id=export_eng.get("claim_id"),
        claim_result=claim_result,
        mean_score=mean,
        aggregate=aggregate_spec,
        cases=cases,
        audit=audit,
        manifest=manifest,
        scorecard=scorecard,
        warnings=warnings,
    )
