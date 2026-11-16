"""The summary/finding publication boundary survives unknown write outcomes."""

from copy import deepcopy

import pytest

from owlbear_delivery_next.audit_runs import publish, record, report_publish
from owlbear_delivery_next.github.provider import ProviderError
from owlbear_delivery_next.local_system.data_repo import DataRepo
from owlbear_delivery_next.state_store import backlog, backlog_issues
from owlbear_delivery_next.state_store.store import Store

from .test_audit_runs import _report


def test_summary_first_custody_survives_lost_creation_and_final_edit():
    state = _report()
    state.update(
        verified=True,
        verifier_session="verifier-fixture",
        session="auditor-fixture",
        summary_issue={"number": None, "url": "", "pending": None, "complete": False},
    )
    candidate = state["findings"][0]
    state["findings"] = [dict(candidate, title="Rejected"), candidate, dict(candidate, title="Unsure")]
    state["verdicts"] = [
        {"finding": 1, "verdict": "rejected", "reason": "Already covered.", "decisions": [], "duplicate_of": "#42"},
        {"finding": 2, "verdict": "accepted", "reason": "Confirmed.", "decisions": [], "duplicate_of": ""},
        {"finding": 3, "verdict": "unsure", "reason": "Planning gap.", "decisions": [], "duplicate_of": ""},
    ]
    saved = []

    def save():
        saved.append(deepcopy(state))

    class Interrupted(report_publish.Recorder):
        hidden = False
        lose_creation = True
        lose_edit = True
        opens = 0
        edits = 0

        def find(self, marker):
            return None if self.hidden else super().find(marker)

        def open(self, title, body, *, labels, marker, pending_since):
            self.opens += 1
            receipt = saved[-1]["summary_issue"] if marker.endswith(":summary") else saved[-1]["findings"][1]
            assert receipt["pending"]
            assert receipt["number"] is None
            assert body.endswith(f"<!-- {marker} -->\n")
            if not marker.endswith(":summary"):
                assert saved[-1]["summary_issue"]["number"] == 1
                assert self.issues[1]["url"] in body
                assert marker.endswith(":2")
            issue = super().open(title, body, labels=labels, marker=marker, pending_since=pending_since)
            if self.lose_creation:
                self.lose_creation = False
                self.hidden = True
                msg = "creation response lost"
                raise OSError(msg)
            return issue

        def edit(self, number, body):
            self.edits += 1
            assert saved[-1]["findings"][1]["number"] == 2
            assert not saved[-1]["summary_issue"]["complete"]
            super().edit(number, body)
            if self.lose_edit:
                self.lose_edit = False
                msg = "edit response lost"
                raise OSError(msg)

    sink = Interrupted()

    def publish():
        report_publish.publish(state, sink, save, project="fixture")

    with pytest.raises(OSError, match="creation response lost"):
        publish()
    state = deepcopy(saved[-1])
    assert state["summary_issue"]["number"] is None
    with pytest.raises(RuntimeError, match="two minutes"):
        publish()
    assert sink.opens == 1
    assert len(sink.issues) == 1
    sink.hidden = False
    with pytest.raises(OSError, match="edit response lost"):
        publish()
    state = deepcopy(saved[-1])
    assert state["summary_issue"]["number"] == 1
    assert state["findings"][1]["number"] == 2
    assert not state["summary_issue"]["complete"]
    publish()
    assert saved[-1]["summary_issue"]["complete"]
    assert len(sink.issues) == 2
    assert sink.opens == 3  # Recovery must call open for found-marker sink finalization.
    assert sink.edits == 2
    assert sink.issues[1]["labels"] == ["audit:summary"]
    assert sink.issues[2]["labels"] == ["type:defect", "severity:medium"]
    assert sink.issues[2]["url"] in sink.issues[1]["body"]
    assert sink.issues[1]["url"] in sink.issues[2]["body"]
    publish()
    assert sink.opens == 3
    assert sink.edits == 2


