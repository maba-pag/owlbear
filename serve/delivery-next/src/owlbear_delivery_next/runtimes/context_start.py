"""What fills a session's context after its first model call, from the SDK's context attribution, in seven parts.

The attribution's five occupied categories (system prompt, custom instructions, built-in tools as ``systemTools``, MCP
tools, messages) add up to its ``totalTokens``. Skills and subagents are entries inside them: each ``skill`` and
``subagent`` entry is taken out of the category its ``parentId`` chain leads to, never found by its ``label``. When
that chain names no category, or a category holds fewer tokens than its entries, that kind stays in its category
and ``kept`` says so. A missing answer or a changed shape is unmeasured with its error, never an exception.

``Start`` reads it once per session Delivery creates, at its first main-agent ``assistant.usage``, beside the session:
the read is bounded by ``BOUND`` and never held by the session, and its line is written as soon as it answers, so a
runner killed later keeps it. A failed, missing, timed-out or cancelled read is written unmeasured with its error.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from owlbear_delivery_next.git.command_failure import rpc_failure
from owlbear_delivery_next.state_store import spend_ledger

if TYPE_CHECKING:
    from copilot.generated.rpc import Entry, SessionContextAttribution

PARTS = ("system_prompt", "custom_instructions", "skills", "subagents", "built_in_tools", "mcp_tools", "messages")
CATEGORIES = {"system_prompt": "system_prompt", "custom_instructions": "custom_instructions",
              "built_in_tools": "system_tools", "mcp_tools": "mcp_tools", "messages": "messages"}  # fmt: skip
ROOTS = {("system", "systemPrompt"): "system_prompt", ("system", "customInstructions"): "custom_instructions",
         ("system", "toolDefinitions"): "built_in_tools"}  # fmt: skip
TAKEN = {"skill": "skills", "subagent": "subagents"}
BOUND = 10.0  # seconds one read may take


@dataclass(frozen=True)
class Context:
    """One measurement: the window, the total and the seven parts, or unmeasured with its error."""

    measured: bool
    window: int = 0
    total: int = 0
    parts: dict[str, int] = field(default_factory=dict)
    kept: str = ""  # which kinds stayed in their category, and why; empty when none did
    error: str = ""

    def fields(self) -> dict[str, Any]:
        """The measurement as a ledger line's fields (``spend_ledger.context``)."""
        if not self.measured:
            return {"measured": False, "error": self.error}
        return {"measured": True, "window": self.window, "total": self.total, "parts": self.parts, "kept": self.kept}


class Start:
    """One session's measurement after its first model call, written as its own ledger line (``spend_ledger.context``).

    *tasks* is the session's set of outstanding requests, when its teardown cancels them; one whose teardown does not
    calls ``ended``.
    """

    def __init__(  # noqa: PLR0913 - the run, what ran and where
        self, run: str, *, agent: str, model: str, context: str, place: spend_ledger.Where,
        tasks: set[asyncio.Task[None]] | None = None,
    ) -> None:  # fmt: skip
        self.run, self.agent, self.model, self.place, self.tasks = run, agent, model, place, tasks
        self.tier = "long" if context == "long" else "default"
        self.session: Any = None
        self.sid = ""
        self.task: asyncio.Task[None] | None = None

    def opened(self, session: Any, sid: str) -> None:  # noqa: ANN401 - the SDK session
        """The session to read, once it exists."""
        self.session, self.sid = session, sid

    def seen(self, kind: str, ev: Any) -> None:  # noqa: ANN401 - an SDK session event, on the session's loop
        """Start the read at the session's first main-agent model call; a subagent's call is not its own."""
        if kind != "assistant.usage" or self.task is not None or self.session is None:
            return
        if getattr(getattr(ev, "data", None), "parent_tool_call_id", None):
            return
        self.task = asyncio.get_running_loop().create_task(self._read())
        if self.tasks is not None:
            self.tasks.add(self.task)
            self.task.add_done_callback(self.tasks.discard)

    async def ended(self) -> None:
        """At teardown: let a read still running finish within its bound, then cancel it."""
        if self.task is not None and not self.task.done():
            await asyncio.wait({self.task}, timeout=BOUND)
            self.task.cancel()

    async def _read(self) -> None:
        try:
            async with asyncio.timeout(BOUND):
                answer = await self.session.rpc.metadata.get_context_attribution()
            found = mapped(answer.context_attribution)
        except asyncio.CancelledError:
            self._write(Context(measured=False, error="the session ended before its context attribution answered"))
            raise
        except TimeoutError:
            found = Context(measured=False, error=f"the context attribution did not answer within {BOUND:g} s")
        except Exception as exc:  # noqa: BLE001 - any failed read is recorded whole; the session goes on
            found = Context(measured=False, error=rpc_failure(exc))
        self._write(found)

    def _write(self, found: Context) -> None:
        spend_ledger.context(self.run, self.sid, agent=self.agent, model=self.model, tier=self.tier,
                             measurement=found.fields(), place=self.place)  # fmt: skip


