"""Approve/reject CLI tool for managing pending memory entries.

Usage:
  python -m owlbear_mcp_memory.approve                  # list pending entries
  python -m owlbear_mcp_memory.approve --interactive    # interactive mode
  python -m owlbear_mcp_memory.approve --approve <ids>  # batch approve
  python -m owlbear_mcp_memory.approve --reject <ids>   # batch reject

Exit codes: 0 on success, 1 if any operation failed.
"""

from __future__ import annotations

import argparse
import json
import os
import sqlite3
import sys
from datetime import UTC, datetime
from pathlib import Path

__all__ = ["main"]

_DEFAULT_DB_PATH = "data/memory/memory.db"

_VALID_TRANSITIONS: frozenset[tuple[str, str]] = frozenset({
    ("pending", "approved"),
    ("pending", "deleted"),
    ("deleted", "pending"),
})


def _now_utc() -> str:
    return datetime.now(UTC).isoformat()


def _resolve_db_path(db_path_arg: str | None) -> Path:
    """Resolve DB path: CLI arg > OWLBEAR_MEMORY_DB_PATH env var > default."""
    if db_path_arg:
        return Path(db_path_arg)
    env = os.environ.get("OWLBEAR_MEMORY_DB_PATH")
    if env:
        return Path(env)
    return Path(_DEFAULT_DB_PATH)


def _open_conn(db_path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(str(db_path), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def _list_pending(conn: sqlite3.Connection) -> list[dict]:
    rows = conn.execute(
        "SELECT id, content, category FROM memory_entries WHERE approval_state = 'pending'"
    ).fetchall()
    return [dict(row) for row in rows]


def _apply_state(conn: sqlite3.Connection, entry_id: str, new_state: str) -> str | None:
    """Transition an entry to new_state.

    Returns None on success, an error-prefixed string for disallowed transitions,
    or raises KeyError if the entry does not exist.
    """
    row = conn.execute(
        "SELECT approval_state FROM memory_entries WHERE id = ?", (entry_id,)
    ).fetchone()
    if row is None:
        msg = f"Entry {entry_id[:8]!r} not found"
        raise KeyError(msg)
    current_state = row["approval_state"]
    if (current_state, new_state) not in _VALID_TRANSITIONS:
        return (
            f"error: transition from '{current_state}' to '{new_state}' is not allowed"
        )
    now = _now_utc()
    deleted_at: str | None = now if new_state == "deleted" else None
    conn.execute(
        """UPDATE memory_entries
           SET approval_state = ?, updated_at = ?, deleted_at = ?
           WHERE id = ?""",
        (new_state, now, deleted_at, entry_id),
    )
    conn.commit()
    return None


def _load_curation_report(db_path: Path) -> dict[str, str] | None:
    """Load curation-report.json from the same directory as the DB.

    Returns a mapping of entry_id -> recommendation string, or None if absent.
    """
    report_path = db_path.parent / "curation-report.json"
    try:
        data = json.loads(report_path.read_text(encoding="utf-8"))
        return {e["id"]: e.get("recommendation", "") for e in data.get("entries", [])}
    except FileNotFoundError:
        return None


def _print_table(entries: list[dict], recommendations: dict[str, str] | None) -> None:
    """Print pending entries as a numbered table to stdout."""
    has_rec = recommendations is not None
    if has_rec:
        header = f"{'#':>3}  {'ID':8}  {'Category':<12}  {'Content Preview':<80}  Recommendation"
        print(header)  # noqa: T201
        print("-" * len(header))  # noqa: T201
    else:
        header = f"{'#':>3}  {'ID':8}  {'Category':<12}  {'Content Preview':<80}"
        print(header)  # noqa: T201
        print("-" * len(header))  # noqa: T201
    for i, entry in enumerate(entries, 1):
        id_short = entry["id"][:8]
        category = entry["category"]
        preview = entry["content"][:80]
        if has_rec:
            rec = recommendations.get(entry["id"], "")
            print(f"{i:3}  {id_short}  {category:<12}  {preview:<80}  {rec}")  # noqa: T201
        else:
            print(f"{i:3}  {id_short}  {category:<12}  {preview:<80}")  # noqa: T201


def _run_interactive(conn: sqlite3.Connection) -> tuple[bool, int, int, int]:
    """Run interactive approve/reject/skip loop.

    Returns (had_error, approved_count, rejected_count, skipped_count).
    """
    entries = _list_pending(conn)
    approved = rejected = skipped = 0
    had_error = False

    for entry in entries:
        print(  # noqa: T201
            f"\n[{entry['id'][:8]}] ({entry['category']}) {entry['content'][:80]}"
        )
        while True:
            choice = input("Approve (a), Reject (r), Skip (s)? ").strip().lower()
            if choice in ("a", "r", "s"):
                break
        if choice == "a":
            try:
                err = _apply_state(conn, entry["id"], "approved")
                if err:
                    print(err, file=sys.stderr)  # noqa: T201
                    had_error = True
                else:
                    approved += 1
            except KeyError as exc:
                print(str(exc), file=sys.stderr)  # noqa: T201
                had_error = True
        elif choice == "r":
            try:
                err = _apply_state(conn, entry["id"], "deleted")
                if err:
                    print(err, file=sys.stderr)  # noqa: T201
                    had_error = True
                else:
                    rejected += 1
            except KeyError as exc:
                print(str(exc), file=sys.stderr)  # noqa: T201
                had_error = True
        else:
            skipped += 1

    return had_error, approved, rejected, skipped


def _run_batch(
    conn: sqlite3.Connection,
    ids: list[str],
    new_state: str,
) -> bool:
    """Apply new_state to each ID. Returns True if any error occurred."""
    had_error = False
    for entry_id in ids:
        try:
            err = _apply_state(conn, entry_id, new_state)
            if err:
                print(err, file=sys.stderr)  # noqa: T201
                had_error = True
        except KeyError as exc:
            print(str(exc), file=sys.stderr)  # noqa: T201
            had_error = True
    return had_error


def main(argv: list[str] | None = None) -> int:
    """Entry point for the approve CLI. Returns exit code."""
    parser = argparse.ArgumentParser(
        description="Manage pending memory entries (approve/reject/list).",
    )
    parser.add_argument("--db-path", dest="db_path", help="Path to memory SQLite DB")
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "--interactive",
        action="store_true",
        help="Interactive approve/reject/skip mode",
    )
    group.add_argument(
        "--approve",
        nargs="+",
        metavar="ID",
        help="Batch approve entry IDs",
    )
    group.add_argument(
        "--reject",
        nargs="+",
        metavar="ID",
        help="Batch reject entry IDs",
    )

    args = parser.parse_args(argv)
    db_path = _resolve_db_path(args.db_path)
    conn = _open_conn(db_path)
    had_error = False

    try:
        if args.interactive:
            had_error, approved, rejected, skipped = _run_interactive(conn)
            print(  # noqa: T201
                f"\nDone: {approved} approved, {rejected} rejected, {skipped} skipped"
            )
        elif args.approve:
            had_error = _run_batch(conn, args.approve, "approved")
        elif args.reject:
            had_error = _run_batch(conn, args.reject, "deleted")
        else:
            # Bare invocation — list pending entries as a numbered table
            entries = _list_pending(conn)
            if entries:
                recommendations = _load_curation_report(db_path)
                if recommendations is None:
                    print(  # noqa: T201
                        "WARNING: curation-report.json not found;"
                        " recommendation column unavailable",
                        file=sys.stderr,
                    )
                _print_table(entries, recommendations)
    finally:
        conn.close()

    return 1 if had_error else 0


if __name__ == "__main__":
    sys.exit(main())
