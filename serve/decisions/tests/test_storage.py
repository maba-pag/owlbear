from __future__ import annotations

import pytest

from owlbear_decisions.errors import ConcurrencyError, DecisionFileError, ImmutableError
from owlbear_decisions.models import State, new_id
from owlbear_decisions.storage import decision_path, load_folder, read, serialize, write


def test_write_then_read(tmp_path, make):
    decision = make()
    revision = write(decision, tmp_path)
    path = tmp_path / "decisions" / f"{decision.id}.md"
    assert read(path) == decision
    assert revision == decision.revision
    assert [p.name for p in path.parent.iterdir()] == [path.name]


def test_create_refuses_an_existing_file(tmp_path, make):
    write(make(), tmp_path)
    with pytest.raises(ConcurrencyError, match="exists"):
        write(make(state=State.REPLACED), tmp_path)


def test_stale_expected_revision_is_refused(tmp_path, make):
    first = make(state=State.DRAFT)
    write(first, tmp_path)
    second = make(state=State.DRAFT, title="Second")
    write(second, tmp_path, expected_revision=first.revision)
    with pytest.raises(ConcurrencyError, match="not the expected"):
        write(make(state=State.DRAFT, title="Third"), tmp_path, expected_revision=first.revision)
    assert read(decision_path(second, tmp_path)) == second


def test_expected_revision_on_a_missing_file_is_refused(tmp_path, make):
    with pytest.raises(ConcurrencyError, match="no file"):
        write(make(), tmp_path, expected_revision="0" * 64)


def test_in_force_statement_is_immutable(tmp_path, make):
    decision = make()
    write(decision, tmp_path)
    with pytest.raises(ImmutableError, match="successor"):
        write(make(statement="Edited wording."), tmp_path, expected_revision=decision.revision)
    write(make(state=State.REPLACED), tmp_path, expected_revision=decision.revision)
    assert read(decision_path(decision, tmp_path)).state is State.REPLACED


def test_draft_statement_may_change(tmp_path, make):
    draft = make(state=State.DRAFT)
    write(draft, tmp_path)
    write(make(state=State.DRAFT, statement="Better."), tmp_path, expected_revision=draft.revision)
    assert read(decision_path(draft, tmp_path)).statement == "Better."


def test_the_lifecycle_only_moves_forward(tmp_path, make):
    accepted = make()
    write(accepted, tmp_path)
    with pytest.raises(ImmutableError, match="cannot go from in_force to draft"):
        write(make(state=State.DRAFT), tmp_path, expected_revision=accepted.revision)
    with pytest.raises(ImmutableError, match="origin"):
        write(make(origin="autonomous"), tmp_path, expected_revision=accepted.revision)
    spent = make(state=State.SPENT)
    write(spent, tmp_path, expected_revision=accepted.revision)
    with pytest.raises(ImmutableError, match="cannot go from spent to in_force"):
        write(make(statement="Revived."), tmp_path, expected_revision=spent.revision)
    with pytest.raises(ImmutableError, match="statement"):
        write(make(state=State.SPENT, statement="Rewritten."), tmp_path, expected_revision=spent.revision)


def test_a_decisions_path_that_is_not_a_folder_is_reported(tmp_path):
    (tmp_path / "decisions").write_text("x", encoding="utf-8")
    assert [error.message for error in load_folder(tmp_path).errors] == [
        "not a folder: decisions must be a real folder"
    ]


def test_hidden_files_are_reported_except_temporaries(tmp_path, make):
    write(make(), tmp_path)
    folder = tmp_path / "decisions"
    for name in (".hidden.md", ".tmp1234.tmp", ".DS_Store"):
        (folder / name).write_text("x", encoding="utf-8")
    assert [error.path.name for error in load_folder(tmp_path).errors] == [".hidden.md"]


def test_malformed_files_are_reported_not_skipped(tmp_path, make):
    good = make()
    write(good, tmp_path)
    folder = tmp_path / "decisions"
    (folder / "broken.md").write_text("no front matter\n", encoding="utf-8")
    (folder / "bad-yaml.md").write_text("---\nid: [unclosed\n---\n", encoding="utf-8")
    other = make(id=new_id())
    (folder / "renamed.md").write_text(serialize(other), encoding="utf-8")
    bad_origin = new_id()
    text = serialize(make(id=bad_origin)).replace("origin: decided", "origin: maybe")
    (folder / f"{bad_origin}.md").write_text(text, encoding="utf-8")
    (folder / "notes.txt").write_text("x", encoding="utf-8")
    loaded = load_folder(tmp_path)
    assert list(loaded.decisions.values()) == [good]
    reported = {error.path.name: error for error in loaded.errors}
    assert set(reported) == {"broken.md", "bad-yaml.md", "renamed.md", f"{bad_origin}.md", "notes.txt"}
    assert "front matter missing" in reported["broken.md"].message
    assert "not valid YAML" in reported["bad-yaml.md"].message
    assert f"{other.id}.md" in reported["renamed.md"].message
    assert reported[f"{bad_origin}.md"].locations == ("origin",)


def test_front_matter_must_not_carry_revision(tmp_path, make):
    path = tmp_path / "x.md"
    path.write_text(serialize(make()).replace("---\n\n", "revision: abc\n---\n\n", 1), encoding="utf-8")
    with pytest.raises(DecisionFileError, match="revision"):
        read(path)
