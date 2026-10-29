"""Item 6: each worker role's mandatory skills load before its first turn; a missing one refuses the step."""

import asyncio
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from owlbear_delivery_next.change_contracts.models import StepKind
from owlbear_delivery_next.change_contracts.permissions import Policy
from owlbear_delivery_next.change_contracts.tools import Worktree
from owlbear_delivery_next.impeccable import pack_files
from owlbear_delivery_next.improvement import chatlogs
from owlbear_delivery_next.local_system import preload
from owlbear_delivery_next.local_system.processes import Termination
from owlbear_delivery_next.runtimes import sdk_adapter
from owlbear_delivery_next.settings.roles import UserConfig

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
    assert shipped == roles | set(pack_files.manifest()["skills"]) | {preload.CHAT}
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


def _user_skills(home: Path, tmp_path: Path) -> None:
    """The owner's skills: his own, one linked in, one named as Delivery's, his copy of the chat skill, a folder."""
    skills = home / "skills"
    skills.mkdir(parents=True)
    for folder, name in [("ah-asking", "ah-asking"), ("mine", None), ("design", "owlbear-module-design"),
                         ("owlbear-change-shaping", None)]:  # fmt: skip
        (skills / folder).mkdir()
        meta = f"name: {name}\n" if name else ""
        (skills / folder / "SKILL.md").write_text(f"---\n{meta}description: x\n---\n")
    linked = tmp_path / "agent-home" / "ah-decisions"
    linked.mkdir(parents=True)
    (linked / "SKILL.md").write_text("---\nname: ah-decisions\ndescription: x\n---\n")
    (skills / "ah-decisions").symlink_to(linked)
    (skills / "notes").mkdir()  # no SKILL.md: no skill


@pytest.mark.parametrize("on", [True, False])
def test_the_owners_skills_are_available_only_with_his_switch_on_never_as_delivery_s(tmp_path, monkeypatch, on):
    home = tmp_path / "copilot"
    _user_skills(home, tmp_path)
    monkeypatch.setenv("COPILOT_HOME", str(home))
    cfg = session(user=UserConfig(instructions=False, skills=True)) if on else session()  # a site that sets none: off
    st = sdk_adapter._Step(cfg, SimpleNamespace(call_soon_threadsafe=lambda *_: None))  # noqa: SLF001
    opts = st.options()
    folder = preload.directory()
    own = [str(folder / "owlbear-module-design"), str(folder / "owlbear-acceptance-criteria")]
    his = [str(home / "skills" / n) for n in ("ah-asking", "ah-decisions", "mine")]  # by their link path
    assert opts["skill_directories"] == own + (his if on else [])
    assert opts["custom_agents"][0]["skills"] == ["owlbear-module-design", "owlbear-acceptance-criteria"]
    assert (opts["enable_config_discovery"], opts["included_builtin_skills"]) == (False, [])


def test_the_runtimes_user_folder_is_copilot_home_else_the_home_s_copilot(tmp_path, monkeypatch):
    monkeypatch.setenv("COPILOT_HOME", str(tmp_path / "elsewhere"))
    assert preload.copilot_home() == tmp_path / "elsewhere"
    monkeypatch.delenv("COPILOT_HOME")
    monkeypatch.setenv("HOME", str(tmp_path))
    assert preload.copilot_home() == tmp_path / ".copilot"
    assert preload.user_skills(tmp_path / ".copilot") == []  # no folder: no skills, no error


def test_a_pack_candidate_s_skill_names_are_reserved_too(tmp_path):
    home, candidate = tmp_path / "copilot", tmp_path / "candidate"
    (home / "skills" / "new-pack-skill").mkdir(parents=True)
    (home / "skills" / "new-pack-skill" / "SKILL.md").write_text("---\nname: new-pack-skill\n---\n")
    (candidate / "new-pack-skill").mkdir(parents=True)
    assert preload.user_skills(home) == [str(home / "skills" / "new-pack-skill")]
    assert preload.user_skills(home, folder=candidate) == []


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
