"""deny-code-writes.py — PreToolUse hook for the doc-writer agent.

Deny-list path guard: blocks writes to source code and infrastructure directories.
Reads VS Code hook stdin JSON, checks paths for write tools, denies writes to denied dirs.
Usage: invoked automatically by VS Code as a PreToolUse hook.

Denied directories (deny-list):
  serve/            — MCP server source code
  v1/               — v1 legacy source code
  tests/            — test suite
  setup/            — setup scripts
  seed/             — seed data
  store/            — runtime data store
  share/agents/     — agent config (self-modification guard)
  .git/             — git internals (privilege escalation vector)
  .owlbear/hooks/   — hook scripts (self-modification guard)
  .owlbear/scripts/ — automation scripts (self-modification guard)

Denied exact paths:
  conftest.py       — root pytest configuration
"""

from __future__ import annotations

import json
import sys

_WRITE_TOOLS = {
    "create_file",
    "replace_string_in_file",
    "multi_replace_string_in_file",
    "apply_patch",
    "create_directory",
    "editFiles",
}

_DENIED_PREFIXES = [
    "serve/",
    "v1/",
    "tests/",
    "setup/",
    "seed/",
    "store/",
    "share/agents/",
    ".git/",
    ".owlbear/hooks/",
    ".owlbear/scripts/",
]

_DENIED_EXACT = {"conftest.py"}


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
    for prefix in _DENIED_PREFIXES:
        if normalized.startswith(prefix):
            return True
    return normalized in _DENIED_EXACT


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
                        f"doc-writer path guard: write target '{normalized}' "
                        "is in a denied directory. Doc-writer must not write "
                        "to source code directories (deny-list: serve/, v1/, "
                        "tests/, setup/, seed/, store/, share/agents/, .git/, "
                        ".owlbear/hooks/, .owlbear/scripts/, conftest.py)."
                    ),
                }
            }
            print(json.dumps(response))
            return

    print("{}")


if __name__ == "__main__":
    main()
