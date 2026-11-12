"""C-26: curate_memory gives an entry a named scope only for an agent its server knows or another reviewed entry names.

A pending entry's whole named scope is checked, also when the call omits it; a curated or approved entry's edit checks
only the names it adds. Pending and exceptional entries never vouch for a name, and neither does provenance.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from types import SimpleNamespace
from typing import NamedTuple

import pytest
from mcp.server.mcpserver.exceptions import ToolError
from owlbear_memory import MemoryEntry, MemoryState

from owlbear_memory_mcp import tools


def _bytes(store: Path, entry: MemoryEntry) -> bytes:
    return (store / f"{entry.id}.md").read_bytes()


class Refusal(NamedTuple):
    target: list  # the target's stored scope, ending with its state when it is reviewed rather than pending
    witnesses: list[tuple[str, MemoryState]]  # other entries, written as builder: (scoped agent, state)
    call: dict
    refused: list[str]
    where: str | None = None  # "global" puts the witnesses in Global memory


B, CUR, APP = "builder", MemoryState.CURATED, MemoryState.APPROVED
REFUSED = {
    "uncorroborated": Refusal([], [], {"scope_agents": [B]}, [B]),
    "pending-witness": Refusal([], [(B, MemoryState.PENDING)], {"scope_agents": [B]}, [B]),
    "own-stored-scope": Refusal([B], [], {"scope_agents": [B]}, [B]),
    "own-stored-scope-omitted": Refusal([B], [], {"content": "Sharper."}, [B]),
    "provenance-only": Refusal([], [("reviewer", CUR)], {"scope_agents": [B, "*"]}, [B]),
    "contested-global": Refusal([], [(B, MemoryState.CONTESTED)], {"scope_agents": [B]}, [B], where="global"),
    "one-misspelt": Refusal([], [(B, APP)], {"scope_agents": [B, "buider"]}, ["buider"]),
    "curated-gains-unknown": Refusal([B, CUR], [(B, APP)], {"scope_agents": [B, "ghost"]}, ["ghost"]),
    "approved-gains-unknown": Refusal([B, APP], [(B, APP)], {"scope_agents": [B, "ghost"]}, ["ghost"]),
}


@pytest.mark.parametrize("case", REFUSED.values(), ids=REFUSED.keys())
@pytest.mark.asyncio
async def test_a_named_scope_nothing_corroborates_is_refused_and_changes_nothing(
    tmp_path: Path,
    case: Refusal,
    memory_entry: Callable[..., MemoryEntry],
    memory_context: Callable[..., SimpleNamespace],
) -> None:
    store, shared = tmp_path / "data" / "shop" / "memory", tmp_path / "data" / "memory"
    reviewed = bool(case.target and isinstance(case.target[-1], MemoryState))
    entry = memory_entry(
        store,
        "Target",
        content="Target: what to know.",
        source_agent="planner",
        scope_agents=list(case.target[:-1] if reviewed else case.target),
        state=case.target[-1] if reviewed else MemoryState.PENDING,
    )
    for scope, state in case.witnesses:  # the witness wrote as builder, so provenance never vouches
        home = shared if case.where == "global" else store
        memory_entry(
            home,
            f"Witness {scope}",
            content=f"Witness {scope}: what to know.",
            scope_agents=[scope],
            state=state,
            source_agent="builder",
        )
    before = _bytes(store, entry)

    with pytest.raises(ToolError) as raised:
        await tools.curate_memory(
            memory_context(store, global_dir=shared), entry_id=entry.id, revision=entry.revision, **case.call
        )

    assert [name for name in ("builder", "buider", "ghost") if f"'{name}'" in str(raised.value)] == case.refused
    assert _bytes(store, entry) == before


PASSES = {
    "curated-witness": (None, MemoryState.CURATED, frozenset(), ["builder"]),
    "approved-global-witness": ("global", MemoryState.APPROVED, frozenset(), ["builder"]),
    "known-agent": (None, None, frozenset({"builder"}), ["builder"]),
    "everyone": (None, None, frozenset(), ["*"]),
}


@pytest.mark.parametrize("case", PASSES.values(), ids=PASSES.keys())
@pytest.mark.asyncio
async def test_a_named_scope_passes_with_a_known_agent_or_another_reviewed_entry(
    tmp_path: Path,
    case: tuple,
    memory_entry: Callable[..., MemoryEntry],
    memory_context: Callable[..., SimpleNamespace],
) -> None:
    where, witness, agents, scope = case
    store, shared = tmp_path / "data" / "shop" / "memory", tmp_path / "data" / "memory"
    entry = memory_entry(store, "Target", content="Target: what to know.", source_agent="planner")
    if witness is not None:
        memory_entry(
            shared if where == "global" else store,
            "Witness",
            content="Witness: what to know.",
            scope_agents=["builder"],
            state=witness,
            source_agent="planner",
        )

    curated = await tools.curate_memory(
        memory_context(store, global_dir=shared, agents=agents),
        entry_id=entry.id,
        revision=entry.revision,
        scope_agents=scope,
    )

    assert (curated["state"], curated["scope_agents"]) == ("curated", scope)


@pytest.mark.asyncio
async def test_a_reviewed_entry_keeps_its_names_when_an_edit_adds_none(
    tmp_path: Path,
    memory_entry: Callable[..., MemoryEntry],
    memory_context: Callable[..., SimpleNamespace],
) -> None:
    store = tmp_path / "memory"
    entry = memory_entry(
        store,
        "Old lesson",
        content="Old lesson: what to know.",
        scope_agents=["ghost"],
        state=MemoryState.CURATED,
        source_agent="planner",
    )

    ctx = memory_context(store)
    edited = await tools.curate_memory(ctx, entry_id=entry.id, revision=entry.revision, content="Sharper.")
    rescoped = await tools.curate_memory(ctx, entry_id=entry.id, revision=edited["revision"], scope_agents=["ghost"])

    assert (edited["content"], rescoped["scope_agents"]) == ("Sharper.", ["ghost"])
