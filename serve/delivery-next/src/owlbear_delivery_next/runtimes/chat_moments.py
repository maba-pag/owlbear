"""A chat's moments for the Spotter (Improvement design §4, "Where: Chats"): its plans, hand-offs and state changes.

Read from the chat's ``events.jsonl`` lines, one dict each, as the runtime wrote them; only the chat's own agent counts
(``events.main_agent``) and only the requester starts a turn (``events.requester``). A trace of the runtime (Copilot
CLI 1.0.103, 2026-10-27) showed what the log holds: each model round between ``assistant.turn_start`` and
``assistant.turn_end``, its ``assistant.message`` with the round's tool requests (none on the final answer), and a
``session.usage_checkpoint`` after each prompt's last round; ``session.idle`` is never written. Marked assumptions
(D-01M5XB9M1A1MNG0S54N367RC70) fill the gaps the trace leaves, each moment naming its rule's id (``assumptions``):
once a reset retired a rule, the follower records its moments as skipped and looks at none, until a decided rule (a new
id) replaces it.

- **Plan** (``assumptions.PLAN``): the agent's first reply with content after a requester message, whatever it asks
  for besides.
- **Hand-off** (``assumptions.HANDOFF``): at most one per requester turn: its final reply (content, no tool requests,
  its round ended), once the turn settled: a checkpoint after it with the log read to its end, the next requester
  message, the session's end, or ``QUIET`` seconds without an event of the agent while no round or call of it is open.
  A round that starts after it supersedes it; an abort drops it.
- **State change** (``assumptions.STATE_CHANGE``): a completed call of the agent judged against the chat's workspace
  folder (a chat has no Change): a write outside it, wherever (no exemption: the look sees caches and temporary
  folders too); or publishing, deleting or settings by its shell command or its tool's name; a shell or tool call
  whose effect is not known is a candidate too, its uncertainty in the moment. Known read-only calls are none.

Only what is read live makes a moment: history (a log read on restart, a chat found before the follower started, a
replaced log) builds the state but arms nothing, so a later checkpoint or quiet time never looks at it.
"""

from __future__ import annotations

import re
import shlex
from pathlib import Path
from typing import Any

from copilot.generated.session_events import PermissionRequestedData

from owlbear_delivery_next.change_contracts import watch_policy
from owlbear_delivery_next.improvement import assumptions
from owlbear_delivery_next.improvement.events import kept_text, main_agent, requester, result_text
from owlbear_delivery_next.runtimes.watch_feed import asked

QUIET = 120.0  # seconds without an event of the agent after its final reply that settle a turn
CALLS = 200  # open calls kept; an older one is forgotten and counted
INSIDE = frozenset({  # built-in tools whose effects stay in the session: reading, asking, its own notes and subagents
    "view", "grep", "glob", "rg", "read_bash", "list_bash", "stop_bash", "read_agent", "list_agents", "report_intent",
    "sql", "ask_user", "askQuestions", "web_fetch", "web_search", "skill", "task", "write_agent", "tool_search_tool",
    "fetch_copilot_cli_documentation", "update_todo", "think",
})  # fmt: skip
CHANGING = frozenset({
    "create", "update", "delete", "remove", "merge", "publish", "push", "post", "send", "submit", "approve",
    "transition", "assign", "book", "record", "save", "set", "configure", "commit", "write", "edit", "add", "cancel",
    "close", "retire", "correct", "store", "upload", "deploy", "register", "subscribe", "unsubscribe", "link",
    "unlink", "comment", "reply", "resolve", "decide", "ingest", "rename", "move", "apply", "trigger", "acquire",
})  # fmt: skip
READING = frozenset({
    "get", "list", "read", "search", "find", "lookup", "show", "view", "fetch", "query", "status", "describe",
    "stats", "snapshot", "check", "count", "diff", "log", "inspect", "recall", "assess", "explain", "preview",
})  # fmt: skip
SEGMENTS = re.compile(r"\|\||&&|[;|&\n]")
MUTATING_METHODS = frozenset({"POST", "PUT", "PATCH", "DELETE"})


def tokens(name: str) -> set[str]:
    """A tool name's words: split at every non-alphanumeric and at camel case, lower-cased."""
    return {t.lower() for t in re.split(r"[^A-Za-z0-9]+|(?<=[a-z0-9])(?=[A-Z])", name) if t}


