"""Typer CLI for Flowpact."""

from __future__ import annotations

import json
import shutil
from importlib import resources
from pathlib import Path

import typer

from flowpact import __version__
from flowpact.pact import (
    PactError,
    blockers_for_claim,
    collect_asks,
    export_eng_payload,
    load_pact,
    validate_pact,
)

app = typer.Typer(
    name="flowpact",
    help="Workflow + success pact CLI for AI product engagements.",
    no_args_is_help=True,
)

TEMPLATES = ("ai-draft-vs-gold",)


def _fail(msg: str, code: int = 1) -> None:
    typer.secho(msg, fg=typer.colors.RED, err=True)
    raise typer.Exit(code)


@app.command()
def version() -> None:
    """Print package version."""
    typer.echo(__version__)


@app.command("init")
def init_cmd(
    path: Path = typer.Argument(Path("pact.yaml"), help="Output path for pact.yaml"),
    template: str = typer.Option(
        "ai-draft-vs-gold",
        "--template",
        "-t",
        help=f"Template name. Available: {', '.join(TEMPLATES)}",
    ),
    force: bool = typer.Option(False, "--force", help="Overwrite existing file"),
) -> None:
    """Write pact.yaml from a starter template."""
    if template not in TEMPLATES:
        _fail(f"unknown template '{template}'. Available: {', '.join(TEMPLATES)}")
    if path.exists() and not force:
        _fail(f"{path} already exists (use --force to overwrite)")
    src = resources.files("flowpact").joinpath(f"resources/templates/{template}.yaml")
    path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(str(src), path)
    typer.secho(f"Wrote {path} from template '{template}'", fg=typer.colors.GREEN)


@app.command()
def validate(
    path: Path = typer.Argument(Path("pact.yaml"), help="Path to pact.yaml"),
    strict: bool = typer.Option(
        False,
        "--strict",
        help="Treat warnings (open blockers) as errors",
    ),
) -> None:
    """Schema + referential checks."""
    try:
        pact = load_pact(path)
    except PactError as exc:
        _fail(str(exc))
    result = validate_pact(pact)
    for w in result.warnings:
        typer.secho(f"warning: {w}", fg=typer.colors.YELLOW, err=True)
    if result.errors:
        for e in result.errors:
            typer.secho(f"error: {e}", fg=typer.colors.RED, err=True)
        _fail(f"validate failed: {len(result.errors)} error(s)", code=1)
    if strict and result.warnings:
        _fail(f"validate failed under --strict: {len(result.warnings)} warning(s)", code=1)
    typer.secho(f"OK — {path}", fg=typer.colors.GREEN)


def _format_asks_md(pact: dict, rows: list[dict]) -> str:
    meta = pact.get("meta") or {}
    lines = [
        f"# Ask list — {meta.get('name', 'pact')}",
        "",
        f"**Client:** {meta.get('client', '')}  ",
        f"**Updated:** {meta.get('updated', '')}  ",
        f"**Items:** {len(rows)}",
        "",
    ]
    current_sev: str | None = None
    for row in rows:
        sev = row["severity"]
        if sev != current_sev:
            current_sev = sev
            lines.append(f"## {sev.capitalize()}")
            lines.append("")
        blocks = ", ".join(f"`{b}`" for b in row.get("blocks") or []) or "_(none)_"
        kind = {"evidence": "E", "policy": "P", "open_slot": "S"}.get(row["kind"], "?")
        lines.append(f"### {kind} · `{row['id']}` ({row['status']}) → blocks {blocks}")
        lines.append(f"**Owner:** {row.get('owner', '')}  ")
        lines.append(f"**Ask:** {row.get('ask', '')}")
        opts = row.get("options") or []
        if opts:
            lines.append(f"**Options:** {' | '.join(opts)}")
        lines.append("")
    if not rows:
        lines.append("_No open asks — evidence delivered and policies/slots resolved._")
        lines.append("")
    return "\n".join(lines)


