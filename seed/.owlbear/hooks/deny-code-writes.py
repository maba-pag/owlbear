"""deny-code-writes.py — PreToolUse hook for the doc-writer agent.

Extension allowlist guard: permits writes only to files with allowed extensions.
Reads VS Code hook stdin JSON, checks paths for write tools, denies writes to
files whose extension is not in the allowlist.
Usage: invoked automatically by VS Code as a PreToolUse hook.

Allowed extensions (consumer-seed variant):
  .md           — documentation files
  .excalidraw   — diagram files

All other extensions (including .py, no extension, dotfiles, directories) are denied.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path as _Path

_WRITE_TOOLS = {
    "create_file",
    "replace_string_in_file",
    "multi_replace_string_in_file",
    "apply_patch",
    "create_directory",
    "editFiles",
}

_ALLOWED_EXTENSIONS = {".md", ".excalidraw"}


def _extract_paths(tool_input: object) -> list[str]:
    if not isinstance(tool_input, dict):
        return []
    paths: list[str] = []

    fp = tool_input.get("filePath")
    if isinstance(fp, str) and fp:
        paths.append(fp)

    dp = tool_input.get("dirPath")
    if isinstance(dp, str) and dp:
        paths.append(dp)

    for r in tool_input.get("replacements") or []:
        if isinstance(r, dict):
            rfp = r.get("filePath")
            if isinstance(rfp, str) and rfp:
                paths.append(rfp)

    for f in tool_input.get("files") or []:
        if isinstance(f, str) and f:
            paths.append(f)
        elif isinstance(f, dict):
            efp = f.get("filePath")
            if isinstance(efp, str) and efp:
                paths.append(efp)

    return paths


def _normalize(path: str) -> str:
    return path.replace("\\", "/").removeprefix("./")


def _is_denied(normalized: str) -> bool:
    """Return True if the path's extension is not in the allowed set."""
    ext = _Path(normalized).suffix.lower()
    return ext not in _ALLOWED_EXTENSIONS


def main() -> None:
    raw = sys.stdin.buffer.read()
    try:
        payload = json.loads(raw.decode("utf-8", errors="replace"))
    except (json.JSONDecodeError, ValueError):
        print("{}")
        return

    tool_name = payload.get("tool_name", "")
    if not tool_name or tool_name not in _WRITE_TOOLS:
        print("{}")
        return

    paths = _extract_paths(payload.get("tool_input"))
    if not paths:
        print("{}")
        return

    for p in paths:
        normalized = _normalize(p)
        if _is_denied(normalized):
            response = {
                "hookSpecificOutput": {
                    "permissionDecision": "deny",
                    "permissionDecisionReason": (
                        f"doc-writer path guard: write to '{normalized}' is denied. "
                        "Only .md and .excalidraw extensions are allowed "
                        "(consumer-seed variant)."
                    ),
                }
            }
            print(json.dumps(response))
            return

    print("{}")


if __name__ == "__main__":  # pragma: no cover
    main()
