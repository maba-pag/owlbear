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
from owlbear_delivery_next.local_system.shell_words import Word

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
    "merge": ("mFsX", "S", frozenset({"--cleanup", "--file", "--into-name", "--message", "--strategy",
                                      "--strategy-option"})),
    "rebase": ("sXCx", "S", frozenset({"--empty", "--exec", "--onto", "--strategy", "--strategy-option",
                                       "--whitespace"})),
    "am": ("Cp", "S", frozenset({"--directory", "--empty", "--exclude", "--include", "--patch-format",
                                 "--quoted-cr", "--whitespace"})),
    "cherry-pick": ("mX", "S", frozenset({"--cleanup", "--empty", "--mainline", "--strategy", "--strategy-option"})),
}  # fmt: skip
_NO_VALUES: tuple[str, str, frozenset[str]] = ("", "", frozenset())
_GIT_FALSE = frozenset({"", "0", "false", "no", "off"})
_MIRROR_KEY = re.compile(r"remote\..+\.mirror", re.IGNORECASE)  # the remote's name keeps its case
_ALIAS = re.compile(r"alias\.(.+)", re.IGNORECASE)
SWITCHES = frozenset({"HUSKY", "LEFTHOOK", "SKIP", "LEFTHOOK_EXCLUDE"})  # hook tools' variables that skip hooks
_SWITCHES_OFF = {"HUSKY": {"0"}, "LEFTHOOK": {"0", "false"}}  # the values that turn the tool off; SKIP and
# LEFTHOOK_EXCLUDE with any value name hooks to skip: pre-commit's and lefthook's
_HOOKED = frozenset({"am", "cherry-pick", "commit", "merge", "push", "rebase"})  # git commands that run hooks
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
    from_env: tuple[tuple[str, str], ...]  # --config-env's keys and the variables holding their values


def _parse_git(words: Sequence[str]) -> _GitCall:
    """Parse the words after git: its global options, then the subcommand and its arguments."""
    config: list[str] = []
    from_env: list[tuple[str, str]] = []
    i = 0
    while i < len(words):
        w = words[i]
        joined = w.startswith("--config-env=")
        if w in _GIT_GLOBAL_OPTIONS or joined:
            flag = getattr(w, "expanded", False)
            value = [Word(w.removeprefix("--config-env="), expanded=flag)] if joined else words[i + 1 : i + 2]
            config += value if w == "-c" else []
            for key, var in (_halves(v) for v in value if joined or w == "--config-env"):
                config.append(Word(f"{key}=", expanded=key.expanded))  # its value is the variable's, unknown here
                from_env.append((key, var))
            i += 1 if joined else 2
        elif w in _GIT_GLOBAL_FLAGS or ("=" in w and w.partition("=")[0] in _GIT_GLOBAL_ATTACHED):
            i += 1
        else:
            break
    rest = tuple(words[i:])
    if rest and not rest[0].startswith("-"):
        return _GitCall(tuple(config), rest[0], rest[1:], tuple(from_env))
    return _GitCall(tuple(config), None, rest, tuple(from_env))


def _disables(setting: str) -> bool:
    """Whether a git setting replaces the hooks or turns commit or tag signing off; a bare key's value is unknown."""
    key, eq, value = setting.partition("=")
    key = key.lower()
    return key == "core.hookspath" or (
        key in {"commit.gpgsign", "tag.gpgsign"} and bool(eq) and value.lower() in _GIT_FALSE
    )


def _mirrors(setting: str) -> bool:
    """Whether a git setting makes every push to a remote a mirror push: remote.<name>.mirror, true or a bare key."""
    key, eq, value = setting.partition("=")
    if not _MIRROR_KEY.fullmatch(key):
        return False
    return not eq or value.lower() in {"true", "yes", "on"} or bool(re.fullmatch(r"[-+]?\d+", value) and int(value))


def _config_set(arguments: Sequence[str]) -> tuple[str, str] | None:
    """The key and value a git config command writes, if it writes one."""
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
    return (plain[0], plain[1]) if len(plain) >= 2 else None  # noqa: PLR2004 - a key and its value


