"""Suppression review through owner routes, real pinned trees, the judge Gate and Backlog custody."""

import contextlib
import json
import threading
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from owlbear_quality import ledger

from owlbear_delivery_next.audit_runs import job, record, suppression_items
from owlbear_delivery_next.change_contracts import exception_tools
from owlbear_delivery_next.change_contracts.models import Change
from owlbear_delivery_next.change_contracts.profile_record import Profile, ProfileEntry
from owlbear_delivery_next.change_flow import worktree
from owlbear_delivery_next.github.provider import FailureCode, ProviderError
from owlbear_delivery_next.local_system.data_repo import DataRepo
from owlbear_delivery_next.local_system.processes import Termination
from owlbear_delivery_next.project_host import audit_routes
from owlbear_delivery_next.runtimes.results import Gate
from owlbear_delivery_next.runtimes.session_result import Run
from owlbear_delivery_next.settings import profile
from owlbear_delivery_next.state_store import backlog, spend_ledger
from owlbear_delivery_next.state_store.store import Lock, Store
from owlbear_delivery_next.workflow_steps import sessions

BASE = "/maintenance/audits/suppressions"


@pytest.fixture
def review(tmp_path, change_repo, shared_repo, monkeypatch, github):
    store = Store(tmp_path / "store", DataRepo(shared_repo[0]), "fixture")
    store.write_profile(Profile(entries={profile.DEFAULT: ProfileEntry(state="known", value="main")}))
    audits = job.Audits(store)
    audits.repo = change_repo
    folder = tmp_path / "review"

    @contextlib.contextmanager
    def allocated(_prefix):
        folder.mkdir(exist_ok=True)
        yield folder

    audits.maintenance = SimpleNamespace(workspace=allocated, retained=lambda _path: False, holding=lambda _kind: [])
    monkeypatch.setattr(job.github_writer, "of", lambda *_args: SimpleNamespace(access=lambda: None))
    pinned = []

    def pin(repo, branch, _access):
        assert branch == "main"
        commit = worktree.head(repo)
        pinned.append(commit)
        return commit

    monkeypatch.setattr(job.workspace, "pin", pin)
    calls, script = [], {"fail": 0, "refuse": True}

    def run(cfg):
        assert cfg.role == "quality-judge"
        assert not cfg.policy.write
        assert cfg.worktree == folder
        assert spend_ledger.where().job == "Suppression review"
        context = json.loads((cfg.worktree / "exceptions-context.json").read_text())
        assert worktree.head(cfg.worktree / "repo") == context["commit"] == pinned[-1]
        assert context["for"] == "maintenance.review"
        calls.append(context)
        done = Run(cfg.session_id, model_check="verified", termination=Termination(confirmed=True))
        if len(calls) == script["fail"]:
            if script.get("raises"):
                done.usage_unread = "fixture usage unreadable"
                raise sessions.UsageUnreadError(done)
            done.ending, done.detail = "error", "fixture model connection ended"
            return done
        gate = Gate(cfg, done, lambda **_e: None, lambda: None)
        assert gate.call(
            exception_tools.SUBMIT,
            {
                "verdicts": [
                    {
                        "id": i["id"],
                        "verdict": "refused" if script["refuse"] else "accepted",
                        "reason": "The code can meet the rule. Full fixture reason.",
                    }
                    for i in context["items"]
                ]
            },
        )[1]
        return done

    audits.run = run
    host = SimpleNamespace(
        launching=threading.RLock(), closed=lambda: False, updating=lambda: "", draining=lambda: False
    )
    app = FastAPI()
    app.include_router(audit_routes.router(audits, host))
    return SimpleNamespace(
        github=github, store=store, audits=audits, client=TestClient(app), calls=calls, script=script, pinned=pinned
    )


def inventory(review, number):
    repo = review.audits.repo
    source = "\n".join(f"v_{n} = {n}  # noqa: F841" for n in range(number)) + "\n"
    (repo / "source.py").write_text(source)
    (repo / "ruff.toml").write_text('ignore = ["F841"]\n')
    worktree.git(repo, "add", "source.py", "ruff.toml")
    worktree.git(repo, "commit", "-qm", "fixture suppressions")
    return suppression_items.scan(repo, ())


