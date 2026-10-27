"""D-01M5YE55W7P4A6PS8YZV8K7J6A: a step switches off each instruction source outside its worktree, by its place;
with the owner's switch on, his own instruction files stay on (D-01M5YE4TRV2T08TW0FA2FGSDBK)."""

import asyncio
from types import SimpleNamespace

import pytest
from copilot.rpc import InstructionLocation

from owlbear_delivery_next.runtimes import instruction_scope

USER, REPO, PLUGIN = InstructionLocation.USER, InstructionLocation.REPOSITORY, InstructionLocation.PLUGIN


class _Rpc:
    def __init__(self, sources, *, applied=True):
        self.sources, self.applied, self.updates = sources, applied, []
        self.instructions = SimpleNamespace(get_sources=self.get_sources)
        self.options = SimpleNamespace(update=self.update)

    async def get_sources(self):
        listed = [(*s, None)[:3] for s in self.sources]  # a source without a place has none
        return SimpleNamespace(sources=[SimpleNamespace(id=i, source_path=p, location=at) for i, p, at in listed])

    async def update(self, params):
        self.updates.append(params.disabled_instruction_sources)
        return SimpleNamespace(success=self.applied)


def _scoped(rpc, work, **user):
    return asyncio.run(instruction_scope.own(SimpleNamespace(rpc=rpc), work, **user))


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

    scope = _scoped(rpc, work)

    assert (scope.off, scope.user) == (["home-copilot", "user-scoped", "escape", "unplaced"], [])
    assert rpc.updates == [scope.off]


def test_a_worktree_reached_through_a_link_still_keeps_its_files(tmp_path):
    real = tmp_path / "real"
    real.mkdir()
    (tmp_path / "link").symlink_to(real)
    rpc = _Rpc([("repo-scoped", str(real / ".github" / "instructions" / "y.instructions.md"))])

    assert _scoped(rpc, tmp_path / "link") == instruction_scope.Scope(off=[], user=[])
    assert rpc.updates == []  # nothing to switch off, no update sent


def test_a_switch_off_the_runtime_refuses_ends_the_step_before_any_message(tmp_path):
    rpc = _Rpc([("home-copilot", "/elsewhere/copilot-instructions.md")], applied=False)

    with pytest.raises(RuntimeError, match="home-copilot"):
        _scoped(rpc, tmp_path)


def _home(tmp_path):
    """A home reached through a link, as /var is on macOS: the runtime reports some paths resolved, some not."""
    real = tmp_path / "real"
    (real / "home" / "instructions").mkdir(parents=True)
    (real / "agent-home").mkdir()
    (tmp_path / "var").symlink_to(real)
    home = tmp_path / "var" / "home"
    (real / "agent-home" / "core.instructions.md").write_text("# linked")
    (home / "instructions" / "core.instructions.md").symlink_to(real / "agent-home" / "core.instructions.md")
    (home / "instructions" / "plain.instructions.md").write_text("# plain")
    (home / "copilot-instructions.md").write_text("# root")
    (real / "plugin.instructions.md").write_text("# a plugin's")
    return home, real


def _probe_sources(home, real, work):
    """The sources as the pinned runtime reports them (SDK 1.0.23, CLI 1.0.103)."""
    return [
        ("linked", str(real / "agent-home" / "core.instructions.md"), USER),  # the link's target, resolved
        ("plain", str(real / "home" / "instructions" / "plain.instructions.md"), USER),
        ("root", str(home / "copilot-instructions.md"), USER),  # unresolved: /var, not /private/var
        ("repo", ".github/copilot-instructions.md", REPO),
        ("in-work", str(work / "AGENTS.md"), REPO),
    ]


def test_the_owners_files_stay_on_only_with_his_switch_on(tmp_path):
    home, real = _home(tmp_path)
    work = tmp_path / "work"
    work.mkdir()

    on = _Rpc(_probe_sources(home, real, work))
    scope = _scoped(on, work, user_instructions=True, home=home)
    assert (scope.off, scope.user) == ([], ["linked", "plain", "root"])
    assert on.updates == []

    off = _Rpc(_probe_sources(home, real, work))
    scope = _scoped(off, work, user_instructions=False, home=home)
    assert (scope.off, scope.user) == (["linked", "plain", "root"], [])
    assert off.updates == [["linked", "plain", "root"]]


@pytest.mark.parametrize(
    ("where", "file", "location", "why"),
    [
        ("real", "agent-home/core.instructions.md", PLUGIN, "an allowed file, a plugin's"),
        ("real", "plugin.instructions.md", USER, "the user's place, not his file"),
        ("home", "copilot-instructions.md", None, "no place reported"),
        ("home", "copilot-instructions.md", "user", "a place that is not the runtime's"),
        (None, None, USER, "no file"),
    ],
)
def test_a_source_that_is_not_the_owners_own_file_stays_off_with_the_switch_on(tmp_path, where, file, location, why):
    home, real = _home(tmp_path)
    path = str({"real": real, "home": home}[where] / file) if where else None
    scope = _scoped(_Rpc([("s", path, location)]), tmp_path / "work", user_instructions=True, home=home)
    assert (scope.off, scope.user) == (["s"], []), why


def test_a_missing_home_admits_nothing_and_still_switches_the_rest_off(tmp_path):
    home, real = _home(tmp_path)
    sources = _probe_sources(home, real, tmp_path / "work")
    scope = _scoped(_Rpc(sources), tmp_path / "work", user_instructions=True, home=tmp_path / "nowhere")
    assert (scope.off, scope.user) == (["linked", "plain", "root"], [])
    assert _scoped(_Rpc(sources), tmp_path / "work", user_instructions=True).user == []  # no home given


def test_a_refused_switch_off_still_ends_the_step_with_the_owners_files_on(tmp_path):
    home, real = _home(tmp_path)
    plugin = ("plugin", str(real / "plugin.instructions.md"), PLUGIN)
    rpc = _Rpc([*_probe_sources(home, real, tmp_path / "work"), plugin], applied=False)
    with pytest.raises(RuntimeError, match="plugin") as caught:
        _scoped(rpc, tmp_path / "work", user_instructions=True, home=home)
    assert "linked" not in str(caught.value)