def _config_write(arguments: Sequence[str]) -> str | None:
    """The setting a git config command writes when it replaces the hooks, turns signing off or mirrors pushes."""
    written = _config_set(arguments)
    setting = "=".join(written or ())
    return " ".join(written) if written and (_disables(setting) or _mirrors(setting)) else None


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
        if sub == "push" and (w.startswith(("--force", "+")) or w == "--mirror"):
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


def _env_settings(env: dict[str, str]) -> list[str]:
    """The settings git configuration passed by environment gives: GIT_CONFIG_PARAMETERS and GIT_CONFIG_KEY_n."""
    try:
        settings = shlex.split(env.get("GIT_CONFIG_PARAMETERS", ""))
    except ValueError:
        settings = [env["GIT_CONFIG_PARAMETERS"]]
    for name, key in env.items():
        if m := _CONFIG_KEY.fullmatch(name):
            value = env.get(f"GIT_CONFIG_VALUE_{m[1]}")
            settings.append(key if value is None else f"{key}={value}")
    return settings


def env_setting(env: dict[str, str], words: Sequence[str]) -> str | None:
    """A setting that git configuration passed by environment to the command *words* uses to skip hooks or signing.

    A mirror setting counts when the command may push (see _may_push), or exports it so that it outlives the command.
    """
    i = shell_programs.builtin(words)
    lasting = (i < len(words) and words[i] == "export") or any(_may_push(r.words) for r in shell_programs.runs(words))
    return next((s for s in _env_settings(env) if _disables(s) or (lasting and _mirrors(s))), None)


def bypass(words: Sequence[str]) -> str | None:
    """Return the setting, option or refspec of a git command that skips hooks or signing, or forces a push."""
    if setting := env_setting(_environment(words), words):  # leading assignments, env's and export's
        return f"environment setting {setting}"
    for run in shell_programs.runs(words):
        if setting := env_setting(run.env, run.words):  # those an env -S split sets too
            return f"environment setting {setting}"
        env = {**_environment(words), **run.env}  # what --config-env reads; another variable's value is unknown
        if shell_programs.name(run.words[0]) != "git":
            continue
        if found := _git_bypass(_parse_git(run.words[1:]), env, push=_may_push(run.words)):
            return found
    return None


def _may_push(words: Sequence[str]) -> bool:
    """Whether a run may push: git push, git text that runs other commands, or another program, which may run git."""
    if shell_programs.name(words[0]) != "git":
        return True
    return _parse_git(words[1:]).sub == "push" or bool(scripts(words) or aliases(words))


def _git_bypass(call: _GitCall, env: dict[str, str], *, push: bool) -> str | None:
    """One git call's setting, option or refspec that skips hooks or signing or forces a push; *env* its variables.

    *push*: the call may push, so a mirror setting counts.
    """
    if setting := next((s for s in call.config if _disables(s) or (push and _mirrors(s))), None):
        return f"-c {setting}"
    if push and (key := next((f"{k}={v}" for k, v in call.from_env if _mirrors(f"{k}={env.get(v, '0')}")), "")):
        return f"--config-env {key}"
    if call.sub == "config" and (setting := _config_write(call.arguments)):
        return f"config {setting}"
    # git remote [-v] add --mirror sets remote.<name>.mirror; =fetch only fetches
    remote = list(call.arguments)
    while remote[:1] in (["-v"], ["--verbose"]):
        remote.pop(0)
    if (
        call.sub == "remote"
        and remote[:1] == ["add"]
        and (flag := next((a for a in remote if a in {"--mirror", "--mirror=push"}), None))
    ):
        return f"remote add {flag}"
    return _sub_bypass(call.sub, call.arguments)


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