def _words(segment: str) -> list[str]:
    try:
        words = shlex.split(segment, posix=True)
    except ValueError:
        words = segment.split()
    while words and (re.fullmatch(r"\w+=.*", words[0]) or words[0] in {"sudo", "command", "env", "exec", "time"}):
        words = words[1:]
    return [*([Path(words[0]).name] if words else []), *words[1:]]


def _method(words: list[str]) -> str:
    for i, w in enumerate(words):
        if w in {"-X", "--method", "--request"} and i + 1 < len(words):
            return words[i + 1].upper()
        if w.startswith(("-X", "--method=", "--request=")):
            return w.split("=", 1)[-1].removeprefix("-X").upper()
    return ""


GH_PUBLISHING = frozenset({"pr", "issue", "release", "repo", "workflow", "run", "gist", "label"})
GH_READING = frozenset({"", "list", "view", "status", "checks", "diff", "watch", "download", "get"})
GH_SETTINGS = frozenset({"auth", "secret", "variable", "config", "extension"})
PUBLISHERS = frozenset({"npm", "pnpm", "yarn", "uv", "twine", "poetry", "cargo"})
DELETERS = frozenset({"rm", "rmdir", "unlink", "shred", "trash"})
CURL_DATA = ("-d", "--data", "-F", "--form", "-T", "--upload")


def _gh(sub: str, verb: str, rest: list[str]) -> set[str]:
    found = {"deleting"} if verb in {"delete", "archive"} or "delete" in rest[:3] else set()
    if sub in GH_PUBLISHING and verb not in GH_READING:
        found.add("publishing")
    if sub == "api" and (_method(rest) in MUTATING_METHODS or {"-f", "-F", "--field", "--raw-field"} & set(rest)):
        found.add("publishing")
    if sub in GH_SETTINGS and verb not in GH_READING:
        found.add("settings")
    return found


def _git(sub: str, rest: list[str]) -> set[str]:
    found = set()
    if sub == "push":
        found.add("publishing")
    flags = set(rest)
    if (sub == "push" and {"--delete", "-d"} & flags) or (sub == "branch" and {"-D", "-d", "--delete"} & flags) or (
            sub == "reset" and "--hard" in flags) or sub == "clean" or (sub == "tag" and "-d" in flags):  # fmt: skip
        found.add("deleting")
    if sub == "config" and not {"--get", "--list", "-l", "--get-all"} & set(rest):
        found.add("settings")
    return found


def _other(head: str, sub: str, verb: str, rest: list[str]) -> set[str]:
    found = set()
    if (head in PUBLISHERS and sub == "publish") or (head == "curl" and (
            _method(rest) in MUTATING_METHODS or any(a.startswith(CURL_DATA) for a in rest))):  # fmt: skip
        found.add("publishing")
    if head in DELETERS or (head == "find" and "-delete" in rest):
        found.add("deleting")
    if head in {"launchctl", "chmod", "chown"} or (head == "defaults" and sub in {"write", "delete"}) or (
            head == "crontab" and "-l" not in rest) or (head in PUBLISHERS and sub == "config" and verb in {
            "set", "delete"}):  # fmt: skip
        found.add("settings")
    return found


def shell_effects(command: str) -> set[str]:
    """Publishing, deleting or settings a shell command does by its words (a marked assumption, never complete)."""
    found: set[str] = set()
    for segment in SEGMENTS.split(command):
        if not (w := _words(segment)):
            continue
        head, rest = w[0], w[1:]
        sub, verb = (rest[0] if rest else ""), (rest[1] if len(rest) > 1 else "")
        found |= _gh(sub, verb, rest) if head == "gh" else _git(sub, rest) if head == "git" else _other(
            head, sub, verb, rest)  # fmt: skip
    return found


