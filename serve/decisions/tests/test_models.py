from __future__ import annotations

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from owlbear_decisions.models import Scope, new_id
from owlbear_decisions.storage import parse, read, serialize, write
from owlbear_decisions.validate import validate

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


def test_revision_of_a_file_without_owner_words_or_selectors_is_unchanged(make):
    # computed by the model before TD-449 and TD-460 removed them: pinned Changes and read revisions stay valid
    assert make().revision == "1fa20ebda080643d149934ca8d9e8718e8841deca1204b7e3fb68175b08aff21"
    assert make().rule_revision == "5b698142e3773945405c3829a75622618a2b41e012170b41b98157026f9f4b39"


def test_an_old_file_with_selectors_loads_validates_and_is_written_back_without_them(make, tmp_path):
    old = serialize(make()).replace("state: in_force\n", "applies_to:\n  paths:\n  - web/**\n  roles:\n  - builder\n"
                                    "state: in_force\n")  # fmt: skip
    assert "applies_to" in old
    loaded = parse(old)
    assert loaded == make()
    assert "applies_to" not in loaded.content()
    assert not hasattr(loaded, "applies_to")
    path = tmp_path / "owlbear" / "decisions" / f"{loaded.id}.md"
    path.parent.mkdir(parents=True)
    path.write_text(old, encoding="utf-8")
    assert read(path).revision == make().revision
    assert validate(tmp_path, [tmp_path / "owlbear"]) == []
    write(loaded.model_copy(update={"read_back": "2026-10-21"}), path.parent.parent, loaded.revision)
    assert "applies_to" not in path.read_text(encoding="utf-8")


def test_an_old_file_with_owner_words_loads_and_is_written_back_without_them(make, tmp_path):
    old = serialize(make()).replace(
        "state: in_force\n", "owner_words:\n- text: lint once\n  date: 2026-10-14\n  alias: TD-87\nstate: in_force\n"
    )
    assert "owner_words" in old
    loaded = parse(old)
    assert loaded == make()
    assert "owner_words" not in loaded.content()
    path = tmp_path / "decisions" / f"{loaded.id}.md"
    path.parent.mkdir()
    path.write_text(old, encoding="utf-8")
    assert read(path).revision == make().revision
    write(loaded.model_copy(update={"read_back": "2026-10-21"}), tmp_path, expected_revision=loaded.revision)
    assert "owner_words" not in path.read_text(encoding="utf-8")


def test_inherited_is_written_only_when_true(make):
    assert "inherited" not in serialize(make())
    inherited = make(inherited=True, read_back="none")
    assert "inherited: true\n" in serialize(inherited)
    assert parse(serialize(inherited)) == inherited
    assert inherited.revision != make(read_back="none").revision


def test_a_change_folder_holds_a_delivery_record_stem(make):
    stem = f"20261020-090000-{'a' * 64}"  # the approval second and the longest slug Delivery accepts
    assert make(scope=Scope.CHANGE, change=stem).change == stem


def test_unquoted_yaml_dates_are_accepted(make):
    text = serialize(make()).replace("read_back: '2026-10-20'", "read_back: 2026-10-20")
    assert "read_back: 2026-10-20\n" in text
    assert parse(text) == make()
