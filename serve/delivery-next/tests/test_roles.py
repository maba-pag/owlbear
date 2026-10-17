import dataclasses
import json
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from owlbear_delivery_next import api, cli, profile, roles, sdk_adapter, tools, vscode_adapter
from owlbear_delivery_next.codebase import CURRENT
from owlbear_delivery_next.config import Agent, Layer, resolve
from owlbear_delivery_next.host import HostRecord
from owlbear_delivery_next.models import StepKind
from owlbear_delivery_next.permissions import Policy
from owlbear_delivery_next.profile_record import Profile, ProfileEntry, RoleModel
from owlbear_delivery_next.store import Store, StoreError
from owlbear_delivery_next.tools import Worktree

NOW = datetime(2026, 10, 10, 12, tzinfo=UTC)


@pytest.mark.parametrize(
    ("session", "model", "effort"),
    [
        (StepKind.PLAN, "claude-opus-5.5", "high"),
        (StepKind.BUILD, "claude-opus-5.5", "medium"),
        (StepKind.CHECK, "claude-haiku-5.5", "low"),
        (StepKind.REVIEW, "gpt-6.1-sol", "xhigh"),
        ("visual-review", "gpt-6.1-sol", "xhigh"),
        ("plan-challenge", "gpt-6.1-sol", "high"),
        ("brief-challenge", "gpt-6.1-sol", "high"),
    ],
)
def test_each_session_runs_with_its_roles_model_and_effort(session, model, effort):
    assert roles.chosen(resolve(None, Layer()), session) == RoleModel(model=model, effort=effort)


def test_plan_challenge_is_the_challenger_not_the_planner():
    settings = resolve(None, Layer(agents={"planner": Agent(model="p", effort="low")}))
    assert roles.chosen(settings, StepKind.PLAN) == RoleModel(model="p", effort="low")
    assert roles.chosen(settings, "plan-challenge") == roles.DEFAULTS["challenger"]


def test_a_project_override_wins_and_is_marked_in_the_table():
    settings = resolve(None, Layer(agents={"builder": Agent(model="m-1", effort="low")}))
    assert roles.chosen(settings, StepKind.BUILD) == RoleModel(model="m-1", effort="low")
    assert roles.chosen(settings, StepKind.REVIEW) == roles.DEFAULTS["reviewer"]
    assert "builder: m-1 effort low (project)" in roles.table(settings)
    assert "reviewer: gpt-6.1-sol effort xhigh\n" in roles.table(settings)


def test_a_role_override_parses_a_model_with_colons():
    assert roles.parse("reviewer=vendor:model:xhigh") == ("reviewer", RoleModel(model="vendor:model", effort="xhigh"))


@pytest.mark.parametrize(
    "text",
    [
        "boss=m:high",
        "builder=m:extreme",
        "builder=:high",
        "builder=   :high",
        "builder",
        "builder=m",
    ],
)
def test_an_invalid_override_is_refused(text, capsys):
    with pytest.raises(ValueError, match=r"role must be|expected ROLE"):
        roles.parse(text)
    with pytest.raises(SystemExit) as exc:
        cli.main(["profile", "--role", text])
    assert exc.value.code == 2
    assert "--role" in capsys.readouterr().err


@pytest.mark.parametrize(
    ("model", "effort"),
    [(" ", "high"), ("auto", "high"), ("AUTO", "low"), ("m", "extreme")],
)
def test_a_role_model_is_refused_everywhere_it_is_built(tmp_path, model, effort):
    refused = r"model must not be empty|must be named|literal_error|Input"
    with pytest.raises(ValueError, match=refused):
        RoleModel(model=model, effort=effort)
    raw = Profile().model_dump(mode="json") | {"format": 1, "roles": {"builder": {"model": model, "effort": effort}}}
    (tmp_path / "profile.json").write_text(json.dumps(raw))
    with pytest.raises(StoreError, match="cannot be migrated"):
        Store(tmp_path).read_profile()


def test_luna_low_and_haiku_medium_load_and_the_defaults_are_valid():
    assert roles.parse("builder=gpt-6-luna:low") == ("builder", RoleModel(model="gpt-6-luna", effort="low"))
    assert roles.parse("reviewer=claude-haiku-5.5:medium")[1].effort == "medium"
    assert all(RoleModel.model_validate(rm.model_dump()) == rm for rm in roles.DEFAULTS.values())


