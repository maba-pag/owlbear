"""Approve/reject CLI tool for managing pending memory entries.

Uses MCP in-memory transport (create_connected_server_and_client_session) to call
list_entries and set_approval_state through the validated MCP tool layer.

Usage:
  python -m owlbear_mcp_memory.approve                  # list pending entries
  python -m owlbear_mcp_memory.approve --interactive    # interactive mode
  python -m owlbear_mcp_memory.approve --approve <ids>  # batch approve
  python -m owlbear_mcp_memory.approve --reject <ids>   # batch reject

Exit codes: 0 on success, 1 if any operation failed.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sqlite3
import sys
from contextlib import asynccontextmanager
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

from mcp.server.fastmcp import FastMCP
from mcp.shared.memory import create_connected_server_and_client_session

from owlbear_mcp_memory.server import AppContext
from owlbear_mcp_memory.tools import list_entries
from owlbear_mcp_memory.tools import set_approval_state as set_approval_state_tool

__all__ = ["main"]

_DEFAULT_DB_PATH = "data/memory/memory.db"
_CONTENT_PREVIEW_LEN = 80


def _resolve_db_path(db_path_arg: str | None) -> Path:
    """Resolve DB path: CLI arg > OWLBEAR_MEMORY_DB_PATH env var > default."""
    if db_path_arg:
        return Path(db_path_arg)
    env = os.environ.get("OWLBEAR_MEMORY_DB_PATH")
    if env:
        return Path(env)
    return Path(_DEFAULT_DB_PATH)


def _build_server(db_path: Path) -> FastMCP:
    """Create a FastMCP server with a custom lifespan for the given DB path."""

    @asynccontextmanager
    async def _lifespan(_server: FastMCP) -> AsyncGenerator[AppContext, None]:
        conn = sqlite3.connect(str(db_path), check_same_thread=False)
        conn.row_factory = sqlite3.Row
        try:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA busy_timeout=5000")
            project_name: str | None = None
            project_json = Path("owlbear-project.json")
            if project_json.is_file():  # noqa: ASYNC240
                data = json.loads(project_json.read_text(encoding="utf-8"))  # noqa: ASYNC240
                project_name = data.get("name")
            yield AppContext(conn=conn, project_name=project_name)
        finally:
            conn.close()

    server = FastMCP("approve-memory", lifespan=_lifespan)
    server.add_tool(list_entries)
    server.add_tool(set_approval_state_tool)
    return server


def _load_curation_report(db_path: Path) -> dict[str, str] | None:
    """Load curation-report.json from the same directory as the DB.

    Supports two formats:
      - Top-level JSON array: [{entry_id: ..., recommendation: ...}, ...]
      - Legacy dict format:   {entries: [{id: ..., recommendation: ...}, ...]}

    Returns a mapping of entry_id -> recommendation string, or None if absent.
    Prints warning to stderr on json.JSONDecodeError.
    """
    report_path = db_path.parent / "curation-report.json"
    try:
        data = json.loads(report_path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None
    except json.JSONDecodeError as exc:
        print(  # noqa: T201
            f"WARNING: curation-report.json is malformed ({exc});"
            " recommendation column unavailable",
            file=sys.stderr,
        )
        return None
    if isinstance(data, list):
        return {e["entry_id"]: e.get("recommendation", "") for e in data}
    return {e["id"]: e.get("recommendation", "") for e in data.get("entries", [])}


def _parse_list_result(content: list) -> list[dict]:
    """Parse FastMCP content items into a list of entry dicts.

    Handles two FastMCP serialization styles:
      - Empty marker: single item with text == "[]"
      - One entry per content item: each item.text is a JSON dict
      - Full list in one item: item.text is a JSON array
    """
    entries: list[dict] = []
    for item in content:
        parsed = json.loads(item.text)
        if isinstance(parsed, list):
            entries.extend(parsed)
        elif isinstance(parsed, dict):
            entries.append(parsed)
        # "[]" string or other non-dict/list values are ignored (empty marker)
    return entries


def _print_table(entries: list[dict], recommendations: dict[str, str] | None) -> None:
    """Print pending entries as a numbered table to stdout."""
    has_rec = recommendations is not None
    col_width = _CONTENT_PREVIEW_LEN + 3  # content + "..."
    if has_rec:
        header = (
            f"{'#':>3}  {'ID':8}  {'Category':<12}"
            f"  {'Content Preview':<{col_width}}  Recommendation"
        )
        print(header)  # noqa: T201
        print("-" * len(header))  # noqa: T201
    else:
        header = f"{'#':>3}  {'ID':8}  {'Category':<12}  {'Content Preview':<{col_width}}"
        print(header)  # noqa: T201
        print("-" * len(header))  # noqa: T201
    for i, entry in enumerate(entries, 1):
        id_short = entry["id"][:8]
        category = entry["category"]
        content = entry["content"]
        if len(content) > _CONTENT_PREVIEW_LEN:
            preview = content[:_CONTENT_PREVIEW_LEN] + "..."
        else:
            preview = content
        if has_rec:
            rec = recommendations.get(entry["id"], "")
            print(f"{i:3}  {id_short}  {category:<12}  {preview:<{col_width}}  {rec}")  # noqa: T201
        else:
            print(f"{i:3}  {id_short}  {category:<12}  {preview:<{col_width}}")  # noqa: T201


async def _async_run_interactive(client: object) -> tuple[bool, int, int, int]:
    """Run interactive approve/reject/skip loop using MCP client.

    Returns (had_error, approved_count, rejected_count, skipped_count).
    Treats blank Enter as skip; handles EOFError gracefully.
    """
    list_result = await client.call_tool("list_entries", {"status": "pending"})  # type: ignore[union-attr]
    entries = _parse_list_result(list_result.content)

    approved = rejected = skipped = 0
    had_error = False

    for entry in entries:
        print(  # noqa: T201
            f"\n[{entry['id'][:8]}] ({entry['category']}) {entry['content'][:80]}"
        )
        while True:
            try:
                choice = input("Approve (a), Reject (r), Skip (s/Enter)? ").strip().lower()  # noqa: ASYNC250
            except EOFError:
                choice = ""
            if choice in ("a", "r", "s", ""):
                break
        if choice == "a":
            result = await client.call_tool(  # type: ignore[union-attr]
                "set_approval_state",
                {"entry_id": entry["id"], "new_state": "approved"},
            )
            text_r = result.content[0].text
            if result.isError or text_r.startswith("error:"):
                print(text_r, file=sys.stderr)  # noqa: T201
                had_error = True
            else:
                approved += 1
                print(f"Approved: {entry['id'][:8]}")  # noqa: T201
        elif choice == "r":
            result = await client.call_tool(  # type: ignore[union-attr]
                "set_approval_state",
                {"entry_id": entry["id"], "new_state": "deleted"},
            )
            text_r = result.content[0].text
            if result.isError or text_r.startswith("error:"):
                print(text_r, file=sys.stderr)  # noqa: T201
                had_error = True
            else:
                rejected += 1
                print(f"Rejected: {entry['id'][:8]}")  # noqa: T201
        else:
            skipped += 1

    return had_error, approved, rejected, skipped


async def _async_run_batch(client: object, ids: list[str], new_state: str) -> bool:
    """Apply new_state to each ID via MCP. Returns True if any error occurred."""
    had_error = False
    action = "Approved" if new_state == "approved" else "Rejected"
    for entry_id in ids:
        result = await client.call_tool(  # type: ignore[union-attr]
            "set_approval_state",
            {"entry_id": entry_id, "new_state": new_state},
        )
        text = result.content[0].text
        if result.isError or text.startswith("error:"):
            print(text, file=sys.stderr)  # noqa: T201
            had_error = True
        else:
            print(f"{action}: {entry_id[:8]}")  # noqa: T201
    return had_error


async def _async_main(argv: list[str] | None = None) -> int:
    """Async implementation of the approve CLI. Returns exit code."""
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
    server = _build_server(db_path)
    had_error = False

    async with create_connected_server_and_client_session(server) as client:
        if args.interactive:
            had_error, approved, rejected, skipped = await _async_run_interactive(client)
            print(  # noqa: T201
                f"\nDone: {approved} approved, {rejected} rejected, {skipped} skipped"
            )
        elif args.approve:
            had_error = await _async_run_batch(client, args.approve, "approved")
        elif args.reject:
            had_error = await _async_run_batch(client, args.reject, "deleted")
        else:
            # Bare invocation — list pending entries as a numbered table
            list_result = await client.call_tool("list_entries", {"status": "pending"})
            entries = _parse_list_result(list_result.content)
            if entries:
                recommendations = _load_curation_report(db_path)
                if recommendations is None:
                    report_path = db_path.parent / "curation-report.json"
                    if not report_path.exists():
                        print(  # noqa: T201
                            "WARNING: curation-report.json not found;"
                            " recommendation column unavailable",
                            file=sys.stderr,
                        )
                _print_table(entries, recommendations)

    return 1 if had_error else 0


def main(argv: list[str] | None = None) -> int:
    """Entry point for the approve CLI. Returns exit code."""
    return asyncio.run(_async_main(argv))


if __name__ == "__main__":
    sys.exit(main())
