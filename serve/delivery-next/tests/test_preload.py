"""Item 6: each worker role's mandatory skills load before its first turn, in both runtimes; a missing one refuses
the step."""

import asyncio
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest

from owlbear_delivery_next import preload, sdk_adapter, vscode_adapter
from owlbear_delivery_next import window_files as wf
from owlbear_delivery_next.models import StepKind
from owlbear_delivery_next.permissions import Policy
from owlbear_delivery_next.processes import Termination
from owlbear_delivery_next.tools import Worktree

ROLES = ("builder", "planner", "reviewer")


def git(cwd: Path, *args: str) -> str:
    done = subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True)  # noqa: S603, S607
    return done.stdout.strip()


@pytest.fixture
def repo(tmp_path: Path, monkeypatch) -> Path:
    (tmp_path / "gitconfig").write_text("")
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", str(tmp_path / "gitconfig"))
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")
    for who in ("AUTHOR", "COMMITTER"):
        monkeypatch.setenv(f"GIT_{who}_NAME", "t")
        monkeypatch.setenv(f"GIT_{who}_EMAIL", "t@t")
    path = tmp_path / "wt"
    path.mkdir()
    git(path, "init", "-q", "-b", "main")
    (path / "README.md").write_text("x\n")
    git(path, "add", "-A")
    git(path, "commit", "-qm", "init")
    return path


@pytest.fixture
def gap(tmp_path: Path, monkeypatch) -> Path:
    """Delivery's skill folder with the acceptance skill missing and module design misnamed."""
    root = tmp_path / "skills"
    (root / "owlbear-module-design").mkdir(parents=True)
    (root / "owlbear-module-design" / "SKILL.md").write_text("---\nname: module-design\ndescription: x\n---\n")
    monkeypatch.setattr(preload, "directory", lambda: root)
    return root


def session(kind=StepKind.BUILD, **kw) -> sdk_adapter.Session:
    fields = {
        "kind": kind,
        "worktree": Path(),
        "session_id": "s1",
        "message": "m",
        "resume": False,
        "policy": Policy(Path(), ()),
        "observe": lambda: Worktree("a" * 40, "b" * 40),
        "checks": (),
        "model": "gpt-6-luna",
    }
    return sdk_adapter.Session(**(fields | kw))


def event(kind: str, **data) -> SimpleNamespace:
    return SimpleNamespace(type=SimpleNamespace(value=kind), data=SimpleNamespace(**data))


def loaded(name: str, trigger="context-load", root: Path | None = None) -> SimpleNamespace:
    path = (root or preload.directory()) / name / "SKILL.md"
    return event("skill.invoked", name=name, trigger=SimpleNamespace(value=trigger), path=str(path))


def test_each_role_has_its_skills_in_delivery_folder_apart_from_the_chat_skill() -> None:
    for role in ROLES:
        assert preload.REQUIRED[role]
        assert preload.missing(role) == []
    shipped = {p.name for p in preload.directory().iterdir() if p.is_dir()}
    assert shipped == {s for r in ROLES for s in preload.REQUIRED[r]}
    assert preload.CHAT not in shipped
    for kind in sdk_adapter.ROLES:
        assert sdk_adapter.agent(kind)["skills"] == list(preload.REQUIRED[sdk_adapter.ROLES[kind]])


@pytest.mark.usefixtures("gap")
def test_a_missing_or_misnamed_skill_is_reported() -> None:
    assert preload.missing("builder") == ["owlbear-module-design", "owlbear-acceptance"]


def test_the_sdk_session_searches_delivery_folder_for_the_role_skills() -> None:
    st = sdk_adapter._Step(session(), SimpleNamespace(call_soon_threadsafe=lambda *_: None))  # noqa: SLF001
    opts = st.options()
    assert opts["skill_directories"] == [str(preload.directory())]
    assert "disabled_skills" not in opts  # a project's own skills stay as the project has them
    assert opts["custom_agents"][0]["skills"] == ["owlbear-module-design", "owlbear-acceptance"]


