"""Unit and CLI tests for flowpact-score."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from flowpact.cli import app as flowpact_app
from flowpact.score.aggregate import parse_aggregate
from flowpact.score.cli import app as score_app
from flowpact.score.diff import diff_runs
from flowpact.score.gates import case_zeroed, evaluate_hard_gates
from flowpact.score.io import ScoreInputError, get_path
from flowpact.score.methods.exact import exact_match
from flowpact.score.methods.overlap import token_overlap
from flowpact.score.population import filter_population
from flowpact.score.report import write_run_artifacts
from flowpact.score.run import run_score
from flowpact.score.soft import score_soft_fields

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE_DIR = ROOT / "examples" / "draft-vs-gold"
EXAMPLE_PACT = EXAMPLE_DIR / "pact.yaml"
GOLD = EXAMPLE_DIR / "gold.jsonl"
DRAFTS = EXAMPLE_DIR / "drafts.jsonl"

runner = CliRunner()


@pytest.fixture
def export_eng(tmp_path: Path) -> Path:
    out = tmp_path / "export-eng.json"
    result = runner.invoke(flowpact_app, ["export-eng", str(EXAMPLE_PACT), "-o", str(out)])
    assert result.exit_code == 0, result.output
    return out


def test_get_path_nested() -> None:
    obj = {"a": {"b": [{"c": 1}]}}
    assert get_path(obj, "a.b.0.c") == 1
    assert get_path(obj, "a.b[0].c") == 1
    assert get_path(obj, "missing") is None


def test_hard_gate_failure_zeros_case_despite_perfect_soft() -> None:
    gold = {
        "citation_url": "https://example.com/a",
        "answer_body": "same text here",
        "topic_tag": "enrollment",
    }
    draft = {
        "citation_url": "https://example.com/WRONG",
        "answer_body": "same text here",
        "topic_tag": "enrollment",
    }
    gates = evaluate_hard_gates(
        gold,
        draft,
        [{"field": "citation_url", "rule": "matches gold", "on_fail": "zero_score"}],
    )
    assert case_zeroed(gates)
    soft, breakdown = score_soft_fields(
        gold,
        draft,
        [
            {"field": "answer_body", "method": "token_overlap", "weight": 0.7},
            {"field": "topic_tag", "method": "exact_match", "weight": 0.3},
        ],
    )
    assert soft == 1.0
    assert all(b["score"] == 1.0 for b in breakdown)
    case_score = 0.0 if case_zeroed(gates) else soft
    assert case_score == 0.0


def test_population_exclude_records_reasons() -> None:
    paired = {
        "keep": (
            {"locale": "en", "topic": "enrollment"},
            {"locale": "en", "topic": "enrollment"},
        ),
        "drop_locale": (
            {"locale": "es", "topic": "enrollment"},
            {"locale": "es", "topic": "enrollment"},
        ),
        "drop_topic": (
            {"locale": "en", "topic": "payroll"},
            {"locale": "en", "topic": "payroll"},
        ),
    }
    population = {
        "include": [
            {"field": "locale", "rule": "equals en"},
            {"field": "topic", "rule": "in enrollment, coverage, claims"},
        ],
        "exclude": [
            {"field": "locale", "rule": "in es, fr"},
            {"field": "topic", "rule": "in payroll, helpdesk"},
        ],
    }
    scored, audit, warnings = filter_population(paired, population)
    assert warnings == []
    assert set(scored) == {"keep"}
    assert audit.n_scored == 1
    assert "drop_locale" in audit.exclude_reasons
    assert "drop_topic" in audit.exclude_reasons
    assert audit.reason_histogram.get("include_miss:locale") == 1
    assert audit.reason_histogram.get("include_miss:topic") == 1


def test_exact_and_overlap_deterministic() -> None:
    assert exact_match("Hello", "hello") == 1.0
    assert exact_match("a", "b") == 0.0
    assert token_overlap("open enrollment november", "open enrollment november") == 1.0
    a = token_overlap("a b c", "a b d")
    b = token_overlap("a b c", "a b d")
    assert a == b
    assert 0.0 < a < 1.0


def test_aggregate_parse_and_allow_unbounded() -> None:
    spec = parse_aggregate("mean_score >= 0.90")
    assert spec.threshold == 0.90
    with pytest.raises(ScoreInputError):
        parse_aggregate("TBD later")
    unbounded = parse_aggregate("TBD later", allow_unbounded=True)
    assert unbounded.unbounded


def test_example_run_writes_artifacts(export_eng: Path, tmp_path: Path) -> None:
    out = tmp_path / "score_run"
    result = run_score(
        export_eng_path=export_eng,
        gold_path=GOLD,
        drafts_path=DRAFTS,
    )
    write_run_artifacts(result, out)
    for name in (
        "manifest.json",
        "scorecard.json",
        "scorecard.md",
        "failure_cards.md",
        "population_audit.json",
    ):
        assert (out / name).is_file(), name

    audit = json.loads((out / "population_audit.json").read_text(encoding="utf-8"))
    assert audit["n_gold"] == 6
    assert audit["n_drafts"] == 6
    assert audit["n_paired"] == 6
    assert audit["n_scored"] == 4  # q1–q4; q5/q6 excluded
    assert audit["n_excluded"] == 2

    scorecard = json.loads((out / "scorecard.json").read_text(encoding="utf-8"))
    by_id = {c["id"]: c for c in scorecard["cases"]}
    assert by_id["q4"]["hard_gate_failed"] is True
    assert by_id["q4"]["score"] == 0.0
    assert by_id["q1"]["score"] == 1.0


def test_cli_run_exit_codes(export_eng: Path, tmp_path: Path) -> None:
    out = tmp_path / "out"
    # Example includes hard-gate fail → mean < 0.90 → exit 1
    result = runner.invoke(
        score_app,
        [
            "run",
            "--export-eng",
            str(export_eng),
            "--gold",
            str(GOLD),
            "--drafts",
            str(DRAFTS),
            "--out",
            str(out),
        ],
    )
    assert result.exit_code == 1, result.output
    assert (out / "manifest.json").is_file()

    bad = runner.invoke(
        score_app,
        [
            "run",
            "--export-eng",
            str(tmp_path / "missing.json"),
            "--gold",
            str(GOLD),
            "--drafts",
            str(DRAFTS),
            "--out",
            str(out),
        ],
    )
    assert bad.exit_code == 2


def test_require_claim_clear(export_eng: Path, tmp_path: Path) -> None:
    out = tmp_path / "out"
    result = runner.invoke(
        score_app,
        [
            "run",
            "--export-eng",
            str(export_eng),
            "--gold",
            str(GOLD),
            "--drafts",
            str(DRAFTS),
            "--out",
            str(out),
            "--require-claim-clear",
            "--pact",
            str(EXAMPLE_PACT),
        ],
    )
    assert result.exit_code == 2
    assert "blocked" in result.output.lower()


def test_diff_regression_and_population_mismatch(export_eng: Path, tmp_path: Path) -> None:
    out_a = tmp_path / "a"
    out_b = tmp_path / "b"
    result_a = run_score(export_eng_path=export_eng, gold_path=GOLD, drafts_path=DRAFTS)
    write_run_artifacts(result_a, out_a)

    # Candidate with worse drafts (break q1 soft + keep population)
    worse = tmp_path / "drafts_worse.jsonl"
    lines = []
    for line in DRAFTS.read_text(encoding="utf-8").splitlines():
        obj = json.loads(line)
        if obj["id"] == "q1":
            obj["answer_body"] = "totally unrelated gibberish xyz"
            obj["topic_tag"] = "wrong"
        lines.append(json.dumps(obj))
    worse.write_text("\n".join(lines) + "\n", encoding="utf-8")

    result_b = run_score(export_eng_path=export_eng, gold_path=GOLD, drafts_path=worse)
    write_run_artifacts(result_b, out_b)

    diff = diff_runs(out_a / "manifest.json", out_b / "manifest.json")
    assert diff.population_hash_mismatch is False
    assert diff.score_delta < 0
    assert "q1" in diff.newly_failing_ids
    assert diff.regression is True

    # Population hash mismatch: mutate manifest population hash
    cand_manifest = json.loads((out_b / "manifest.json").read_text(encoding="utf-8"))
    cand_manifest["hashes"]["population"] = "deadbeef"
    mismatched = tmp_path / "mismatched" / "manifest.json"
    mismatched.parent.mkdir(parents=True)
    mismatched.write_text(json.dumps(cand_manifest), encoding="utf-8")
    # copy scorecard for case maps
    (mismatched.parent / "scorecard.json").write_text(
        (out_b / "scorecard.json").read_text(encoding="utf-8"), encoding="utf-8"
    )
    diff2 = diff_runs(out_a / "manifest.json", mismatched)
    assert diff2.population_hash_mismatch is True
    assert diff2.regression is True

    cli = runner.invoke(
        score_app,
        [
            "diff",
            "--baseline",
            str(out_a / "manifest.json"),
            "--candidate",
            str(out_b / "manifest.json"),
        ],
    )
    assert cli.exit_code == 1


def test_embedding_method_errors_without_extra() -> None:
    with pytest.raises(ScoreInputError, match="embedding_similarity"):
        score_soft_fields(
            {"body": "a"},
            {"body": "a"},
            [{"field": "body", "method": "embedding_similarity", "weight": 1.0}],
        )


def test_unparseable_population_rule_exits() -> None:
    paired = {
        "x": ({"locale": "en"}, {"locale": "en"}),
    }
    population = {"include": [{"field": "locale", "rule": "non-English until resolved"}]}
    with pytest.raises(ScoreInputError, match="Unparseable"):
        filter_population(paired, population, lenient_rules=False)
