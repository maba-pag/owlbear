"""Item 5 slice 3: the curator works across the shared repository's project folders, makes an entry global, and
reads its threshold (TD-292, TD-400)."""

import json
import subprocess
from collections.abc import Callable
from pathlib import Path
from types import SimpleNamespace

import pytest
from mcp.server.mcpserver.exceptions import ToolError
from owlbear_memory import MemoryEngine, MemoryEntry, MemoryState, storage

from owlbear_memory_mcp import tools


def git(root: Path, *args: str) -> str:
    return subprocess.run(["git", *args], cwd=root, check=True, capture_output=True, text=True).stdout.strip()  # noqa: S603, S607


@pytest.fixture
def root(tmp_path: Path) -> Path:
    data = tmp_path / "data"
    data.mkdir()
    for project in ("shop", "docs"):
        (data / project / "memory").mkdir(parents=True)
    return data


@pytest.fixture
def git_repository(root: Path) -> None:
    git(root, "init", "-q")
    git(root, "config", "user.name", "t")
    git(root, "config", "user.email", "t@t")


@pytest.fixture
def ctx(root: Path, memory_context: Callable[..., SimpleNamespace]) -> SimpleNamespace:
    return memory_context(root / "shop" / "memory", global_dir=root / "memory")


@pytest.fixture
def saved(memory_entry: Callable[..., MemoryEntry]) -> Callable[..., MemoryEntry]:
    def seed(folder: Path, title: str, *, curated: bool = False) -> MemoryEntry:
        return memory_entry(
            folder,
            title,
            content=f"{title}: what to know",
            source_agent="builder",
            scope_agents=["builder"] if curated else [],
            state=MemoryState.CURATED if curated else MemoryState.PENDING,
        )

    return seed


@pytest.mark.asyncio
async def test_the_curator_works_on_another_project_folder_and_never_on_global_by_name(
    root: Path,
    saved: Callable[..., MemoryEntry],
    memory_context: Callable[..., SimpleNamespace],
) -> None:
    pending = saved(root / "docs" / "memory", "Pin the runtime")
    ctx = memory_context(root / "shop" / "memory", global_dir=root / "memory", agents=frozenset({"builder"}))

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
        await tools.list_memories(memory_context(root / "shop" / "memory"), folder="docs")


@pytest.mark.usefixtures("git_repository")
@pytest.mark.asyncio
async def test_make_global_records_the_project_and_commits_both_paths(
    root: Path,
    ctx: SimpleNamespace,
    saved: Callable[..., MemoryEntry],
) -> None:
    entry, pending = (
        saved(root / "docs" / "memory", "Pin the runtime", curated=True),
        saved(root / "docs" / "memory", "x"),
    )
    git(root, "add", "-A")
    git(root, "commit", "-qm", "seed")
    with pytest.raises(ToolError, match="changed since"):
        await tools.make_global(ctx, entry_id=entry.id, revision="0" * 16, folder="docs")
    with pytest.raises(ToolError, match="only a curated or approved entry"):
        await tools.make_global(ctx, entry_id=pending.id, revision=pending.revision, folder="docs")
    moved = await tools.make_global(ctx, entry_id=entry.id, revision=entry.revision, folder="docs")

    assert (moved["origin"], moved["commit_sha"]) == ("docs", git(root, "rev-parse", "HEAD"))
    assert git(root, "log", "-1", "--format=%s") == "chore: memory make global Pin the runtime from docs (memory-mcp)"
    assert sorted(git(root, "show", "--no-renames", "--name-only", "--format=", "HEAD").splitlines()) == sorted(
        [f"docs/memory/{entry.id}.md", f"memory/{entry.id}.md"]
    )  # fmt: skip
    assert git(root, "status", "--porcelain") == ""  # exactly the move, nothing left over
    assert MemoryEngine(root / "memory").get_entry(entry.id).origin == "docs"
    read = await tools.read_memory(ctx, entry_id=entry.id)  # Global is read beside the own folder
    assert read["origin"] == "docs"


@pytest.mark.asyncio
async def test_the_threshold_is_the_global_settings_value_else_unset(
    root: Path,
    ctx: SimpleNamespace,
    memory_context: Callable[..., SimpleNamespace],
) -> None:
    unset = {"threshold": None, "source": "unset", "error": tools.UNSET_THRESHOLD}
    assert await tools.curation_threshold(ctx) == unset
    (root / "config.json").write_text(json.dumps({"format": 2, "curator_threshold": 90}))
    assert await tools.curation_threshold(ctx) == {"threshold": 90, "source": "global"}
    (root / "config.json").write_text(json.dumps({"format": 2, "curator_threshold": 30}))
    assert await tools.curation_threshold(ctx) == unset
    assert await tools.curation_threshold(memory_context(root / "shop" / "memory")) == unset


