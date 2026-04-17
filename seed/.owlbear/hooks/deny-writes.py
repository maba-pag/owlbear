"""deny-writes.py — PreToolUse hook for read-only agents.

Reads VS Code hook stdin JSON, denies write tool calls, passes through all others.
Usage: invoked automatically by VS Code as a PreToolUse hook.
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


def main() -> None:
    raw = sys.stdin.buffer.read()
    try:
        payload = json.loads(raw.decode("utf-8", errors="replace"))
    except (json.JSONDecodeError, ValueError):
        print("{}")
        return

    tool_name = payload.get("tool_name", "")

    if tool_name and tool_name in _WRITE_TOOLS:
        response = {
            "hookSpecificOutput": {
                "permissionDecision": "deny",
                "permissionDecisionReason": "This agent is read-only. File writes are not permitted.",
            }
        }
        print(json.dumps(response))
    else:
        print("{}")


if __name__ == "__main__":
    main()
