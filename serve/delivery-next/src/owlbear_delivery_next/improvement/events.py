"""Improvement's event intake (design §4): a watched session's own events, kept bounded for the Spotter's cards.

Every SDK event passes through ``Kept.add`` as the same dict a session's ``events.jsonl`` line holds (``to_dict()``),
so a live session and a logged one read alike. Only the session's own agent counts (no subagent's events). Kept:
the first requester message (the step's task) and the last few, the agent's last messages, the last answers to its
questions, and a ring of the last actions, each field cut to a bound; what the ring drops is counted. A snapshot is a
frozen copy: a result that completes after it is not in it.
"""

from __future__ import annotations

import json
import re
from collections import deque
from typing import Any

from owlbear_delivery_next.local_system.mask import redact, secret_key

ACTIONS, CALLS = 120, 200  # actions kept; calls awaiting their completion
TEXT, SAID, ARGS, RESULT = 6000, 1500, 1500, 4000  # characters kept of a request, a message, arguments, a result
QUESTIONS = frozenset({"ask_user", "askQuestions"})
STOPS = frozenset({"abort", "session.abort", "session.shutdown"})
OPEN, CLOSE = "<browser_context>", "</browser_context>"
BROWSER = re.compile(rf"{OPEN}.*?{CLOSE}", re.DOTALL)
OMITTED = "[browser context omitted]"


def no_browser(text: str) -> str:
    """*text* without the browser context VS Code attaches, a region cut in two included."""
    text = BROWSER.sub(OMITTED, text)
    if CLOSE in text:  # its opening was cut off: everything up to it was browser context
        text = OMITTED + text.rsplit(CLOSE, 1)[1]
    if OPEN in text:  # its end was cut off
        text = text.split(OPEN, 1)[0] + OMITTED
    return text


def main_agent(d: dict[str, Any]) -> bool:
    """Whether the event is the session's own agent's, not a subagent's."""
    data = d.get("data")
    return isinstance(data, dict) and not d.get("agentId") and not data.get("parentToolCallId")


def as_dict(ev: Any) -> dict[str, Any]:  # noqa: ANN401 - an SDK event object or a logged event
    """The event as its log line holds it."""
    data = ev.to_dict() if hasattr(ev, "to_dict") else ev
    return data if isinstance(data, dict) else {}


CUT = " [...] "
RAW = 262144  # characters cleaned whole; a longer text is omitted, as no cut of it is known to be safe
EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
PROTECT = re.compile(r"(?:/(?:Users|private|var|tmp|Library|home)/[^\s\"'`:;,)\]}]+)|\b[0-9a-f]{40}\b")


def _text(value: object) -> str:
    return value if isinstance(value, str) else json.dumps(value, ensure_ascii=False, default=str)


def clip(text: object, n: int) -> str:
    """*text* as a string of at most *n* characters, its start and end kept."""
    s = _text(text)
    if len(s) <= n:
        return s
    if n <= len(CUT):
        return s[:n]
    head = (n - len(CUT)) // 2
    return s[:head] + CUT + s[len(s) - (n - len(CUT) - head) :]


def clean(text: str) -> str:
    """*text* without credentials, emails or browser context.

    Every credential rule applies everywhere; only the long-value rule spares file paths and commit ids, which are no
    secrets (as the pilot's cards were).
    """
    kept: list[str] = []

    def hold(m: re.Match[str]) -> str:
        kept.append(m.group(0))
        return f"\x00{len(kept) - 1}\x00"

    text = PROTECT.sub(hold, redact(no_browser(text.replace("\x00", "")), blobs=False))
    return EMAIL.sub("<email>", re.sub(r"\x00(\d+)\x00", lambda m: kept[int(m.group(1))], redact(text)))


def omitted(length: int) -> str:
    """What stands for a text too long to clean."""
    return f"[{length} characters, too long to clean: omitted]"


def _scrubbed(value: Any) -> Any:  # noqa: ANN401 - JSON values
    """*value* with every string cleaned and every credential-named field's value masked, before it is encoded."""
    if isinstance(value, str):
        return clean(value)
    if isinstance(value, list):
        return [_scrubbed(v) for v in value]
    if isinstance(value, dict):
        return {k: "***" if secret_key(str(k)) and not isinstance(v, dict | list) else _scrubbed(v)
                for k, v in value.items()}  # fmt: skip
    return value


