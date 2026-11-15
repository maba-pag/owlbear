"""What fills a session's context after its first model call, from the SDK's context attribution, in seven parts.

The attribution's five occupied categories (system prompt, custom instructions, built-in tools as ``systemTools``, MCP
tools, messages) add up to its ``totalTokens``. Skills and subagents are entries inside them: each ``skill`` and
``subagent`` entry is taken out of the category its ``parentId`` chain leads to, never found by its ``label``. When
that chain names no category, or a category holds fewer tokens than its entries, that kind stays in its category
and ``kept`` says so. A missing answer or a changed shape is unmeasured with its error, never an exception.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from copilot.generated.rpc import Entry, SessionContextAttribution

PARTS = ("system_prompt", "custom_instructions", "skills", "subagents", "built_in_tools", "mcp_tools", "messages")
CATEGORIES = {"system_prompt": "system_prompt", "custom_instructions": "custom_instructions",
              "built_in_tools": "system_tools", "mcp_tools": "mcp_tools", "messages": "messages"}  # fmt: skip
ROOTS = {("system", "systemPrompt"): "system_prompt", ("system", "customInstructions"): "custom_instructions",
         ("system", "toolDefinitions"): "built_in_tools"}  # fmt: skip
TAKEN = {"skill": "skills", "subagent": "subagents"}


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
        raise ValueError(f"categories {parts} do not add up to totalTokens {total}")
    entries = {e.id: e for e in attribution.entries}
    taken = dict.fromkeys(TAKEN.values(), 0)
    kept = []
    for kind, part in TAKEN.items():
        tops = [e for e in entries.values() if e.kind == kind and not _nested(e, entries)]
        found = [(_bucket(e, entries), int(e.tokens)) for e in tops]
        need = {b: sum(t for x, t in found if x == b) for b, _ in found}
        if None in need:
            kept.append(f"{part}: {sum(t for _, t in found)} tokens stay in their category, which nesting does not name")
        elif any(parts[b] < t for b, t in need.items()):  # type: ignore[index]
            kept.append(f"{part}: {sum(t for _, t in found)} tokens stay in their category, which holds fewer")
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
