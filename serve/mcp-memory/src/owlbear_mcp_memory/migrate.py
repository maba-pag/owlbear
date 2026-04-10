"""Memory migration CLI tool — bulk import /memories/repo/ files into memory.db."""

from __future__ import annotations

import argparse
import os
import re
import sqlite3
import sys
import uuid
from datetime import UTC, datetime
from pathlib import Path

from owlbear_mcp_memory.models import MemoryEntry

__all__ = ["main"]

_DEFAULT_DB_PATH = "store/memory/memory.db"

_DDL = """
CREATE TABLE IF NOT EXISTS memory_entries (
    id TEXT PRIMARY KEY,
    content TEXT NOT NULL,
    category TEXT NOT NULL,
    confidence REAL NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    source TEXT NOT NULL,
    scope_agent TEXT,
    scope_project TEXT,
    approval_state TEXT NOT NULL DEFAULT 'pending',
    deleted_at TEXT
)
"""

_LABEL_TO_CATEGORY: dict[str, str] = {
    "problems_faced": "knowledge",
    "workarounds_applied": "knowledge",
    "patterns_discovered": "behavior",
    "time_sinks": "context",
    "quality_gaps": "context",
}

_INBOX_HEADING_RE = re.compile(r"^#\s+Lessons:.*?\(([^,)]+),\s*([^)]+)\)")
_DATE_IN_PARENS_RE = re.compile(r"\(([^)]+)\)")


def _resolve_db_path(db_path_arg: str | None) -> Path:
    """Resolve DB path from CLI arg > env var > default."""
    if db_path_arg:
        return Path(db_path_arg)
    env = os.environ.get("OWLBEAR_MEMORY_DB_PATH")
    if env:
        return Path(env)
    return Path(_DEFAULT_DB_PATH)


def _slugify(heading: str) -> str:
    """Convert a ## heading line to a lowercase hyphenated slug."""
    clean = re.sub(r"^#+\s*", "", heading).strip()
    slug = clean.lower().replace(" ", "-")
    return re.sub(r"[^a-z0-9-]", "", slug)


def _parse_inbox_file(filepath: Path, now: str) -> list[dict[str, object]]:
    """Parse an inbox lessons file into a list of entry dicts."""
    try:
        text = filepath.read_text(encoding="utf-8-sig")
    except (OSError, UnicodeDecodeError) as exc:
        print(f"WARNING: Could not read {filepath.name}: {exc}", file=sys.stderr)  # noqa: T201
        return []

    lines = text.splitlines()
    agent_name: str | None = None
    created_at = now

    for line in lines:
        m = _INBOX_HEADING_RE.match(line)
        if m:
            agent_name = m.group(1).strip()
            created_at = m.group(2).strip()
            break

    filename = filepath.name
    entries: list[dict[str, object]] = []

    for line in lines:
        m2 = re.match(r"^-\s+(\w+):\s*(.*)", line)
        if not m2:
            continue
        label = m2.group(1)
        content = m2.group(2).strip()
        if not content:
            continue

        category = _LABEL_TO_CATEGORY.get(label)
        if category is None:
            print(  # noqa: T201
                f"WARNING: Unrecognized label '{label}' in {filename}, mapping to knowledge",
                file=sys.stderr,
            )
            category = "knowledge"

        entries.append(
            {
                "id": str(uuid.uuid4()),
                "content": content,
                "category": category,
                "confidence": 0.7,
                "created_at": created_at,
                "updated_at": now,
                "source": f"migration:inbox/{filename}",
                "scope_agent": agent_name,
                "scope_project": None,
                "approval_state": "pending",
                "deleted_at": None,
            }
        )

    return entries


def _extract_created_at(lines: list[str], filepath: Path) -> str:
    """Extract created_at from the # title line or fall back to file mtime."""
    for line in lines:
        if line.startswith("# "):
            m = _DATE_IN_PARENS_RE.search(line)
            if m:
                return m.group(1).strip()
            break
    mtime = filepath.stat().st_mtime
    return datetime.fromtimestamp(mtime, tz=UTC).isoformat()


def _make_established_entry(
    content: str,
    source: str,
    created_at: str,
    updated_at: str,
) -> dict[str, object]:
    """Build an established-file entry dict."""
    return {
        "id": str(uuid.uuid4()),
        "content": content,
        "category": "knowledge",
        "confidence": 0.7,
        "created_at": created_at,
        "updated_at": updated_at,
        "source": source,
        "scope_agent": None,
        "scope_project": None,
        "approval_state": "approved",
        "deleted_at": None,
    }


