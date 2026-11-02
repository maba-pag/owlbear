"""Permission decisions for one step's worker session and their reasons (D4 §3.6, TD-82, TD-86).

Every shell command and file access is allowed, except in every step a hook or signing bypass or a force push,
and in a read-only step any write. The read-only shell rule is ported from the old agents' deny-writes guard.
A shell request is judged by its whole command text, not the runtime's segments, which lose pipes, redirections and
here-document bodies. Commands behind wrapper programs (env, env -S, xargs, timeout, find -exec, ...) are judged the
same way, and so is turning hooks or signing off through git config. So is every script a shell runs (``shell_walk``):
its -c script, script file, startup files, here-document or here-string, a sourced file, eval's words and a shell
script run by path. What the guard can't read is refused: a shell reading input from another program, a command or
script built at run time, a script or program run after an earlier write in the same command, and a relative path
once the folder can't be followed.

How a shell bypass is met depends on the owner's guard level (``Level``) and on the class of the reader that found
it. Core findings are today's readers, everything the guard can't read in a write step, globbed command names and
mirror pushes; variant findings are git aliases a command writes, commands git runs (rebase --exec, submodule
foreach) and hook-tool switches; doubtful findings are bypasses in interpreters' inline code and expanded git
arguments. strict refuses core and variant and warns doubtful; standard refuses core and warns the rest; lenient
warns all; off checks no shell bypass. Outside the ladder, at every level: a read-only step's writes, a confined
step's rules, file, MCP, memory and custom-tool requests.
"""

from __future__ import annotations

import functools
import re
from dataclasses import dataclass, replace
from typing import TYPE_CHECKING, Any, Literal

from owlbear_delivery_next.change_contracts import git_reading, shell_walk, tools
from owlbear_delivery_next.local_system import shell_parse, shell_programs

if TYPE_CHECKING:
    from collections.abc import Sequence
    from pathlib import Path

