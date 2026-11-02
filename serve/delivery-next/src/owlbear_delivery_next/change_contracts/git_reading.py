"""What one git command does that the shell guard judges: its global options, subcommand and settings.

The guard reads git's words as git parses them: global options, then the subcommand and its options with their
values. A bypass is an option, refspec or setting that skips hooks or signing or forces a push, given on the command
line, through git config, or through git configuration passed by environment. A write is any subcommand outside the
read-only list, or an output option.
"""

from __future__ import annotations

import re
import shlex
from typing import TYPE_CHECKING, NamedTuple

from owlbear_delivery_next.local_system import shell_programs

if TYPE_CHECKING:
    from collections.abc import Sequence

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
        "check-ignore",
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
    i = shell_programs.builtin(words)  # then export ..., command export ...
    if i < len(words) and shell_programs.name(words[i]) == "env":
        i = shell_programs.operand(words, i)
    elif i < len(words) and words[i] == "export":
        i = len(words)
    return shell_programs.assignments(words[:i])


def env_setting(env: dict[str, str]) -> str | None:
    """A setting that git configuration passed by environment uses to replace the hooks or turn signing off."""
    try:
        settings = shlex.split(env.get("GIT_CONFIG_PARAMETERS", ""))
    except ValueError:
        settings = [env["GIT_CONFIG_PARAMETERS"]]
    for name, key in env.items():
        if m := _CONFIG_KEY.fullmatch(name):
            value = env.get(f"GIT_CONFIG_VALUE_{m[1]}")
            settings.append(key if value is None else f"{key}={value}")
    return next((s for s in settings if _disables(s)), None)


def bypass(words: Sequence[str]) -> str | None:
    """Return the setting, option or refspec of a git command that skips hooks or signing, or forces a push."""
    if setting := env_setting(_environment(words)):  # leading assignments, env's and export's
        return f"environment setting {setting}"
    for run in shell_programs.runs(words):
        if setting := env_setting(run.env):  # those an env -S split sets too
            return f"environment setting {setting}"
        if shell_programs.name(run.words[0]) != "git":
            continue
        call = _parse_git(run.words[1:])
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


def mutation(words: Sequence[str]) -> str | None:
    """How a git command one command's words run would write."""
    for prog in (r.words for r in shell_programs.runs(words) if shell_programs.name(r.words[0]) == "git"):
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
