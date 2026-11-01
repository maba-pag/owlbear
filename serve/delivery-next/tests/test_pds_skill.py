"""#777: the PDS knowledge skill a project's session preloads, chosen from its worktree."""

import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest

from owlbear_delivery_next.change_contracts.models import StepKind
from owlbear_delivery_next.change_contracts.permissions import Policy
from owlbear_delivery_next.change_contracts.tools import Worktree
from owlbear_delivery_next.local_system import pds_skill, preload
from owlbear_delivery_next.runtimes import lessons, sdk_adapter


def skill(folder: Path, name: str) -> Path:
    folder.mkdir(parents=True)
    (folder / "SKILL.md").write_text(f"---\nname: {name}\ndescription: x\n---\n")
    return folder


def react(project: Path, *, installed: bool = True) -> Path:
    """A project that depends on the React package, installed with its knowledge skill or not."""
    project.mkdir()
    deps = '{"devDependencies": {"@porsche-design-system/components-react": "^4.10.0"}}'
    (project / "package.json").write_text(deps)
    package = project / "node_modules" / "@porsche-design-system" / "components-react"
    if installed:
        skill(package / "skills" / "pds-knowledge-react", "pds-knowledge-react")
        (package / "package.json").write_text('{"version": "4.10.1"}')
    return package / "skills" / "pds-knowledge-react"


@pytest.fixture
def owlbear(tmp_path: Path) -> Path:
    """A package pinning 4.10.1 with its vendored knowledge skill."""
    root = tmp_path / "package"
    skill(root / pds_skill.VENDORED, "pds-knowledge-js")
    (root / pds_skill.PIN).write_text('{"version": "4.10.1", "integrity": "x", "files": {}}')
    return root


def pages(project: Path, *tracked: str, untracked: str = "") -> Path:
    """A plain-JS project whose tracked pages hold *tracked*, one line each."""
    project.mkdir()
    for n, line in enumerate(tracked):
        (project / f"page{n}.html").write_text(f"<script src='{line}'></script>\n")
    subprocess.run(["git", "init", "-q", str(project)], check=True)  # noqa: S603, S607
    subprocess.run(["git", "-C", str(project), "add", "."], check=True)  # noqa: S603, S607
    if untracked:
        (project / "draft.html").write_text(untracked)
    return project


def test_a_project_depending_on_a_pds_package_gets_its_installed_skill_or_the_reason(tmp_path, owlbear) -> None:
    chosen = react(tmp_path / "app")
    assert pds_skill.choose(tmp_path / "app", owlbear) == pds_skill.Choice("pds-knowledge-react", chosen)
    react(tmp_path / "bare", installed=False)
    assert pds_skill.choose(tmp_path / "bare", owlbear) == pds_skill.Choice(
        reason="the project's PDS package is not installed"
    )


def test_pages_loading_owlbear_s_pinned_release_get_its_vendored_skill_any_other_none(tmp_path, owlbear) -> None:
    cdn = "https://cdn.ui.porsche.com/porsche-design-system/components/porsche-design-system.v{}.abc.js"
    at_pin = pages(tmp_path / "pinned", cdn.format("4.10.1"), untracked=cdn.format("3.0.0"))  # untracked: not read
    assert pds_skill.choose(at_pin, owlbear) == pds_skill.Choice("pds-knowledge-js", owlbear / pds_skill.VENDORED)
    other = pages(tmp_path / "other", cdn.format("4.9.0"), cdn.format("4.10.1"))
    assert pds_skill.choose(other, owlbear) == pds_skill.Choice(
        reason="the project loads PDS 4.10.1, 4.9.0; OwlBear's skill is for 4.10.1"
    )


def test_a_project_that_names_no_pds_is_not_a_pds_project(tmp_path, owlbear) -> None:
    assert pds_skill.choose(pages(tmp_path / "plain", "app.js"), owlbear) is None
    assert pds_skill.choose(tmp_path / "missing", owlbear) is None  # not a git checkout either


def session(worktree: Path, **kw) -> sdk_adapter.Session:
    fields = {
        "kind": StepKind.REVIEW,
        "worktree": worktree,
        "session_id": "s1",
        "message": "m",
        "resume": False,
        "policy": Policy(worktree),
        "observe": lambda: Worktree("a" * 40, "b" * 40),
        "checks": (),
        "model": "gpt-6-luna",
    }
    return sdk_adapter.Session(**(fields | kw))


def step(cfg: sdk_adapter.Session) -> sdk_adapter._Step:
    return sdk_adapter._Step(cfg, SimpleNamespace(call_soon_threadsafe=lambda *_: None))  # noqa: SLF001


@pytest.mark.parametrize(
    ("fields", "loads"),
    [
        ({"kind": StepKind.BUILD, "ui": True}, True),
        ({"role": "design-judge"}, True),
        ({}, True),  # the reviewer
        ({"role": "challenger"}, True),
        ({"kind": StepKind.BUILD}, False),  # a builder without a user interface
        ({"kind": StepKind.PLAN}, False),
        ({"role": "challenger", "skills": preload.directory()}, False),  # a pack candidate's session: its own only
    ],
)
def test_the_sdk_options_preload_the_chosen_skill_for_the_roles_that_judge_or_build_a_ui(
    tmp_path, fields, loads
) -> None:
    chosen = react(tmp_path / "app")
    opts = step(session(tmp_path / "app", **fields)).options()
    assert (str(chosen) in opts["skill_directories"]) is loads
    assert ("pds-knowledge-react" in opts["custom_agents"][0]["skills"]) is loads


def event(kind: str, **data) -> SimpleNamespace:
    return SimpleNamespace(type=SimpleNamespace(value=kind), data=SimpleNamespace(**data))


def test_only_the_chosen_skill_s_own_load_satisfies_the_first_turn_check(tmp_path) -> None:
    chosen = react(tmp_path / "app")
    elsewhere = skill(tmp_path / "copy" / "pds-knowledge-react", "pds-knowledge-react")
    for folder, done in ((elsewhere, True), (chosen, False)):
        st = step(session(tmp_path / "app"))
        st.created = True
        named = [(n, preload.directory() / n) for n in preload.REQUIRED["reviewer"]] + [("pds-knowledge-react", folder)]
        for name, path in named:
            trigger = SimpleNamespace(value="context-load")
            st.on_event(event("skill.invoked", name=name, trigger=trigger, path=str(path / "SKILL.md")))
        st.on_event(event("assistant.turn_start"))
        assert st.done is done
        assert st.run.detail == ("skills not preloaded: pds-knowledge-react" if done else "")


def test_a_pds_project_without_its_skill_is_told_why_and_a_resume_still_finds_the_message(tmp_path) -> None:
    react(tmp_path / "bare", installed=False)
    st = step(session(tmp_path / "bare"))
    first = pds_skill.noted("Review the change.", st.pds)
    assert first.splitlines()[0] == f"{pds_skill.NOTE}the project's PDS package is not installed."
    transcript = [event("user.message", content=first)]
    assert lessons.sent(transcript, "Review the change.")
    assert pds_skill.noted("m", None) == "m"
