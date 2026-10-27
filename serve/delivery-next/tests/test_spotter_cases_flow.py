"""The Spotter cases' seed from the pilot's saved cards, the retro-review check, publication, the job and commands."""

from __future__ import annotations

import asyncio
import json
import subprocess
import threading
from types import SimpleNamespace
from typing import TYPE_CHECKING, Any

import pytest

from owlbear_delivery_next.commands import cli
from owlbear_delivery_next.improvement import case_intake, case_replay, case_review, cases, pilot_seed
from owlbear_delivery_next.improvement.cases import CaseError
from owlbear_delivery_next.improvement.credit_meter import Meter
from owlbear_delivery_next.local_system.data_repo import DataRepo
from owlbear_delivery_next.local_system.slots import Slots
from owlbear_delivery_next.machine_host import cases_job
from owlbear_delivery_next.runtimes import retro_review

if TYPE_CHECKING:
    from pathlib import Path


def saved(mid: str, session: str, family: str, *, hand_off: bool = False, decisions: bool = False) -> dict[str, Any]:
    """A pilot moment's saved card, in the pilot's own (old) shape."""
    last = (
        {
            "event_index": 50,
            "event_id": "e50",
            "at": "2026-10-24T10:00:00Z",
            "type": "assistant_message",
            "text": "Done: the first half works; the rest is for later.",
        }
        if hand_off
        else {
            "event_index": 49,
            "event_id": "e49",
            "at": "2026-10-24T10:00:00Z",
            "type": "tool",
            "tool": "bash",
            "args": "uv run pytest",
            "ok": False,
            "exit": 1,
            "result_excerpt": "1 failed",
            "completed_event_index": 50,
        }
    )
    return {
        "id": mid,
        "family": family,
        "split": "fresh",
        "stratum": "interactive",
        "source": {
            "session": session,
            "cutoff_event_index": 50,
            "cutoff_event_id": "e50",
            "cutoff_at": "2026-10-24T10:00:00Z",
        },
        "intent": {
            "kind": "interactive",
            "role": "owner",
            "messages": [
                {"event_index": 1, "at": "2026-10-24T09:00:00Z", "text": "Build all of it; mail me at a@b.example"},
                {"event_index": 30, "at": "2026-10-24T09:30:00Z", "text": "continue"},
            ],
        },
        "last_actions": [last],
        "evidence": [{"event_id": "e10", "tool": "bash", "why": "test", "output_chars": 900}],
        "context_gaps": ["workspace/custom instructions are not in the event log"],
        "owner_answers": [],
        "agent_plan": [{"at": "2026-10-24T09:31:00Z", "role": "first reply", "text": "I'll build it."}],
        "timing": {
            "now": "2026-10-24T10:00:00Z",
            "minutes_since_owner_message": 30,
            "minutes_since_agent_changed_a_file": 2,
            "minutes_waiting_in_last_30": 0,
        },
        "open_work": {"plan_open_rows": ["#9 the rest"]} if not decisions else {},
        **({"decisions": [{"id": "D-1", "refs": "TD-1", "statement": "keep it small"}]} if decisions else {}),
    }


def pilot(folder: Path) -> Path:
    """A pilot folder: five hindsight moments, each verdict, both split files."""
    rows = [
        ("wr-f-should1", "should"),
        ("wr-p-759028", "should"),
        ("wr-f-cns", "could-not-should"),
        ("wr-f-noi", "no-issue"),
        ("wr-p-b75e11", "unknown"),
    ]
    hs = [{"id": m, "verdict": v, "problem": f"problem {m}", "why": f"why {m}", "cost": "minor"} for m, v in rows]
    (folder / "hindsight.jsonl").write_text("".join(json.dumps(r) + "\n" for r in hs))
    cards = [
        saved("wr-f-should1", "s1", "session:s1", hand_off=True),
        saved("wr-p-759028", "s2", "session:s2", decisions=True),
        saved("wr-f-cns", "s3", "session:s3"),
        saved("wr-f-noi", "s4", "session:s4"),
        saved("wr-p-b75e11", "s5", "session:s5"),
    ]
    (folder / "moments-fresh-cards.jsonl").write_text("".join(json.dumps(c) + "\n" for c in cards))
    for name in ("moments-dev-v2p.jsonl", "moments-holdout-v2p.jsonl", "moments-fresh2-cards.jsonl"):
        (folder / name).write_text("")
    split = {
        "sessions": {"s1": {"family": "session:s1", "split": "holdout"}, "s3": {"family": "session:s3", "split": "dev"}}
    }
    (folder / "split.json").write_text(json.dumps(split))
    (folder / "eval-ids.json").write_text(json.dumps({"dev": ["wr-p-759028"], "holdout": []}))
    return folder


