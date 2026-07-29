"""Write score run artifacts (JSON + Markdown)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from flowpact.score.run import CaseScore, ScoreRunResult


def write_run_artifacts(result: ScoreRunResult, out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    _write_json(out_dir / "manifest.json", result.manifest)
    _write_json(out_dir / "scorecard.json", result.scorecard)
    _write_json(out_dir / "population_audit.json", result.audit.to_dict())
    (out_dir / "scorecard.md").write_text(_scorecard_md(result), encoding="utf-8")
    (out_dir / "failure_cards.md").write_text(_failure_cards_md(result.cases), encoding="utf-8")


def _write_json(path: Path, obj: Any) -> None:
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _scorecard_md(result: ScoreRunResult) -> str:
    lines = [
        f"# Scorecard — {result.claim_id or '(no claim)'}",
        "",
        f"**Result:** {result.claim_result}",
        f"**Mean score:** {result.mean_score:.4f}",
        f"**Aggregate:** `{result.aggregate.expression or '(unbounded)'}`",
        f"**Cases scored:** {len(result.cases)}",
        "",
        "| id | score | hard_gate_failed | failed_gates |",
        "| --- | ---: | --- | --- |",
    ]
    for c in result.cases:
        gates = ", ".join(c.failed_gates) if c.failed_gates else "—"
        lines.append(f"| `{c.id}` | {c.score:.4f} | {c.hard_gate_failed} | {gates} |")
    lines.append("")
    return "\n".join(lines)


def _failure_cards_md(cases: list[CaseScore]) -> str:
    failures = [
        c for c in cases if c.hard_gate_failed or any(sf["score"] < 1.0 for sf in c.soft_fields)
    ]
    lines = ["# SME failure cards", ""]
    if not failures:
        lines.append("No failing cases.")
        lines.append("")
        return "\n".join(lines)

    for c in failures:
        lines.append(f"## Case `{c.id}`")
        lines.append("")
        lines.append(f"- **Case score:** {c.score:.4f}")
        if c.failed_gates:
            lines.append(f"- **Failed hard gates:** {', '.join(f'`{g}`' for g in c.failed_gates)}")
        else:
            lines.append("- **Failed hard gates:** none")

        soft_sorted = sorted(c.soft_fields, key=lambda s: (s["score"], s["field"]))
        worst = soft_sorted[:3]
        if worst:
            lines.append("- **Worst soft fields:**")
            for sf in worst:
                lines.append(
                    f"  - `{sf['field']}` ({sf['method']}): "
                    f"score={sf['score']:.4f}, weight={sf['weight']}"
                )
                lines.append(f"    - gold: {sf.get('gold')!r}")
                lines.append(f"    - draft: {sf.get('draft')!r}")
        lines.append("")
    return "\n".join(lines)