def _interrupt_backlog(store, book, monkeypatch, github):
    create, edit = book.issues.create, book.issues.edit
    fail_link = True

    def lost_creation(title, body, labels):
        assert record.load(store)["doc"]["summary_issue"]["pending"]
        made = create(title, body, labels)
        monkeypatch.setattr(book.issues, "create", create)
        github.hidden.add(made["number"])
        msg = "summary creation response lost"
        raise OSError(msg)

    def lost_edit(number, fields):
        nonlocal fail_link
        persisted = record.load(store)["doc"]
        if number == 1 and fail_link:
            fail_link = False
            assert persisted["findings"][0]["pending"]
            github.hidden.add(3)
            monkeypatch.setattr(backlog, "_recent", {})
            msg = "repeat-link edit interrupted"
            raise OSError(msg)
        answer = edit(number, fields)
        if number == 2:
            assert persisted["findings"][0]["number"] == 3
            assert not persisted["summary_issue"]["complete"]
            monkeypatch.setattr(book.issues, "edit", edit)
            msg = "summary edit response lost"
            raise OSError(msg)
        return answer

    monkeypatch.setattr(book.issues, "create", lost_creation)
    monkeypatch.setattr(book.issues, "edit", lost_edit)


def _check_backlog_report(state, book, github):
    assert state["summary_issue"]["complete"]
    assert len(github.issues) == 3
    assert book.current("1").links == ["3"]
    entry, summary = book.current("3"), github.issues[2]
    assert entry.links == ["1"]
    assert entry.count == 1
    assert [label["name"] for label in summary["labels"]] == ["audit:summary"]
    assert backlog_issues.fields(summary) is None
    assert entry.evidence[:2] == ["audit:run-one:1", summary["html_url"]]
    assert summary["html_url"] in entry.text
    assert github.issues[3]["html_url"] in summary["body"]
    assert summary["body"].endswith("<!-- audit:run-one:summary -->\n")
    assert "Audit: doc" in summary["body"]


def test_backlog_summary_recovery_finishes_repeat_links_and_refuses_public_zero_findings(
    tmp_path, monkeypatch, shared_repo, github
):
    store = Store(tmp_path / "store", DataRepo(shared_repo[0]), "fixture")
    state = _report()
    state.update(
        verified=True,
        verifier_session="verifier-fixture",
        session="auditor-fixture",
        verdicts=[{"finding": 1, "verdict": "accepted", "reason": "Confirmed.", "decisions": [], "duplicate_of": ""}],
        summary_issue={"number": None, "url": "", "pending": None, "complete": False},
    )
    book = backlog.Backlog.of(store)
    earlier, _ = book.add(state["findings"][0]["title"], "earlier observation", "audit", ["audit:earlier:1"])
    book.update(earlier.id, {"kind": "defect", "status": "done"})
    monkeypatch.setattr(publish.backlog.Backlog, "of", lambda _store: book)
    _interrupt_backlog(store, book, monkeypatch, github)

    def attempt():
        publish.findings(store, state, lambda: record.save(store, "doc", state), audit="doc")

    with pytest.raises(OSError, match="summary creation response lost"):
        attempt()
    state = record.load(store)["doc"]
    with pytest.raises(RuntimeError, match="two minutes"):
        attempt()
    assert len(github.issues) == 2
    github.hidden.clear()
    with pytest.raises(OSError, match="repeat-link edit interrupted"):
        attempt()
    state = record.load(store)["doc"]
    with pytest.raises(RuntimeError, match="two minutes"):
        attempt()
    github.hidden.clear()
    with pytest.raises(OSError, match="summary edit response lost"):
        attempt()
    state = record.load(store)["doc"]
    assert not state["summary_issue"]["complete"]
    attempt()
    _check_backlog_report(record.load(store)["doc"], book, github)

    state = dict(
        state,
        id="zero-accepted",
        findings=[],
        verdicts=[],
        summary_issue={"number": None, "url": "", "pending": None, "complete": False},
    )
    github.visibility = "public"
    monkeypatch.setattr(backlog_issues, "_private", {})
    with pytest.raises(ProviderError, match="not private"):
        attempt()
    assert len(github.issues) == 3


