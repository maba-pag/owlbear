"""Item 5 slice 3: the curator works across the shared repository's project folders, makes an entry global, and
reads its threshold (TD-292, TD-400)."""

import json
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest
from mcp.server.mcpserver.exceptions import ToolError
from owlbear_memory import MemoryCategory, MemoryEngine

from owlbear_memory_mcp import tools


def git(root: Path, *args: str) -> str:
    return subprocess.run(["git", *args], cwd=root, check=True, capture_output=True, text=True).stdout.strip()  # noqa: S603, S607


@pytest.fixture
def root(tmp_path: Path) -> Path:
    data = tmp_path / "data"
    data.mkdir()
    git(data, "init", "-q")
    git(data, "config", "user.name", "t")
    git(data, "config", "user.email", "t@t")
    for project in ("shop", "docs"):
        (data / project / "memory").mkdir(parents=True)
    return data


def bound(root: Path, project: str = "shop", *, shared: bool = True) -> SimpleNamespace:
    store = root / project / "memory"
    context = SimpleNamespace(
        engine=MemoryEngine(store), memory_dir=store, global_dir=root / "memory" if shared else None, global_engine=None
    )
    return SimpleNamespace(request_context=SimpleNamespace(lifespan_context=context))


def saved(folder: Path, title: str, *, curated: bool = False):
    engine = MemoryEngine(folder)
    entry = engine.save(
        title=title, content=f"{title}: what to know", categories=[MemoryCategory.PROCESS], confidence=0.8,
        source_agent="builder", scope_agents=[],
    )  # fmt: skip
    return engine.edit(entry.id, {"scope_agents": ["builder"]}, expected_revision=entry.revision) if curated else entry


@pytest.mark.asyncio
async def test_the_curator_works_on_another_project_folder_and_never_on_global_by_name(root: Path) -> None:
    pending = saved(root / "docs" / "memory", "Pin the runtime")
    ctx = bound(root)

    listed = await tools.list_memories(ctx, folder="docs")
    curated = await tools.curate_memory(
        ctx, entry_id=pending.id, revision=pending.revision, scope_agents=["builder"], folder="docs"
    )

    assert [e["id"] for e in listed] == [pending.id]
    assert (curated["state"], MemoryEngine(root / "docs" / "memory").get_entry(pending.id).state) == (
        "curated", "curated"
    )  # fmt: skip
    assert await tools.list_memories(ctx) == []  # its own folder is untouched
    for wrong in ("memory", "../docs", "nowhere"):
        with pytest.raises(ToolError):
            await tools.list_memories(ctx, folder=wrong)
    with pytest.raises(ToolError, match="no shared repository"):
        await tools.list_memories(bound(root, shared=False), folder="docs")


@pytest.mark.asyncio
async def test_make_global_records_the_project_and_commits_both_paths(root: Path) -> None:
    entry, pending = (
        saved(root / "docs" / "memory", "Pin the runtime", curated=True),
        saved(root / "docs" / "memory", "x"),
    )
    git(root, "add", "-A")
    git(root, "commit", "-qm", "seed")
    ctx = bound(root)

    with pytest.raises(ToolError, match="changed since"):
        await tools.make_global(ctx, entry_id=entry.id, revision="0" * 16, folder="docs")
    with pytest.raises(ToolError, match="curate it"):
        await tools.make_global(ctx, entry_id=pending.id, revision=pending.revision, folder="docs")
    moved = await tools.make_global(ctx, entry_id=entry.id, revision=entry.revision, folder="docs")

    assert (moved["origin"], moved["commit_sha"]) == ("docs", git(root, "rev-parse", "HEAD"))
    assert git(root, "log", "-1", "--format=%s") == "memory docs: make global Pin the runtime"
    assert sorted(git(root, "show", "--no-renames", "--name-only", "--format=", "HEAD").splitlines()) == sorted(
        [f"docs/memory/{entry.id}.md", f"memory/{entry.id}.md"]
    )  # fmt: skip
    assert git(root, "status", "--porcelain") == ""  # exactly the move, nothing left over
    assert MemoryEngine(root / "memory").get_entry(entry.id).origin == "docs"
    read = await tools.read_memory(ctx, entry_id=entry.id)  # Global is read beside the own folder
    assert read["origin"] == "docs"


@pytest.mark.asyncio
async def test_the_threshold_is_the_global_settings_value_else_95(root: Path) -> None:
    ctx = bound(root)
    assert await tools.curation_threshold(ctx) == {"threshold": 95, "source": "default"}
    (root / "config.json").write_text(json.dumps({"format": 2, "curator_threshold": 90}))
    assert await tools.curation_threshold(ctx) == {"threshold": 90, "source": "global"}
    (root / "config.json").write_text(json.dumps({"format": 2, "curator_threshold": 30}))
    assert await tools.curation_threshold(ctx) == {"threshold": 95, "source": "default"}
    assert await tools.curation_threshold(bound(root, shared=False)) == {"threshold": 95, "source": "default"}


@pytest.mark.asyncio
async def test_a_folder_that_links_to_global_or_outside_the_repository_is_refused(root: Path, tmp_path: Path) -> None:
    (root / "memory").mkdir()
    (root / "alias").mkdir()
    (root / "alias" / "memory").symlink_to(root / "memory")
    (tmp_path / "elsewhere" / "memory").mkdir(parents=True)
    (root / "outside").symlink_to(tmp_path / "elsewhere")
    ctx = bound(root)

    for folder in ("alias", "outside"):
        with pytest.raises(ToolError, match="no memory folder"):
            await tools.list_memories(ctx, folder=folder)


@pytest.mark.asyncio
async def test_a_make_global_whose_commit_fails_leaves_the_entry_where_it_was_and_can_be_tried_again(
    root: Path,
) -> None:
    folder = root / "docs" / "memory"
    entry = saved(folder, "Pin the runtime", curated=True)
    git(root, "add", "-A")
    git(root, "commit", "-qm", "seed")
    ctx = bound(root)
    (root / ".git" / "hooks" / "pre-commit").write_text("#!/bin/sh\nexit 1\n")
    (root / ".git" / "hooks" / "pre-commit").chmod(0o755)

    with pytest.raises(ToolError, match="stays in docs"):
        await tools.make_global(ctx, entry_id=entry.id, revision=entry.revision, folder="docs")
    assert (git(root, "status", "--porcelain"), MemoryEngine(folder).get_entry(entry.id).origin) == ("", None)

    (root / ".git" / "hooks" / "pre-commit").unlink()
    moved = await tools.make_global(ctx, entry_id=entry.id, revision=entry.revision, folder="docs")
    assert (moved["origin"], git(root, "status", "--porcelain")) == ("docs", "")
