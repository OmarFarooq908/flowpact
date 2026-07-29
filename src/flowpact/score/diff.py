"""Regression diff between two score run manifests / scorecards."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from flowpact.score.io import ScoreInputError, load_json


@dataclass
class DiffResult:
    population_hash_mismatch: bool
    score_delta: float
    newly_failing_ids: list[str]
    newly_passing_ids: list[str]
    baseline_mean: float
    candidate_mean: float
    baseline_claim: str
    candidate_claim: str
    report: dict[str, Any]

    @property
    def regression(self) -> bool:
        if self.population_hash_mismatch:
            return True
        if self.newly_failing_ids:
            return True
        if self.candidate_mean < self.baseline_mean:
            return True
        if self.baseline_claim == "PASS" and self.candidate_claim == "FAIL":
            return True
        return False


def _load_manifest(path: Path) -> dict[str, Any]:
    data = load_json(path)
    if not isinstance(data, dict):
        raise ScoreInputError(f"Manifest must be a JSON object: {path}")
    return data


def _load_scorecard_beside(manifest_path: Path) -> dict[str, Any] | None:
    sibling = manifest_path.parent / "scorecard.json"
    if not sibling.is_file():
        return None
    data = load_json(sibling)
    return data if isinstance(data, dict) else None


def _case_pass_map(scorecard: dict[str, Any] | None) -> dict[str, bool]:
    """A case 'passes' when score > 0 and hard_gate_failed is false."""
    if not scorecard:
        return {}
    out: dict[str, bool] = {}
    for case in scorecard.get("cases") or []:
        if not isinstance(case, dict):
            continue
        cid = str(case.get("id"))
        score = float(case.get("score") or 0.0)
        failed = bool(case.get("hard_gate_failed"))
        out[cid] = (not failed) and score > 0.0
    return out


def diff_runs(baseline_manifest: Path, candidate_manifest: Path) -> DiffResult:
    base = _load_manifest(baseline_manifest)
    cand = _load_manifest(candidate_manifest)

    base_pop = (base.get("hashes") or {}).get("population")
    cand_pop = (cand.get("hashes") or {}).get("population")
    pop_mismatch = base_pop != cand_pop

    base_mean = float(base.get("mean_score") or 0.0)
    cand_mean = float(cand.get("mean_score") or 0.0)
    score_delta = cand_mean - base_mean

    base_cases = _case_pass_map(_load_scorecard_beside(baseline_manifest))
    cand_cases = _case_pass_map(_load_scorecard_beside(candidate_manifest))

    newly_failing = sorted(
        cid for cid, passed in base_cases.items() if passed and not cand_cases.get(cid, False)
    )
    newly_passing = sorted(
        cid for cid, passed in cand_cases.items() if passed and not base_cases.get(cid, False)
    )

    report = {
        "population_hash_mismatch": pop_mismatch,
        "baseline_population_hash": base_pop,
        "candidate_population_hash": cand_pop,
        "baseline_mean": base_mean,
        "candidate_mean": cand_mean,
        "score_delta": score_delta,
        "baseline_claim_result": base.get("claim_result"),
        "candidate_claim_result": cand.get("claim_result"),
        "newly_failing_ids": newly_failing,
        "newly_passing_ids": newly_passing,
        "regression": False,  # filled below
    }
    result = DiffResult(
        population_hash_mismatch=pop_mismatch,
        score_delta=score_delta,
        newly_failing_ids=newly_failing,
        newly_passing_ids=newly_passing,
        baseline_mean=base_mean,
        candidate_mean=cand_mean,
        baseline_claim=str(base.get("claim_result") or ""),
        candidate_claim=str(cand.get("claim_result") or ""),
        report=report,
    )
    report["regression"] = result.regression
    return result


def format_diff_markdown(diff: DiffResult) -> str:
    lines = [
        "# Score diff",
        "",
        f"**Regression:** {diff.regression}",
        f"**Population hash mismatch:** {diff.population_hash_mismatch}",
        f"**Mean delta:** {diff.score_delta:+.4f} "
        f"({diff.baseline_mean:.4f} → {diff.candidate_mean:.4f})",
        f"**Claim:** {diff.baseline_claim} → {diff.candidate_claim}",
        "",
        f"**Newly failing:** {', '.join(f'`{i}`' for i in diff.newly_failing_ids) or '—'}",
        f"**Newly passing:** {', '.join(f'`{i}`' for i in diff.newly_passing_ids) or '—'}",
        "",
    ]
    return "\n".join(lines)


def write_diff_report(diff: DiffResult, out_path: Path | None) -> str:
    text = format_diff_markdown(diff)
    if out_path is not None:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(text, encoding="utf-8")
        if out_path.suffix == ".md":
            json_path = out_path.with_name(out_path.stem + ".json")
        elif out_path.suffix:
            json_path = out_path.with_suffix(".json")
        else:
            json_path = Path(str(out_path) + ".json")
        json_path.write_text(
            json.dumps(diff.report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
    return text
