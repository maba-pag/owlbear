"""Permission decisions for one step's worker session and their reasons (D4 §3.6, TD-82, TD-86).

Every shell command and file access is allowed, except in every step a hook or signing bypass or a force push,
and in a read-only step any write. The read-only shell rule is ported from the old agents' deny-writes guard.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import PurePath
from typing import TYPE_CHECKING, Any, NamedTuple

from owlbear_delivery_next import tools

if TYPE_CHECKING:
    from collections.abc import Sequence
    from pathlib import Path

_HARMLESS = re.compile(r"\d*>>?\s*/dev/null(?![^\s;&|)])|\d*>&\d+")  # discarded output or a descriptor copy
_REDIRECTION = re.compile(r"&?[<>]+[&|]?")
_PREFIX_WORDS = frozenset({"!", "{", "do", "elif", "else", "if", "then", "time", "until", "while"})
_ASSIGNMENT = re.compile(r"[A-Za-z_]\w*=")
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


@dataclass
class _Level:
    """The command being read at one nesting level of shell text."""

    words: list[str] = field(default_factory=list)
    word: str | None = None
    quote: str = ""
    redirect: bool = False  # the next word is a redirection's target, not an argument

    def add(self, chars: str) -> None:
        self.word = (self.word or "") + chars

    def end_word(self) -> None:
        if self.word is not None:
            if not self.redirect:
                self.words.append(self.word)
            self.redirect = False
        self.word = None

    def end_command(self, commands: list[list[str]]) -> None:
        self.end_word()
        if self.words:
            commands.append(self.words)
        self.words, self.redirect = [], False


class _Lexer:
    """Splits shell text into each command's words at unquoted operators and newlines, and into substitutions."""

    def __init__(self, text: str) -> None:
        self.text = text
        self.commands: list[list[str]] = []

    def level(self, i: int, close: str = "") -> int:
        """Read text[i:] up to the unquoted *close*, or to the end without one; return the index after it.

        Raises:
            ValueError: A quote, subshell or substitution is not closed.
        """
        s = _Level()
        while i < len(self.text) and (s.quote or self.text[i] != close):
            i = self._step(s, i)
        if s.quote or (close and i >= len(self.text)):
            raise ValueError
        s.end_command(self.commands)
        return i + 1

    def _step(self, s: _Level, i: int) -> int:
        text, ch = self.text, self.text[i]
        if s.quote == "'" or (s.quote and ch == '"'):
            if ch == s.quote:
                s.quote = ""
            else:
                s.add(ch)
            return i + 1
        if ch == "\\":
            nxt = text[i + 1 : i + 2]
            if nxt != "\n":
                s.add(nxt if not s.quote or nxt in '"\\`$' else ch + nxt)
            return i + 2
        if ch == "`" or text.startswith("$(", i):
            s.add("$")  # the substitution's commands are checked on their own
            return self.level(i + 1, "`") if ch == "`" else self.level(i + 2, ")")
        if s.quote:
            s.add(ch)
            return i + 1
        return self._unquoted(s, i)

    def _unquoted(self, s: _Level, i: int) -> int:
        text, ch = self.text, self.text[i]
        if ch in "'\"":
            s.quote = ch
            s.add("")
        elif ch == "#" and s.word is None:
            end = text.find("\n", i)
            return len(text) if end < 0 else end
        elif match := _REDIRECTION.match(text, i):
            if s.word is not None and s.word.isdigit():
                s.word = None  # a file descriptor
            s.end_word()
            s.redirect = True
            return match.end()
        elif ch == "(":
            s.end_command(self.commands)
            return self.level(i + 1, ")")
        elif ch in ";&|\n)":
            s.end_command(self.commands)
        elif ch in " \t":
            s.end_word()
        else:
            s.add(ch)
        return i + 1


def _commands(text: str) -> list[list[str]]:
    """The words of each command in *text*, including those of subshells and command substitutions.

    Raises:
        ValueError: The text cannot be parsed.
    """
    lexer = _Lexer(text)
    lexer.level(0)
    return lexer.commands


class _GitCall(NamedTuple):
    config: tuple[str, ...]  # the -c settings
    sub: str | None
    arguments: tuple[str, ...]  # the subcommand's, or the unparsed rest without one


def _parse_git(words: Sequence[str]) -> _GitCall:
    """Parse the words after git: its global options, then the subcommand and its arguments."""
    config: list[str] = []
    i = 0
    while i < len(words):
        w = words[i]
        if w in _GIT_GLOBAL_OPTIONS:
            config += words[i + 1 : i + 2] if w == "-c" else []
            i += 2
        elif w in _GIT_GLOBAL_FLAGS or ("=" in w and w.partition("=")[0] in _GIT_GLOBAL_ATTACHED):
            i += 1
        else:
            break
    rest = tuple(words[i:])
    if rest and not rest[0].startswith("-"):
        return _GitCall(tuple(config), rest[0], rest[1:])
    return _GitCall(tuple(config), None, rest)


def _disables(setting: str) -> bool:
    """Whether a git -c setting replaces the hooks or turns commit or tag signing off."""
    key, eq, value = setting.partition("=")
    key = key.lower()
    return key == "core.hookspath" or (
        key in {"commit.gpgsign", "tag.gpgsign"} and bool(eq) and value.lower() in _GIT_FALSE
    )


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
    return None


def _bypass(words: Sequence[str]) -> str | None:
    """Return the setting, option or refspec of a git command that skips hooks or signing, or forces a push."""
    i = next((i for i, w in enumerate(words) if w not in _PREFIX_WORDS and not _ASSIGNMENT.match(w)), len(words))
    if i == len(words) or PurePath(words[i]).name != "git":
        return None
    call = _parse_git(words[i + 1 :])
    if setting := next((s for s in call.config if _disables(s)), None):
        return f"-c {setting}"
    return _sub_bypass(call.sub, call.arguments)


def _is_read_only_branch(arguments: Sequence[str]) -> bool:
    if list(arguments) in ([], ["--show-current"]):
        return True
    return arguments[0] == "--list" and not any(a.startswith("-") for a in arguments[1:])  # else it creates one


def _git_mutation(words: Sequence[str]) -> str | None:
    """How a git command anywhere in one command's words would write."""
    for i in (i for i, w in enumerate(words) if PurePath(w).name == "git"):
        call = _parse_git(words[i + 1 :])
        if option := next((a for a in call.arguments if a.partition("=")[0] in _GIT_WRITE_OPTIONS), None):
            return f"Git output option {option}"
        if call.sub == "branch" and _is_read_only_branch(call.arguments):
            continue
        if call.sub not in _READ_ONLY_GIT and (call.sub or call.arguments):
            return f"Git command '{call.sub or ' '.join(words[i:])}'"
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
        try:
            commands = _commands(text)
        except ValueError:
            return f"`{text}` cannot be parsed"
        if not commands:
            return "the shell request names no command"
        if flag := next(filter(None, map(_bypass, commands)), None):
            return f"`{text}` uses {flag}, which skips hooks or signing or forces history"
        if not policy.write and (found := _mutation(text, commands)):
            return f"`{text}` uses {found}, which writes in a read-only step"
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