def kept_text(value: object, n: int) -> str:
    """*value* cleaned whole, then clipped to *n*: a credential is never cut from what names it or quotes it.

    Structured values are cleaned field by field before they are encoded, so no escaped quote hides a credential. A
    text over ``RAW`` is omitted: a cut could split a quoted or labelled credential, and no cut is known to be safe.
    """
    if not isinstance(value, str):
        size = len(_text(value))
        return omitted(size) if size > RAW else clip(_text(_scrubbed(json.loads(_text(value)))), n)
    s = no_browser(value)
    return omitted(len(s)) if len(s) > RAW else clip(clean(s), n)


def result_text(data: dict[str, Any]) -> str:
    """A completed call's result as the agent saw it, else its error."""
    result = data.get("result")
    if isinstance(result, dict):
        return str(result.get("content") or result.get("detailedContent") or "")
    if isinstance(result, str):
        return result
    error = data.get("error")
    return error if isinstance(error, str) else json.dumps(error) if error else ""


class Kept:
    """One session's bounded intake."""

    def __init__(self) -> None:
        self.task, self.task_n = "", 0  # the first requester message: a step's task, criteria and scope
        self.first_reply: dict[str, Any] | None = None  # the agent's first message after the latest request: its plan
        self.requests: deque[dict[str, Any]] = deque(maxlen=4)
        self.answers: deque[dict[str, Any]] = deque(maxlen=3)
        self.said: deque[dict[str, Any]] = deque(maxlen=12)
        self.actions: deque[dict[str, Any]] = deque(maxlen=ACTIONS)
        self.calls: dict[str, dict[str, Any]] = {}
        self.dropped = {"actions": 0, "requests": 0, "messages": 0, "texts too long to clean": 0}  # what is not held
        self.n = 0  # events seen

    def add(self, ev: Any) -> bool:  # noqa: ANN401 - an SDK event object or a logged event
        """Take in one event of the main agent (a subagent's is left out); whether it completed a main-agent call."""
        d = as_dict(ev)
        self.n += 1
        kind, data, at = d.get("type"), d.get("data") or {}, str(d.get("timestamp") or "")
        if not main_agent(d):
            return False
        if kind == "user.message":
            text = self._kept(str(data.get("content") or ""), TEXT)
            if not self.task:
                self.task, self.task_n = text, self.n
            self._ring(self.requests, {"n": self.n, "at": at, "text": text}, "requests")
            self.first_reply = None
        elif kind == "assistant.message" and str(data.get("content") or "").strip():
            message = {"n": self.n, "at": at, "text": self._kept(str(data["content"]), SAID)}
            self.first_reply = self.first_reply or message
            self._ring(self.said, message, "messages")
        elif kind == "tool.execution_start":
            call = {"n": self.n, "at": at, "tool": str(data.get("toolName") or ""), "id": str(data.get("toolCallId")),
                    "args": self._kept(data.get("arguments"), ARGS)}  # fmt: skip
            self._push(call)
            if len(self.calls) < CALLS:
                self.calls[call["id"]] = call
        elif kind == "tool.execution_complete" and (call := self.calls.pop(str(data.get("toolCallId")), None)):
            call |= {"done_at": at, "ok": data.get("success"), "result": self._kept(result_text(data), RESULT)}
            if call["tool"] in QUESTIONS and not self._stopped(call):
                self.answers.append(
                    {"at": at, "question": clip(call["args"], 400), "answer": clip(call["result"], 400)}
                )
            return True
        elif kind in STOPS or kind == "session.compaction_complete":
            self._push({"n": self.n, "at": at, "kind": "stop" if kind in STOPS else "compaction"})
        return False

    def _stopped(self, call: dict[str, Any]) -> bool:
        """Whether a question's result was written by a stop, not answered (the pilot's b6f1f8)."""
        return "cancelled the request" in call.get("result", "") and any(
            a.get("kind") == "stop" for a in list(self.actions)[-3:]
        )

    def _kept(self, value: object, n: int) -> str:
        text = kept_text(value, n)
        if text.endswith("too long to clean: omitted]") and text.startswith("["):
            self.dropped["texts too long to clean"] += 1
        return text

    def _push(self, action: dict[str, Any]) -> None:
        self._ring(self.actions, action, "actions")

    def _ring(self, ring: deque[dict[str, Any]], item: dict[str, Any], what: str) -> None:
        if len(ring) == ring.maxlen:
            self.dropped[what] += 1
        ring.append(item)

    def snapshot(self) -> dict[str, Any]:
        """A frozen copy at this moment; calls still open have no result in it."""
        return json.loads(json.dumps({
            "task": self.task, "task_n": self.task_n, "first_reply": self.first_reply, "requests": list(self.requests),
            "answers": list(self.answers), "said": list(self.said), "actions": list(self.actions),
            "dropped": self.dropped, "n": self.n,
        }, default=str))  # fmt: skip