class Moments:
    """One chat's moments, from its events in order; nothing here reads a file or makes a call."""

    def __init__(self, workspace: str, home: Path, tmp: Path | None) -> None:
        """*workspace* is the chat's folder: the boundary its state changes are judged by."""
        self.places = watch_policy.Places((), (), (), home, tmp).resolved()  # no exemption: every outside write counts
        self.own = watch_policy.canonical(workspace, home, self.places)
        self.turn = ""  # the requester message's event id
        self.planned = self.handed = False  # this turn's plan and hand-off moments were made
        self.final: dict[str, Any] | None = None  # this turn's latest final reply, while it may still settle
        self.ended = self.checkpoint = False  # its round ended; a checkpoint came after it
        self.rounds = 0  # rounds of the agent open
        self.calls: dict[str, dict[str, Any]] = {}  # the agent's calls started and not completed
        self.forgotten = 0  # open calls dropped past ``CALLS``
        self.chunks: dict[str, list[dict[str, Any]]] = {}  # a chunked message's parts so far
        self.heard = 0.0  # when an event of the agent was last read live (monotonic)

    def feed(self, d: dict[str, Any], *, live: bool, now: float) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        """Take one event; the moments it makes: those to look at before the event enters the card, and after."""
        if not main_agent(d):
            return [], []
        if live:
            self.heard = now
        kind = d.get("type")
        if kind == "user.message":
            return (self._requested(d) if requester(d) else []), []
        if kind == "assistant.message":
            return [], self._message(d, live=live)
        if kind == "tool.execution_complete":
            call = self.calls.pop(str((d.get("data") or {}).get("toolCallId")), None)
            return [], ([m] if call and live and self.turn and (m := self._changed(call, d)) else [])
        if kind == "session.shutdown":
            return self._handed_off("the session ended"), []
        self._noted(str(kind), d)
        return [], []

    def _requested(self, d: dict[str, Any]) -> list[dict[str, Any]]:
        """A requester message: the turn it closes is handed off before it; it starts the next."""
        before = self._handed_off("the next requester message")
        self.turn, self.planned, self.handed = str(d.get("id") or ""), False, False
        self._drop()
        return before

    def _noted(self, kind: str, d: dict[str, Any]) -> None:
        if kind == "assistant.turn_start":
            self.rounds += 1
            if self.final is not None and self.ended:  # a later round supersedes the reply it followed
                self._drop()
        elif kind == "assistant.turn_end":
            self.rounds = max(0, self.rounds - 1)
            self.ended = self.final is not None
        elif kind == "tool.execution_start":
            self._started(d)
        elif kind == "permission.requested":
            self._asked(d.get("data") or {})
        elif kind == "session.usage_checkpoint":
            self.checkpoint = self.final is not None and self.ended
        elif kind in {"abort", "session.abort"}:
            self._drop()

    def settle(self, *, frontier: bool, now: float) -> list[dict[str, Any]]:
        """At a pass's end: the hand-off of a settled turn; *frontier* says the log was read to its end."""
        if not frontier or self.final is None or not self.ended:
            return []
        if self.checkpoint:
            return self._handed_off("a usage checkpoint after the final reply")
        if not self.rounds and not self.calls and now - self.heard >= QUIET:
            return self._handed_off(f"{QUIET:.0f} seconds without an event of the agent after its final reply")
        return []

    def _drop(self) -> None:
        self.final, self.ended, self.checkpoint = None, False, False

    def _handed_off(self, boundary: str) -> list[dict[str, Any]]:
        final, ended = self.final, self.ended
        self._drop()
        if final is None or not ended or not final["live"] or self.handed or not self.turn:
            return []
        self.handed = True
        return [{"look": "hand-off", "at": final["at"], "kind": "a turn that ends with a reply to the requester",
                 "call": final["call"], "turn": self.turn, "result": final["text"], "settled": boundary,
                 "assumption": assumptions.HANDOFF}]  # fmt: skip

    def _message(self, d: dict[str, Any], *, live: bool) -> list[dict[str, Any]]:
        data = d["data"]
        if (whole := self._whole(data)) is None:
            return []
        text, tools = whole
        out = []
        if text.strip() and not self.planned and self.turn:
            self.planned = True
            if live:
                out.append({"look": "plan", "at": d.get("timestamp"), "call": str(d.get("id") or ""),
                            "kind": "the agent's first reply after the requester's message", "turn": self.turn,
                            "result": kept_text(text, 3000), "asks_for_tools": tools,
                            "assumption": assumptions.PLAN})  # fmt: skip
        if tools:
            self._drop()
        elif text.strip():
            self.final = {"at": d.get("timestamp"), "call": str(d.get("id") or ""), "text": kept_text(text, 3000),
                          "live": live}  # fmt: skip
            self.ended = self.checkpoint = False
        return out

    def _whole(self, data: dict[str, Any]) -> tuple[str, int] | None:
        """A message's text and tool requests; a chunked one's once its last chunk came (None before)."""
        index, count = data.get("chunkIndex"), data.get("chunkCount")
        if not isinstance(index, int) or not isinstance(count, int) or count <= 1:
            return str(data.get("content") or ""), len(data.get("toolRequests") or [])
        parts = self.chunks.setdefault(str(data.get("messageId")), [])
        parts.append(data)
        if index < count - 1:
            return None
        del self.chunks[str(data.get("messageId"))]
        parts.sort(key=lambda p: p.get("chunkIndex") or 0)
        return "".join(str(p.get("content") or "") for p in parts), sum(len(p.get("toolRequests") or []) for p in parts)

    def _started(self, d: dict[str, Any]) -> None:
        data = d["data"]
        if len(self.calls) >= CALLS:
            self.calls.pop(next(iter(self.calls)))
            self.forgotten += 1
        info = data.get("shellToolInfo")
        redirect = bool(info.get("hasWriteFileRedirection")) if isinstance(info, dict) else False
        self.calls[str(data.get("toolCallId"))] = {"tool": str(data.get("toolName") or ""), "args": data.get(
            "arguments"), "redirect": redirect, "asked": [], "unread": 0, "at": d.get("timestamp")}  # fmt: skip

    def _asked(self, data: dict[str, Any]) -> None:
        """A logged permission request, read the way the SDK reads a live one; one it cannot read is counted."""
        try:
            request = PermissionRequestedData.from_dict(data).permission_request
        except AssertionError, ValueError, TypeError, KeyError, AttributeError:
            request, cid = None, str((data.get("permissionRequest") or {}).get("toolCallId") or "")
        else:
            cid = str(getattr(request, "tool_call_id", "") or "")
        if (call := self.calls.get(cid)) is None:
            return
        if request is None:
            call["unread"] += 1
        else:
            call["asked"].append(request)

    def _changed(self, call: dict[str, Any], d: dict[str, Any]) -> dict[str, Any] | None:
        """The state-change moment of a completed call, or None when it is known to change nothing outside."""
        certainty, what, targets = classify(call, self.own, self.places)
        if certainty == "none":
            return None
        command = (call["args"] or {}).get("command") if isinstance(call["args"], dict) else None
        return {"look": "state-change", "at": d.get("timestamp"), "kind": "a state change",
                "call": str(d["data"].get("toolCallId")), "turn": self.turn, "tool": call["tool"],
                "args": kept_text(command or call["args"], 1500), "certainty": certainty, "what": sorted(what),
                "targets": list(targets[:20]), "workspace": str(self.own),
                "result": kept_text(result_text(d["data"]), 1500), "assumption": assumptions.STATE_CHANGE}  # fmt: skip


