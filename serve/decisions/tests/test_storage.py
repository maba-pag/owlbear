from __future__ import annotations

import os
import stat
import subprocess
import sys
from pathlib import Path

import pytest

from owlbear_decisions import storage
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


# A read or a write in a child process: code that would wait on a pipe is killed at the timeout, and nothing is ever
# written into the pipe to release it. The last line printed names what was raised, or "returned".
CHILD = r"""
import sys
from pathlib import Path
from owlbear_decisions.storage import parse, read, write
path = Path(sys.argv[2])
try:
    if sys.argv[1] == "read":
        read(path)
    else:
        write(parse(sys.argv[3]), path.parent.parent, "any")
    print("returned")
except Exception as exc:
    print(f"{type(exc).__name__}: {exc}")
"""


def _bounded(*args: str) -> str:
    env = {**os.environ, "PYTHONPATH": os.pathsep.join(p for p in sys.path if p)}
    try:
        done = subprocess.run(  # noqa: S603 - this interpreter and a fixed script
            [sys.executable, "-c", CHILD, *args], capture_output=True, text=True, timeout=15, env=env, check=False
        )
    except subprocess.TimeoutExpired:
        return "hung"
    assert done.returncode == 0, done.stderr
    return done.stdout.strip().splitlines()[-1]


@pytest.mark.parametrize("how", ["read", "write"])
def test_a_pipe_at_a_decision_files_name_is_unreadable_and_never_waited_on(tmp_path, make, how):
    """A pipe where a decision file belongs is refused as unreadable by a read and by a write's read of the current
    file, at once: it is never waited on, written into or replaced."""
    decision = make()
    path = decision_path(decision, tmp_path)
    path.parent.mkdir(parents=True)
    os.mkfifo(path)

    said = _bounded(how, str(path), serialize(decision))

    assert said == "DecisionFileError: unreadable: NotRegularFileError", said
    assert stat.S_ISFIFO(os.lstat(path).st_mode)
    assert [p.name for p in path.parent.iterdir()] == [path.name]  # no temporary was left either


def test_a_link_that_appears_after_the_symlink_check_is_never_read_through(tmp_path, make, monkeypatch):
    """A link taking the file's name after `read` checked it is not one is refused when it is opened, never followed
    to the decision file it names."""
    decision = make()
    write(decision, tmp_path)
    real = decision_path(decision, tmp_path)
    linked = tmp_path / "elsewhere" / real.name
    linked.parent.mkdir()
    linked.symlink_to(real)
    monkeypatch.setattr(Path, "is_symlink", lambda _self: False)  # the check passed before the link appeared

    with pytest.raises(DecisionFileError, match="unreadable: OSError"):
        read(linked)


def test_a_folder_at_a_decision_files_name_is_unreadable(tmp_path, make):
    path = decision_path(make(), tmp_path)
    path.mkdir(parents=True)
    with pytest.raises(DecisionFileError, match="unreadable"):
        read(path)


def test_the_storage_under_test_is_this_checkouts_own():
    assert (
        Path(storage.__file__).resolve() == (Path(__file__).parents[1] / "src/owlbear_decisions/storage.py").resolve()
    )


def test_a_regular_utf8_file_is_read_as_before_and_other_failures_keep_their_names(tmp_path, make):
    """A regular file reads as `Path.read_text` decoded it, CRLF line ends included; bytes that are not UTF-8 and a
    missing file stay refused as unreadable, each naming its error."""
    decision = make(rationale="Why: **speed**.\n\nÄ second paragraph.")
    path = decision_path(decision, tmp_path)
    path.parent.mkdir(parents=True)
    path.write_bytes(serialize(decision).replace("\n", "\r\n").encode("utf-8"))
    assert read(path) == decision
    path.write_bytes(serialize(decision).encode("utf-8"))
    assert read(path) == decision
    path.write_bytes(b"\xff\xfe not utf-8")
    with pytest.raises(DecisionFileError, match="unreadable: UnicodeDecodeError"):
        read(path)
    with pytest.raises(DecisionFileError, match="unreadable: FileNotFoundError"):
        read(tmp_path / "missing.md")