CALLS = {"wr-f-should1": "hand-off-fitness", "wr-p-759028": "course-and-constraints"}


def by_moment() -> dict[str, str]:
    return {cases.fact(c)["provenance"]["pilot"]["moment"]: c for c in cases.current()["cases"]}


def test_the_seed_maps_saved_cards_and_names_what_they_lack(tmp_path) -> None:
    got = pilot_seed.seed(pilot(tmp_path), CALLS, "owner")
    assert got == {"seeded": 4, "already": 0, "left_out": ["wr-p-b75e11"]}  # unknown is never a positive
    ids, cur = by_moment(), cases.current()["cases"]
    assert {m: cur[c]["call"] for m, c in ids.items()} == {
        "wr-f-should1": "hand-off-fitness",
        "wr-p-759028": "course-and-constraints",
        "wr-f-cns": "none",
        "wr-f-noi": "none",
    }
    assert all(e["stage"] == "candidate" for e in cur.values())
    assert cases.fact(ids["wr-p-759028"])["unscored"].startswith("TD-435")
    hand_off, other = cases.card(ids["wr-f-should1"]), cases.card(ids["wr-f-cns"])
    assert (hand_off["moment"]["kind"], other["moment"]["kind"]) == ("hand-off", "a completed action")
    assert hand_off["intent"]["task"] == "Build all of it; mail me at <email>"  # cleaned as a live card is
    assert hand_off["intent"]["later_requests"] == ["continue"]
    assert hand_off["evidence"] == []
    assert any("evidence outputs were not saved" in g for g in hand_off["gaps"])
    assert "the decisions in force were not given at this moment" in hand_off["gaps"]
    assert "D-1 (TD-1): keep it small" in cases.card(ids["wr-p-759028"])["decisions"]
    assert other["recent"][-1]["result"] == "1 failed"


def test_the_seed_keeps_both_pilot_splits_assigns_the_rest_once_and_adds_nothing_twice(tmp_path) -> None:
    folder = pilot(tmp_path)
    pilot_seed.seed(folder, CALLS, "owner")
    ids = by_moment()
    assert cases.fact(ids["wr-f-should1"])["reserve"] is True  # split.json's holdout
    assert cases.fact(ids["wr-f-cns"])["reserve"] is False  # split.json's dev
    assert cases.fact(ids["wr-p-759028"])["reserve"] is False  # eval-ids.json's dev
    fams = case_intake.families()
    assert fams["session:s1"]["how"] == "the pilot's split"
    assert fams["session:s4"]["how"] == "hashed once"
    before = (cases.place() / "families.json").read_text()
    assert pilot_seed.seed(folder, CALLS, "owner")["seeded"] == 0
    assert (cases.place() / "families.json").read_text() == before


def test_the_seed_never_guesses_a_should_moments_category(tmp_path) -> None:
    with pytest.raises(CaseError, match="wr-p-759028"):
        pilot_seed.seed(pilot(tmp_path), {"wr-f-should1": "hand-off-fitness"}, "owner")
    assert cases.current()["n"] == 0