def classify(  # noqa: PLR0911 - one verdict a line
    call: dict[str, Any], own: Path, places: watch_policy.Places
) -> tuple[str, set[str], tuple[str, ...]]:
    """A completed call's effect outside *own*: "identified" (what and where), "unresolved" or "none".

    Evidence first: an identified write outside wins; then the runtime's own read-only evidence for a shell call (every
    parsed command read-only, no redirection into a file at its start or in a request, every request read); only then
    the command's words, else the effect stays unresolved.
    """
    tool, args, requests = call["tool"], call["args"], call["asked"]
    shaped = tuple(asked(r) for r in requests)
    policy = watch_policy.Call(tool, args, redirect=bool(call.get("redirect")), asked=shaped)
    outcome = watch_policy.judge(policy, own, places)
    if outcome.targets:
        return "identified", {"outside write"}, outcome.targets
    if tool in watch_policy.SHELLS or any(a.kind == "shell" for a in shaped):
        if not outcome.unresolved and not call["unread"]:
            return "none", set(), ()
        texts = [str(args.get("command") or "")] if isinstance(args, dict) else []
        texts += [getattr(r, "full_command_text", "") or "" for r in requests if getattr(r, "kind", "") == "shell"]
        if what := set().union(*(shell_effects(t) for t in texts if t)):
            return "identified", what, ()
        return "unresolved", {"shell effect"}, ()
    if tool in watch_policy.WRITERS:
        return ("unresolved", {"file edit without a path"}, ()) if outcome.unresolved else ("none", set(), ())
    if tool in INSIDE and not call["unread"]:
        return "none", set(), ()
    if any(getattr(r, "kind", "") == "mcp" and getattr(r, "read_only", False) for r in requests):
        return "none", set(), ()
    words = tokens(tool)
    if words & CHANGING:
        return "identified", {"a tool that changes outside state"}, ()
    if words & READING and not call["unread"]:
        return "none", set(), ()
    return "unresolved", {"a tool whose effect is not known"}, ()
