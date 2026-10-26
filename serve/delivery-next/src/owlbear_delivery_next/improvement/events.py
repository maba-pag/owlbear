"""Improvement's event intake (design §4): a watched session's own events, kept bounded for the Spotter's cards.

Every SDK event passes through ``Kept.add`` as the same dict a session's ``events.jsonl`` line holds (``to_dict()``),
so a live session and a logged one read alike. Only the session's own agent counts (no subagent's events). Kept:
the first requester message (the step's task) and the last few, the agent's last messages, the last answers to its
questions, and a ring of the last actions, each field cut to a bound; what the ring drops is counted. A snapshot is a
frozen copy: a result that completes after it is not in it.
"""

from __future__ import annotations

import json
from collections import deque
from typing import Any

ACTIONS, CALLS = 120, 200  # actions kept; calls awaiting their completion
TEXT, SAID, ARGS, RESULT = 6000, 1500, 1500, 4000  # characters kept of a request, a message, arguments, a result
QUESTIONS = frozenset({"ask_user", "askQuestions"})
STOPS = frozenset({"abort", "session.abort", "session.shutdown"})


def as_dict(ev: Any) -> dict[str, Any]:  # noqa: ANN401 - an SDK event object or a logged event
    """The event as its log line holds it."""
    data = ev.to_dict() if hasattr(ev, "to_dict") else ev
    return data if isinstance(data, dict) else {}


def clip(text: object, n: int) -> str:
    """*text* as a string of at most *n* characters, its start and end kept."""
    s = text if isinstance(text, str) else json.dumps(text, ensure_ascii=False, default=str)
    return s if len(s) <= n else s[: n // 2] + " [...] " + s[-(n // 2) :]


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
        self.task = ""  # the first requester message: a step's task, criteria and scope
        self.requests: deque[dict[str, Any]] = deque(maxlen=4)
        self.answers: deque[dict[str, Any]] = deque(maxlen=3)
        self.said: deque[dict[str, Any]] = deque(maxlen=12)
        self.actions: deque[dict[str, Any]] = deque(maxlen=ACTIONS)
        self.calls: dict[str, dict[str, Any]] = {}
        self.dropped = 0  # actions the ring no longer holds
        self.n = 0  # events seen

    def add(self, ev: Any) -> None:  # noqa: ANN401 - an SDK event object or a logged event
        """Take in one event of the main agent; a subagent's is left out."""
        d = as_dict(ev)
        self.n += 1
        kind, data, at = d.get("type"), d.get("data") or {}, str(d.get("timestamp") or "")
        if not isinstance(data, dict) or d.get("agentId") or data.get("parentToolCallId"):
            return  # a subagent's own events
        if kind == "user.message":
            text = clip(data.get("content") or "", TEXT)
            self.task = self.task or text
            self.requests.append({"n": self.n, "at": at, "text": text})
        elif kind == "assistant.message" and str(data.get("content") or "").strip():
            self.said.append({"n": self.n, "at": at, "text": clip(data["content"], SAID)})
        elif kind == "tool.execution_start":
            call = {"n": self.n, "at": at, "tool": str(data.get("toolName") or ""), "id": str(data.get("toolCallId")),
                    "args": clip(data.get("arguments"), ARGS)}  # fmt: skip
            self._push(call)
            if len(self.calls) < CALLS:
                self.calls[call["id"]] = call
        elif kind == "tool.execution_complete" and (call := self.calls.pop(str(data.get("toolCallId")), None)):
            call |= {"done_at": at, "ok": data.get("success"), "result": clip(result_text(data), RESULT)}
            if call["tool"] in QUESTIONS and not self._stopped(call):
                self.answers.append(
                    {"at": at, "question": clip(call["args"], 400), "answer": clip(call["result"], 400)}
                )
        elif kind in STOPS or kind == "session.compaction_complete":
            self._push({"n": self.n, "at": at, "kind": "stop" if kind in STOPS else "compaction"})

    def _stopped(self, call: dict[str, Any]) -> bool:
        """Whether a question's result was written by a stop, not answered (the pilot's b6f1f8)."""
        return "cancelled the request" in call.get("result", "") and any(
            a.get("kind") == "stop" for a in list(self.actions)[-3:]
        )

    def _push(self, action: dict[str, Any]) -> None:
        if len(self.actions) == self.actions.maxlen:
            self.dropped += 1
        self.actions.append(action)

    def snapshot(self) -> dict[str, Any]:
        """A frozen copy at this moment; calls still open have no result in it."""
        return json.loads(json.dumps({
            "task": self.task, "requests": list(self.requests), "answers": list(self.answers),
            "said": list(self.said), "actions": list(self.actions), "dropped": self.dropped, "n": self.n,
        }, default=str))  # fmt: skip
