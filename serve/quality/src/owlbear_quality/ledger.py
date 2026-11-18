"""Atomic, local verdict history, counted per identity and optional caller scope."""

from __future__ import annotations

import fcntl
import json
import uuid
from contextlib import contextmanager
from datetime import UTC, datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterator, Sequence
    from pathlib import Path

FILE = "exceptions.json"


@contextmanager
def _locked(root: Path) -> Iterator[dict[str, list[dict]]]:
    """One writer at a time; a ledger that does not exist yet is empty, and a lost one costs a new judgement."""
    root.mkdir(parents=True, exist_ok=True)
    with (root / ".exceptions.lock").open("a+", encoding="utf-8") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        path = root / FILE
        try:
            rows = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
        except (OSError, ValueError) as exc:
            msg = f"Exception ledger {path} could not be read: {exc}"
            raise RuntimeError(msg) from exc
        yield rows


def _write(path: Path, rows: dict) -> None:
    sibling = path.with_name(f".exceptions-{uuid.uuid4().hex}")
    try:
        with sibling.open("w", encoding="utf-8") as stream:
            stream.write(json.dumps(rows, indent=2, ensure_ascii=False) + "\n")
        sibling.replace(path)
    finally:
        sibling.unlink(missing_ok=True)


def counting(root: Path, identity: str, *, scope: str | None = None) -> list[dict]:
    """Counting verdicts for an identity, optionally only those given for one Change's slug."""
    with _locked(root) as rows:
        return [
            v | {"index": n}
            for n, v in enumerate(rows.get(identity, []))
            if not v["aside"] and (scope is None or v["for"] == scope)
        ]


def counting_scope(root: Path, scope: str) -> list[dict]:
    """Counting verdicts given for one Change, across all identities."""
    with _locked(root) as rows:
        return [v for entries in rows.values() for v in entries if not v["aside"] and v["for"] == scope]


def add(root: Path, verdicts: Sequence[dict]) -> None:
    """Append one verdict per copy; a replacement explicitly names entries to set aside first."""
    with _locked(root) as rows:
        at = datetime.now(UTC).isoformat()
        for entry in verdicts:
            identity = entry["identity"]
            for index in entry.get("replaces", []):
                rows[identity][index]["aside"] = True
            row = {k: v for k, v in entry.items() if k not in {"identity", "replaces"}}
            rows.setdefault(identity, []).append({"at": at, "backlog": "", "aside": False, **row})
        _write(root / FILE, rows)


def set_aside(root: Path, identity: str, indexes: Sequence[int]) -> None:
    """Retain history while removing the named zero-based entries from all counts."""
    with _locked(root) as rows:
        for index in indexes:
            rows[identity][index]["aside"] = True
        _write(root / FILE, rows)


def published(root: Path, members: Sequence[dict], number: int) -> None:
    """Receipt a refused copy's Backlog entry without replacing its verdict or history."""
    with _locked(root) as rows:
        for member in members:
            rows[member["identity"]][member["index"]]["backlog"] = str(number)
        _write(root / FILE, rows)


def current(root: Path) -> dict[str, list[dict]]:
    """One consistent read of every counting verdict, with indexes for history-preserving actions."""
    with _locked(root) as rows:
        return {
            identity: [row | {"index": n} for n, row in enumerate(entries) if not row["aside"]]
            for identity, entries in rows.items()
        }