@app.command()
def asks(
    path: Path = typer.Argument(Path("pact.yaml"), help="Path to pact.yaml"),
    output: Path | None = typer.Option(None, "--output", "-o", help="Write Markdown to this path"),
) -> None:
    """Emit client ask list (undelivered evidence + open policies/slots)."""
    try:
        pact = load_pact(path)
    except PactError as exc:
        _fail(str(exc))
    result = validate_pact(pact)
    if result.errors:
        for e in result.errors:
            typer.secho(f"error: {e}", fg=typer.colors.RED, err=True)
        _fail("fix schema before asks", code=1)
    rows = collect_asks(pact)
    md = _format_asks_md(pact, rows)
    if output:
        output.write_text(md, encoding="utf-8")
        typer.secho(f"Wrote {output}", fg=typer.colors.GREEN)
    else:
        typer.echo(md)


def _format_no_claim_md(pact: dict) -> tuple[str, bool]:
    meta = pact.get("meta") or {}
    claims = (pact.get("success") or {}).get("claims") or []
    any_blocked = False
    lines = [
        f"# No-claim report — {meta.get('name', 'pact')}",
        "",
        f"**Client:** {meta.get('client', '')}  ",
        f"**Updated:** {meta.get('updated', '')}",
        "",
    ]
    for claim in claims:
        cid = claim["id"]
        blockers = blockers_for_claim(pact, cid)
        blocked = bool(blockers)
        any_blocked = any_blocked or blocked
        status = "**BLOCKED — cannot claim**" if blocked else "**CLEAR — no open blockers**"
        lines.append(f"## Claim: `{cid}`")
        lines.append("")
        lines.append(claim.get("statement", "").strip())
        lines.append("")
        lines.append(f"### Status: {status}")
        lines.append("")
        if blockers:
            lines.append("| Kind | Id | Status | Owner | Detail |")
            lines.append("| --- | --- | --- | --- | --- |")
            for b in blockers:
                detail = (b.get("detail") or "").replace("|", "\\|").replace("\n", " ")
                lines.append(
                    f"| {b['kind']} | `{b['id']}` | {b['status']} | "
                    f"{b.get('owner', '')} | {detail} |"
                )
            lines.append("")
        else:
            lines.append("No open evidence, policies, or slots block this claim.")
            lines.append("")
    return "\n".join(lines), any_blocked


@app.command("no-claim")
def no_claim(
    path: Path = typer.Argument(Path("pact.yaml"), help="Path to pact.yaml"),
    output: Path | None = typer.Option(None, "--output", "-o", help="Write Markdown to this path"),
    strict: bool = typer.Option(
        False,
        "--strict",
        help="Exit 1 if any success claim has blockers",
    ),
) -> None:
    """Per-claim blocker report."""
    try:
        pact = load_pact(path)
    except PactError as exc:
        _fail(str(exc))
    result = validate_pact(pact)
    if result.errors:
        for e in result.errors:
            typer.secho(f"error: {e}", fg=typer.colors.RED, err=True)
        _fail("fix schema before no-claim", code=1)
    md, any_blocked = _format_no_claim_md(pact)
    if output:
        output.write_text(md, encoding="utf-8")
        typer.secho(f"Wrote {output}", fg=typer.colors.GREEN)
    else:
        typer.echo(md)
    if strict and any_blocked:
        raise typer.Exit(1)


