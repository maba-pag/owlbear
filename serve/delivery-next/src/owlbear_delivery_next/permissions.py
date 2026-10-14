"""Permission decisions for one step's worker session and their reasons (D4 §3.6, TD-82, TD-86).

Every shell command and file access is allowed, except in every step a hook or signing bypass or a force push,
and in a read-only step any write. The read-only shell rule is ported from the old agents' deny-writes guard.
Commands behind wrapper programs (env, xargs, timeout, find -exec, ...) and scripts given to a nested shell (-c) or
eval are judged the same way, and so is turning hooks or signing off through git config. Not read: a script file a
shell runs, a shell's standard input (pipes, here-strings), env -S, and commands built at run time.
"""

from __future__ import annotations

import re
import shlex
from dataclasses import dataclass
from pathlib import PurePath
from typing import TYPE_CHECKING, Any, NamedTuple

from owlbear_delivery_next import shell_parse, tools

if TYPE_CHECKING:
    from collections.abc import Sequence
    from pathlib import Path

_HARMLESS = re.compile(r"\d*>>?\s*/dev/null(?![^\s;&|)])|\d*>&\d+")  # discarded output or a descriptor copy
_CONFIG_VALUES = frozenset({"-f", "--file", "--blob", "--type", "--default", "--comment"})
_CONFIG_QUERIES = frozenset(
    {"--get", "--get-all", "--get-regexp", "--get-urlmatch", "--get-color", "--get-colorbool", "--list", "-l",
     "get", "list"}
)  # fmt: skip
_CONFIG_READS = _CONFIG_QUERIES | {  # git config operations that set no value
    "--unset", "--unset-all", "--remove-section", "--rename-section", "--edit", "-e", "unset", "remove-section",
    "rename-section", "edit",
}  # fmt: skip
_CONFIG_KEY = re.compile(r"GIT_CONFIG_KEY_(\d+)")
_READ_ONLY_GIT = frozenset(
    {
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
)
_GIT_GLOBAL_FLAGS = frozenset(
    {
        "--bare",
        "--exec-path",
        "--glob-pathspecs",
        "--help",
        "--html-path",
        "--icase-pathspecs",
        "--info-path",
        "--literal-pathspecs",
        "--man-path",
        "--no-advice",
        "--no-lazy-fetch",
        "--no-optional-locks",
        "--no-pager",
        "--no-replace-objects",
        "--noglob-pathspecs",
        "--paginate",
        "--version",
        "-P",
        "-h",
        "-p",
        "-v",
    }
)
_GIT_GLOBAL_OPTIONS = frozenset(
    {"-C", "-c", "--attr-source", "--config-env", "--git-dir", "--namespace", "--work-tree"}
)
_GIT_GLOBAL_ATTACHED = _GIT_GLOBAL_OPTIONS | {"--exec-path", "--list-cmds", "--super-prefix"}  # as --option=value
_GIT_VALUES = {  # short options taking the next word or only an attached value, and long ones taking a value
    "commit": (
        "mFCct",
        "Su",
        frozenset(
            {
                "--author",
                "--cleanup",
                "--date",
                "--file",
                "--fixup",
                "--message",
                "--pathspec-from-file",
                "--reedit-message",
                "--reuse-message",
                "--squash",
                "--template",
                "--trailer",
            }
        ),
    ),
    "push": ("o", "", frozenset({"--exec", "--push-option", "--receive-pack", "--recurse-submodules", "--repo"})),
}
_NO_VALUES: tuple[str, str, frozenset[str]] = ("", "", frozenset())
_GIT_FALSE = frozenset({"", "0", "false", "no", "off"})
_GIT_WRITE_OPTIONS = frozenset(
    {
        "--output",
        "--output-indicator-context",
        "--output-indicator-new",
        "--output-indicator-old",
    }
)
_REDIRECT = re.compile(r"(?:^|[^>])(?:&>|>>?|\d+>>?)(?![>&])")
_SHELL_MUTATION = re.compile(
    r"(?:^|[\s;&|])(?:chmod|chown|chflags|cp|dd|install|ln|mkdir|mv|patch|rm|rmdir|tee|touch|truncate)\b"
    r"|\bsed\s+[^\n;&|]*-[^\s]*i\b"
    r"|\bperl\s+[^\n;&|]*-[^\s]*[pi][^\s]*\b"
    r"|(?<![<>&])>(?![>&])"
    r"|\.(?:chmod|rename|replace|unlink|write_bytes|write_text)\s*\("
    r"|\bopen\s*\([^\n)]*,\s*['\"][wax+]"
)


@dataclass(frozen=True)
class Policy:
    """One step's permission policy: its worktree, and whether the step may write (D4 §3.6)."""

    root: Path
    write: bool = True


@dataclass(frozen=True)
class Request:
    """The parts of a permission request the policy judges."""

    kind: str
    commands: tuple[str, ...] = ()
    paths: tuple[str, ...] = ()
    tool: str = ""
    server: str = ""  # an MCP request's server


def identities(req: Request) -> set[str]:
    """The tools a request names, lower case: each shell command's program, else its tool or kind (TD-36)."""
    programs = {
        words[0].rsplit("/", 1)[-1].lower()
        for text in req.commands
        for part in re.split(r"[;&|\n]+", text)
        if (words := part.split()) and words[0] != "cd"
    }
    return programs or {(req.tool or req.kind).lower()}


class _GitCall(NamedTuple):
    config: tuple[str, ...]  # the -c settings, and the keys --config-env sets
    sub: str | None
    arguments: tuple[str, ...]  # the subcommand's, or the unparsed rest without one


def _parse_git(words: Sequence[str]) -> _GitCall:
    """Parse the words after git: its global options, then the subcommand and its arguments."""
    config: list[str] = []
    i = 0
    while i < len(words):
        w = words[i]
        if w in _GIT_GLOBAL_OPTIONS:
            value = words[i + 1 : i + 2]
            config += value if w == "-c" else [v.partition("=")[0] + "=" for v in value] if w == "--config-env" else []
            i += 2
        elif w.startswith("--config-env="):
            config.append(w.removeprefix("--config-env=").partition("=")[0] + "=")  # its value is unknown here
            i += 1
        elif w in _GIT_GLOBAL_FLAGS or ("=" in w and w.partition("=")[0] in _GIT_GLOBAL_ATTACHED):
            i += 1
        else:
            break
    rest = tuple(words[i:])
    if rest and not rest[0].startswith("-"):
        return _GitCall(tuple(config), rest[0], rest[1:])
    return _GitCall(tuple(config), None, rest)


def _disables(setting: str) -> bool:
    """Whether a git setting replaces the hooks or turns commit or tag signing off; a bare key's value is unknown."""
    key, eq, value = setting.partition("=")
    key = key.lower()
    return key == "core.hookspath" or (
        key in {"commit.gpgsign", "tag.gpgsign"} and bool(eq) and value.lower() in _GIT_FALSE
    )


def _config_write(arguments: Sequence[str]) -> str | None:
    """The setting a git config command writes when it replaces the hooks or turns signing off."""
    if any(a in _CONFIG_READS for a in arguments):
        return None
    plain: list[str] = []
    i = 0
    while i < len(arguments):
        w = arguments[i]
        i += 2 if w in _CONFIG_VALUES else 1
        if not w.startswith("-") and w not in _CONFIG_VALUES:
            plain.append(w)
    if plain[:1] == ["set"]:
        plain = plain[1:]
    if len(plain) >= 2 and _disables(f"{plain[0]}={plain[1]}"):  # noqa: PLR2004 - a key and its value
        return f"{plain[0]} {plain[1]}"
    return None


def _short(cluster: str, required: str, optional: str) -> tuple[str, bool]:
    """The flags of a short-option cluster before an option taking a value, and whether that value is the next word."""
    for j, ch in enumerate(cluster):
        if ch in required or ch in optional:
            return cluster[:j], ch in required and j == len(cluster) - 1
    return cluster, False


def _sub_bypass(sub: str | None, arguments: Sequence[str]) -> str | None:
    """Return the option or refspec of a git subcommand that skips hooks or signing or forces a push."""
    required, optional, long_values = _GIT_VALUES.get(sub or "", _NO_VALUES)
    forbidden = {"commit": "n", "push": "f"}.get(sub or "", "")
    i = 0
    while i < len(arguments) and (w := arguments[i]) != "--":
        name, eq, _ = w.partition("=")
        flags, takes = _short(w[1:], required, optional) if re.fullmatch(r"-[^-].*", w) else ("", False)
        if w in {"--no-verify", "--no-gpg-sign"} or set(flags) & set(forbidden):
            return w
        if sub == "push" and w.startswith(("--force", "+")):
            return w
        i += 2 if takes or (name in long_values and not eq) else 1
    if sub == "push":  # after --, a refspec still forces with a leading +
        return next((w for w in arguments[i + 1 :] if w.startswith("+")), None)
    return None


def _environment(words: Sequence[str]) -> dict[str, str]:
    """The variables one command sets for what it runs: leading assignments, env's, and export's."""
    i = next((i for i, w in enumerate(words) if not shell_parse.ASSIGNMENT.match(w)), len(words))
    found = list(words[:i])
    if i < len(words) and PurePath(words[i]).name == "env":
        found += [w for w in words[i + 1 : shell_parse.operand(words, i)] if shell_parse.ASSIGNMENT.match(w)]
    elif i < len(words) and words[i] == "export":
        found += [w for w in words[i + 1 :] if shell_parse.ASSIGNMENT.match(w)]
    return dict(w.partition("=")[::2] for w in found)


def _env_setting(words: Sequence[str]) -> str | None:
    """A setting that git configuration passed by environment uses to replace the hooks or turn signing off."""
    env = _environment(words)
    try:
        settings = shlex.split(env.get("GIT_CONFIG_PARAMETERS", ""))
    except ValueError:
        settings = [env["GIT_CONFIG_PARAMETERS"]]
    for name, key in env.items():
        if m := _CONFIG_KEY.fullmatch(name):
            value = env.get(f"GIT_CONFIG_VALUE_{m[1]}")
            settings.append(key if value is None else f"{key}={value}")
    return next((s for s in settings if _disables(s)), None)


def _bypass(words: Sequence[str]) -> str | None:
    """Return the setting, option or refspec of a git command that skips hooks or signing, or forces a push."""
    if setting := _env_setting(words):
        return f"environment setting {setting}"
    for prog in shell_parse.programs(words):
        if PurePath(prog[0]).name != "git":
            continue
        call = _parse_git(prog[1:])
        if setting := next((s for s in call.config if _disables(s)), None):
            return f"-c {setting}"
        if call.sub == "config" and (setting := _config_write(call.arguments)):
            return f"config {setting}"
        if found := _sub_bypass(call.sub, call.arguments):
            return found
    return None


def _is_read_only_branch(arguments: Sequence[str]) -> bool:
    if list(arguments) in ([], ["--show-current"]):
        return True
    return arguments[0] == "--list" and not any(a.startswith("-") for a in arguments[1:])  # else it creates one


def _git_mutation(words: Sequence[str]) -> str | None:
    """How a git command one command's words run would write."""
    for prog in (p for p in shell_parse.programs(words) if PurePath(p[0]).name == "git"):
        call = _parse_git(prog[1:])
        if option := next((a for a in call.arguments if a.partition("=")[0] in _GIT_WRITE_OPTIONS), None):
            return f"Git output option {option}"
        if call.sub == "branch" and _is_read_only_branch(call.arguments):
            continue
        if call.sub == "config" and any(a in _CONFIG_QUERIES for a in call.arguments):
            continue
        if call.sub not in _READ_ONLY_GIT and (call.sub or call.arguments):
            return f"Git command '{call.sub or ' '.join(prog)}'"
    return None


def _mutation(text: str, commands: Sequence[Sequence[str]]) -> str | None:
    """How a shell command would write files or change Git state; discarded output does not count."""
    if found := next(filter(None, map(_git_mutation, commands)), None):
        return found
    text = _HARMLESS.sub("", text)
    if _REDIRECT.search(text):
        return "a redirect"
    if match := _SHELL_MUTATION.search(text):
        return f"filesystem mutation '{match[0].strip(' \t;&|')}'"
    return None


def _shell(policy: Policy, req: Request) -> str | None:
    for text in req.commands or ("",):
        if reason := _check(policy, text):
            return reason
    return None


def _check(policy: Policy, text: str, depth: int = 0) -> str | None:
    """Judge one shell text, and each script it hands to a nested shell or eval the same way."""
    try:
        commands = shell_parse.commands(text)
    except ValueError:
        return f"`{text}` cannot be parsed"
    if not commands:
        return "the shell request names no command" if depth == 0 else None  # an empty script does nothing
    if flag := next(filter(None, map(_bypass, commands)), None):
        return f"`{text}` uses {flag}, which skips hooks or signing or forces history"
    if not policy.write and (found := _mutation(text, commands)):
        return f"`{text}` uses {found}, which writes in a read-only step"
    return _nested(policy, text, commands, depth)


def _nested(policy: Policy, text: str, commands: Sequence[Sequence[str]], depth: int) -> str | None:
    for script in (s for words in commands for s in shell_parse.scripts(words)):
        if depth >= shell_parse.NESTING:
            return f"`{text}` nests scripts more than {shell_parse.NESTING} deep"
        if reason := _check(policy, script, depth + 1):
            return reason
    return None


def decide(policy: Policy, req: Request, offered: frozenset[str] = frozenset()) -> str | None:
    """Return None to allow, or the denial reason the agent and the activity log see.

    *offered* are the MCP tools the role's agent file names as server/tool, such as saving a memory (TD-70); the
    runtime names a request's tool server-tool.
    """
    if req.kind == "mcp" and f"{req.server}/{req.tool.removeprefix(f'{req.server}-')}" in offered:
        return None
    if req.kind == "custom-tool":
        return (
            None
            if req.tool in {*(s.name for s in tools.SPECS), tools.FIRST_LOOK, tools.SCAN_DESIGN}
            else f"tool {req.tool} is not allowed"
        )
    if req.kind in {"read", "write"}:
        return "writes are not allowed in this step" if req.kind == "write" and not policy.write else None
    if req.kind == "url":
        return None
    return _shell(policy, req) if req.kind == "shell" else f"{req.kind} requests are not allowed in this step"


def view(r: Any) -> Request:  # noqa: ANN401 - one of the SDK's permission request classes
    """Normalise one SDK permission request into a Request."""
    kind = getattr(r, "kind", type(r).__name__)
    if kind == "shell":
        texts = [s.full_command_text for s in r.command_segments or ()] or [c.identifier for c in r.commands]
        return Request(kind, tuple(texts or [r.full_command_text]), tuple(r.possible_paths or ()))
    if kind in {"read", "write"}:
        path = r.resolved_path or getattr(r, "path", None) or getattr(r, "file_name", "")
        return Request(kind, paths=(path,) if path else ())
    return Request(kind, tool=getattr(r, "tool_name", ""), server=getattr(r, "server_name", ""))