def test_the_synthetic_cases_are_cards_of_todays_shape_for_the_missing_categories() -> None:
    pilot_seed.synthetic("owner")
    cur = cases.current()["cases"]
    calls = sorted(e["call"] for e in cur.values())
    assert calls.count("outside-state-changes") == 2
    assert calls.count("irreversible-harm") == 2
    for cid in cur:
        f = cases.fact(cid)
        assert (f["source"], f["reserve"], f["assumption"]) == ("synthetic", False, "synthetic-cases-1")
        assert {"intent", "moment", "recent", "gaps"} <= set(cases.card(cid))
    assert pilot_seed.synthetic("owner") == {"seeded": 0, "already": 6}


def spend(meter: Meter, cost: float | None) -> None:
    share = meter.part()
    share.call(cost)
    share.ended(cost, confirmed=True)


def asker(answers: list[str], spent: float = 0.1, during: Any = None):
    seen: list[str] = []

    async def ask(message: str, meter: Meter) -> str:
        seen.append(message)
        if during:
            during()
        spend(meter, spent)
        return answers[len(seen) - 1]

    return ask, seen


def candidates(n: int) -> list[str]:
    out = []
    for i in range(n):
        cid = cases.freeze({"intent": {"task": f"t{i}"}}, {"source": "pilot", "family": f"session:{i}"})
        cases.commit(
            cases.current()["n"],
            {cid: {"stage": "candidate", "call": "none", "why": f"w{i}", "example": "", "review": None}},
            "t",
            "add",
        )
        out.append(cid)
    return out


def check_request(ids: list[str]) -> dict[str, Any]:
    cur = cases.current()["cases"]
    return {
        "id": "r-check",
        "kind": "check",
        "at": "t",
        "by": "owner",
        "ids": {c: cases.content(c, cur[c]) for c in ids},
    }


def test_a_check_promotes_only_what_the_card_supports() -> None:
    a, b, c = candidates(3)
    ask, seen = asker(['{"supported": true, "note": "silence fits"}', '{"supported": false, "note": "no"}', "huh"])
    out = asyncio.run(case_review.check(check_request([a, b, c]), ask, Meter(10, "retro-run")))
    cur = cases.current()["cases"]
    assert [cur[x]["stage"] for x in (a, b, c)] == ["test", "candidate", "candidate"]
    assert cur[a]["review"]["by"] == "retro-review"
    assert out["reviews"][c]["result"] == "no usable answer"
    assert '"card": {"intent": {"task": "t0"}}' in seen[0]


def test_a_check_never_promotes_a_case_changed_during_its_review_and_stops_at_its_limit() -> None:
    a, b = candidates(2)
    request = check_request([a, b])

    def edit() -> None:
        entry = cases.current()["cases"][a]
        cases.commit(cases.current()["n"], {a: {**entry, "why": "changed"}}, "t", "edit")

    ask, seen = asker(['{"supported": true}', '{"supported": true}'], spent=1.0, during=edit)
    out = asyncio.run(case_review.check(request, ask, Meter(1.0, "retro-run")))
    assert cases.current()["cases"][a]["stage"] == "candidate"
    assert "changed during the review" in out["reviews"][a]["result"]
    assert len(seen) == 1
    assert out["result"].startswith("stopped")


def _git(cwd: Path, *args: str) -> str:
    return subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True).stdout  # noqa: S603, S607 - git on a test repository


def reviewed(call: str = "hand-off-fitness", source: str = "pilot", stage: str = "test") -> str:
    cid = cases.freeze({"intent": {"task": "raw: token ghp_" + "a" * 36}}, {"source": source, "family": "f"})
    entry = {"stage": "candidate", "call": call, "why": "why", "example": "", "review": None}
    cases.commit(cases.current()["n"], {cid: entry}, "t", "add")
    if stage == "test":
        cases.commit(cases.current()["n"], {cid: cases.edited(cid, entry, stage="test", reviewed_by="sol")}, "t", "r")
    return cid


GOOD = '{"situation": "An agent stopped with half the task done.", "call": "hand-off-fitness", "why": "Unfinished."}'