def test_oversized_summary_preserves_full_reasons_and_recovers_comment_receipts(
    tmp_path, monkeypatch, shared_repo, github
):
    store = Store(tmp_path / "store", DataRepo(shared_repo[0]), "fixture")
    state = _report()
    candidate = state["findings"][0]
    state.update(
        verified=True,
        verifier_session="verifier-fixture",
        session="auditor-fixture",
        findings=[dict(candidate, title=f"Finding {index}") for index in range(41)],
        verdicts=[
            {
                "finding": index + 1,
                "verdict": "accepted" if index == 0 else "rejected",
                "reason": f"Reason {index}: " + "\u96ea" * 1790,
                "decisions": [],
                "duplicate_of": "",
            }
            for index in range(41)
        ],
        summary_issue={"number": None, "url": "", "pending": None, "complete": False},
    )
    state["verdicts"][1]["reason"] = "<!-- audit:run-one:summary:part:2 -->\n" + state["verdicts"][1]["reason"]
    book = backlog.Backlog.of(store)
    monkeypatch.setattr(publish.backlog.Backlog, "of", lambda _store: book)
    comment, edit = github.comment, book.issues.edit
    hidden, lose_comment, lose_edit = True, True, True

    def interrupted_comment(number, method, params, body):
        nonlocal lose_comment
        if method == "GET" and hidden:
            return 0, []
        answer = comment(number, method, params, body)
        if method == "POST" and lose_comment:
            lose_comment = False
            assert record.load(store)["code"]["summary_parts"][0]["pending"]
            return 502, "comment response lost"
        return answer

    def interrupted_edit(number, fields):
        nonlocal lose_edit
        answer = edit(number, fields)
        if number == 1 and lose_edit:
            lose_edit = False
            msg = "final summary edit response lost"
            raise OSError(msg)
        return answer

    monkeypatch.setattr(github, "comment", interrupted_comment)
    monkeypatch.setattr(book.issues, "edit", interrupted_edit)

    def attempt():
        publish.findings(store, state, lambda: record.save(store, "code", state), audit="code")

    with pytest.raises(ProviderError, match="comment response lost"):
        attempt()
    state = record.load(store)["code"]
    assert state["findings"][0]["number"] == 2
    assert record.unpublished(state) == 1
    planned = [part["body"] for part in state["summary_parts"]]
    with pytest.raises(ProviderError, match="two minutes"):
        attempt()
    assert len(github.comments) == 1
    hidden = False
    monkeypatch.setattr(report_publish, "PART_BYTES", 15_000)
    with pytest.raises(OSError, match="final summary edit response lost"):
        attempt()
    state = record.load(store)["code"]
    assert not state["summary_issue"]["complete"]
    attempt()
    _complete_large_report(record.load(store)["code"], planned, github)


def _complete_large_report(final, planned, github):
    assert final["summary_issue"]["complete"]
    assert record.unpublished(final) == 0
    assert len(github.issues) == 2
    assert len(github.comments) == len(planned)
    assert [part["body"] for part in final["summary_parts"]] == planned
    assert all(part["url"] and part["pending"] is None for part in final["summary_parts"])
    bodies = [issue["body"] for issue in github.issues.values()] + [body for _, body in github.comments]
    assert all(len(body.encode("utf-8")) <= 65_536 for body in bodies)
    details = "".join(body for _, body in github.comments)
    assert all(verdict["reason"] in details for verdict in final["verdicts"][1:])
    assert github.issues[2]["html_url"] in details
    assert github.issues[1]["html_url"] in github.issues[2]["body"]
    assert final["summary_parts"][0]["url"] in github.issues[1]["body"]
