"""deny-src-writes.py — PreToolUse hook for test-only roles.

Allow-list path guard: only writes to test directories, colocated test files,
or `.owlbear/scratch/` are permitted. Reads VS Code hook stdin JSON, checks
paths for write tools, denies writes outside those surfaces. Usage: invoked
automatically by VS Code as a PreToolUse hook.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

_WRITE_TOOLS = {
    "create_file",
    "replace_string_in_file",
    "multi_replace_string_in_file",
    "apply_patch",
    "create_directory",
    "editFiles",
    "edit/createDirectory",
    "edit/createFile",
    "edit/editFiles",
    "edit/rename",
    "rename",
}

_PATH_FIELDS = (
    "filePath",
    "dirPath",
    "oldPath",
    "newPath",
    "oldFilePath",
    "newFilePath",
    "sourcePath",
    "targetPath",
)


def _extract_paths(tool_input: object) -> list[str]:
    if not isinstance(tool_input, dict):
        return []
    paths: list[str] = []

    for field_name in _PATH_FIELDS:
        value = tool_input.get(field_name)
        if isinstance(value, str) and value:
            paths.append(value)

    patch_input = tool_input.get("input")
    if isinstance(patch_input, str):
        for line in patch_input.splitlines():
            if line.startswith(("*** Update File: ", "*** Add File: ", "*** Delete File: ")):
                path = line.split(": ", 1)[1].strip()
                if path:
                    paths.append(path)

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


def _is_allowed_path(path: str) -> bool:
    path_parts = Path(path).parts
    filename = Path(path).name
    return bool(
        "tests" in path_parts
        or "__tests__" in path_parts
        or "e2e" in path_parts
        or re.fullmatch(r"[^/]+\.(?:test|spec)\.[cm]?[jt]sx?", filename)
        or path == ".owlbear/scratch"
        or path.startswith(".owlbear/scratch/")
    )


def _normalize(path: str) -> str | None:
    root = Path.cwd().resolve()
    candidate = Path(path.replace("\\", "/"))
    if not candidate.is_absolute():
        candidate = root / candidate
    try:
        return candidate.resolve(strict=False).relative_to(root).as_posix()
    except (OSError, RuntimeError, ValueError):
        return None


def main() -> None:
    """Deny hook-request writes outside test and scratch directories."""
    raw = sys.stdin.buffer.read()
    try:
        payload = json.loads(raw.decode("utf-8", errors="replace"))
    except (json.JSONDecodeError, ValueError):
        print("{}")
        return
    if not isinstance(payload, dict):
        print("{}")
        return

    tool_name = payload.get("tool_name", "")
    if not tool_name or tool_name not in _WRITE_TOOLS:
        print("{}")
        return

    paths = _extract_paths(payload.get("tool_input"))
    if not paths:
        response = {
            "hookSpecificOutput": {
                "permissionDecision": "deny",
                "permissionDecisionReason": "test-writer path guard: write target is missing",
            }
        }
        print(json.dumps(response))
        return

    for p in paths:
        normalized = _normalize(p)
        if normalized is None or not _is_allowed_path(normalized):
            display_path = p if normalized is None else normalized
            response = {
                "hookSpecificOutput": {
                    "permissionDecision": "deny",
                    "permissionDecisionReason": (
                        f"test-writer path guard: write target "
                        f"'{display_path}' is outside the allowed "
                        "test surfaces. Only writes to tests/, __tests__/, e2e/, "
                        "colocated *.test.* or *.spec.* files, or "
                        ".owlbear/scratch/ are permitted."
                    ),
                }
            }
            print(json.dumps(response))
            return

    print("{}")


if __name__ == "__main__":
    main()