def test_a_reviewed_case_is_published_with_only_its_local_id(shared_repo) -> None:
    root, remote = shared_repo
    cid = reviewed()
    reviewed(source="synthetic")
    reviewed(stage="candidate")
    ask, seen = asker([GOOD])
    out = asyncio.run(case_review.sync(DataRepo(root), ask, Meter(5, "retro-run")))
    assert out["published"] == [cid]
    assert len(seen) == 1
    path = root / "owlbear" / "improvement" / "spotter-cases" / f"{cid}.json"
    body = json.loads(path.read_text())
    assert body["provenance"] == {"local": cid}
    assert body["call"] == "hand-off-fitness"
    assert "ghp_" not in path.read_text()
    assert f"{cid}.json" in _git(remote, "--git-dir=.", "ls-tree", "-r", "--name-only", "main")
    assert asyncio.run(case_review.sync(DataRepo(root), ask, Meter(5, "retro-run")))["published"] == []  # nothing due


@pytest.mark.parametrize(
    ("answer", "why"),
    [
        ('{"situation": "s", "call": "none", "why": "w"}', "changed the call"),
        ('{"situation": "token ghp_' + "b" * 36 + '", "call": "hand-off-fitness", "why": "w"}', "a credential"),
        ('{"situation": "mail x@y.example", "call": "hand-off-fitness", "why": "w"}', "an email address"),
        ('{"situation": "in /Users/someone/app", "call": "hand-off-fitness", "why": "w"}', "a home path"),
        ('{"situation": "s", "call": "hand-off-fitness", "why": "w", "session": "abc"}', "more than"),
        ("no json", "no JSON object"),
        (
            json.dumps({"situation": '{"password": "example-secret"}', "call": "hand-off-fitness", "why": "w"}),
            "a credential",
        ),  # quoted JSON: escaped in the export, found in the decoded text
        (
            json.dumps({"situation": "s", "call": "hand-off-fitness", "why": "config: {'api_key': 'example-key-1'}"}),
            "a credential",
        ),
    ],
)
def test_a_review_that_fails_validation_stays_here_owner_only(shared_repo, answer, why) -> None:
    root, _ = shared_repo
    cid = reviewed()
    ask, _seen = asker([answer])
    out = asyncio.run(case_review.sync(DataRepo(root), ask, Meter(5, "retro-run")))
    assert out["refused"] == [cid]
    state = case_review.state()[cid]
    assert why in state["review"]["why"]
    assert (state["review"]["outcome"], state["remote"]) == ("refused", "")
    assert case_review.due() == ({}, {}, [])  # a refused revision is not reviewed again until the case changes
    assert not (root / "owlbear").exists()
    [kept] = (cases.place() / "rejected").iterdir()
    assert kept.stat().st_mode & 0o777 == 0o600


def test_a_case_removed_during_its_review_is_not_published_and_a_published_one_is_withdrawn(shared_repo) -> None:
    root, _ = shared_repo
    cid = reviewed()

    def remove() -> None:
        cases.commit(cases.current()["n"], {cid: None}, "t", "removed")

    ask, _ = asker([GOOD], during=remove)
    asyncio.run(case_review.sync(DataRepo(root), ask, Meter(5, "retro-run")))
    assert not (root / "owlbear" / "improvement" / "spotter-cases" / f"{cid}.json").exists()
    other = reviewed()
    ask, _ = asker([GOOD])
    asyncio.run(case_review.sync(DataRepo(root), ask, Meter(5, "retro-run")))
    cases.commit(cases.current()["n"], {other: None}, "t", "removed")
    out = asyncio.run(case_review.sync(DataRepo(root), ask, Meter(5, "retro-run")))
    assert out["removed"] == [other]
    assert not (root / "owlbear" / "improvement" / "spotter-cases" / f"{other}.json").exists()


def test_an_unpushed_publication_is_pending_and_pushed_later_without_another_review(shared_repo) -> None:
    root, remote = shared_repo
    url = _git(root, "remote", "get-url", "origin").strip()
    _git(root, "remote", "set-url", "origin", str(root / "nowhere.git"))
    _git(root, "config", "--unset", f"url.{remote}.insteadOf")
    cid = reviewed()
    ask, seen = asker([GOOD])
    out = asyncio.run(case_review.sync(DataRepo(root), ask, Meter(5, "retro-run")))
    assert out["pending"] == [cid]
    assert case_review.state()[cid]["pushed"] is False
    _git(root, "config", f"url.{remote}.insteadOf", url)
    _git(root, "remote", "set-url", "origin", url)
    out = asyncio.run(case_review.sync(DataRepo(root), ask, Meter(5, "retro-run")))
    assert out["published"] == [cid]
    assert len(seen) == 1


