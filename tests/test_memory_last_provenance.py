"""Maintenance tells the curator's own commits from the owner's memory actions (N1, PR #822)."""

from __future__ import annotations

import subprocess
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace

import pytest
from owlbear_memory import MemoryCategory, MemoryEngine

from owlbear_delivery_next.project_host import pack_routes
from owlbear_delivery_next.state_store import curation_runs
from owlbear_memory_mcp import tools


def git(root: Path, *args: str) -> str:
    return subprocess.run(["git", *args], cwd=root, check=True, capture_output=True, text=True).stdout.strip()  # noqa: S603, S607


@pytest.mark.asyncio
async def test_a_curator_moving_an_entry_global_before_its_run_ends_leaves_the_run_shown(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Copilot's counterexample: make_global committed with the Memory page's subject, so a running curation read as
    the owner's finished action."""
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    root = tmp_path / "data"
    folder = root / "shop" / "memory"
    folder.mkdir(parents=True)
    git(root, "init", "-q")
    git(root, "config", "user.name", "t")
    git(root, "config", "user.email", "t@t")
    engine = MemoryEngine(folder)
    entry = engine.save(
        title="Pin the runtime", content="Pin the runtime: what to know", categories=[MemoryCategory.PROCESS],
        confidence=0.8, source_agent="builder", scope_agents=[],
    )  # fmt: skip
    entry = engine.edit(entry.id, {"scope_agents": ["builder"]}, expected_revision=entry.revision)
    git(root, "add", "-A")
    git(root, "commit", "-qm", "seed")
    started = datetime.now(UTC) - timedelta(minutes=1)
    state = Path.home() / ".owlbear" / curation_runs.STATE
    state.parent.mkdir(parents=True)
    runs = {"shop": curation_runs.FolderRun(state="running", started_at=started)}
    state.write_text(curation_runs.Runs(folders=runs).model_dump_json())
    context = SimpleNamespace(
        engine=engine, memory_dir=folder, global_dir=root / "memory", global_engine=None, agents=frozenset()
    )
    store = SimpleNamespace(
        name="shop", shared=SimpleNamespace(root=root, memory_path=lambda name: root / name / "memory")
    )

    await tools.make_global(
        SimpleNamespace(request_context=SimpleNamespace(lifespan_context=context)),
        entry_id=entry.id, revision=entry.revision,
    )  # fmt: skip

    assert git(root, "log", "-1", "--format=%s") != "seed"  # the move was committed
    assert pack_routes.owner_last(store) is None
    assert (pack_routes.memory_last(store) or {}).get("state") == "running"
