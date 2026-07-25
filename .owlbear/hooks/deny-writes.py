"""deny-writes.py — PreToolUse hook for read-only agents with scratch access.

Reads VS Code hook stdin JSON, allows writes only under `.owlbear/scratch/`,
and denies all other write targets. Usage: invoked automatically by VS Code as
a PreToolUse hook.
"""

from __future__ import annotations

import json
import re
import shlex
import sys

_WRITE_TOOLS = {
    "create_file",
    "replace_string_in_file",
    "multi_replace_string_in_file",
    "apply_patch",
    "create_directory",
    "editFiles",
}

_SCRATCH_RE = re.compile(r"(^|/)\.owlbear/scratch(/|$)")
_TERMINAL_TOOLS = {"execute/runInTerminal", "runInTerminal", "run_in_terminal"}
_GIT_COMMAND_RE = re.compile(r"\bgit\b(?P<arguments>[^\n;&|]*)")
_READ_ONLY_GIT_COMMANDS = {
    "cat-file",
    "describe",
    "diff",
    "diff-tree",
    "for-each-ref",
    "grep",
    "log",
    "ls-files",
    "ls-tree",
    "merge-base",
    "name-rev",
    "rev-list",
    "rev-parse",
    "show",
    "show-ref",
    "status",
}
_GIT_GLOBAL_FLAGS = {
    "--bare",
    "--literal-pathspecs",
    "--no-pager",
    "--no-replace-objects",
    "--paginate",
    "--version",
}
_GIT_GLOBAL_OPTIONS = {"--exec-path", "--git-dir", "--namespace", "--work-tree", "-C", "-c"}
_GIT_WRITE_OPTIONS = {"--output", "--output-indicator-context", "--output-indicator-new", "--output-indicator-old"}
_SHELL_MUTATION_RE = re.compile(
    r"(?:^|[\s;&|])(?:chmod|chown|chflags|cp|dd|install|ln|mkdir|mv|patch|rm|rmdir|tee|touch|truncate)\b"
    r"|\bsed\s+[^\n;&|]*-[^\s]*i\b"
    r"|\bperl\s+[^\n;&|]*-[^\s]*[pi][^\s]*\b"
    r"|(?<![<>&])>(?![>&])"
    r"|\.(?:chmod|rename|replace|unlink|write_bytes|write_text)\s*\("
    r"|\bopen\s*\([^\n)]*,\s*['\"][wax+]"
)


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


def _normalize(path: str) -> str:
    return path.replace("\\", "/").removeprefix("./")


def _is_scratch_path(normalized: str) -> bool:
    return _SCRATCH_RE.search(normalized) is not None


def _git_command(arguments: str) -> str | None:
    try:
        tokens = shlex.split(arguments)
    except ValueError:
        return None
    index = 0
    while index < len(tokens):
        token = tokens[index]
        if token in _GIT_GLOBAL_FLAGS:
            index += 1
            continue
        if token in _GIT_GLOBAL_OPTIONS:
            index += 2
            continue
        if any(token.startswith(f"{option}=") for option in _GIT_GLOBAL_OPTIONS if option.startswith("--")):
            index += 1
            continue
        return token if not token.startswith("-") else None
    return "--version" if "--version" in tokens else None


def _git_mutation(command: str) -> str | None:
    for match in _GIT_COMMAND_RE.finditer(command):
        try:
            git_tokens = shlex.split(match.group("arguments"))
        except ValueError:
            return "malformed Git command"
        if any(
            token in _GIT_WRITE_OPTIONS or any(token.startswith(f"{option}=") for option in _GIT_WRITE_OPTIONS)
            for token in git_tokens
        ):
            return "Git output option"
        subcommand = _git_command(match.group("arguments"))
        if subcommand not in _READ_ONLY_GIT_COMMANDS and subcommand != "--version":
            return f"non-read-only Git command '{subcommand or match.group(0).strip()}'"
    return None


def _terminal_mutation(command: object) -> str | None:
    if not isinstance(command, str) or not command.strip():
        return "terminal command is missing"
    if mutation := _git_mutation(command):
        return mutation
    if re.search(r"(?:^|[^>])(?:&>|>>?|\d+>>?)(?![>&])", command):
        return "filesystem redirection"
    if match := _SHELL_MUTATION_RE.search(command):
        return f"filesystem mutation '{match.group(0).strip()}'"
    return None


def _deny(reason: str) -> None:
    response = {
        "hookSpecificOutput": {
            "permissionDecision": "deny",
            "permissionDecisionReason": reason,
        }
    }
    print(json.dumps(response))


def main() -> None:
    """Deny hook-request writes that target paths outside the scratch directory."""
    raw = sys.stdin.buffer.read()
    try:
        payload = json.loads(raw.decode("utf-8", errors="replace"))
    except json.JSONDecodeError, ValueError:
        print("{}")
        return

    tool_name = payload.get("tool_name", "")

    if "--terminal-read-only" in sys.argv and tool_name in _TERMINAL_TOOLS:
        tool_input = payload.get("tool_input")
        command = tool_input.get("command") if isinstance(tool_input, dict) else None
        if mutation := _terminal_mutation(command):
            _deny(f"read-only terminal guard: {mutation} is denied")
            return

    if not tool_name or tool_name not in _WRITE_TOOLS:
        print("{}")
        return

    paths = _extract_paths(payload.get("tool_input"))
    if not paths:
        print("{}")
        return

    for path in paths:
        normalized = _normalize(path)
        if not _is_scratch_path(normalized):
            _deny(
                f"read-only path guard: write to '{normalized}' is denied. "
                "Only .owlbear/scratch/ is writable for this agent."
            )
            return

    print("{}")


if __name__ == "__main__":
    main()
