"""D-01M5X05KTVCSBYA5BZ14XH62N6: a step switches off each instruction source outside its worktree, by its place."""

import asyncio
from types import SimpleNamespace

import pytest

from owlbear_delivery_next.runtimes import instruction_scope


class _Rpc:
    def __init__(self, sources, *, applied=True):
        self.sources, self.applied, self.updates = sources, applied, []
        self.instructions = SimpleNamespace(get_sources=self.get_sources)
        self.options = SimpleNamespace(update=self.update)

    async def get_sources(self):
        return SimpleNamespace(sources=[SimpleNamespace(id=i, source_path=p) for i, p in self.sources])

    async def update(self, params):
        self.updates.append(params.disabled_instruction_sources)
        return SimpleNamespace(success=self.applied)


def _scoped(rpc, work):
    return asyncio.run(instruction_scope.own(SimpleNamespace(rpc=rpc), work))


def test_only_the_worktrees_own_files_stay_on(tmp_path):
    work, home = tmp_path / "work", tmp_path / "home"
    (work / "docs").mkdir(parents=True)
    rpc = _Rpc([
        ("home-copilot", str(home / "copilot-instructions.md")),
        ("user-scoped", str(home / "instructions" / "x.instructions.md")),
        ("repo-copilot", ".github/copilot-instructions.md"),
        ("repo-scoped", str(work / ".github" / "instructions" / "y.instructions.md")),
        ("child", str(work / "docs" / "AGENTS.md")),
        ("escape", "../elsewhere/AGENTS.md"),
        ("unplaced", None),
    ])  # fmt: skip

    off = _scoped(rpc, work)

    assert off == ["home-copilot", "user-scoped", "escape", "unplaced"]
    assert rpc.updates == [off]


def test_a_worktree_reached_through_a_link_still_keeps_its_files(tmp_path):
    real = tmp_path / "real"
    real.mkdir()
    (tmp_path / "link").symlink_to(real)
    rpc = _Rpc([("repo-scoped", str(real / ".github" / "instructions" / "y.instructions.md"))])

    assert _scoped(rpc, tmp_path / "link") == []
    assert rpc.updates == []  # nothing to switch off, no update sent


def test_a_switch_off_the_runtime_refuses_ends_the_step_before_any_message(tmp_path):
    rpc = _Rpc([("home-copilot", "/elsewhere/copilot-instructions.md")], applied=False)

    with pytest.raises(RuntimeError, match="home-copilot"):
        _scoped(rpc, tmp_path)
