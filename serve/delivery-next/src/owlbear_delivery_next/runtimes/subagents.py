"""Built-in subagents (TD-129): which one a session may start, and what each did.

Every SDK session is watched: agent, model, tokens, tool calls, credits and duration per subagent, unknown kept apart
from zero. Only an SDK planner session with the experiment enabled may start a subagent, and then only one genuine
built-in `explore` at a time; any other start voids the step, and Auto stays a wrong model (TD-53).
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from typing import Any

from owlbear_delivery_next.change_contracts.models import StepKind

ALLOWED = "explore"  # the one built-in the experiment admits (TD-129)
LAUNCHER = "task"  # the runtime tool that starts a subagent; without it an admitted explore cannot start (live)


@dataclass
class Seen:
    """One subagent as its events described it; None where an event did not say."""

    agent: str
    model: str | None
    started: str
    allowed: bool
    outcome: str = "unfinished"  # completed or failed once its end event arrives
    tokens: int | None = None
    tool_calls: int | None = None
    seconds: float | None = None
    credits: float = 0.0
    credits_known: bool = True  # every call it billed reported its credits
    calls: int = 0
    models: list[str] = field(default_factory=list)  # the models its calls billed


def eligible(kind: StepKind, role: str, *, enabled: bool) -> bool:
    """Whether a session may start the allowed built-in: an enabled SDK planner, never a judge or builder."""
    return enabled and kind == StepKind.PLAN and role == "planner"


class Watch:
    """The subagents of one SDK session, keyed by the tool call that started each."""

    def __init__(self, *, allowed: bool) -> None:
        """*allowed*: this session may start one ``explore`` at a time."""
        self.allowed, self.seen, self.active = allowed, dict[str, Seen](), set[str]()

    def started(self, data: Any) -> str:  # noqa: ANN401 - SDK subagent event data
        """Register a start; why it voids the step ("auto" for a wrong model), or "" when it is allowed."""
        cid, name = getattr(data, "tool_call_id", "") or "", getattr(data, "agent_name", "") or ""
        model = getattr(data, "model", None)
        ok = self.allowed and name == ALLOWED and not self.active and bool(cid)
        self.seen[cid] = Seen(name, model, datetime.now(UTC).isoformat(timespec="seconds"), ok)
        if model and model.lower() == "auto":
            return "auto"
        if ok:
            self.active.add(cid)
            return ""
        if self.allowed and name == ALLOWED and self.active:
            return f"{name} started while another runs; one at a time"
        return f"a subagent started: {name}; no subagent may run"

    def owns(self, parent: str | None) -> bool:
        """Whether a call or message under *parent* belongs to an allowed subagent."""
        s = self.seen.get(parent or "")
        return bool(s and s.allowed)

    def ended(self, data: Any, outcome: str) -> dict[str, Any] | None:  # noqa: ANN401 - SDK subagent event data
        """Its end: outcome, tokens, tool calls and duration where the event says them; its record, if known."""
        cid = getattr(data, "tool_call_id", "") or ""
        if (s := self.seen.get(cid)) is None:
            return None
        s.outcome, s.model = outcome, getattr(data, "model", None) or s.model
        s.tokens, s.tool_calls = getattr(data, "total_tokens", None), getattr(data, "total_tool_calls", None)
        took = getattr(data, "duration", None)
        s.seconds = took.total_seconds() if took is not None else None
        self.active.discard(cid)
        return {"call": cid, **asdict(s)}

    def call(self, data: Any) -> bool:  # noqa: ANN401 - SDK usage event data
        """Count one billed call of an allowed subagent; False when its parent is none (the gate then decides)."""
        s = self.seen.get(getattr(data, "parent_tool_call_id", None) or "")
        if s is None or not s.allowed:
            return False
        s.calls += 1
        if (model := getattr(data, "model", None)) and model not in s.models:
            s.models.append(model)
        nano = getattr(getattr(data, "copilot_usage", None), "total_nano_aiu", None)
        if nano is None:
            s.credits_known = False
        else:
            s.credits += nano / 1e9
        return True

    def child_models(self) -> set[str]:
        """The models allowed subagents billed, which the session's usage may name besides its own."""
        return {m for s in self.seen.values() if s.allowed for m in s.models}

    def report(self) -> list[dict[str, Any]]:
        """Each subagent as recorded; credits stay a breakdown of the session's own usage, never added to it."""
        return [{"call": cid, **asdict(s)} for cid, s in self.seen.items()]