def test_a_published_case_removed_while_its_new_revision_is_reviewed_is_withdrawn(shared_repo) -> None:
    root, remote = shared_repo
    cid = reviewed()
    ask, _ = asker([GOOD])
    asyncio.run(case_review.sync(DataRepo(root), ask, Meter(5, "retro-run")))
    path = root / "owlbear" / "improvement" / "spotter-cases" / f"{cid}.json"
    assert path.exists()
    entry = cases.current()["cases"][cid]  # a new revision: another why, reviewed again
    cases.commit(cases.current()["n"], {cid: cases.edited(cid, entry, why="a new why", reviewed_by="sol")}, "t", "e")

    def remove() -> None:
        cases.commit(cases.current()["n"], {cid: None}, "t", "removed")

    ask, _ = asker([GOOD], during=remove)
    out = asyncio.run(case_review.sync(DataRepo(root), ask, Meter(5, "retro-run")))
    assert out["changed"] == [cid]
    assert not path.exists()
    assert f"{cid}.json" not in _git(remote, "--git-dir=.", "ls-tree", "-r", "--name-only", "main")
    state = case_review.state()[cid]
    assert (state["remote"], state["pushed"], state["review"]["outcome"]) == ("", True, "changed")
    assert case_review.due() == ({}, {}, [])


def test_without_a_shared_repository_nothing_is_reviewed() -> None:
    reviewed()
    ask, seen = asker([GOOD])
    out = asyncio.run(case_review.sync(None, ask, Meter(5, "retro-run")))
    assert out["stopped"] == "no shared repository on this machine"
    assert seen == []


def test_publication_stops_at_its_run_credit_limit(shared_repo) -> None:
    root, _ = shared_repo
    reviewed()
    reviewed()
    ask, seen = asker([GOOD, GOOD], spent=2.0)
    out = asyncio.run(case_review.sync(DataRepo(root), ask, Meter(1.5, "retro-run")))
    assert len(seen) == 1
    assert out["stopped"]


class Job:
    """A cases job with fakes for its sessions and limits."""

    def __init__(self, monkeypatch, limits: dict[str, float | None] | None = None) -> None:
        self.looks: list = []
        self.asks: list = []
        given = {"replay": 10.0, "retro": 5.0, "look": 1.0} if limits is None else limits
        monkeypatch.setattr(cases_job, "limits", lambda: given)
        monkeypatch.setattr(cases_job, "role", lambda _name: cases_job.RoleModel(model="m", effort="medium"))
        slots = Slots(lambda: 1)
        slots.open()
        self.paused = False

        async def looked(_card, prompt, meter, _spot) -> dict[str, Any]:
            self.looks.append(prompt.hash)
            spend(meter, 0.1)
            return {"category": "none", "note": ""}

        async def asked(message, meter, _role) -> str:
            self.asks.append(message)
            spend(meter, 0.1)
            return GOOD

        self.job = cases_job.CasesJob(
            slots, paused=lambda: self.paused, looked=looked, asked=asked, shared=lambda: None
        )


def queue_regression() -> str:
    for i in range(2):
        cid = reviewed(call="none")
        assert i is not None
        assert cid
    chosen = reviewed()
    cur = cases.current()
    edits = {chosen: cases.edited(chosen, cur["cases"][chosen], stage="example", example="a moment")}
    return case_replay.ask(case_replay.regression(edits, "owner", "promote"))


