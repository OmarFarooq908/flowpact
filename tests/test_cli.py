"""Smoke tests for Flowpact CLI against the draft-vs-gold example pact."""

from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from flowpact.cli import app
from flowpact.pact import blockers_for_claim, collect_asks, load_pact, validate_pact

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "examples" / "draft-vs-gold" / "pact.yaml"

runner = CliRunner()


@pytest.fixture
def pact() -> dict:
    return load_pact(EXAMPLE)


def test_example_validates(pact: dict) -> None:
    result = validate_pact(pact)
    assert result.ok, result.errors


def test_asks_include_open_blockers(pact: dict) -> None:
    rows = collect_asks(pact)
    ids = {r["id"] for r in rows}
    assert "labeled_holdout" in ids
    assert "incomplete_policy" in ids
    assert "locale_scope" in ids
    assert "retrieval_labels" in ids
    # resolved items must not appear
    assert "accuracy_method" not in ids
    assert "sample_queue_access" not in ids


def test_answer_quality_blocked(pact: dict) -> None:
    blockers = blockers_for_claim(pact, "answer_quality")
    ids = {b["id"] for b in blockers}
    assert "labeled_holdout" in ids
    assert "retrieval_labels" not in ids  # engineering track only


def test_cli_validate_example() -> None:
    result = runner.invoke(app, ["validate", str(EXAMPLE)])
    assert result.exit_code == 0, result.output


def test_cli_no_claim_strict() -> None:
    result = runner.invoke(app, ["no-claim", str(EXAMPLE), "--strict"])
    assert result.exit_code == 1
    assert "answer_quality" in result.output
    assert "BLOCKED" in result.output


def test_cli_export_eng(tmp_path: Path) -> None:
    out = tmp_path / "export-eng.json"
    result = runner.invoke(app, ["export-eng", str(EXAMPLE), "-o", str(out)])
    assert result.exit_code == 0, result.output
    text = out.read_text(encoding="utf-8")
    assert "hard_gates" in text
    assert "help_center_publish" in text
    assert "citation_url" in text
