"""The read-back queue (TD-427): the reason a read-back waits, and the queue's order."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from pydantic import ValidationError

from owlbear_decisions import ReadBackKind, State, new_id, queue, queued
from owlbear_decisions.readbacks import CONFLICT
from owlbear_decisions.storage import parse, serialize

AT = datetime(2026, 10, 20, tzinfo=UTC)


def waiting(make, kind: str, why: str = "New evidence.", **changes):
    return make(id=new_id(), read_back="pending", read_back_why=why, read_back_kind=kind, **changes)


def test_a_pending_read_back_needs_why_and_kind_an_answered_one_keeps_them_and_none_has_none(make):
    held = waiting(make, "blocked", "  The vendor changed its terms.  ")
    assert (held.read_back_why, held.read_back_kind) == ("The vendor changed its terms.", ReadBackKind.BLOCKED)
    assert parse(serialize(held)) == held
    for wrong in (
        {"read_back_why": "x"},
        {"read_back_kind": "safety"},
        {"read_back_why": " ", "read_back_kind": "safety"},
    ):
        with pytest.raises(ValidationError, match="pending read-back needs"):
            make(read_back="pending", **wrong)
    answered = held.model_copy(update={"read_back": "2026-10-20"})
    assert parse(serialize(answered)) == answered  # the reason it was answered on stays
    assert make(read_back="2026-10-20").read_back_why == ""
    for wrong in ({"read_back_why": "x"}, {"read_back_kind": "safety"}):
        with pytest.raises(ValidationError, match="belong to a read-back"):
            make(read_back="none", **wrong)
    with pytest.raises(ValidationError):
        make(read_back="pending", read_back_why="x", read_back_kind="someday")


def test_the_rule_revision_ignores_the_read_back_and_the_revision_does_not(make):
    rule = make()
    held = make(id=rule.id, read_back="pending", read_back_why="New data.", read_back_kind="safety")
    answered = held.model_copy(update={"read_back": "2026-10-20"})
    inherited = make(id=rule.id, inherited=True)
    assert {rule.rule_revision, held.rule_revision, answered.rule_revision, inherited.rule_revision} == {
        rule.rule_revision}  # fmt: skip
    assert len({rule.revision, held.revision, answered.revision, inherited.revision}) == 4
    assert make(id=rule.id, statement="Something else.").rule_revision != rule.rule_revision


def test_a_file_without_the_reason_loads_and_keeps_its_revision(make):
    plain = make()
    text = serialize(plain)
    assert "read_back_why" not in text
    assert "read_back_kind" not in text
    assert "read_back_why" not in plain.content()
    assert parse(text).revision == plain.revision


def test_the_queue_orders_by_kind_then_oldest_and_puts_ignored_ones_last(make):
    later = AT + timedelta(days=1)
    old_gap = waiting(make, "improvement", created_at=AT)
    new_doubt = waiting(make, "uncertain", created_at=later)
    old_doubt = waiting(make, "uncertain", created_at=AT)
    danger = waiting(make, "safety", created_at=later)
    flagged = make(id=new_id(), conflict=True, created_at=later)
    quiet = make(id=new_id())
    gone = waiting(make, "safety", state=State.REPLACED)

    found = queue([old_gap, new_doubt, quiet, old_doubt, flagged, danger, gone])
    assert [q.decision for q in found] == [danger, flagged, old_doubt, new_doubt, old_gap]
    last = queue([old_gap, new_doubt, old_doubt, danger], last={danger.id})
    assert [q.decision for q in last] == [old_doubt, new_doubt, old_gap, danger]


def test_a_conflict_is_queued_as_blocked_work_without_being_written(make):
    flagged = make(conflict=True)
    q = queued(flagged)
    assert (q.kind, q.why, q.derived) == (ReadBackKind.BLOCKED, CONFLICT, True)
    assert flagged.read_back == "2026-10-20"  # nothing on the decision changed
    both = queued(waiting(make, "improvement", conflict=True))
    assert (both.kind, both.why, both.derived) == (ReadBackKind.BLOCKED, "New evidence.", False)
    assert queued(waiting(make, "safety", conflict=True)).kind is ReadBackKind.SAFETY
    assert queued(make()) is None