def test_sdk_options_carry_the_model_reasoning_effort_and_context_tier():
    rm = roles.chosen(resolve(None, Layer()), StepKind.BUILD)
    cfg = sdk_adapter.Session(
        StepKind.BUILD, Path(), "s1", "m", resume=False, policy=Policy(Path()), observe=Worktree, checks=(),
        model=rm.model, effort=rm.effort, context=rm.context,
    )  # fmt: skip
    opts = sdk_adapter._Step(cfg, SimpleNamespace(call_soon_threadsafe=lambda *_: None)).options()  # noqa: SLF001
    assert (opts["model"], opts["reasoning_effort"], opts["context_tier"]) == ("claude-opus-5.5", "medium", None)
    long = roles.chosen(resolve(None, Layer(agents={"builder": Agent(context="long")})), StepKind.BUILD)
    cfg = dataclasses.replace(cfg, context=long.context)
    opts = sdk_adapter._Step(cfg, SimpleNamespace(call_soon_threadsafe=lambda *_: None)).options()  # noqa: SLF001
    assert opts["context_tier"] == "long_context"  # the default tier is left to the runtime, as before


@pytest.mark.parametrize("kind", sorted(sdk_adapter.ROLES))
def test_every_role_runs_autopilot_and_only_delivery_can_ask_the_owner(kind):
    cfg = sdk_adapter.Session(kind, Path(), "s1", "m", resume=True, policy=Policy(Path()), observe=Worktree, checks=())
    opts = sdk_adapter._Step(cfg, SimpleNamespace(call_soon_threadsafe=lambda *_: None)).options()  # noqa: SLF001
    assert opts["excluded_tools"] == ["ask_user"]  # the runtime's own question tool; N10's request is ask_question
    assert "on_user_input_request" not in opts
    assert opts["agent"] == f"owlbear-{sdk_adapter.ROLES[kind]}"  # TD-169
    assert tools.ASK.name in {t.name for t in opts["tools"]}
    assert vscode_adapter.CONFIG["mode"] == "autopilot"
    st = sdk_adapter._Step(cfg, SimpleNamespace(call_soon_threadsafe=lambda *_: None))  # noqa: SLF001
    question = {
        "question": "Which key?",
        "why": "owner's",
        "options": [{"label": "A", "effect": "a"}, {"label": "B", "effect": "b"}],
    }
    asked = st._handle(tools.ASK, SimpleNamespace(arguments=question))  # noqa: SLF001
    late = st._handle(tools.ASK, SimpleNamespace(arguments=question))  # noqa: SLF001
    assert (asked.result_type, late.result_type, st.run.ending) == ("success", "rejected", "ask")


def rules(strict: str, resolution: str) -> Profile:
    def known(v):
        return ProfileEntry(state="known", value=v, evidence="rules")

    return Profile(
        entries={profile.DEFAULT: known("main"), profile.STRICT: known(strict), profile.RESOLUTION: known(resolution)}
    )


@pytest.mark.parametrize(
    ("strict", "resolution", "expected"),
    [
        ("yes", "yes", []),
        (
            "no",
            "no",
            [
                (
                    "GitHub does not require branches to be up to date or conversation resolution on main. Delivery "
                    "checks both itself; turning them on in the repository settings closes the last gap."
                )
            ],
        ),
        (
            "yes",
            "no",
            [
                (
                    "GitHub does not require conversation resolution on main. Delivery checks this itself; turning it "
                    "on in the repository settings closes the last gap."
                )
            ],
        ),
    ],
)
def test_the_project_api_serves_a_note_for_each_rule_github_does_not_require(tmp_path, strict, resolution, expected):
    class Host:
        wake = SimpleNamespace(set=lambda: None)
        record = HostRecord(url="http://127.0.0.1:9/", token="tok", pid=1, started_at=NOW, code=CURRENT)  # noqa: S106

    store = Store(tmp_path)
    store.write_profile(rules(strict, resolution))
    app = TestClient(
        api.create_app(store, "t", Host()), base_url="http://127.0.0.1", headers={"authorization": "Bearer t"}
    )
    assert app.get("/api/next/project").json() == {"notes": expected}
    assert app.get("/api/next/project", headers={"authorization": "Bearer x"}).status_code == 401


def test_unknown_rules_give_no_note():
    assert profile.notes(Profile()) == []