def test_the_job_runs_a_queued_replay_once_on_a_slot_and_nothing_while_paused(monkeypatch) -> None:
    j = Job(monkeypatch)
    rid = queue_regression()
    j.paused = True
    j.job.tick(0)
    assert j.looks == []
    assert case_replay.queued()
    j.paused = False
    j.job.tick(0)
    assert len(j.looks) == 4
    assert next(r for r in case_replay.results() if r["id"] == rid)["result"] == "passed"
    j.job.tick(1)
    assert len(j.looks) == 4
    assert not case_replay.queued()
    assert j.job.slots.counts(cases_job.SLOT)[0] == 0


def test_a_replay_taken_by_a_host_that_ended_is_recorded_stopped_never_rerun(monkeypatch) -> None:
    j = Job(monkeypatch)
    rid = queue_regression()
    assert case_replay.take(rid)  # the host ended while it ran
    j.job.tick(0)
    assert j.looks == []
    [r] = [r for r in case_replay.results() if r["id"] == rid]
    assert r["result"].startswith("stopped: OwlBear ended")


def test_an_unset_limit_refuses_the_replay_never_a_built_in_value(monkeypatch) -> None:
    j = Job(monkeypatch, {"replay": None, "retro": 5.0, "look": 1.0})
    rid = queue_regression()
    j.job.tick(0)
    assert j.looks == []
    assert next(r for r in case_replay.results() if r["id"] == rid)["result"].startswith("refused: the replay run")


def test_a_stop_closes_the_running_replays_meter(monkeypatch) -> None:
    j = Job(monkeypatch)
    rid = queue_regression()
    original = j.job.looked

    async def stopping(the_card, prompt, meter, spot) -> dict[str, Any]:
        j.job.stop()
        return await original(the_card, prompt, meter, spot)

    j.job.looked = stopping
    j.job.tick(0)
    assert len(j.looks) == 1
    assert next(r for r in case_replay.results() if r["id"] == rid)["result"].startswith("refused: stopped")


def test_publication_runs_on_its_own_and_no_paid_replay_does(monkeypatch, shared_repo) -> None:
    j = Job(monkeypatch)
    j.job.shared = lambda: DataRepo(shared_repo[0])
    j.job.tick(0)
    assert (j.looks, j.asks) == ([], [])  # nothing queued, nothing due
    reviewed()
    j.job.tick(1000)
    assert len(j.asks) == 1
    assert j.looks == []
    assert next(r for r in case_replay.results() if r["kind"] == "publication")["published"]


def test_a_pause_that_comes_while_the_slot_is_granted_leaves_the_request_queued(monkeypatch) -> None:
    j = Job(monkeypatch)
    rid = queue_regression()
    asked = iter([False])  # the pass begins unpaused; the pause comes before admission
    j.job.paused = lambda: next(asked, True)
    j.job.tick(0)
    assert j.looks == []
    assert [r["id"] for r in case_replay.queued()] == [rid]
    assert j.job.slots.counts(cases_job.SLOT)[0] == 0
    j.job.paused = lambda: False
    j.job.tick(1)
    assert len(j.looks) == 4


def test_a_failed_check_is_kept_with_its_spend_and_never_rerun(monkeypatch) -> None:
    j = Job(monkeypatch)
    calls: list = []

    async def failing(_text, meter, _role) -> str:
        calls.append(1)
        spend(meter, 0.3)
        raise TimeoutError

    j.job.asked = failing
    cid = reviewed(stage="candidate")
    request = {"id": "r-check1", "kind": "check", "at": "t", "by": "owner",
               "ids": {cid: cases.content(cid, cases.current()["cases"][cid])}}  # fmt: skip
    case_replay.ask(request)
    j.job.tick(0)
    j.job.tick(1)
    assert calls == [1]
    [kept] = [r for r in case_replay.results() if r["id"] == "r-check1"]
    assert kept["result"].startswith("failed: TimeoutError")
    assert kept["credits"]["credits"] == pytest.approx(0.3)
    assert not case_replay.queued()
    assert not list((cases.place() / "queue").glob("*.taken"))


