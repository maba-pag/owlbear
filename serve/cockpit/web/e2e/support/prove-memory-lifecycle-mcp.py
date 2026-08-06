# ruff: noqa: INP001
"""Capture exceptional-state curation rejections through MCP stdio transport."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.types import CallToolResult, TextContent

EXCEPTIONAL_ENTRIES = {
    "contested": "22222222-2222-4222-8222-222222222222",
    "disputed": "33333333-3333-4333-8333-333333333333",
    "stale": "44444444-4444-4444-8444-444444444444",
}


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--memory-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def _snapshot(memory_dir: Path) -> dict[str, bytes]:
    return {path.name: path.read_bytes() for path in sorted(memory_dir.glob("*.md"))}


def _response_text(result: CallToolResult) -> str:
    return "\n".join(item.text for item in result.content if isinstance(item, TextContent)).strip()


async def _capture(root: Path, memory_dir: Path) -> list[dict[str, object]]:
    before = _snapshot(memory_dir)
    environment = os.environ.copy()
    environment["OWLBEAR_MEMORY_DIR"] = str(memory_dir)
    server = StdioServerParameters(
        command=sys.executable,
        args=["-m", "owlbear_memory_mcp"],
        env=environment,
        cwd=root,
    )
    responses: list[dict[str, object]] = []

    async with (
        stdio_client(server) as (read_stream, write_stream),
        ClientSession(read_stream, write_stream) as session,
    ):
        await session.initialize()
        for state, entry_id in EXCEPTIONAL_ENTRIES.items():
            result = await session.call_tool(
                "curate_memory",
                {"entry_id": entry_id, "title": "Mutation must be rejected"},
            )
            message = _response_text(result)
            if result.isError is not True or state not in message:
                msg = f"curate_memory did not reject {state}: {message}"
                raise RuntimeError(msg)
            responses.append(
                {
                    "entry_id": entry_id,
                    "state": state,
                    "is_error": True,
                    "message": message,
                }
            )

    if _snapshot(memory_dir) != before:
        msg = "MCP rejection probe mutated the exceptional-state fixture"
        raise RuntimeError(msg)
    return responses


def _tested_sha(root: Path) -> str:
    git = shutil.which("git")
    if git is None:
        msg = "git executable is required to record the tested SHA"
        raise RuntimeError(msg)
    return subprocess.run(  # noqa: S603
        [git, "rev-parse", "HEAD"],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _write_receipt(output: Path, tested_sha: str, responses: list[dict[str, object]]) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(
            {
                "tested_sha": tested_sha,
                "transport": "mcp-stdio",
                "operations": ["curate_memory"],
                "responses": responses,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )


def main() -> None:
    """Run the MCP memory lifecycle proof and write its receipt."""
    args = _parse_args()
    root = args.root.resolve()
    responses = asyncio.run(_capture(root, args.memory_dir.resolve()))
    _write_receipt(args.output.resolve(), _tested_sha(root), responses)


if __name__ == "__main__":
    main()
