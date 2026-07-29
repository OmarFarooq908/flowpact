"""JSONL loading, dotted-path access, and stable hashing helpers."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


class ScoreInputError(Exception):
    """Usage or input contract error (maps to exit code 2)."""


def get_path(obj: Any, path: str) -> Any:
    """Resolve a dotted / index path like ``a.b.0.c`` or ``a.b[0].c``.

    Segments are property names or integer indices. Missing paths return ``None``.
    """
    if not path:
        return obj
    cur: Any = obj
    # Normalize a.b[0].c → walk segments
    parts: list[str] = []
    for raw in path.replace("[", ".").replace("]", "").split("."):
        if raw == "":
            continue
        parts.append(raw)
    for part in parts:
        if cur is None:
            return None
        if isinstance(cur, dict):
            cur = cur.get(part)
        elif isinstance(cur, (list, tuple)) and part.isdigit():
            idx = int(part)
            cur = cur[idx] if 0 <= idx < len(cur) else None
        else:
            return None
    return cur


def normalize_value(value: Any) -> Any:
    """Normalize scalars for exact / gate comparison."""
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return float(value)
    if value is None:
        return None
    if isinstance(value, str):
        return value.strip().lower()
    return value


def load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ScoreInputError(f"File not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ScoreInputError(f"Invalid JSON in {path}: {exc}") from exc


def load_jsonl(path: Path, id_field: str) -> dict[str, dict[str, Any]]:
    """Load JSONL into an id → record map. Duplicate ids raise ScoreInputError."""
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise ScoreInputError(f"File not found: {path}") from exc

    records: dict[str, dict[str, Any]] = {}
    for line_no, line in enumerate(text.splitlines(), start=1):
        stripped = line.strip()
        if not stripped:
            continue
        try:
            obj = json.loads(stripped)
        except json.JSONDecodeError as exc:
            raise ScoreInputError(f"Invalid JSONL at {path}:{line_no}: {exc}") from exc
        if not isinstance(obj, dict):
            raise ScoreInputError(f"JSONL record at {path}:{line_no} must be an object")
        key = get_path(obj, id_field)
        if key is None or key == "":
            raise ScoreInputError(f"JSONL record at {path}:{line_no} missing id field {id_field!r}")
        key_str = str(key)
        if key_str in records:
            raise ScoreInputError(f"Duplicate id {key_str!r} in {path}")
        records[key_str] = obj
    return records


def canonical_json(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    try:
        with path.open("rb") as fh:
            for chunk in iter(lambda: fh.read(65536), b""):
                h.update(chunk)
    except FileNotFoundError as exc:
        raise ScoreInputError(f"File not found: {path}") from exc
    return h.hexdigest()


def sha256_keys(keys: list[str]) -> str:
    return sha256_text(canonical_json(sorted(keys)))


def sha256_records(records: dict[str, dict[str, Any]]) -> str:
    ordered = {k: records[k] for k in sorted(records)}
    return sha256_text(canonical_json(ordered))