@pytest.mark.asyncio
async def test_a_folder_that_links_to_global_or_outside_the_repository_is_refused(
    root: Path,
    tmp_path: Path,
    ctx: SimpleNamespace,
) -> None:
    (root / "memory").mkdir()
    (root / "alias").mkdir()
    (root / "alias" / "memory").symlink_to(root / "memory")
    (tmp_path / "elsewhere" / "memory").mkdir(parents=True)
    (root / "outside").symlink_to(tmp_path / "elsewhere")
    for folder in ("alias", "outside"):
        with pytest.raises(ToolError, match="no memory folder"):
            await tools.list_memories(ctx, folder=folder)


@pytest.mark.usefixtures("git_repository")
@pytest.mark.asyncio
async def test_make_global_refuses_while_deliverys_apply_of_a_curation_run_is_cut_short(
    root: Path,
    ctx: SimpleNamespace,
    saved: Callable[..., MemoryEntry],
) -> None:
    """#875: the cut-short set names its entries where they are; Delivery finishes it from its record by name."""
    entry = saved(root / "docs" / "memory", "Pin the runtime", curated=True)
    git(root, "add", "-A")
    git(root, "commit", "-qm", "seed")
    record = Path(git(root, "rev-parse", "--absolute-git-dir")) / "owlbear-curation-apply.json"
    record.write_text(json.dumps({"folder": "docs", "steps": {}}))

    with pytest.raises(ToolError, match=f"{entry.id} stays: the memory curation of docs was cut short"):
        await tools.make_global(ctx, entry_id=entry.id, revision=entry.revision, folder="docs")

    assert (root / "docs" / "memory" / f"{entry.id}.md").is_file()
    assert git(root, "status", "--porcelain") == ""


@pytest.mark.usefixtures("git_repository")
@pytest.mark.asyncio
async def test_a_make_global_whose_commit_fails_leaves_the_entry_where_it_was_and_can_be_tried_again(
    root: Path,
    ctx: SimpleNamespace,
    saved: Callable[..., MemoryEntry],
) -> None:
    folder = root / "docs" / "memory"
    entry = saved(folder, "Pin the runtime", curated=True)
    git(root, "add", "-A")
    git(root, "commit", "-qm", "seed")
    (root / ".git" / "hooks" / "pre-commit").write_text("#!/bin/sh\nexit 1\n")
    (root / ".git" / "hooks" / "pre-commit").chmod(0o755)

    with pytest.raises(ToolError, match="stays in docs"):
        await tools.make_global(ctx, entry_id=entry.id, revision=entry.revision, folder="docs")
    assert (git(root, "status", "--porcelain"), MemoryEngine(folder).get_entry(entry.id).origin) == ("", None)

    (root / ".git" / "hooks" / "pre-commit").unlink()
    moved = await tools.make_global(ctx, entry_id=entry.id, revision=entry.revision, folder="docs")
    assert (moved["origin"], git(root, "status", "--porcelain")) == ("docs", "")


@pytest.mark.usefixtures("git_repository")
@pytest.mark.asyncio
async def test_make_global_refuses_a_contested_entry_and_a_global_folder_that_links_elsewhere(
    root: Path,
    tmp_path: Path,
    ctx: SimpleNamespace,
    saved: Callable[..., MemoryEntry],
) -> None:
    """Copilot on #586: unresolved entries stay with the owner; a linked Global never takes an entry out."""
    folder = root / "docs" / "memory"
    entry = saved(folder, "Pin the runtime", curated=True)
    engine = MemoryEngine(folder)
    contested = engine.get_entry(entry.id).model_copy(update={"state": "contested"})
    storage.write_entry(folder / f"{entry.id}.md", contested, memory_dir=folder)
    with pytest.raises(ToolError, match="contested"):
        await tools.make_global(ctx, entry_id=entry.id, revision=contested.revision, folder="docs")
    other = saved(folder, "Sign commits", curated=True)
    (tmp_path / "elsewhere").mkdir()
    (root / "memory").rmdir()  # the refused move made it, empty
    (root / "memory").symlink_to(tmp_path / "elsewhere")
    with pytest.raises(ToolError, match="link out"):
        await tools.make_global(ctx, entry_id=other.id, revision=other.revision, folder="docs")
    assert {e.id for e in MemoryEngine(folder).get_entries()} == {entry.id, other.id}
