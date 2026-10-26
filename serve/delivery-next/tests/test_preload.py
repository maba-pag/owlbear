"""Item 6: each worker role's mandatory skills load before its first turn; a missing one refuses the step."""

import asyncio
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from owlbear_delivery_next.change_contracts.models import StepKind
from owlbear_delivery_next.change_contracts.permissions import Policy
from owlbear_delivery_next.change_contracts.tools import Worktree
from owlbear_delivery_next.design_packs import design_pack
from owlbear_delivery_next.local_system import preload
from owlbear_delivery_next.local_system.processes import Termination
from owlbear_delivery_next.runtimes import chatlogs, sdk_adapter

ROLES = ("builder", "planner", "reviewer")


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
        "policy": Policy(Path()),
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


def test_each_role_has_its_skills_in_the_one_skills_folder_and_none_loads_the_chat_skill() -> None:
    for role in ROLES:
        assert preload.REQUIRED[role]
        assert preload.missing(role) == []
    shipped = {p.name for p in preload.directory().iterdir() if p.is_dir()}
    roles = {s for r in ROLES for s in preload.required(r, ui=True)}
    assert shipped == roles | set(design_pack.manifest()["skills"]) | {preload.CHAT}
    assert not any(preload.CHAT in preload.required(r, ui=True) for r in preload.REQUIRED)
    for kind in sdk_adapter.ROLES:
        assert sdk_adapter.agent(kind)["skills"] == list(preload.REQUIRED[sdk_adapter.ROLES[kind]])


@pytest.mark.usefixtures("gap")
def test_a_missing_or_misnamed_skill_is_reported() -> None:
    assert preload.missing("builder") == ["owlbear-module-design", "owlbear-acceptance-criteria"]


def test_front_matter_is_read_as_yaml() -> None:
    doc = '---\nname: x\ndescription: "a: b, c"\ntools:\n  - view\n  - owlbear-memory/recall_memory\n---\n\nProse.\n'
    meta, body = preload.front_matter(doc)
    assert meta == {"name": "x", "description": "a: b, c", "tools": ["view", "owlbear-memory/recall_memory"]}
    assert body.strip() == "Prose."
    for bad in ("name: x\n", "---\nname: x\n", "---\n- x\n---\n"):
        with pytest.raises(ValueError, match="no front matter"):
            preload.front_matter(bad)


def test_a_skill_whose_front_matter_is_not_yaml_counts_as_missing(gap) -> None:
    (gap / "owlbear-acceptance-criteria").mkdir()
    (gap / "owlbear-acceptance-criteria" / "SKILL.md").write_text('---\nname: "owlbear-acceptance-criteria\n---\n')
    assert preload.missing("builder") == ["owlbear-module-design", "owlbear-acceptance-criteria"]


def test_the_sdk_session_sees_only_its_roles_skill_folders() -> None:
    st = sdk_adapter._Step(session(), SimpleNamespace(call_soon_threadsafe=lambda *_: None))  # noqa: SLF001
    opts = st.options()
    folder = preload.directory()
    assert opts["skill_directories"] == [
        str(folder / "owlbear-module-design"),
        str(folder / "owlbear-acceptance-criteria"),
    ]
    assert "disabled_skills" not in opts  # a project's own skills stay as the project has them
    assert opts["custom_agents"][0]["skills"] == ["owlbear-module-design", "owlbear-acceptance-criteria"]


@pytest.mark.usefixtures("gap")
def test_a_step_whose_skills_are_missing_never_starts_a_runtime(monkeypatch) -> None:
    monkeypatch.setattr(sdk_adapter, "CopilotClient", lambda **_: pytest.fail("no runtime may start"))
    run = asyncio.run(sdk_adapter.run(session(kind=StepKind.PLAN)))
    assert (run.ending, run.detail) == (
        "error",
        "Delivery's worker skills are missing: owlbear-acceptance-criteria, owlbear-module-design",
    )
    assert run.termination == Termination(confirmed=True)
    lines = [json.loads(x) for x in (chatlogs.root() / "manifest.jsonl").read_text().splitlines()]  # design §5
    assert [(x["event"], x["session"], x.get("kind")) for x in lines] == [
        ("started", "s1", "plan"),
        ("ended", "s1", None),
    ]


def step(kind=StepKind.REVIEW) -> sdk_adapter._Step:
    st = sdk_adapter._Step(session(kind=kind), SimpleNamespace(call_soon_threadsafe=lambda *_: None))  # noqa: SLF001
    st.created = True
    return st


def test_a_created_session_must_have_preloaded_every_role_skill_by_its_first_turn(tmp_path) -> None:
    st = step(StepKind.PLAN)
    for e in (loaded("owlbear-acceptance-criteria"), loaded("owlbear-module-design"), event("assistant.turn_start")):
        st.on_event(e)
    assert not st.done
    short = step(StepKind.PLAN)
    short.on_event(loaded("owlbear-acceptance-criteria"))
    short.on_event(loaded("owlbear-module-design", trigger="agent-invoked"))  # the agent's own call is no preload
    short.on_event(event("assistant.turn_start"))
    assert (short.run.ending, short.run.detail) == ("error", "skills not preloaded: owlbear-module-design")
    other = step(StepKind.PLAN)
    other.on_event(loaded("owlbear-acceptance-criteria"))
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
