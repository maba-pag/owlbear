"""How a chat's memory server finds its folders in the shared data repository (TD-72, TD-241)."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from owlbear_memory_mcp.server import global_dir, memory_dir
from owlbear_memory_mcp.store import StoreError, identity, shared_stores


def _workspace(path: Path, origin: str | None = None) -> Path:
    path.mkdir(parents=True)
    subprocess.run(["git", "init", "-q"], cwd=path, check=True)  # noqa: S607
    if origin:
        subprocess.run(["git", "remote", "add", "origin", origin], cwd=path, check=True)  # noqa: S603, S607
    return path


def _claim(data: Path, folder: str, who: str) -> None:
    if not (data / ".git").exists():
        _workspace(data)
    (data / folder).mkdir(parents=True, exist_ok=True)
    (data / folder / "repository").write_text(who + "\n", encoding="utf-8")


@pytest.mark.parametrize(
    "origin",
    ["https://github.com/acme/shop.git", "https://me@github.com/acme/shop", "git@github.com:acme/shop.git"],
)
def test_identity_is_the_origin_as_delivery_names_it(tmp_path: Path, origin: str) -> None:
    assert identity(_workspace(tmp_path / "shop", origin)) == "github.com/acme/shop"


def test_identity_without_origin_is_the_main_checkout(tmp_path: Path) -> None:
    work = _workspace(tmp_path / "shop")
    assert identity(work) == str(work.resolve())


def test_the_claimed_folder_holds_the_memory_and_the_root_global_memory(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    data, work = tmp_path / "data", _workspace(tmp_path / "work", "git@github.com:acme/shop.git")
    _claim(data, "store", "github.com/acme/shop")
    _claim(data, "other", "github.com/acme/other")
    monkeypatch.setenv("OWLBEAR_DATA", str(data))
    monkeypatch.chdir(work)

    assert shared_stores(work) == (data.resolve() / "store/memory", data.resolve() / "memory")
    assert (memory_dir(), global_dir()) == (data.resolve() / "store/memory", data.resolve() / "memory")


def test_the_machine_pointer_names_the_shared_repository(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    data, work = tmp_path / "data", _workspace(tmp_path / "work", "https://github.com/acme/shop.git")
    _claim(data, "shop", "github.com/acme/shop")
    (tmp_path / "home/.owlbear").mkdir(parents=True)
    (tmp_path / "home/.owlbear/data.json").write_text(json.dumps({"repository": str(data)}), encoding="utf-8")
    monkeypatch.delenv("OWLBEAR_DATA")
    monkeypatch.setenv("HOME", str(tmp_path / "home"))

    assert shared_stores(work) == (data.resolve() / "shop/memory", data.resolve() / "memory")


def test_an_unclaimed_workspace_keeps_its_own_memory(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    data, work = tmp_path / "data", _workspace(tmp_path / "work", "https://github.com/acme/shop.git")
    _claim(data, "other", "github.com/acme/other")
    (work / ".owlbear").mkdir()
    monkeypatch.setenv("OWLBEAR_DATA", str(data))
    monkeypatch.chdir(work)

    assert (memory_dir(), global_dir()) == (work.resolve() / ".owlbear/memory", None)


def test_delivery_named_folders_win_over_a_claim(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    data, work = tmp_path / "data", _workspace(tmp_path / "work", "https://github.com/acme/shop.git")
    _claim(data, "shop", "github.com/acme/shop")
    monkeypatch.setenv("OWLBEAR_DATA", str(data))
    monkeypatch.setenv("OWLBEAR_MEMORY_DIR", str(tmp_path / "named"))
    monkeypatch.chdir(work)

    assert (memory_dir(), global_dir()) == ((tmp_path / "named").resolve(), None)


@pytest.mark.parametrize(
    ("setup", "message"),
    [
        ("two claims", "all claim github.com/acme/shop"),
        ("missing folder", "no git repository's top folder"),
        ("plain folder", "no git repository's top folder"),
        ("broken pointer", "names no shared repository"),
    ],
)
def test_an_unusable_shared_repository_is_reported_not_bypassed(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, setup: str, message: str
) -> None:
    data, work = tmp_path / "data", _workspace(tmp_path / "work", "https://github.com/acme/shop.git")
    _claim(data, "shop", "github.com/acme/shop")
    monkeypatch.setenv("OWLBEAR_DATA", str(data))
    if setup == "two claims":
        _claim(data, "shop-copy", "github.com/acme/shop")
    elif setup == "missing folder":
        monkeypatch.setenv("OWLBEAR_DATA", str(tmp_path / "gone"))
    elif setup == "plain folder":
        monkeypatch.setenv("OWLBEAR_DATA", str(data / "shop"))  # inside the repository, not its top folder
    else:
        (tmp_path / "home/.owlbear").mkdir(parents=True)
        (tmp_path / "home/.owlbear/data.json").write_text("{", encoding="utf-8")
        monkeypatch.delenv("OWLBEAR_DATA")
        monkeypatch.setenv("HOME", str(tmp_path / "home"))

    with pytest.raises(StoreError, match=message):
        shared_stores(work)
