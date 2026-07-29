"""Load and validate pact.yaml documents."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from importlib import resources
from pathlib import Path
from typing import Any

import yaml
from jsonschema import Draft202012Validator


class PactError(Exception):
    """User-facing pact load or validation failure."""


def _schema() -> dict[str, Any]:
    raw = (
        resources.files("flowpact")
        .joinpath("resources/pact.schema.json")
        .read_text(encoding="utf-8")
    )
    return json.loads(raw)


def load_pact(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise PactError(f"pact file not found: {path}")
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise PactError(f"invalid YAML in {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise PactError(f"pact root must be a mapping: {path}")
    return data


@dataclass
class ValidationResult:
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors


def _claim_ids(pact: dict[str, Any]) -> set[str]:
    claims = (pact.get("success") or {}).get("claims") or []
    tracks = (pact.get("success") or {}).get("engineering_tracks") or []
    ids = {c["id"] for c in claims if isinstance(c, dict) and "id" in c}
    ids |= {t["id"] for t in tracks if isinstance(t, dict) and "id" in t}
    return ids


def _unique_ids(items: list[Any], label: str, errors: list[str]) -> None:
    seen: set[str] = set()
    for item in items:
        if not isinstance(item, dict) or "id" not in item:
            continue
        iid = item["id"]
        if iid in seen:
            errors.append(f"duplicate {label} id: {iid}")
        seen.add(iid)


def validate_pact(pact: dict[str, Any]) -> ValidationResult:
    result = ValidationResult()
    validator = Draft202012Validator(_schema())
    for err in sorted(validator.iter_errors(pact), key=lambda e: list(e.path)):
        path = ".".join(str(p) for p in err.path) or "(root)"
        result.errors.append(f"{path}: {err.message}")

    if result.errors:
        return result

    claim_ids = _claim_ids(pact)
    stages = (pact.get("process") or {}).get("stages") or []
    _unique_ids(stages, "stage", result.errors)
    _unique_ids(pact.get("policies") or [], "policy", result.errors)
    _unique_ids((pact.get("success") or {}).get("claims") or [], "claim", result.errors)
    _unique_ids(
        (pact.get("success") or {}).get("engineering_tracks") or [],
        "engineering_track",
        result.errors,
    )
    _unique_ids(pact.get("evidence") or [], "evidence", result.errors)
    _unique_ids(pact.get("open_slots") or [], "open_slot", result.errors)

    for policy in pact.get("policies") or []:
        for bid in policy.get("blocks") or []:
            if bid not in claim_ids:
                result.errors.append(
                    f"policy {policy.get('id')}: blocks unknown claim/track id '{bid}'"
                )
        if policy.get("status") == "resolved" and not policy.get("decision"):
            result.warnings.append(
                f"policy {policy.get('id')}: status is resolved but decision is empty"
            )
        if policy.get("status") in {"open", "blocked_on_client"} and policy.get("blocks"):
            result.warnings.append(
                f"policy {policy.get('id')}: open and blocks {policy.get('blocks')}"
            )

    for ev in pact.get("evidence") or []:
        for rid in ev.get("required_for") or []:
            if rid not in claim_ids:
                result.errors.append(
                    f"evidence {ev.get('id')}: required_for unknown claim/track id '{rid}'"
                )
        if ev.get("status") != "delivered" and ev.get("required_for"):
            result.warnings.append(
                f"evidence {ev.get('id')}: status={ev.get('status')} "
                f"required_for={ev.get('required_for')}"
            )

    for slot in pact.get("open_slots") or []:
        for bid in slot.get("blocks") or []:
            if bid not in claim_ids:
                result.errors.append(
                    f"open_slot {slot.get('id')}: blocks unknown claim/track id '{bid}'"
                )
        if slot.get("status") == "open" and slot.get("blocks"):
            result.warnings.append(
                f"open_slot {slot.get('id')}: open and blocks {slot.get('blocks')}"
            )

    return result


SEVERITY_RANK = {"critical": 0, "high": 1, "medium": 2}


def evidence_severity(ev: dict[str, Any]) -> str:
    """Heuristic severity for evidence rows (not stored on evidence in v0 schema)."""
    # Missing evidence that gates any claim/track: critical; partial: high; else medium.
    if ev.get("status") == "missing":
        return "critical" if ev.get("required_for") else "medium"
    if ev.get("status") == "partial":
        return "high"
    return "medium"


def collect_asks(pact: dict[str, Any]) -> list[dict[str, Any]]:
    """Ask list = undelivered evidence + open policies + open slots."""
    rows: list[dict[str, Any]] = []

    for ev in pact.get("evidence") or []:
        if ev.get("status") == "delivered":
            continue
        rows.append(
            {
                "kind": "evidence",
                "id": ev["id"],
                "severity": evidence_severity(ev),
                "status": ev.get("status"),
                "owner": ev.get("owner", ""),
                "ask": ev.get("ask", ""),
                "blocks": list(ev.get("required_for") or []),
            }
        )

    for policy in pact.get("policies") or []:
        if policy.get("status") not in {"open", "blocked_on_client"}:
            continue
        blocks = list(policy.get("blocks") or [])
        rows.append(
            {
                "kind": "policy",
                "id": policy["id"],
                "severity": "high",
                "status": policy.get("status"),
                "owner": policy.get("owner", ""),
                "ask": policy.get("question", ""),
                "blocks": blocks,
                "options": list(policy.get("options") or []),
            }
        )

    for slot in pact.get("open_slots") or []:
        if slot.get("status") != "open":
            continue
        rows.append(
            {
                "kind": "open_slot",
                "id": slot["id"],
                "severity": slot.get("severity", "medium"),
                "status": slot.get("status"),
                "owner": slot.get("owner", ""),
                "ask": slot.get("ask", ""),
                "blocks": list(slot.get("blocks") or []),
            }
        )

    def sort_key(row: dict[str, Any]) -> tuple:
        sev = SEVERITY_RANK.get(row["severity"], 9)
        # Prefer items that block at least one claim/track.
        has_blocks = 0 if row.get("blocks") else 1
        return (sev, has_blocks, row["kind"], row["id"])

    rows.sort(key=sort_key)
    return rows


def blockers_for_claim(pact: dict[str, Any], claim_id: str) -> list[dict[str, Any]]:
    blockers: list[dict[str, Any]] = []

    for ev in pact.get("evidence") or []:
        if claim_id not in (ev.get("required_for") or []):
            continue
        if ev.get("status") == "delivered":
            continue
        blockers.append(
            {
                "kind": "evidence",
                "id": ev["id"],
                "status": ev.get("status"),
                "owner": ev.get("owner", ""),
                "detail": ev.get("ask", ""),
            }
        )

    for policy in pact.get("policies") or []:
        if claim_id not in (policy.get("blocks") or []):
            continue
        if policy.get("status") not in {"open", "blocked_on_client"}:
            continue
        blockers.append(
            {
                "kind": "policy",
                "id": policy["id"],
                "status": policy.get("status"),
                "owner": policy.get("owner", ""),
                "detail": policy.get("question", ""),
            }
        )

    for slot in pact.get("open_slots") or []:
        if claim_id not in (slot.get("blocks") or []):
            continue
        if slot.get("status") != "open":
            continue
        blockers.append(
            {
                "kind": "open_slot",
                "id": slot["id"],
                "status": slot.get("status"),
                "owner": slot.get("owner", ""),
                "detail": slot.get("ask", ""),
            }
        )

    return blockers


def export_eng_payload(pact: dict[str, Any]) -> dict[str, Any]:
    claims = (pact.get("success") or {}).get("claims") or []
    primary = claims[0] if claims else {}
    stages = (pact.get("process") or {}).get("stages") or []
    resolved = [
        {
            "id": p["id"],
            "decision": p.get("decision"),
            "owner": p.get("owner"),
        }
        for p in (pact.get("policies") or [])
        if p.get("status") == "resolved"
    ]
    return {
        "flowpact": pact.get("flowpact"),
        "meta": {
            "name": (pact.get("meta") or {}).get("name"),
            "client": (pact.get("meta") or {}).get("client"),
            "updated": (pact.get("meta") or {}).get("updated"),
        },
        "claim_id": primary.get("id"),
        "population": primary.get("population"),
        "hard_gates": primary.get("hard_gates"),
        "soft_fields": primary.get("soft_fields"),
        "aggregate": primary.get("aggregate"),
        "not_measuring": primary.get("not_measuring"),
        "out_of_scope_stage_ids": [s["id"] for s in stages if not s.get("in_scope", True)],
        "resolved_policies": resolved,
        "engineering_tracks": (pact.get("success") or {}).get("engineering_tracks") or [],
    }