def start(review):
    reply = review.client.post(BASE, json={})
    assert reply.status_code == 200, reply.text
    review.audits.thread.join()
    return review.audits.read("suppressions")


def verdict(review, group, action):
    reply = review.client.post(f"{BASE}/verdicts", json={"id": group["id"], "action": action})
    assert reply.status_code == 200, reply.text
    return reply.json()["verdicts"]


def test_bounded_runs_continue_and_owner_verdicts_replace_history(review):
    items = inventory(review, 603)
    accepted = items[1]
    row = {
        "verdict": "accepted",
        "reason": "Change judgment",
        "by": "judge",
        "for": "change-one",
        "commit": worktree.head(review.audits.repo),
        "place": accepted["place"],
        "directive": accepted["directive"],
    }
    ledger.add(
        review.store.root,
        [
            row | {"identity": accepted["identity"]},
            row | {"identity": items[2]["identity"], "for": "chat:/checkout:branch"},
            row | {"identity": "removed", "verdict": "refused"},
        ],
    )
    last = start(review)
    assert last["state"] == "done", last["reason"]
    assert last["counts"] == {"held": 604, "accepted": 2, "refused": 600, "unjudged": 2}
    assert len(review.calls) == 10
    assert all(len(c["items"]) == 60 for c in review.calls)
    assert all(i["code"] for c in review.calls for i in c["items"])
    assert not any("code" in i for i in last["inventory"])
    judged = {i["identity"] for c in review.calls for i in c["items"]}
    assert not {accepted["identity"], items[2]["identity"]} & judged
    assert last["commit"] == review.pinned[0]
    second = start(review)
    assert second["counts"]["unjudged"] == 0
    assert len(review.calls[-1]["items"]) == 2
    assert len(review.calls) == 11
    offered = next(a for a in review.client.get("/maintenance/audits").json()["audits"] if a["audit"] == "suppressions")
    assert len(offered["last"]["backlog_entries"]) == 2
    assert "inventory" not in offered["last"]
    assert ledger.counting(review.store.root, "removed")[0]["backlog"] == ""
    groups = review.client.get(f"{BASE}/verdicts").json()["verdicts"]
    refused = next(g for g in groups if g["verdict"] == "refused")
    denied = review.client.post(
        f"{BASE}/verdicts", json={"id": refused["id"], "action": "accept"}, headers={"x-owlbear-use": "chat"}
    )
    assert denied.status_code == 403
    groups = verdict(review, refused, "accept")
    member = refused["members"][0]
    rows = ledger.counting(review.store.root, member["identity"])
    assert rows[-1]["by"] == "owner"
    assert rows[-1]["verdict"] == "accepted"
    history = json.loads((review.store.root / ledger.FILE).read_text())[member["identity"]]
    assert history[member["index"]]["aside"]
    accepted_group = next(g for g in groups if g["verdict"] == "accepted" and g["reason"].startswith("Owner"))
    verdict(review, accepted_group, "again")
    review.script["refuse"] = False
    before = len(review.calls)
    third = start(review)
    assert len(review.calls) > before
    assert third["counts"]["unjudged"] == 1
    assert start(review)["counts"]["unjudged"] == 0
    assert review.client.post(BASE, json={"note": "scope"}).status_code == 409