Level = Literal["strict", "standard", "lenient", "off"]
CORE, VARIANT, DOUBTFUL = 0, 1, 2  # the reader classes, each pass reading with its own and the ones before
_REFUSED = {"strict": DOUBTFUL, "standard": VARIANT, "lenient": CORE, "off": CORE}  # classes below it are refused
BYPASS = "which skips hooks or signing or forces history"  # the end of every bypass denial's reason
_HARMLESS = re.compile(r"\d*>>?\s*/dev/null(?![^\s;&|)])|\d*>&\d+")  # discarded output or a descriptor copy
_LOOKUP = re.compile(  # command -v cp: names the program, runs nothing
    r"(?<![^\s;&|(])command(?:[ \t]+-p)*[ \t]+-[pV]*[vV][pvV]*(?:[ \t]+-[pvV]+)*(?:[ \t]+--)?(?:[ \t]+[\w./+-]+)+"
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
    confined: bool = False  # writes only inside the root and no shell: an editor of third-party text (TD-194)


@dataclass(frozen=True)
class Request:
    """The parts of a permission request the policy judges."""

    kind: str
    commands: tuple[str, ...] = ()  # a shell request's segments as the runtime split them
    paths: tuple[str, ...] = ()
    tool: str = ""
    server: str = ""  # an MCP request's server
    text: str = ""  # a shell request's whole command: segments lose pipes, redirections and here-document bodies


def identities(req: Request) -> set[str]:
    """The tools a request names, lower case: each shell command's program, else its tool or kind (TD-36)."""
    programs = {
        words[0].rsplit("/", 1)[-1].lower()
        for text in req.commands
        for part in re.split(r"[;&|\n]+", text)
        if (words := part.split()) and words[0] != "cd"
    }
    return programs or {(req.tool or req.kind).lower()}


@dataclass(frozen=True)
class Verdict:
    """What the guard found in one request, and whether the step's level refuses it or only warns."""

    reason: str
    refuse: bool = True


def judge(
    policy: Policy,
    req: Request,
    offered: frozenset[str] = frozenset(),
    *,
    memory: bool = False,
    level: Level = "strict",
) -> Verdict | None:
    """Judge one request at the owner's guard level: None allows it, a Verdict refuses it or warns about it."""
    if req.kind != "shell" or policy.confined:
        reason = _fixed(policy, req, offered, memory=memory)
        return Verdict(reason) if reason else None
    if not policy.write and (reason := _shell(policy, req, None)):  # a read-only step's writes: refused at any level
        found = _shell(replace(policy, write=True), req, VARIANT)
        return Verdict(_marked(reason, found) if found and bypass(found) else reason)
    if level == "off":
        return None
    for reading in (CORE, VARIANT, DOUBTFUL):
        if reason := _shell(policy, req, reading):
            return Verdict(reason, refuse=reading < _REFUSED[level])
    return None


def _marked(reason: str, found: str) -> str:
    """A read-only refusal that also names the bypass, so it counts as one, not as a wrong choice of tool."""
    name = reason.partition(" uses ")[0]
    return (
        f"{reason}; it also {found.removeprefix(f'{name} ')}"
        if found.startswith(f"{name} uses ")
        else f"{reason}; {found}"
    )


def _mutation(text: str, commands: Sequence[Sequence[str]]) -> str | None:
    """How a shell command would write files or change Git state.

    Discarded output, a lookup (command -v cp) and an arithmetic comparison ($((1 > 0))) write nothing.
    """
    if found := next(filter(None, map(git_reading.mutation, commands)), None):
        return found
    for run in (r for words in commands for r in shell_programs.runs(words)):  # env -S hides it, /bin/cp names it
        if match := _SHELL_MUTATION.match(" ".join([shell_programs.name(run.words[0]), *run.words[1:]])):
            return f"filesystem mutation '{match[0].strip(' \t;&|')}'"
    text = _LOOKUP.sub("", _HARMLESS.sub("", _without_arithmetic(text)))
    if _REDIRECT.search(text):
        return "a redirect"
    if match := _SHELL_MUTATION.search(text):
        return f"filesystem mutation '{match[0].strip(' \t;&|')}'"
    return None


def _shell(policy: Policy, req: Request, reading: int | None) -> str | None:
    """One pass over a shell request: *reading* None reads no bypass, else the readers up to that class."""
    for text in (req.text,) if req.text else req.commands or ("",):
        if reason := _check(policy, text, reading=reading):
            return reason
    if reading is None:
        return None
    for text in req.commands if req.text else ():  # the runtime's own reading too, should the text be misread
        try:
            flag = next(filter(None, (git_reading.bypass(c.words) for c in shell_parse.parse(text))), None)
        except ValueError:  # the whole text was judged already
            continue
        if flag:
            return f"`{text}` uses {flag}, {BYPASS}"
    return None


def bypass(reason: str) -> bool:
    """Whether a denial's *reason* refused a bypass of hooks, signing or history, not a choice of tool (C-28 T8)."""
    return reason.endswith(BYPASS)


def _check(  # noqa: PLR0913 - the walk calls it back with the text's place; the pass stays fixed
    policy: Policy,
    text: str,
    depth: int = 0,
    state: shell_walk.State | None = None,
    label: str = "",
    *,
    reading: int | None,
) -> str | None:
    """Judge one shell text, and each script it runs, the same way; *label* names a script file in reasons."""
    name = label or text
    try:
        commands = shell_parse.parse(text)
    except ValueError:
        return f"`{name}` cannot be parsed"
    if not commands:
        return "the shell request names no command" if depth == 0 else None  # an empty script does nothing
    try:
        found = (git_reading.bypass(c.words) for c in commands) if reading is not None else ()
        if flag := next(filter(None, found), None):
            return f"`{name}` uses {flag}, {BYPASS}"
        if not policy.write and (found := _mutation(text, [c.words for c in commands])):
            return f"`{name}` uses {found}, which writes in a read-only step"
        mutation = functools.partial(_run_mutation, policy)
        nested = functools.partial(_check, policy, reading=reading)
        walk = shell_walk.Walk(name, depth, nested, _writes, _run_bypass if reading is not None else _none, mutation)
        return walk.commands(commands, state or shell_walk.State(policy.root))
    except shell_programs.UnreadableError as error:
        return f"`{name}` {error}"


def _run_bypass(name: str, run: shell_programs.Run) -> str | None:
    """The refusal of a #! line's program that skips hooks or signing or forces history, as env -S runs it."""
    if setting := git_reading.env_setting(run.env):
        return f"`{name}` uses environment setting {setting}, {BYPASS}"
    return f"`{name}` uses {flag}, {BYPASS}" if (flag := git_reading.bypass(run.words)) else None


def _none(_name: str, _run: shell_programs.Run) -> None:
    """No bypass reader: the read-only pass."""


def _run_mutation(policy: Policy, name: str, run: shell_programs.Run) -> str | None:
    """The refusal of a #! line's program that writes, in a read-only step (#!/usr/bin/env -S rm -f)."""
    if policy.write or not (found := _mutation(" ".join(run.words), [run.words])):
        return None
    return f"`{name}` uses {found}, which writes in a read-only step"


def _writes(command: shell_parse.Command) -> bool:
    """Whether one command writes files or changes Git state, as the read-only rule sees it."""
    return _mutation(command.raw, [command.words]) is not None


def _without_arithmetic(text: str) -> str:
    """*text* without its $((...)) expansions outside quotes that hold no substitution: their < and > compare."""
    out, i, quote = [], 0, ""
    while i < len(text):
        ch = text[i]
        if ch == "\\" and quote != "'":
            out.append(text[i : i + 2])
            i += 2
            continue
        if (quote and ch == quote) or (not quote and ch in "'\""):
            quote = "" if quote else ch
        elif quote != "'" and text.startswith("$((", i) and (end := shell_parse.arithmetic_end(text, i + 3)):
            span = text[i:end]
            if "$(" not in span[1:] and "`" not in span and "'" not in span and '"' not in span:
                i = end
                continue
        out.append(ch)
        i += 1
    return "".join(out)


def decide(
    policy: Policy,
    req: Request,
    offered: frozenset[str] = frozenset(),
    *,
    memory: bool = False,
    level: Level = "strict",
) -> str | None:
    """Return None to allow, or the denial reason the agent and the activity log see; a warning allows."""
    verdict = judge(policy, req, offered, memory=memory, level=level)
    return verdict.reason if verdict and verdict.refuse else None


def _fixed(policy: Policy, req: Request, offered: frozenset[str], *, memory: bool) -> str | None:
    """The rules outside the guard level: None to allow, or the denial reason.

    *offered* are the MCP tools the role's agent file names as server/tool, such as saving a memory (TD-70); the
    runtime names a request's tool server-tool. *memory* is the owner's Copilot Memory switch: with it on, a role
    whose agent file names store_memory or vote_memory may save or vote (D-01M69EQN3KZE2QSBPH1CMDFK22).
    """
    if req.kind in {"mcp", "memory"}:
        return _offered(req, offered, memory=memory)
    if req.kind == "custom-tool":
        return (
            None
            if req.tool in {*(s.name for s in tools.SPECS), tools.FIRST_LOOK, tools.SCAN_DESIGN, tools.LOOKUP}
            else f"tool {req.tool} is not allowed"
        )
    if req.kind in {"read", "write"}:
        return _file(policy, req)
    if req.kind == "url":
        return None
    if req.kind == "shell":
        return "this step runs no shell commands"
    return f"{req.kind} requests are not allowed in this step"


def _offered(req: Request, offered: frozenset[str], *, memory: bool) -> str | None:
    """An MCP server's tool, or with Copilot Memory on the runtime's memory tool, that the role's agent file names."""
    if req.kind == "mcp":
        named = f"{req.server}/{req.tool.removeprefix(f'{req.server}-')}" in offered
        return None if named else "mcp requests are not allowed in this step"
    if not memory:
        return "Copilot Memory is off for Delivery's sessions"
    return None if req.tool in offered else f"{req.tool or 'this memory request'} is not offered to this role"


def _file(policy: Policy, req: Request) -> str | None:
    if req.kind == "read":
        return None
    if not policy.write:
        return "writes are not allowed in this step"
    return _outside(policy, req) if policy.confined else None


def _outside(policy: Policy, req: Request) -> str | None:
    root = policy.root.resolve()
    if not req.paths:
        return "a write must name its file"
    for path in req.paths:
        if not (root / path).resolve().is_relative_to(root):
            return f"{path} is outside this step's folder; write only under {root}"
    return None


def view(r: Any) -> Request:  # noqa: ANN401 - one of the SDK's permission request classes
    """Normalise one SDK permission request into a Request."""
    kind = getattr(r, "kind", type(r).__name__)
    if kind == "shell":
        whole = getattr(r, "full_command_text", "") or ""
        texts = [s.full_command_text for s in r.command_segments or ()] or [c.identifier for c in r.commands]
        return Request(kind, tuple(texts or [whole]), tuple(r.possible_paths or ()), text=whole)
    if kind in {"read", "write"}:
        path = r.resolved_path or getattr(r, "path", None) or getattr(r, "file_name", "")
        edits = getattr(r, "file_edits", None) or ()  # a move names a before and an after path
        moved = [side.path for e in edits for side in (e.before, e.after) if side is not None and side.path]
        return Request(kind, paths=tuple(dict.fromkeys([*([path] if path else []), *moved])))
    if kind == "memory":  # a Copilot Memory save or vote names its tool by its action
        action = getattr(r, "action", None)
        return Request(kind, tool=f"{getattr(action, 'value', action)}_memory" if action else "")
    return Request(kind, tool=getattr(r, "tool_name", ""), server=getattr(r, "server_name", ""))
