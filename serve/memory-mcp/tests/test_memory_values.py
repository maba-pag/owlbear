"""The memory tools take the owner's memory values from the global settings at each request, never from code."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest
from mcp.server.mcpserver.exceptions import ToolError
from owlbear_memory import MemoryEngine, MemoryEntry, MemoryState, storage

from owlbear_memory_mcp import tools

_TS = "2026-10-01T10:00:00+00:00"
_VALUES = {
    "outstanding_boost": 0.1,
    "unremarkable_penalty": 0.01,
    "stale_factor": 50,
    "recall_limit": 20,
    "explore_slots": 2,
    "challenge_slots": 2,
}


def git(root: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=root, check=True, capture_output=True)  # noqa: S603, S607


@pytest.fixture
def root(tmp_path: Path) -> Path:
    data = tmp_path / "data"
    (data / "shop" / "memory").mkdir(parents=True)
    git(data, "init", "-q")
    return data


@pytest.fixture
def store(root: Path) -> Path:
    return root / "shop" / "memory"


def bound(root: Path) -> SimpleNamespace:
    folder = root / "shop" / "memory"
    context = SimpleNamespace(
        engine=MemoryEngine(folder),
        memory_dir=folder,
        global_dir=root / "memory",
        global_engine=None,
        agents=frozenset(),
    )
    return SimpleNamespace(request_context=SimpleNamespace(lifespan_context=context))


def hold(root: Path, **values: object) -> None:
    (root / "config.json").write_text(json.dumps({"format": 21, "memory": values}), encoding="utf-8")


def seed(folder: Path, n: int, title: str, **fields: object) -> MemoryEntry:
    state = fields.get("state", "approved")
    entry = MemoryEntry(
        **{
            "id": f"550e8400-e29b-41d4-a716-4466554{n:05d}",
            "title": title,
            "content": f"{title}: what to know.",
            "categories": ["process"],
            "confidence": 0.8,
            "state": state,
            "score": 0.8,
            "scope_agents": ["builder"],
            "source_agent": "builder",
            "created_at": _TS,
            "updated_at": _TS,
            "approved_at": _TS if state == "approved" else None,
        }
        | fields
    )
    storage.write_entry(folder / f"{entry.id}.md", entry, memory_dir=folder)
    return entry


def titles(recalled: str) -> list[str]:
    return [line[3:] for line in recalled.splitlines() if line.startswith("## ")]


def snapshot(folder: Path) -> dict[str, bytes]:
    return {path.name: path.read_bytes() for path in sorted(folder.glob("*.md"))}


@pytest.mark.asyncio
async def test_recall_refuses_naming_the_values_the_settings_do_not_hold(root: Path, store: Path) -> None:
    seed(store, 1, "one")
    ctx = bound(root)

    with pytest.raises(ToolError, match="outstanding_boost, unremarkable_penalty, explore_slots, challenge_slots"):
        await tools.recall_memory(ctx, agent="builder", limit=5)

    hold(root, **{k: v for k, v in _VALUES.items() if k != "recall_limit"})
    assert titles(await tools.recall_memory(ctx, agent="builder", limit=5)) == ["one"]  # a limit asked for needs none
    with pytest.raises(ToolError, match="recall_limit"):
        await tools.recall_memory(ctx, agent="builder")


@pytest.mark.asyncio
@pytest.mark.parametrize("text", ["<<<<<<< ours\n{}\n=======\n{}\n>>>>>>> theirs", ""], ids=["conflict", "empty"])
async def test_settings_that_cannot_be_read_are_refused_with_the_file_and_the_reason_not_as_unset(
    root: Path, store: Path, text: str
) -> None:
    seed(store, 1, "one")
    (root / "config.json").write_text(text)

    with pytest.raises(ToolError, match="can't be read") as refused:
        await tools.recall_memory(bound(root), agent="builder", limit=5)
    assert str(root / "config.json") in str(refused.value)
    assert "unset" not in str(refused.value)  # a broken file is not an unset value


@pytest.mark.asyncio
async def test_assessing_refuses_without_the_stale_factor_but_a_wrong_report_needs_none(
    root: Path, store: Path
) -> None:
    entry = seed(store, 1, "one")
    ctx, before = bound(root), snapshot(store)
    rated = [{"entry_id": entry.id, "revision": entry.revision, "bucket": "outstanding"}]

    with pytest.raises(ToolError, match="stale_factor"):
        await tools.assess_memories(ctx, assessments=rated, task_id="task-a")
    assert snapshot(store) == before

    wrong = [{"entry_id": entry.id, "revision": entry.revision, "bucket": "factually_wrong"}]
    result = await tools.assess_memories(ctx, assessments=wrong, task_id="task-b")
    assert result["results"][0]["success"] is True


@pytest.mark.asyncio
async def test_a_changed_setting_applies_to_the_next_request_of_the_same_server(root: Path, store: Path) -> None:
    for n in (1, 2, 3):
        seed(store, n, f"entry {n}")
    ctx = bound(root)  # one lifespan: the server never restarts between the two settings

    hold(root, **_VALUES | {"recall_limit": 1, "explore_slots": 0, "challenge_slots": 0, "stale_factor": 100})
    assert len(titles(await tools.recall_memory(ctx, agent="builder"))) == 1
    first = MemoryEngine(store).get_entry(seed(store, 6, "to rate", didnt_use_count=5).id)
    await tools.assess_memories(
        ctx,
        assessments=[{"entry_id": first.id, "revision": first.revision, "bucket": "didnt_use"}],
        task_id="task-a",
    )
    assert MemoryEngine(store).get_entry(first.id).state == MemoryState.APPROVED

    hold(root, **_VALUES | {"recall_limit": 3, "explore_slots": 0, "challenge_slots": 0, "stale_factor": 5})
    assert len(titles(await tools.recall_memory(ctx, agent="builder"))) == 3
    second = MemoryEngine(store).get_entry(seed(store, 7, "to rate again", didnt_use_count=5).id)
    await tools.assess_memories(
        ctx,
        assessments=[{"entry_id": second.id, "revision": second.revision, "bucket": "didnt_use"}],
        task_id="task-a",
    )
    assert MemoryEngine(store).get_entry(second.id).state == MemoryState.STALE


def fixed(folder: Path) -> None:
    """Two entries recall always takes for its explore slots and two for its challenge slots."""
    seed(folder, 1, "explore one")
    seed(folder, 2, "explore two")
    seed(folder, 3, "challenge one", didnt_use_count=3)
    seed(folder, 4, "challenge two", didnt_use_count=3)


def competing(folder: Path, kind: str) -> None:
    """Two regular candidates whose order the points decide, with stored scores that say the opposite."""
    if kind == "boost":  # a leads when a boost is worth more than 0.2
        seed(folder, 5, "regular a", confidence=0.8, score=9.0, outstanding_count=2)
        seed(folder, 6, "regular b", confidence=1.0, score=0.1, outstanding_count=1)
    else:  # a leads when a penalty is worth less than 0.02
        seed(folder, 5, "regular a", confidence=0.8, score=0.1, outstanding_count=1, unremarkable_count=5)
        seed(folder, 6, "regular b", confidence=0.7, score=9.0, outstanding_count=1)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("kind", "points", "winner"),
    [
        pytest.param("boost", {"outstanding_boost": 0.1}, "regular b", id="small-boost"),
        pytest.param("boost", {"outstanding_boost": 0.3}, "regular a", id="large-boost"),
        pytest.param("penalty", {"unremarkable_penalty": 0.01}, "regular a", id="small-penalty"),
        pytest.param("penalty", {"unremarkable_penalty": 0.05}, "regular b", id="large-penalty"),
    ],
)
async def test_recall_ranks_by_the_current_points_and_never_by_the_stored_score(
    root: Path, store: Path, kind: str, points: dict[str, float], winner: str
) -> None:
    loser = ({"regular a", "regular b"} - {winner}).pop()
    fixed(store)
    competing(store, kind)
    hold(root, **_VALUES | points)
    ctx, before = bound(root), snapshot(store)

    one_regular_slot = titles(await tools.recall_memory(ctx, agent="builder", limit=5))
    assert (winner in one_regular_slot, loser in one_regular_slot) == (True, False)  # regular pool membership

    every_slot = titles(await tools.recall_memory(ctx, agent="builder", limit=6))
    assert every_slot.index(winner) < every_slot.index(loser)  # the final order
    assert snapshot(store) == before  # a recall writes nothing


@pytest.mark.asyncio
async def test_the_slots_come_from_the_settings(root: Path, store: Path) -> None:
    fixed(store)
    competing(store, "boost")
    ctx = bound(root)

    hold(root, **_VALUES | {"explore_slots": 0, "challenge_slots": 0})
    plain = titles(await tools.recall_memory(ctx, agent="builder", limit=3))
    assert len(plain) == 3
    assert "explore two" not in plain  # ranked by score alone, it is not among the best three
    hold(root, **_VALUES | {"explore_slots": 0, "challenge_slots": 2})  # only the challenge slots changed
    challenged = titles(await tools.recall_memory(ctx, agent="builder", limit=3))
    assert len(challenged) == 3
    assert {"explore one", "explore two"} <= set(challenged)  # the two entries rated outstanding least
    hold(root, **_VALUES | {"explore_slots": 4, "challenge_slots": 0})
    explored = titles(await tools.recall_memory(ctx, agent="builder", limit=4))
    assert {"explore one", "explore two"} <= set(explored)
    assert len(explored) == 4


@pytest.mark.asyncio
async def test_writers_need_no_points_and_leave_the_stored_score_alone(root: Path, store: Path) -> None:
    rated, curated = seed(store, 1, "rated", score=0.3), seed(store, 2, "curated", state="curated", score=0.3)
    hold(root, stale_factor=50)  # no points held: nothing that writes may need them
    ctx = bound(root)

    await tools.assess_memories(
        ctx,
        assessments=[{"entry_id": rated.id, "revision": rated.revision, "bucket": "outstanding"}],
        task_id="task-a",
    )
    await tools.curate_memory(ctx, entry_id=curated.id, revision=curated.revision, confidence=0.9)

    engine = MemoryEngine(store)
    assert (engine.get_entry(rated.id).outstanding_count, engine.get_entry(rated.id).score) == (1, 0.3)
    assert (engine.get_entry(curated.id).confidence, engine.get_entry(curated.id).score) == (0.9, 0.3)


@pytest.mark.asyncio
async def test_a_projection_carries_no_stored_score(root: Path, store: Path) -> None:
    entry = seed(store, 1, "listed", score=0.3)
    ctx = bound(root)

    assert "score" not in await tools.read_memory(ctx, entry_id=entry.id)
    assert all("score" not in item for item in await tools.list_memories(ctx))