def _render_md(pact: dict) -> str:
    meta = pact.get("meta") or {}
    process = pact.get("process") or {}
    stages = process.get("stages") or []
    lines = [
        f"# {meta.get('name', 'Pact')}",
        "",
        f"**Client:** {meta.get('client', '')}  ",
        f"**Engagement:** {meta.get('engagement', '')}  ",
        f"**Updated:** {meta.get('updated', '')}  ",
        f"**WCA:** {(meta.get('owners') or {}).get('wca', '')}",
        "",
        "## Process",
        "",
        process.get("boundary_note", "").strip(),
        "",
        "```mermaid",
        "flowchart LR",
    ]
    in_scope = [s for s in stages if s.get("in_scope")]
    out_scope = [s for s in stages if not s.get("in_scope")]
    for i, s in enumerate(in_scope):
        lines.append(f'  {s["id"]}["{s["name"]}"]')
        if i > 0:
            prev = in_scope[i - 1]["id"]
            lines.append(f"  {prev} --> {s['id']}")
    if in_scope and out_scope:
        lines.append(f"  {in_scope[-1]['id']} -.-> {out_scope[0]['id']}")
    for s in out_scope:
        lines.append(f'  {s["id"]}["{s["name"]} (out of scope)"]')
    for i in range(1, len(out_scope)):
        lines.append(f"  {out_scope[i - 1]['id']} --> {out_scope[i]['id']}")
    lines.extend(["```", "", "### Stages", ""])
    for s in stages:
        scope = "in scope" if s.get("in_scope") else "out of scope"
        lines.append(f"- **`{s['id']}`** — {s['name']} ({scope}, owner: {s.get('owner', '')})")
        lines.append(f"  - {s.get('does', '')}")
    lines.extend(["", "## Glossary", ""])
    for g in pact.get("glossary") or []:
        lines.append(f"- **{g.get('term')}** — {g.get('plain_english')}")
    lines.extend(["", "## Policies", ""])
    for p in pact.get("policies") or []:
        lines.append(f"- **`{p['id']}`** [{p.get('status')}] — {p.get('question', '')}")
        if p.get("decision"):
            lines.append(f"  - Decision: {p['decision'].strip()}")
    lines.extend(["", "## Success claims", ""])
    for c in (pact.get("success") or {}).get("claims") or []:
        lines.append(f"### `{c['id']}`")
        lines.append("")
        lines.append(c.get("statement", "").strip())
        lines.append("")
        lines.append(f"- **Aggregate:** `{c.get('aggregate')}`")
        lines.append(f"- **Hard gates:** {len(c.get('hard_gates') or [])}")
        lines.append(f"- **Soft fields:** {len(c.get('soft_fields') or [])}")
        nm = c.get("not_measuring") or []
        if nm:
            lines.append("- **Not measuring:** " + "; ".join(nm))
        lines.append("")
    tracks = (pact.get("success") or {}).get("engineering_tracks") or []
    if tracks:
        lines.append("### Engineering tracks")
        lines.append("")
        for t in tracks:
            lines.append(
                f"- **`{t['id']}`** — {t.get('statement', '')} "
                f"(blocks_claim={t.get('blocks_claim')})"
            )
        lines.append("")
    lines.extend(["## Evidence", ""])
    for e in pact.get("evidence") or []:
        req = ", ".join(f"`{r}`" for r in e.get("required_for") or [])
        lines.append(
            f"- **`{e['id']}`** [{e.get('status')}] required_for {req} — {e.get('what', '')}"
        )
    lines.extend(["", "## Open slots", ""])
    for s in pact.get("open_slots") or []:
        blocks = ", ".join(f"`{b}`" for b in s.get("blocks") or []) or "_(none)_"
        lines.append(
            f"- **`{s['id']}`** [{s.get('severity')}/{s.get('status')}] "
            f"blocks {blocks} — {s.get('ask', '')}"
        )
    lines.append("")
    return "\n".join(lines)


@app.command()
def render(
    path: Path = typer.Argument(Path("pact.yaml"), help="Path to pact.yaml"),
    output: Path | None = typer.Option(None, "--output", "-o", help="Write Markdown to this path"),
) -> None:
    """Human-readable Markdown (process Mermaid, glossary, claims)."""
    try:
        pact = load_pact(path)
    except PactError as exc:
        _fail(str(exc))
    result = validate_pact(pact)
    if result.errors:
        for e in result.errors:
            typer.secho(f"error: {e}", fg=typer.colors.RED, err=True)
        _fail("fix schema before render", code=1)
    md = _render_md(pact)
    if output:
        output.write_text(md, encoding="utf-8")
        typer.secho(f"Wrote {output}", fg=typer.colors.GREEN)
    else:
        typer.echo(md)


@app.command("export-eng")
def export_eng(
    path: Path = typer.Argument(Path("pact.yaml"), help="Path to pact.yaml"),
    output: Path = typer.Option(
        Path("export-eng.json"),
        "--output",
        "-o",
        help="Output JSON path",
    ),
) -> None:
    """Export population / gates / out-of-scope stages for harness consumers."""
    try:
        pact = load_pact(path)
    except PactError as exc:
        _fail(str(exc))
    result = validate_pact(pact)
    if result.errors:
        for e in result.errors:
            typer.secho(f"error: {e}", fg=typer.colors.RED, err=True)
        _fail("fix schema before export-eng", code=1)
    payload = export_eng_payload(pact)
    output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    typer.secho(f"Wrote {output}", fg=typer.colors.GREEN)


if __name__ == "__main__":
    app()
