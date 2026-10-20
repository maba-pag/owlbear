from __future__ import annotations

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from owlbear_decisions.models import Scope, new_id
from owlbear_decisions.storage import parse, serialize

AT = datetime(2026, 10, 20, tzinfo=UTC)


def test_round_trip_keeps_every_field_and_revision(make):
    decision = make()
    text = serialize(decision)
    again = parse(text)
    assert again == decision
    assert again.revision == decision.revision
    assert serialize(again) == text
    assert text.startswith("---\nid: D-")
    assert text.endswith("---\n\nWhy: **speed**.\n\nSecond paragraph.\n")
    assert "revision" not in text


def test_revision_is_stable_and_tracks_content(make):
    assert make().revision == make().revision
    assert len(make().revision) == 64
    assert make(statement="Another wording.").revision != make().revision
    assert make(rationale="  padded  \n").revision == make(rationale="padded").revision
    assert make(consequences="Pages change.").revision != make().revision
    assert parse(serialize(make(consequences="Pages change."))).consequences == "Pages change."


def test_new_id_format_and_seed():
    assert new_id(AT, seed="x") == new_id(AT, seed="x")
    assert new_id(AT, seed="x") != new_id(AT, seed="y")
    assert new_id() != new_id()
    assert new_id(AT, seed="x").startswith("D-")
    assert len(new_id()) == 28
    assert new_id(AT, seed="a") < new_id(datetime(2026, 10, 21, tzinfo=UTC), seed="a")


@pytest.mark.parametrize(
    "changes",
    [
        {"scope": Scope.GLOBAL},
        {"scope": Scope.CHANGE},
        {"scope": Scope.PROJECT, "change": "slug"},
        {"id": "D-123"},
        {"aliases": ("td 1",)},
        {"read_back": "soon"},
        {"read_back": "2026-13-40"},
        {"applies_to": {"paths": ["../outside"]}},
        {"applies_to": {"paths": ["/abs/*.py"]}},
        {"created_at": datetime(2026, 10, 20)},  # noqa: DTZ001 - naive on purpose
        {"links": ({"type": "contradicts", "target": new_id()},)},
    ],
)
def test_schema_refusals(make, changes):
    with pytest.raises(ValidationError):
        make(**changes)


def test_long_statement_and_missing_words_still_load(make):
    decision = make(statement="x" * 300, owner_words=())
    assert parse(serialize(decision)) == decision


def test_unquoted_yaml_dates_are_accepted(make):
    text = serialize(make()).replace("read_back: '2026-10-20'", "read_back: 2026-10-20")
    assert "read_back: 2026-10-20\n" in text
    assert parse(text) == make()
