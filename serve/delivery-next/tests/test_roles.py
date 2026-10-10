import json
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from owlbear_delivery_next import api, cli, profile, roles, sdk_adapter
from owlbear_delivery_next.host import HostRecord
from owlbear_delivery_next.models import Profile, ProfileEntry, RoleModel, StepKind
from owlbear_delivery_next.permissions import Policy
from owlbear_delivery_next.store import Store, StoreError
from owlbear_delivery_next.tools import Worktree

NOW = datetime(2026, 10, 10, 12, tzinfo=UTC)


@pytest.mark.parametrize(
    ("session", "model", "effort"),
    [
        (StepKind.PLAN, "claude-opus-5.5", "high"),
        (StepKind.BUILD, "gpt-6-luna", "max"),
        (StepKind.CHECK, "gpt-6-luna", "max"),
        (StepKind.REVIEW, "gpt-6.1-sol", "high"),
        ("visual-review", "gpt-6.1-sol", "high"),
        ("plan-review", "gpt-6.1-sol", "medium"),
        ("brief-review", "gpt-6.1-sol", "medium"),
    ],
)
def test_each_session_runs_with_its_roles_model_and_effort(session, model, effort):
    assert roles.chosen(None, session) == RoleModel(model=model, effort=effort)


def test_plan_review_is_the_challenger_not_the_planner():
    planner = RoleModel(model="p", effort="low")
    prof = Profile(roles={"planner": planner})
    assert roles.chosen(prof, StepKind.PLAN) == planner
    assert roles.chosen(prof, "plan-review") == roles.DEFAULTS["challenger"]


def test_a_project_override_wins_and_is_marked_in_the_table():
    prof = Profile(roles={"builder": RoleModel(model="m-1", effort="low")})
    assert roles.chosen(prof, StepKind.BUILD) == RoleModel(model="m-1", effort="low")
    assert roles.chosen(prof, StepKind.REVIEW) == roles.DEFAULTS["reviewer"]
    assert "builder: m-1 effort low (project)" in roles.table(prof)
    assert "reviewer: gpt-6.1-sol effort high\n" in roles.table(prof)


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
        "builder=gpt-6-luna:high",
        "reviewer=claude-haiku-4.5:xhigh",
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
    ("model", "effort"), [(" ", "high"), ("gpt-6-luna", "xhigh"), ("claude-haiku-4.5", "low"), ("m", "extreme")]
)
def test_a_role_model_is_refused_everywhere_it_is_built(tmp_path, model, effort):
    with pytest.raises(ValueError, match=r"model must not be empty|always runs with effort max|literal_error|Input"):
        RoleModel(model=model, effort=effort)
    raw = Profile().model_dump(mode="json") | {"roles": {"builder": {"model": model, "effort": effort}}}
    (tmp_path / "profile.json").write_text(json.dumps(raw))
    with pytest.raises(StoreError, match="cannot be migrated"):
        Store(tmp_path).read_profile()


def test_luna_and_haiku_accept_max_and_the_defaults_are_valid():
    assert RoleModel(model="claude-haiku-4.5", effort="max").effort == "max"
    assert all(RoleModel.model_validate(rm.model_dump()) == rm for rm in roles.DEFAULTS.values())


def test_sdk_options_carry_the_model_and_reasoning_effort():
    rm = roles.chosen(None, StepKind.BUILD)
    cfg = sdk_adapter.Session(
        StepKind.BUILD, Path(), "s1", "m", resume=False, policy=Policy(Path(), ()), observe=Worktree, checks=(),
        model=rm.model, effort=rm.effort,
    )  # fmt: skip
    opts = sdk_adapter._Step(cfg, SimpleNamespace(call_soon_threadsafe=lambda *_: None)).options()  # noqa: SLF001
    assert (opts["model"], opts["reasoning_effort"]) == ("gpt-6-luna", "max")


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
        record = HostRecord(url="http://127.0.0.1:9/", token="tok", pid=1, started_at=NOW)  # noqa: S106

    store = Store(tmp_path)
    store.write_profile(rules(strict, resolution))
    app = TestClient(
        api.create_app(store, "t", Host()), base_url="http://127.0.0.1", headers={"authorization": "Bearer t"}
    )
    assert app.get("/api/next/project").json() == {"notes": expected}
    assert app.get("/api/next/project", headers={"authorization": "Bearer x"}).status_code == 401


def test_unknown_rules_give_no_note():
    assert profile.notes(Profile()) == []