def mapped(attribution: SessionContextAttribution | None) -> Context:
    """The seven parts of *attribution*; unmeasured when it is missing or its shape changed."""
    if attribution is None:
        return Context(measured=False, error="no context attribution")
    try:
        return _mapped(attribution)
    except (AttributeError, KeyError, TypeError, ValueError) as exc:
        return Context(measured=False, error=f"context attribution changed shape: {type(exc).__name__}: {exc}")


def _mapped(attribution: SessionContextAttribution) -> Context:
    parts = {p: int(getattr(attribution.categories, c)) for p, c in CATEGORIES.items()}
    total = int(attribution.total_tokens)
    if any(v < 0 for v in parts.values()) or sum(parts.values()) != total:
        msg = f"categories {parts} do not add up to totalTokens {total}"
        raise ValueError(msg)
    entries = {e.id: e for e in attribution.entries}
    taken = dict.fromkeys(TAKEN.values(), 0)
    kept = []
    for kind, part in TAKEN.items():
        tops = [e for e in entries.values() if e.kind == kind and not _nested(e, entries)]
        found = [(_bucket(e, entries), int(e.tokens)) for e in tops]
        need = {b: sum(t for x, t in found if x == b) for b, _ in found}
        held = sum(t for _, t in found)
        if None in need:
            kept.append(f"{part}: {held} tokens stay in their category, which nesting does not name")
        elif any(parts[b] < t for b, t in need.items()):  # type: ignore[index]
            kept.append(f"{part}: {held} tokens stay in their category, which holds fewer")
        else:
            for b, t in need.items():
                parts[b] -= t  # type: ignore[index]
            taken[part] = sum(need.values())
    return Context(measured=True, window=int(attribution.limit), total=total,
                   parts={p: parts.get(p, taken.get(p, 0)) for p in PARTS}, kept="; ".join(kept))  # fmt: skip


def _chain(entry: Entry, entries: dict[str, Entry]) -> list[Entry]:
    """*entry*'s ancestors, nearest first; a cycle or a missing parent ends the chain."""
    out: list[Entry] = []
    seen = {entry.id}
    while entry.parent_id and (entry := entries.get(entry.parent_id)) and entry.id not in seen:  # type: ignore[assignment]
        seen.add(entry.id)
        out.append(entry)
    return out


def _nested(entry: Entry, entries: dict[str, Entry]) -> bool:
    """Whether a skill or subagent entry holds *entry*: its tokens are counted there already."""
    return any(e.kind in TAKEN for e in _chain(entry, entries))


def _bucket(entry: Entry, entries: dict[str, Entry]) -> str | None:
    """The part whose category holds *entry*, from its outermost ancestor; None when the nesting names none."""
    chain = _chain(entry, entries)
    root = chain[-1] if chain else entry
    if root.parent_id:  # a missing parent or a cycle: no outermost ancestor
        return None
    if root.kind == "mcpServer":
        return "mcp_tools"
    return ROOTS.get((root.kind, root.id))