def test_a_failed_publication_is_kept_with_its_spend(monkeypatch, shared_repo) -> None:
    j = Job(monkeypatch)
    j.job.shared = lambda: DataRepo(shared_repo[0])

    async def failing(_text, meter, _role) -> str:
        spend(meter, 0.2)
        msg = "the runtime went away"
        raise RuntimeError(msg)

    j.job.asked = failing
    reviewed()
    j.job.tick(1000)
    [kept] = [r for r in case_replay.results() if r["kind"] == "publication"]
    assert kept["result"].startswith("failed: RuntimeError")
    assert kept["credits"]["credits"] == pytest.approx(0.2)


def test_the_job_counts_in_what_a_stop_waits_for(monkeypatch) -> None:
    j = Job(monkeypatch)
    queue_regression()
    seen: list = []
    original = j.job.looked

    async def watching(the_card, prompt, meter, spot) -> dict[str, Any]:
        seen.append(j.job.working())
        return await original(the_card, prompt, meter, spot)

    j.job.looked = watching
    j.job.tick(0)
    assert seen[0][0].startswith("Spotter cases: r-")
    assert j.job.working() == []
    stop = threading.Event()
    stop.set()
    j.job.loop(stop, lambda: 0.0)  # a stopped machine's loop ends at once


def test_the_commands_write_moves_and_queue_a_paid_one(capsys) -> None:
    cid = reviewed(call="none")
    reviewed(call="none")
    assert cli.main(["cases", "move", cid, "example", "--example", "a moment"]) == 0
    assert "queued r-" in capsys.readouterr().out
    assert cases.current()["cases"][cid]["stage"] == "test"
    assert cli.main(["cases", "move", cid, "candidate"]) == 0
    assert cases.current()["cases"][cid]["stage"] == "candidate"
    assert cli.main(["cases", "rollback", "999"]) == 1
    assert "refused: there is no version 999" in capsys.readouterr().out
    assert cli.main(["cases", "check"]) == 0
    assert [r["kind"] for r in case_replay.queued()] == ["regression", "check"]
    assert cli.main(["cases", "list"]) == 0
    assert cli.main(["improvement", "reset"]) == 0
    assert "retired:" in capsys.readouterr().out


def test_a_retro_review_session_is_charged_as_it_reports_and_aborted_at_its_runs_limit(  # noqa: C901 - its fakes
    monkeypatch,
) -> None:
    made: dict[str, Any] = {"aborted": False}

    def usage(nano: float) -> SimpleNamespace:
        cost = SimpleNamespace(copilot_usage=SimpleNamespace(total_nano_aiu=nano))
        return SimpleNamespace(type="assistant.usage", data=cost)

    class Session:
        session_id = "review-1"

        def __init__(self, on_event: Any) -> None:
            self.on_event = on_event
            self.rpc = SimpleNamespace(usage=SimpleNamespace(get_metrics=self.metrics))
            self.done = asyncio.Event()

        async def metrics(self) -> Any:
            return SimpleNamespace(total_nano_aiu=1.2e9)

        async def send_and_wait(self, _message: str, **_kw: Any) -> None:
            self.on_event(usage(1.2e9))  # one billed call past the run's limit
            await self.done.wait()  # the turn goes on until it is aborted

        async def abort(self) -> None:
            made["aborted"] = True
            self.done.set()

        async def disconnect(self) -> None:
            pass

    class Client:
        def __init__(self, **_kw: Any) -> None:
            pass

        async def start(self) -> None:
            pass

        async def create_session(self, **kw: Any) -> Session:
            return Session(kw["on_event"])

        async def stop(self) -> None:
            pass

    monkeypatch.setattr(retro_review, "CopilotClient", Client)
    monkeypatch.setattr(retro_review, "cli_path", lambda: "/bin/false")
    run_meter = Meter(1.0, "retro-run")
    role = cases_job.RoleModel(model="m", effort="medium")
    assert asyncio.run(retro_review.asked("review this", run_meter, role)) == ""
    assert made["aborted"] is True
    report = run_meter.report()
    assert (report["credits"], report["stopped"], report["stopped_by"]) == (pytest.approx(1.2), "reached", "retro-run")
    with pytest.raises(RuntimeError, match="no review starts"):
        asyncio.run(retro_review.asked("another", run_meter, role))