def aliases(words: Sequence[str]) -> list[tuple[str, str]]:
    """The git aliases one command defines, each name and body: by -c, --config-env, environment or config write.

    A --config-env value is the variable's when the command sets it; an alias whose body is unknown is left out.
    """
    settings = _env_settings(_environment(words))
    for run in shell_programs.runs(words):
        settings += _env_settings(run.env)
        if shell_programs.name(run.words[0]) != "git":
            continue
        env = {**_environment(words), **run.env}
        call = _parse_git(run.words[1:])
        settings += [*call.config, *(f"{key}={env[var]}" for key, var in call.from_env if var in env)]
        if call.sub == "config" and (written := _config_set(call.arguments)):
            settings.append("=".join(written))
    found = (s.partition("=") for s in settings)
    return [(m[1], body) for key, _, body in found if body and (m := _ALIAS.fullmatch(key))]


def subcommand(words: Sequence[str]) -> str | None:
    """The subcommand, or alias, the git command *words* runs."""
    return _parse_git(words[1:]).sub


def alias_arguments(words: Sequence[str]) -> tuple[str, ...]:
    """The words the git command *words* passes the subcommand or alias it runs."""
    return _parse_git(words[1:]).arguments


def scripts(words: Sequence[str]) -> list[tuple[str, bool]]:
    """The shell texts a git command runs, each with whether it runs after the command wrote.

    rebase runs each --exec text after a commit it made; submodule foreach runs its text in each submodule.
    """
    call = _parse_git(words[1:])
    arguments = list(call.arguments)
    if call.sub == "rebase":
        return [
            (text, True)
            for text in _rebase_exec(arguments[: arguments.index("--")] if "--" in arguments else arguments)
        ]
    while arguments[:1] in (["-q"], ["--quiet"]):
        arguments.pop(0)
    if call.sub != "submodule" or arguments[:1] != ["foreach"]:
        return []
    given = arguments[1:]
    while given[:1] in (["-q"], ["--quiet"], ["--recursive"]):  # its only options; its command's are its own
        given.pop(0)
    # git runs sh -c '<first> "$@"' <the rest>; a word the shell built stays an expansion there
    rest = [forwarded(w) for w in given[1:]]
    return [(" ".join([given[0], *rest]).strip(), False)] if given else []


def forwarded(word: str) -> str:
    """*word* as shell text that gives the same word, or an expansion if the calling shell built it."""
    if not getattr(word, "expanded", False):
        return shlex.quote(word)
    return f'"{word}"' if not set(word) & {'"', "\\", "`"} else '"$FORWARDED"'


def _rebase_exec(arguments: Sequence[str]) -> list[str]:
    """The texts git rebase runs with -x or --exec, given in the next word or attached."""
    found: list[str] = []
    for i, w in enumerate(arguments):
        following = arguments[i + 1] if i + 1 < len(arguments) else ""
        if w == "--exec":
            found.append(following)
        elif w.startswith("--exec="):
            found.append(w.removeprefix("--exec="))
        elif re.fullmatch(r"-[^-].*", w):
            flags, _ = _short(w[1:], *_GIT_VALUES["rebase"][:2])
            if w[len(flags) + 1 : len(flags) + 2] == "x":
                found.append(w[len(flags) + 2 :] or following)
    return [text for text in found if text]


def switch(words: Sequence[str], env: dict[str, str]) -> str | None:
    """A hook tool's switch in *env* that skips the hooks of the git command *words* runs: HUSKY=0, and the like.

    A value built at run time is not read here.
    """
    if shell_programs.name(words[0]) != "git" or _parse_git(words[1:]).sub not in _HOOKED:
        return None
    return next((f"environment setting {k}={v}" for k, v in env.items() if turns_off(k, v)), None)


def turns_off(key: str, value: str) -> bool:
    """Whether a hook tool's variable set to *value* skips hooks; a value built at run time is not read."""
    if getattr(value, "expanded", False):
        return False
    return value in _SWITCHES_OFF.get(key, ()) or (key in {"SKIP", "LEFTHOOK_EXCLUDE"} and bool(value))


