"""deny-writes.py — PreToolUse hook for path-bounded agents.

Reads VS Code hook stdin JSON, allows scratch writes and optional durable
research writes, and denies all other write targets. Usage: invoked
automatically by VS Code as a PreToolUse hook.
"""

from __future__ import annotations

import json
import re
import shlex
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


def _normalize(path: str) -> str | None:
    root = Path.cwd().resolve()
    candidate = Path(path.replace("\\", "/"))
    if not candidate.is_absolute():
        candidate = root / candidate
    try:
        return candidate.resolve(strict=False).relative_to(root).as_posix()
    except OSError, RuntimeError, ValueError:
        return None


def _is_scratch_path(normalized: str) -> bool:
    return normalized == ".owlbear/scratch" or normalized.startswith(".owlbear/scratch/")


def _is_allowed_write_path(normalized: str, *, allow_research: bool) -> bool:
    return _is_scratch_path(normalized) or (
        allow_research and (normalized == ".owlbear/research" or normalized.startswith(".owlbear/research/"))
    )


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
    """Deny hook-request writes that target paths outside configured roots."""
    raw = sys.stdin.buffer.read()
    try:
        payload = json.loads(raw.decode("utf-8", errors="replace"))
    except json.JSONDecodeError, ValueError:
        print("{}")
        return
    if not isinstance(payload, dict):
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
        _deny("read-only path guard: write target is missing")
        return

    allow_research = "--allow-research" in sys.argv
    allowed_description = ".owlbear/scratch/ or .owlbear/research/" if allow_research else ".owlbear/scratch/"
    for path in paths:
        normalized = _normalize(path)
        if normalized is None or not _is_allowed_write_path(normalized, allow_research=allow_research):
            display_path = path if normalized is None else normalized
            _deny(
                f"read-only path guard: write to '{display_path}' is denied. "
                f"Only {allowed_description} is writable for this agent."
            )
            return

    print("{}")


if __name__ == "__main__":
    main()