def test_failed_batch_keeps_verdicts_and_finish_recovers_a_lost_publication(review, monkeypatch, github):
    items = inventory(review, 65)
    review.script["fail"] = 2
    book = backlog.Backlog.of(review.store)
    add = book.add

    def lost(*args, **kwargs):
        entry, _repeated = add(*args, **kwargs)
        monkeypatch.setattr(book, "add", add)
        github.hidden.add(int(entry.id))
        monkeypatch.setattr(backlog, "_recent", {})
        raise ProviderError(FailureCode.RESPONSE_UNKNOWN, "create_issue", "fixture response lost", retry_safe=False)

    monkeypatch.setattr(book, "add", lost)
    monkeypatch.setattr(job.backlog.Backlog, "of", lambda _store: book)
    partial = start(review)
    assert partial["state"] == "publishing"
    assert partial["counts"] == {"held": 66, "accepted": 0, "refused": 60, "unjudged": 6}
    assert "fixture model connection ended" in partial["judging_reason"]
    assert "fixture response lost" in partial["reason"]
    assert partial["findings"][0]["pending"]
    assert len(github.issues) == 1
    shown = review.client.get(f"{BASE}/verdicts").json()["verdicts"][0]
    held = review.client.post(f"{BASE}/verdicts", json={"id": shown["id"], "action": "accept"})
    assert held.status_code == 409
    assert "Finish publishing" in held.text
    assert review.client.post(f"{BASE}/publish", json={}).status_code == 200
    review.audits.thread.join()
    assert "two minutes" in review.audits.read("suppressions")["reason"]
    github.hidden.clear()
    assert review.client.post(f"{BASE}/publish", json={}).status_code == 200
    review.audits.thread.join()
    last = review.audits.read("suppressions")
    assert last["state"] == "failed"
    assert "remain recorded" in last["reason"]
    assert len(review.calls) == 2
    assert len(github.issues) == 1
    assert all(f["number"] for f in last["findings"])
    assert all("type:improvement" in [v["name"] for v in issue["labels"]] for issue in github.issues.values())
    refused = [i["judgment"] for i in suppression_items.joined(review.store.root, items) if i["judgment"]]
    assert len(refused) == 60
    assert all(r["backlog"] for r in refused)
    assert sum(len(m) for m in last["suppression_members"]) == 60
    check_authority_and_readonly(review, monkeypatch)


def test_a_removed_copy_s_verdict_does_not_undo_the_owner_s_action(review):
    item = inventory(review, 1)[0]
    row = {
        "identity": item["identity"],
        "verdict": "refused",
        "reason": "Earlier refusal",
        "by": "judge",
        "for": "review",
        "commit": worktree.head(review.audits.repo),
        "place": "gone.py:1",
        "directive": item["directive"],
    }
    running = Change.model_validate_json((Path(__file__).parent / "fixtures" / "c1_v4_waiting.json").read_text())
    review.store.write(Lock(running.slug), running)
    ledger.add(
        review.store.root,
        [row, row | {"place": item["place"]}, row | {"place": "new.py:1", "verdict": "accepted", "for": running.slug}],
    )
    assert start(review)["counts"]["refused"] == 2
    refused = next(g for g in review.client.get(f"{BASE}/verdicts").json()["verdicts"] if item["place"] in g["places"])
    groups = verdict(review, refused, "accept")
    mine = next(g for g in groups if item["place"] in g["places"])
    assert mine["verdict"] == "accepted"
    verdict(review, mine, "again")
    assert [r["for"] for r in ledger.counting(review.store.root, item["identity"])] == [running.slug]
    covered = next(g for g in review.client.get(f"{BASE}/verdicts").json()["verdicts"] if item["place"] in g["places"])
    held = review.client.post(f"{BASE}/verdicts", json={"id": covered["id"], "action": "again"})
    assert held.status_code == 409
    assert running.slug in held.text


def test_a_raised_session_error_still_publishes_the_completed_batches(review):
    inventory(review, 65)
    review.script.update(fail=2, raises=True)
    last = start(review)
    assert last["state"] == "failed"
    assert "fixture usage unreadable" in last["reason"]
    assert last["findings"]
    assert all(f["number"] for f in last["findings"])


def check_authority_and_readonly(review, monkeypatch):
    before = len(review.calls)
    with monkeypatch.context() as blocked:
        blocked.setattr(
            job.suppression_review.exceptions, "chat_authority", lambda _s: {"failed": "decisions unreadable"}
        )
        failed = start(review)
        assert failed["state"] == "failed"
        assert "decisions unreadable" in failed["reason"]
        assert len(review.calls) == before
        assert record.load(review.store)["suppressions"]["counts"]["refused"] == 60
    run = review.audits.run

    def mutate(cfg):
        worktree.git(review.audits.repo, "tag", "fixture-review-mutation")
        return run(cfg)

    review.audits.run = mutate
    tampered = start(review)
    assert tampered["state"] == "failed"
    assert "fixture-review-mutation" in tampered["reason"]
    assert tampered["counts"]["refused"] == 60
