"""Challenge-round records and settings (TD-208, TD-209, TD-211): pinned policies and stable finding IDs."""

from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from owlbear_delivery_next.change_contracts.models import Brief, Change, Task
from owlbear_delivery_next.change_contracts.round_records import RoundLoop, RoundPolicy, parse
from owlbear_delivery_next.change_flow import disputes
from owlbear_delivery_next.local_system.codebase import CURRENT
from owlbear_delivery_next.project_host import api
from owlbear_delivery_next.project_host.host import HostRecord
from owlbear_delivery_next.settings import rounds
from owlbear_delivery_next.settings.config import CONFIG_FORMAT, Agent, FinalReview, GlobalLayer, Layer, resolve
from owlbear_delivery_next.state_store.store import Store
from owlbear_delivery_next.workflow_steps import review

AUTH = {"authorization": "Bearer t"}


class Host:
    maintenance = None
    wake = SimpleNamespace(set=lambda: None)
    record = HostRecord(url="http://127.0.0.1:9/", token="tok", pid=1, started_at=datetime.now(UTC), code=CURRENT)  # noqa: S106


def test_the_owners_defaults_are_three_rounds_ten_findings_four_and_seven():
    assert RoundPolicy().model_dump() == {"max_rounds": 3, "max_findings": 10, "last_round_at": 4, "ask_owner_at": 7}


@pytest.mark.parametrize(
    "values",
    [
        {"last_round_at": 7},  # not below ask owner at
        {"ask_owner_at": 11},  # above max findings
        {"max_findings": 21},  # above a review result's cap
        {"max_rounds": 0},
    ],
)
def test_a_policy_keeps_its_thresholds_in_order(values):
    with pytest.raises(ValidationError):
        RoundPolicy(**values)


def test_the_final_review_uses_the_builders_values_unless_its_own_are_set():
    builder = Layer(agents={"builder": Agent(max_rounds=5)})
    s = resolve(None, builder)
    assert (s.final_review.max_rounds, s.sources["final_review.max_rounds"]) == (5, "builder")
    own = resolve(GlobalLayer(final_review=FinalReview(max_rounds=4)), builder)
    assert (own.final_review.max_rounds, own.sources["final_review.max_rounds"]) == (4, "global")
    assert rounds.policy(own, rounds.FINAL).max_rounds == 4
    assert rounds.policy(own, "t1").max_rounds == 5


def test_layers_that_do_not_combine_are_refused_on_save_and_stop_a_run(tmp_path):
    store = Store(tmp_path / "store")
    store.global_path = tmp_path / "global.json"
    c = TestClient(api.create_app(store, "t", Host()), base_url="http://127.0.0.1", headers=AUTH)
    got = c.get("/api/next/config").json()
    layer = {"format": CONFIG_FORMAT, "agents": {"builder": {"ask_owner_at": 6}}}
    assert c.put("/api/next/config/global", json={"rev": got["global_rev"], "layer": layer}).status_code == 200
    got = c.get("/api/next/config").json()
    clash = {"format": CONFIG_FORMAT, "agents": {"builder": {"last_round_at": 6}}}  # valid alone, not over the global
    assert c.put("/api/next/config/project", json={"rev": got["project_rev"], "layer": clash}).status_code == 422
    fits = {"format": CONFIG_FORMAT, "agents": {"builder": {"last_round_at": 5}}}
    assert c.put("/api/next/config/project", json={"rev": got["project_rev"], "layer": fits}).status_code == 200
    got = c.get("/api/next/config").json()
    under = {"format": CONFIG_FORMAT, "agents": {"builder": {"ask_owner_at": 5}}}  # valid alone, not under the project
    assert c.put("/api/next/config/global", json={"rev": got["global_rev"], "layer": under}).status_code == 422
    path = Path(store.config_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(Layer.model_validate(clash).model_dump_json())  # written by another tool
    with pytest.raises(Exception, match="do not combine"):
        store.settings()


def test_a_loop_pins_its_policy_when_it_starts():
    c = Change(slug="c1", brief=Brief(version=1))
    first = rounds.loop(c, "t1", resolve(None, Layer()))
    later = rounds.loop(c, "t1", resolve(None, Layer(agents={"builder": Agent(max_rounds=9)})))
    assert (later is first, later.policy.max_rounds) == (True, 3)


def test_finding_ids_continue_across_rounds_and_survive_packing():
    lp = RoundLoop(subject="t1", policy=RoundPolicy(), round=1)
    one = lp.raise_findings(["a.txt:1: p - fix: f", "a.txt:2: q - fix: g"])
    lp.round = 2
    two = lp.raise_findings(["a.txt:3: r - fix: h"], [["t1"]])
    assert [(f.id, f.raised, f.tasks) for f in [*one, *two]] == [("F1", 1, []), ("F2", 1, []), ("F3", 2, ["t1"])]
    long = lp.raise_findings([f"a.txt:{i}: {'x' * 1500} - fix: y" for i in range(4, 7)])
    parts = review.pack([f.line for f in [two[0], *long]])
    keys = [list(disputes.keyed(Task(id="t", title="fix", origin="review", detail=p))) for p in parts]
    assert keys == [["F3", "F4", "F5"], ["F6"]]
    assert parse("- F12: a.txt:1: p - fix: f") == ("F12", "a.txt:1: p - fix: f")
    assert parse("- a.txt:1: p - fix: f") is None
