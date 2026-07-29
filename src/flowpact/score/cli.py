"""CLI for ``flowpact-score`` (optional ``flowpact[score]`` extra)."""

from __future__ import annotations

from pathlib import Path

import typer

from flowpact.score.diff import diff_runs, write_diff_report
from flowpact.score.io import ScoreInputError
from flowpact.score.report import write_run_artifacts
from flowpact.score.run import run_score

app = typer.Typer(
    name="flowpact-score",
    help="Execute a Flowpact success claim as structured draft-vs-gold scoring.",
    no_args_is_help=True,
)


def _exit_input(msg: str) -> None:
    typer.secho(msg, fg=typer.colors.RED, err=True)
    raise typer.Exit(code=2)


@app.command("run")
def run_cmd(
    export_eng: Path = typer.Option(..., "--export-eng", help="export-eng.json from flowpact"),
    gold: Path = typer.Option(..., "--gold", help="Gold JSONL path"),
    drafts: Path = typer.Option(..., "--drafts", help="Drafts JSONL path"),
    out: Path = typer.Option(..., "--out", help="Output directory for score artifacts"),
    id_field: str = typer.Option("id", "--id-field", help="Join key field (dotted path ok)"),
    allow_unbounded: bool = typer.Option(
        False,
        "--allow-unbounded",
        help="Allow unparseable/missing aggregate (skip claim threshold)",
    ),
    lenient_rules: bool = typer.Option(
        False,
        "--lenient-rules",
        help="WARN and skip unparseable population rules instead of exiting",
    ),
    require_claim_clear: bool = typer.Option(
        False,
        "--require-claim-clear",
        help="Refuse to score if pact claim has no-claim blockers (needs --pact)",
    ),
    pact: Path | None = typer.Option(
        None,
        "--pact",
        help="pact.yaml for --require-claim-clear (reuses flowpact no-claim blockers)",
    ),
) -> None:
    """Score gold vs drafts using the recipe in export-eng.json."""
    try:
        if require_claim_clear:
            if pact is None:
                _exit_input("--require-claim-clear requires --pact PATH")
            _check_claim_clear(pact, export_eng)

        result = run_score(
            export_eng_path=export_eng,
            gold_path=gold,
            drafts_path=drafts,
            id_field=id_field,
            allow_unbounded=allow_unbounded,
            lenient_rules=lenient_rules,
        )
    except ScoreInputError as exc:
        _exit_input(str(exc))

    for w in result.warnings:
        typer.secho(f"WARNING: {w}", fg=typer.colors.YELLOW, err=True)

    write_run_artifacts(result, out)
    typer.echo(f"Wrote score artifacts to {out}")
    typer.echo(f"claim_result={result.claim_result} mean_score={result.mean_score:.4f}")

    if result.claim_result == "FAIL":
        raise typer.Exit(code=1)


def _check_claim_clear(pact_path: Path, export_eng_path: Path) -> None:
    from flowpact.pact import blockers_for_claim, load_pact, validate_pact
    from flowpact.score.io import load_json

    pact_data = load_pact(pact_path)
    v = validate_pact(pact_data)
    if not v.ok:
        raise ScoreInputError("Invalid pact:\n" + "\n".join(v.errors))

    export = load_json(export_eng_path)
    claim_id = export.get("claim_id") if isinstance(export, dict) else None
    if not claim_id:
        raise ScoreInputError("export-eng.json missing claim_id for --require-claim-clear")
    blockers = blockers_for_claim(pact_data, str(claim_id))
    if blockers:
        ids = ", ".join(b["id"] for b in blockers)
        raise ScoreInputError(
            f"Claim {claim_id!r} is blocked ({ids}). "
            "Run `flowpact no-claim --strict` or clear blockers before scoring."
        )


@app.command("diff")
def diff_cmd(
    baseline: Path = typer.Option(..., "--baseline", help="Baseline manifest.json"),
    candidate: Path = typer.Option(..., "--candidate", help="Candidate manifest.json"),
    out: Path | None = typer.Option(
        None,
        "--out",
        help="Optional path for diff markdown (JSON written beside it)",
    ),
) -> None:
    """Compare two score runs for regressions."""
    try:
        result = diff_runs(baseline, candidate)
    except ScoreInputError as exc:
        _exit_input(str(exc))

    text = write_diff_report(result, out)
    typer.echo(text)
    if result.regression:
        raise typer.Exit(code=1)


def main() -> None:
    app()


if __name__ == "__main__":
    main()
