"""Cockpit startup through the canonical Delivery loader: format gate and controller lock (N02-A)."""

from __future__ import annotations

import builtins
import io
import json
import os
import subprocess
from typing import TYPE_CHECKING, Any

import pytest

import owlbear_delivery_mcp.server as live_server
from owlbear_cockpit.target_context import load_target_context
from owlbear_delivery import PortfolioApplication, close_delivery_application
from owlbear_delivery.git_executable import resolve_git_executable
from owlbear_delivery.state_formats import record_tree_digest
from owlbear_delivery.storage_io import ControllerFencedError, acquire_controller_lock

if TYPE_CHECKING:
    from pathlib import Path

_GIT = resolve_git_executable()
_CONFIG = {
    "schema_version": 2,
    "remote": "origin",
    "target_branch": "main",
    "github_repository": "example/project",
}


def _git(repository: Path, *arguments: str) -> None:
    subprocess.run((_GIT, "-C", str(repository), *arguments), check=True, capture_output=True)  # noqa: S603


def _workspace(tmp_path: Path, config: dict[str, object] = _CONFIG) -> Path:
    repository = tmp_path / "repository"
    repository.mkdir()
    _git(repository, "init", "-b", "main")
    _git(repository, "config", "user.name", "Cockpit Startup Test")
    _git(repository, "config", "user.email", "cockpit-startup@example.invalid")
    (repository / "product.txt").write_text("baseline\n", encoding="utf-8")
    _git(repository, "add", "product.txt")
    _git(repository, "commit", "-m", "baseline")
    _git(repository, "remote", "add", "origin", "https://github.com/example/project.git")
    _git(repository, "update-ref", "refs/remotes/origin/main", "HEAD")
    config_path = repository / ".owlbear/delivery/config.json"
    config_path.parent.mkdir(parents=True)
    config_path.write_text(json.dumps(config), encoding="utf-8")
    return repository


def test_cockpit_refuses_a_newer_config_before_its_typed_parse(tmp_path: Path) -> None:
    repository = _workspace(tmp_path, {**_CONFIG, "schema_version": 3, "future_field": True})

    with pytest.raises(RuntimeError, match="state_version: state-newer-than-controller") as refusal:
        load_target_context(repository)

    assert "config.json" in str(refusal.value)


def test_cockpit_refuses_newer_state_with_the_typed_loader_detail(tmp_path: Path) -> None:
    repository = _workspace(tmp_path)
    issuer = repository / ".owlbear/delivery/runtime/changes/change-a/claim-issuers/attempt-1.json"
    issuer.parent.mkdir(parents=True)
    issuer.write_text('{"schema_version": 2, "window": null}', encoding="utf-8")
    digests = record_tree_digest(repository)

    with pytest.raises(RuntimeError, match="state_version: state-newer-than-controller"):
        load_target_context(repository)

    assert record_tree_digest(repository) == digests


def test_cockpit_is_fenced_by_an_exclusive_controller_lock_holder(tmp_path: Path) -> None:
    repository = _workspace(tmp_path)
    holder = acquire_controller_lock(repository / ".owlbear/delivery/runtime", exclusive=True)
    try:
        with pytest.raises(RuntimeError, match="controller_lock: controller-fenced"):
            load_target_context(repository)
    finally:
        holder.release()


def test_cockpit_from_checkout_code_refuses_a_pinned_workspace(tmp_path: Path) -> None:
    repository = _workspace(tmp_path)
    pin = repository / ".owlbear/controller/pin.json"
    pin.parent.mkdir(parents=True)
    pin.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "commit": "a" * 40,
                "previous": None,
                "release_sha256": "f" * 64,
            }
        ),
        encoding="utf-8",
    )
    digests = record_tree_digest(repository)

    with pytest.raises(RuntimeError, match="state_version: controller-not-pinned"):
        load_target_context(repository)

    assert record_tree_digest(repository) == digests
    acquire_controller_lock(repository / ".owlbear/delivery/runtime", exclusive=True).release()


@pytest.mark.parametrize("state", ["backed-up", "applying", "applied", "aborting"])
def test_cockpit_refuses_a_migration_journal_that_is_not_verified(tmp_path: Path, state: str) -> None:
    repository = _workspace(tmp_path)
    migration_id = "b" * 64
    journal = repository / ".owlbear/delivery/runtime/migrations" / migration_id / "journal.json"
    journal.parent.mkdir(parents=True)
    journal.write_text(json.dumps({"schema_version": 1, "migration_id": migration_id, "state": state}), "utf-8")
    (repository / ".owlbear/delivery/runtime/format.json").write_text('{"format":1}\n', encoding="utf-8")
    digests = record_tree_digest(repository)

    with pytest.raises(RuntimeError, match="state_version: state-migration-incomplete"):
        load_target_context(repository)

    assert record_tree_digest(repository) == digests


@pytest.mark.parametrize(
    "content",
    [json.dumps({**_CONFIG, "schema_version": 3, "future_field": True}), '{"schema_version": 2, "remote": '],
    ids=["newer", "malformed"],
)
def test_cockpit_fence_wins_before_the_configuration_is_opened(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, content: str
) -> None:
    repository = _workspace(tmp_path)
    (repository / ".owlbear/delivery/config.json").write_text(content, encoding="utf-8")
    holder = acquire_controller_lock(repository / ".owlbear/delivery/runtime", exclusive=True)
    opened: list[str] = []
    for module, name in ((os, "open"), (io, "open"), (builtins, "open")):
        original = getattr(module, name)

        def spy(path: object, *args: object, _original: Any = original, **kwargs: object) -> object:
            if isinstance(path, str | os.PathLike) and os.fspath(path).endswith("config.json"):
                opened.append(os.fspath(path))
            return _original(path, *args, **kwargs)

        monkeypatch.setattr(module, name, spy)
    try:
        with pytest.raises(RuntimeError, match="controller_lock: controller-fenced"):
            load_target_context(repository)
    finally:
        monkeypatch.undo()
        holder.release()

    assert opened == []


@pytest.mark.asyncio
async def test_mcp_and_cockpit_start_together_on_one_portfolio_sharing_the_lock(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository = _workspace(tmp_path)
    runtime_root = repository / ".owlbear/delivery/runtime"
    monkeypatch.chdir(repository)

    async with live_server.app_lifespan(live_server.mcp) as context:
        cockpit = load_target_context(repository)
        assert isinstance(context.application, PortfolioApplication)
        assert isinstance(cockpit, PortfolioApplication)
        assert cockpit.list_work_items() == context.application.list_work_items() == ()
        with pytest.raises(ControllerFencedError):
            acquire_controller_lock(runtime_root, exclusive=True)
        close_delivery_application(cockpit)
        with pytest.raises(ControllerFencedError):
            acquire_controller_lock(runtime_root, exclusive=True)

    acquire_controller_lock(runtime_root, exclusive=True).release()
