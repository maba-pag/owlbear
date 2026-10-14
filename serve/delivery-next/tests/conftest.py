import subprocess
from pathlib import Path

import pytest

from owlbear_delivery_next import design_pack, model_choices
from owlbear_delivery_next.steps import worktree


@pytest.fixture(autouse=True)
def _no_shared_settings(tmp_path_factory, monkeypatch):
    """Tests never read the machine's pointer to the shared settings repository (TD-57), nor go online."""
    monkeypatch.setenv("OWLBEAR_HOME", str(tmp_path_factory.mktemp("owlbear-home")))
    monkeypatch.delenv("OWLBEAR_COMMON", raising=False)
    monkeypatch.setattr(design_pack, "fetch", _offline)
    monkeypatch.setattr(model_choices, "_read", lambda: _offline("models.list"))
    root = tmp_path_factory.mktemp("worktrees").resolve()
    monkeypatch.setattr(worktree, "data_root", lambda: root)  # never the machine's worktrees


@pytest.fixture
def change_repo(tmp_path, monkeypatch) -> Path:
    """A temporary Change worktree: ``main`` with one commit and ``owlbear/c1`` one commit ahead, checked out."""
    (tmp_path / "gitconfig").write_text("")
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", str(tmp_path / "gitconfig"))
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")
    for who in ("AUTHOR", "COMMITTER"):
        monkeypatch.setenv(f"GIT_{who}_NAME", "t")
        monkeypatch.setenv(f"GIT_{who}_EMAIL", "t@t")
    work = (tmp_path / "work").resolve()
    work.mkdir()
    for args in (("init", "-q", "-b", "main"), ("commit", "-q", "--allow-empty", "-m", "base")):
        subprocess.run(["git", *args], cwd=work, check=True, capture_output=True)  # noqa: S603, S607
    (work / "a.txt").write_text("a\n")
    for args in (("checkout", "-q", "-b", "owlbear/c1"), ("add", "-A"), ("commit", "-qm", "a")):
        subprocess.run(["git", *args], cwd=work, check=True, capture_output=True)  # noqa: S603, S607
    return work


def _offline(url: str, *_args: object, **_kwargs: object) -> bytes:
    msg = f"offline in tests: {url}"
    raise OSError(msg)