@pytest.mark.usefixtures("gap")
def test_a_step_whose_skills_are_missing_never_starts_a_runtime(monkeypatch) -> None:
    monkeypatch.setattr(sdk_adapter, "CopilotClient", lambda **_: pytest.fail("no runtime may start"))
    run = asyncio.run(sdk_adapter.run(session(kind=StepKind.PLAN)))
    assert (run.ending, run.detail) == (
        "error",
        "Delivery's worker skills are missing: owlbear-acceptance, owlbear-module-design",
    )
    assert run.termination == Termination(confirmed=True)


def step(kind=StepKind.REVIEW) -> sdk_adapter._Step:
    st = sdk_adapter._Step(session(kind=kind), SimpleNamespace(call_soon_threadsafe=lambda *_: None))  # noqa: SLF001
    st.created = True
    return st


def test_a_created_session_must_have_preloaded_every_role_skill_by_its_first_turn(tmp_path) -> None:
    st = step()
    for e in (loaded("owlbear-acceptance"), loaded("owlbear-module-design"), event("assistant.turn_start")):
        st.on_event(e)
    assert not st.done
    short = step()
    short.on_event(loaded("owlbear-acceptance"))
    short.on_event(loaded("owlbear-module-design", trigger="agent-invoked"))  # the agent's own call is no preload
    short.on_event(event("assistant.turn_start"))
    assert (short.run.ending, short.run.detail) == ("error", "skills not preloaded: owlbear-module-design")
    other = step()
    other.on_event(loaded("owlbear-acceptance"))
    other.on_event(loaded("owlbear-module-design", root=tmp_path))  # a same-named skill from elsewhere
    other.on_event(event("assistant.turn_start"))
    assert other.run.detail == "skills not preloaded: owlbear-module-design"


def test_a_resumed_session_is_not_checked_again() -> None:
    st = step()
    st.created = False  # the runtime loaded the skills when it created the session
    st.on_event(event("assistant.turn_start"))
    assert not st.done


def test_a_preload_counts_through_a_linked_install(tmp_path, monkeypatch) -> None:
    real = tmp_path / "real"
    real.mkdir()
    (tmp_path / "link").symlink_to(real)
    monkeypatch.setattr(preload, "directory", lambda: tmp_path / "link")
    st = step()
    for name in preload.REQUIRED["reviewer"]:
        st.on_event(loaded(name, root=real))  # the runtime reports the canonical path
    st.on_event(event("assistant.turn_start"))
    assert not st.done


def test_the_window_agent_names_its_skills_and_they_are_placed_out_of_every_commit(repo) -> None:
    text = wf.agent("reviewer", Path("/i.json"))(None)
    assert "\nskills: [owlbear-acceptance, owlbear-module-design]\n---\n" in text
    placed = [wf.place(repo, rel, render) for rel, render in wf.skills("reviewer")]
    for name in preload.REQUIRED["reviewer"]:
        assert (repo / wf.skill_path(name)).read_text() == preload.text(name)
    assert git(repo, "status", "--porcelain") == ""
    assert wf.restore(repo, placed) == []
    assert not (repo / ".github").exists()


@pytest.mark.usefixtures("gap")
def test_a_window_step_whose_skills_are_missing_ends_before_any_window(repo, tmp_path) -> None:
    env = vscode_adapter.Env(
        connect=lambda _p: pytest.fail("no window may open"),
        settle=lambda *_: Termination(confirmed=True),
    )
    run = vscode_adapter.run(session(worktree=repo), tmp_path / "steps" / "s1.json", env)
    assert run.ending == "error"
    assert "Delivery's worker skills are missing: owlbear-module-design, owlbear-acceptance" in run.detail
    assert git(repo, "status", "--porcelain", "--ignored") == ""