def _split_into_sections(
    lines: list[str],
    filename: str,
    created_at: str,
    now: str,
) -> list[dict[str, object]]:
    """Split file lines on ## headings into section entries."""
    entries: list[dict[str, object]] = []
    pre_content_lines: list[str] = []
    current_heading: str | None = None
    current_lines: list[str] = []

    for line in lines:
        if line.startswith("## "):
            if current_heading is not None:
                content = "\n".join(current_lines).strip()
                if content:
                    src = f"migration:{filename}#{_slugify(current_heading)}"
                    entries.append(_make_established_entry(content, src, created_at, now))
            elif pre_content_lines:
                pre = [ln for ln in pre_content_lines if not ln.startswith("# ")]
                content = "\n".join(pre).strip()
                if content:
                    entries.append(
                        _make_established_entry(
                            content,
                            f"migration:{filename}",
                            created_at,
                            now,
                        )
                    )
            current_heading = line
            current_lines = []
        elif current_heading is None:
            pre_content_lines.append(line)
        else:
            current_lines.append(line)

    # Flush the final section
    if current_heading is not None:
        content = "\n".join(current_lines).strip()
        if content:
            src = f"migration:{filename}#{_slugify(current_heading)}"
            entries.append(_make_established_entry(content, src, created_at, now))

    return entries


def _parse_established_file(filepath: Path, now: str) -> list[dict[str, object]]:
    """Parse a top-level established memory file into entry dicts."""
    try:
        text = filepath.read_text(encoding="utf-8-sig")
    except (OSError, UnicodeDecodeError) as exc:
        print(f"WARNING: Could not read {filepath.name}: {exc}", file=sys.stderr)  # noqa: T201
        return []

    filename = filepath.name
    lines = text.splitlines()
    created_at = _extract_created_at(lines, filepath)

    if not any(line.startswith("## ") for line in lines):
        # No sections: single entry excluding the # title line
        content_lines = [line for line in lines if not line.startswith("# ")]
        content = "\n".join(content_lines).strip()
        if not content:
            return []
        return [_make_established_entry(content, f"migration:{filename}", created_at, now)]

    return _split_into_sections(lines, filename, created_at, now)


def _collect_entries(source_dir: Path, now: str) -> list[dict[str, object]]:
    """Collect all entries from inbox and established top-level files."""
    entries: list[dict[str, object]] = []

    inbox_dir = source_dir / "inbox"
    if inbox_dir.is_dir():
        for md_file in sorted(inbox_dir.glob("*.md")):
            entries.extend(_parse_inbox_file(md_file, now))

    for md_file in sorted(source_dir.glob("*.md")):
        entries.extend(_parse_established_file(md_file, now))

    return entries


def _dry_run(entries: list[dict[str, object]]) -> None:
    """Print dry-run output: one line per entry plus summary counts by category."""
    for entry in entries:
        preview = str(entry["content"])[:80]
        print(f"  {entry['source']} | {entry['category']} | {preview}")  # noqa: T201

    categories: dict[str, int] = {}
    for entry in entries:
        cat = str(entry["category"])
        categories[cat] = categories.get(cat, 0) + 1

    print("\nSummary by category:")  # noqa: T201
    for cat, count in sorted(categories.items()):
        print(f"  {cat}: {count}")  # noqa: T201


def _insert_entry(conn: sqlite3.Connection, entry: dict[str, object]) -> None:
    """Validate via MemoryEntry model and insert into memory_entries table."""
    model = MemoryEntry(**entry)
    conn.execute(
        """INSERT INTO memory_entries
           (id, content, category, confidence, created_at, updated_at, source,
            scope_agent, scope_project, approval_state, deleted_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            model.id,
            model.content,
            model.category,
            model.confidence,
            model.created_at,
            model.updated_at,
            model.source,
            model.scope_agent,
            model.scope_project,
            model.approval_state,
            model.deleted_at,
        ),
    )


def main(argv: list[str] | None = None) -> int:
    """Run the memory migration CLI."""
    parser = argparse.ArgumentParser(
        description="Bulk import /memories/repo/ files into memory.db",
    )
    parser.add_argument(
        "--source-dir",
        required=True,
        help="Path to Copilot repo memory directory",
    )
    parser.add_argument("--db-path", default=None, help="SQLite DB path")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print entries without writing to DB",
    )

    args = parser.parse_args(argv)

    source_dir = Path(args.source_dir)
    if not source_dir.is_dir():
        print(  # noqa: T201
            f"ERROR: --source-dir {source_dir!r} is not a directory",
            file=sys.stderr,
        )
        return 1

    now = datetime.now(tz=UTC).isoformat()
    all_entries = _collect_entries(source_dir, now)

    if args.dry_run:
        _dry_run(all_entries)
        return 0

    db_path = _resolve_db_path(args.db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(str(db_path))
    try:
        conn.execute(_DDL)
        # Pre-load existing sources so all entries from the same inbox file are
        # inserted on the first run (same source) but skipped on subsequent runs.
        existing: set[str] = {r[0] for r in conn.execute("SELECT source FROM memory_entries").fetchall()}
        inserted = 0
        skipped = 0
        for entry in all_entries:
            src = str(entry["source"])
            if src in existing:
                skipped += 1
                continue
            try:
                _insert_entry(conn, entry)
                inserted += 1
            except Exception as exc:  # noqa: BLE001
                print(  # noqa: T201
                    f"WARNING: Failed to insert {src!r}: {exc}",
                    file=sys.stderr,
                )
        conn.commit()
    finally:
        conn.close()

    print(f"Migrated {inserted} entries, skipped {skipped} duplicates.")  # noqa: T201
    return 0


if __name__ == "__main__":
    sys.exit(main())
