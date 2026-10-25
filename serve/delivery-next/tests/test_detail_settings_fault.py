"""The Change detail page still loads, with its owner controls, while a settings layer is unreadable (R15, review)."""

import subprocess

import pytest
from fastapi.testclient import TestClient

from owlbear_delivery_next.change_contracts.models import Change, Names, Plan, Step, StepKind, Task
from owlbear_delivery_next.change_flow.status import Activity
from owlbear_delivery_next.project_host import api
from owlbear_delivery_next.settings import config
from owlbear_delivery_next.state_store.store import Store

AUTH = {"authorization": "Bearer " + "t"}


class Host:
    wake = type("W", (), {"set": lambda _self: None})()
    record = None

    def activity(self, _slug):
        return Activity(host_up=True)


@pytest.fixture
def store(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path / "home"))  # the machine layer lives under this temporary home only
    for args in (
        ["init", "-q"],
        ["-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "--allow-empty", "-m", "i"],
    ):
        subprocess.run(["git", *args], cwd=tmp_path, check=True, capture_output=True)  # noqa: S603, S607
    opened = Store.open(tmp_path)
    c = Change(
        slug="c1",
        plan=Plan(tasks=[Task(id="t1", title="greet", checks=["npm test"])]),
        step=Step(kind=StepKind.BUILD, task="t1"),
        names=Names(worktree=str(tmp_path)),
    )
    with opened.lock("c1") as lock:
        opened.write(lock, c)
    return opened


def detail(store: Store) -> dict:
    client = TestClient(api.create_app(store, "t", Host()), base_url="http://127.0.0.1", headers=AUTH)
    got = client.get("/api/next/changes/c1")
    assert got.status_code == 200
    return got.json()


def test_malformed_project_settings_keep_the_detail_page_and_report_the_fault(store):
    store.config_path.parent.mkdir(parents=True, exist_ok=True)
    store.config_path.write_text("{not json")

    body = detail(store)

    assert body["settings_fault"]
    assert (body["asks_merge"], body["deletes_branch"]) == (None, None)  # unreadable is not a configured value
    assert body["paused"] is False


def test_a_cross_layer_invalid_policy_keeps_the_detail_page_and_reports_the_fault(store):
    bad = config.Agent(max_rounds=3, max_findings=10, last_round_at=8, ask_owner_at=7)  # rounds do not hold together
    store.update_config(lambda cur: cur.model_copy(update={"agents": {"shaper": bad}}))

    body = detail(store)

    assert body["settings_fault"]
    assert (body["asks_merge"], body["deletes_branch"]) == (None, None)
