"""C-26: curate_memory gives an entry a named scope only for an agent its server knows or another reviewed entry names.

A pending entry's whole named scope is checked, also when the call omits it; a curated or approved entry's edit checks
only the names it adds. Pending and exceptional entries never vouch for a name, and neither does provenance.
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import NamedTuple

import pytest
from mcp.server.mcpserver.exceptions import ToolError
from owlbear_memory import MemoryCategory, MemoryEngine, MemoryEntry, MemoryState, storage

from owlbear_memory_mcp import tools


def _context(store: Path, *, shared: Path | None = None, agents: frozenset[str] = frozenset()) -> SimpleNamespace:
    context = SimpleNamespace(
        engine=MemoryEngine(store), memory_dir=store, global_dir=shared, global_engine=None, agents=agents
    )
    return SimpleNamespace(request_context=SimpleNamespace(lifespan_context=context))


def _entry(
    store: Path, title: str, *, scope: list[str], state: MemoryState = MemoryState.PENDING, source: str = "planner"
) -> MemoryEntry:
    """An entry seeded through the engine, never through curate_memory."""
    engine = MemoryEngine(store)
    entry = engine.save(
        title=title, content=f"{title}: what to know.", categories=[MemoryCategory.PROCESS], confidence=0.8,
        source_agent=source, scope_agents=[] if state != MemoryState.PENDING else scope,
    )  # fmt: skip
    if state == MemoryState.PENDING:
        return entry
    entry = engine.edit(entry.id, {"scope_agents": scope}, expected_revision=entry.revision)
    if state == MemoryState.CURATED:
        return entry
    entry = engine.approve(entry.id, expected_revision=entry.revision)
    if state == MemoryState.APPROVED:
        return entry
    exceptional = entry.model_copy(update={"state": state, "approved_at": None})
    storage.write_entry(store / f"{entry.id}.md", exceptional, memory_dir=store)
    return exceptional


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


def _target(store: Path, spec: list) -> MemoryEntry:
    """A pending entry with *spec* as its stored scope, or a reviewed one when *spec* ends with its state."""
    if spec and isinstance(spec[-1], MemoryState):
        return _entry(store, "Target", scope=list(spec[:-1]), state=spec[-1])
    return _entry(store, "Target", scope=list(spec))


@pytest.mark.parametrize("case", REFUSED.values(), ids=REFUSED.keys())
@pytest.mark.asyncio
async def test_a_named_scope_nothing_corroborates_is_refused_and_changes_nothing(tmp_path: Path, case: Refusal) -> None:
    store, shared = tmp_path / "data" / "shop" / "memory", tmp_path / "data" / "memory"
    entry = _target(store, case.target)
    for scope, state in case.witnesses:  # the witness wrote as builder, so provenance never vouches
        home = shared if case.where == "global" else store
        _entry(home, f"Witness {scope}", scope=[scope], state=state, source="builder")
    before = _bytes(store, entry)

    with pytest.raises(ToolError) as raised:
        await tools.curate_memory(
            _context(store, shared=shared), entry_id=entry.id, revision=entry.revision, **case.call
        )

    assert [name for name in ("builder", "buider", "ghost") if f"'{name}'" in str(raised.value)] == case.refused
    assert _bytes(store, entry) == before


PASSES = {
    "curated-witness": (None, MemoryState.CURATED, frozenset(), ["builder"]),
    "approved-global-witness": ("global", MemoryState.APPROVED, frozenset(), ["builder"]),
    "known-agent": (None, None, frozenset({"builder"}), ["builder"]),
    "everyone": (None, None, frozenset(), ["*"]),
}


@pytest.mark.parametrize(("where", "witness", "agents", "scope"), PASSES.values(), ids=PASSES.keys())
@pytest.mark.asyncio
async def test_a_named_scope_passes_with_a_known_agent_or_another_reviewed_entry(
    tmp_path: Path, where: str | None, witness: MemoryState | None, agents: frozenset[str], scope: list[str]
) -> None:
    store, shared = tmp_path / "data" / "shop" / "memory", tmp_path / "data" / "memory"
    entry = _entry(store, "Target", scope=[])
    if witness is not None:
        _entry(shared if where == "global" else store, "Witness", scope=["builder"], state=witness)

    curated = await tools.curate_memory(
        _context(store, shared=shared, agents=agents), entry_id=entry.id, revision=entry.revision, scope_agents=scope
    )

    assert (curated["state"], curated["scope_agents"]) == ("curated", scope)


@pytest.mark.asyncio
async def test_a_reviewed_entry_keeps_its_names_when_an_edit_adds_none(tmp_path: Path) -> None:
    store = tmp_path / "memory"
    entry = _entry(store, "Old lesson", scope=["ghost"], state=MemoryState.CURATED)

    edited = await tools.curate_memory(_context(store), entry_id=entry.id, revision=entry.revision, content="Sharper.")
    rescoped = await tools.curate_memory(
        _context(store), entry_id=entry.id, revision=edited["revision"], scope_agents=["ghost"]
    )

    assert (edited["content"], rescoped["scope_agents"]) == ("Sharper.", ["ghost"])
