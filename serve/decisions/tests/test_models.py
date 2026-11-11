from __future__ import annotations

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from owlbear_decisions.models import Scope, new_id
from owlbear_decisions.storage import parse, read, serialize, write
from owlbear_decisions.validate import validate

AT = datetime(2026, 10, 20, tzinfo=UTC)


@pytest.mark.parametrize(
    "legacy",
    [
        "",
        "applies_to:\n  paths:\n  - web/**\n  roles:\n  - builder\n",
        "owner_words:\n- text: lint once\n  date: 2026-10-14\n  alias: TD-87\n",
        "inherited: true\n",
    ],
)
def test_legacy_wire_format_round_trips_without_retired_fields(make, tmp_path, legacy):
    decision = make()
    if legacy == "inherited: true\n":
        decision = make(inherited=True, read_back="none")
    text = serialize(decision)
    if legacy and not decision.inherited:
        text = text.replace("state: in_force\n", legacy + "state: in_force\n")
    text = text.replace("read_back: '2026-10-20'", "read_back: 2026-10-20")
    again = parse(text)
    assert again == decision
    assert again.revision == decision.revision
    canonical = serialize(again)
    assert parse(canonical) == again
    assert serialize(parse(canonical)) == canonical
    assert text.startswith("---\nid: D-")
    assert text.endswith("---\n\nWhy: **speed**.\n\nSecond paragraph.\n")
    assert "revision" not in text
    for removed in ("applies_to", "owner_words"):
        assert removed not in again.content()
        assert removed not in canonical
        assert not hasattr(again, removed)
    assert ("inherited: true\n" in canonical) is decision.inherited
    assert decision.inherited or "inherited" not in canonical
    path = tmp_path / "owlbear" / "decisions" / f"{decision.id}.md"
    path.parent.mkdir(parents=True)
    path.write_text(text, encoding="utf-8")
    assert read(path).revision == decision.revision
    assert validate(tmp_path, [path.parent.parent]) == []
    write(again.model_copy(update={"read_back": "2026-10-21"}), path.parent.parent, again.revision)
    assert parse(path.read_text(encoding="utf-8")).read_back == "2026-10-21"
    assert all(removed not in path.read_text(encoding="utf-8") for removed in ("applies_to", "owner_words"))
    assert make(inherited=True, read_back="none").revision != make(read_back="none").revision


def test_file_and_rule_revision_keep_legacy_identity(make):
    # Pinned Changes and read revisions retain the pre-migration identity.
    assert make().revision == "1fa20ebda080643d149934ca8d9e8718e8841deca1204b7e3fb68175b08aff21"
    assert make().rule_revision == "5b698142e3773945405c3829a75622618a2b41e012170b41b98157026f9f4b39"
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
        {"scope": Scope.CHANGE, "change": "x" * 97},
        {"id": "D-123"},
        {"aliases": ("td 1",)},
        {"read_back": "soon"},
        {"read_back": "2026-13-40"},
        {"created_at": datetime(2026, 10, 20)},  # noqa: DTZ001 - naive on purpose
        {"links": ({"type": "contradicts", "target": new_id()},)},
    ],
)
def test_schema_refusals(make, changes):
    with pytest.raises(ValidationError):
        make(**changes)


def test_long_statement_still_loads(make):
    decision = make(statement="x" * 300)
    assert parse(serialize(decision)) == decision


def test_a_change_folder_holds_a_delivery_record_stem(make):
    stem = f"20261020-090000-{'a' * 64}"  # the approval second and the longest slug Delivery accepts
    assert make(scope=Scope.CHANGE, change=stem).change == stem