def expanded(words: Sequence[str], run: shell_programs.Run, switches: dict[str, str]) -> str | None:
    """A word of the git command *run* runs, built at run time, that may skip hooks or signing or force a push.

    *words* are the command's, *switches* the hook tools' variables the run sees. Only a git command that writes, or
    whose subcommand is built at run time, is read. Then: its subcommand, a -c key, the value of a hook, signing or
    mirror key; in a git command that runs hooks also a switch's value and any other word, except an option's value
    that stays one word and a path after --. A push's refspecs are never exempt.
    """
    if shell_programs.name(run.words[0]) != "git":  # it may run git push, which reads the settings it is given
        return _built_setting(_parse_git([]), {**_environment(words), **run.env}, push=True)
    call = _parse_git(run.words[1:])
    if _built(call.sub):
        return f"subcommand `{call.sub}`"
    if not mutation(run.words):
        return None
    if found := _built_setting(call, {**_environment(words), **run.env}, push=_may_push(run.words)):
        return found
    if call.sub not in _HOOKED:
        return None
    built = (f"environment setting {k}={v}" for k, v in switches.items() if getattr(v, "expanded", False))
    return next(built, None) or next((f"`{w}`" for w in _unexempt(call.sub, call.arguments) if _built(w)), None)


def _built(word: str | None) -> bool:
    return bool(word) and getattr(word, "expanded", False) and "$" in word


def _built_setting(call: _GitCall, env: dict[str, str], *, push: bool) -> str | None:
    """A -c, environment or config-write setting whose key, or a guarded key's value, is built at run time."""
    settings = [_halves(c) for c in call.config]
    settings += [
        (k, env.get(f"GIT_CONFIG_VALUE_{m[1]}", Word())) for n, k in env.items() if (m := _CONFIG_KEY.fullmatch(n))
    ]
    settings += [(Word("GIT_CONFIG_PARAMETERS"), env.get("GIT_CONFIG_PARAMETERS", ""))]
    settings += [(key, env.get(var, var)) for key, var in call.from_env]  # a variable named at run time is built
    if call.sub == "config" and (written := _config_set(call.arguments)):
        settings.append(written)
        push = True  # a mirror key written to the configuration mirrors later pushes
    return next(
        (f"setting `{k}={v}`" for k, v in settings if _built(k) or (_guarded(k, push=push) and _built(v))), None
    )


def _halves(setting: str) -> tuple[Word, Word]:
    """A -c or --config-env setting's two halves, each built at run time when its own text holds the expansion."""
    key, _, value = setting.partition("=")
    flag = getattr(setting, "expanded", False)
    return Word(key, expanded=flag), Word(value, expanded=flag)


def _guarded(key: str, *, push: bool) -> bool:
    """Whether a git key replaces the hooks or signs, whatever its value; or, in a push, mirrors it."""
    return key.lower() in {"core.hookspath", "commit.gpgsign", "tag.gpgsign", "git_config_parameters"} or (
        push and bool(_MIRROR_KEY.fullmatch(key))
    )


def _unexempt(sub: str, arguments: Sequence[str]) -> list[str]:
    """The words of a git subcommand that may be options: all but an option's one-word value and paths after --."""
    required, optional, long_values = _GIT_VALUES.get(sub, _NO_VALUES)
    found: list[str] = []
    i = 0
    while i < len(arguments) and (w := arguments[i]) != "--":
        name, eq, _ = w.partition("=")
        flags, takes = _short(w[1:], required, optional) if re.fullmatch(r"-[^-].*", w) else (w[1:], False)
        # -m"$M"; in -"$F" the F is the variable's
        short = flags != w[1:] and not takes and "$" not in w[1 : len(flags) + 2]
        attached = (eq and name.startswith("--") and "$" not in name) or short
        if not attached or getattr(w, "split", False):
            found.append(w)
        valued = takes or (name in long_values and not eq)
        if valued and i + 1 < len(arguments) and getattr(arguments[i + 1], "split", False):
            found.append(arguments[i + 1])
        i += 2 if valued else 1
    return found + list(arguments[i + 1 :]) if sub == "push" else found
