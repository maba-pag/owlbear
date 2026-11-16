"""The summary/finding publication boundary survives unknown write outcomes."""

from copy import deepcopy

import pytest

from owlbear_delivery_next.audit_runs import report_publish

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
