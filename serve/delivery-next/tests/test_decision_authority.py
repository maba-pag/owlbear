"""A completion hold reads pinned Git authority, with the same scope/failure semantics as a snapshot."""

import json
from datetime import UTC, datetime

import pytest

from owlbear_decisions import (
    Decision,
    Link,
    LinkType,
    Origin,
    ReadBackKind,
    Scope,
    State,
    decision_path,
    new_id,
    snapshot,
    write,
)
from owlbear_decisions.storage import serialize
from owlbear_delivery_next.local_system import decision_authority, publication_hold
from owlbear_delivery_next.local_system.data_repo import DataRepo


@pytest.fixture
def authority(shared_repo):
    repo = DataRepo(shared_repo[0])
    repo.claim("owlbear", "github.com/maba-pag/owlbear")
    rule = Decision(
        id=new_id(),
        title="Publish one report",
        statement="This instruction ends when the report is published.",
        scope=Scope.PROJECT,
        project="owlbear",
        origin=Origin.DECIDED,
        actor="owner",
        state=State.IN_FORCE,
        created_at=datetime(2026, 10, 21, tzinfo=UTC),
    )
    write(rule, repo.root / "owlbear")
    path = decision_path(rule, repo.root / "owlbear")
    assert repo.publish(path, "seed authority") == ""
    return repo, rule, path


def test_pinned_authority_does_not_read_the_changed_working_copy(authority):
    repo, rule, path = authority
    commit = repo.git("rev-parse", "HEAD").stdout.strip()
    write(rule.model_copy(update={"conflict": True}), repo.root / "owlbear", expected_revision=rule.revision)
    assert not snapshot(repo.root, "owlbear").active(rule.id)
    assert decision_authority.inactive(repo, commit, path.relative_to(repo.root).as_posix(), None) == ""


def test_pinned_authority_reads_multiple_decisions_in_one_content_launch(authority, monkeypatch):
    repo, rule, path = authority
    another = rule.model_copy(update={"id": new_id(), "title": "Another report"})
    write(another, repo.root / "owlbear")
    assert repo.publish(decision_path(another, repo.root / "owlbear"), "another decision") == ""
    real, calls = repo.git, []

    def observe(_repo, *args, **kwargs):
        calls.append(args[0])
        return real(*args, **kwargs)

    monkeypatch.setattr(DataRepo, "git", observe)
    assert decision_authority.inactive(repo, "HEAD", path.relative_to(repo.root).as_posix(), None) == ""
    assert calls.count("grep") == 1
    assert "show" not in calls


@pytest.mark.parametrize("where", ["own", "global", "foreign"])
@pytest.mark.parametrize(
    "damage",
    ["empty", "malformed", "symlink", "non-markdown", "wrong-name", "directory", "invalid-utf8", "carriage-return"],
)
def test_pinned_unreadable_authority_matches_snapshot_scope(authority, where, damage):
    repo, rule, path = authority
    folders = {"own": repo.root / "owlbear", "global": repo.root, "foreign": repo.root / "other"}
    broken = folders[where] / "decisions" / f"{new_id()}.md"
    broken.parent.mkdir(parents=True, exist_ok=True)
    if damage == "non-markdown":
        broken = broken.with_suffix(".txt")
        broken.write_text("an unfinished entry\n")
    elif damage == "wrong-name":
        candidate = rule.model_copy(
            update={
                "id": new_id(),
                "scope": Scope.GLOBAL if where == "global" else Scope.PROJECT,
                "project": "" if where == "global" else folders[where].name,
            }
        )
        broken.write_text(serialize(candidate))
    elif damage == "directory":
        broken.mkdir()
        (broken / "unfinished.txt").write_text("not a decision\n")
    elif damage == "invalid-utf8":
        broken.write_bytes(b"unreadable \xff\n")
    elif damage == "carriage-return":
        broken.write_bytes(b"unreadable\rdecision\n")
    elif damage == "symlink":
        broken.symlink_to("missing")
    else:
        broken.write_text("" if damage == "empty" else "not a decision\n")
    rel = broken.relative_to(repo.root).as_posix()
    assert repo.git("add", "--", rel).returncode == 0
    assert repo.git("commit", "-qm", "seed unusable authority").returncode == 0
    if damage == "symlink":
        assert repo.git("ls-tree", "HEAD", "--", rel).stdout.startswith("120000 ")
    commit = repo.git("rev-parse", "HEAD").stdout.strip()
    complete = snapshot(repo.root, "owlbear").complete
    refused = decision_authority.inactive(repo, commit, path.relative_to(repo.root).as_posix(), None)
    assert complete is (where == "foreign")
    assert bool(refused) is (not complete)


@pytest.mark.parametrize("ending", ["\r\n", "\r"])
def test_pinned_authority_normalizes_newlines_after_separating_records(authority, ending):
    repo, rule, path = authority
    path.write_bytes(serialize(rule).replace("\n", ending).encode())
    rel = path.relative_to(repo.root).as_posix()
    assert repo.git("add", "--", rel).returncode == 0
    assert repo.git("commit", "-qm", "native newlines").returncode == 0
    assert snapshot(repo.root, "owlbear").active(rule.id)
    assert decision_authority.inactive(repo, "HEAD", rel, None) == ""


def test_lossless_git_output_preserves_exact_bytes(authority):
    repo, _rule, _path = authority
    raw = b"first\rsecond\r\nthird\nnul\0\xff"
    (repo.root / "raw.bin").write_bytes(raw)
    blob = repo.git("hash-object", "-w", "raw.bin").stdout.strip()
    with pytest.raises(UnicodeDecodeError):
        repo.git("cat-file", "blob", blob)
    said = repo.git("cat-file", "blob", blob, lossless=True)
    assert said.returncode == 0
    assert said.stdout.encode("utf-8", "surrogateescape") == raw


@pytest.mark.parametrize("name", [".DS_Store", ".in-flight.tmp"])
def test_pinned_authority_uses_the_same_ignored_entry_rules(authority, name):
    repo, _rule, path = authority
    ignored = path.parent / name
    ignored.write_bytes(b"\xff")
    assert repo.git("add", "-f", "--", ignored.relative_to(repo.root).as_posix()).returncode == 0
    assert repo.git("commit", "-qm", "ignored housekeeping").returncode == 0
    assert snapshot(repo.root, "owlbear").complete
    assert decision_authority.inactive(repo, "HEAD", path.relative_to(repo.root).as_posix(), None) == ""


@pytest.mark.parametrize(
    ("rel", "damage"),
    [
        ("decisions", "file"),
        ("decisions", "symlink"),
        ("owlbear/changes", "file"),
        ("owlbear/changes", "symlink"),
        ("owlbear/changes/report", "symlink"),
        ("owlbear/changes/report/decisions", "file"),
        ("owlbear/changes/report/decisions", "symlink"),
        ("other/changes", "file"),
        ("other/changes", "symlink"),
        ("other/changes/report", "symlink"),
        ("other/changes/report/decisions", "file"),
        ("other/changes/report/decisions", "symlink"),
    ],
)
def test_pinned_authority_rejects_unreadable_layer_containers(authority, rel, damage):
    repo, _rule, path = authority
    broken = repo.root / rel
    broken.parent.mkdir(parents=True, exist_ok=True)
    if damage == "symlink":
        broken.symlink_to("missing")
    else:
        broken.write_text("not a folder\n")
    assert repo.git("add", "--", rel).returncode == 0
    assert repo.git("commit", "-qm", "unreadable layer container").returncode == 0
    if rel in {"owlbear/changes", "owlbear/changes/report"}:
        with pytest.raises(NotADirectoryError):
            snapshot(repo.root, "owlbear")
    else:
        assert snapshot(repo.root, "owlbear").complete is rel.startswith("other/")
    refused = decision_authority.inactive(repo, "HEAD", path.relative_to(repo.root).as_posix(), None)
    assert bool(refused) is (not rel.startswith("other/"))


@pytest.mark.parametrize(
    ("setting", "value"),
    [("color.grep", "always"), ("grep.column", "true"), ("grep.patternType", "fixed")],
)
def test_pinned_authority_is_independent_of_git_presentation_settings(authority, setting, value):
    repo, _rule, path = authority
    assert repo.git("config", setting, value).returncode == 0
    assert decision_authority.inactive(repo, "HEAD", path.relative_to(repo.root).as_posix(), None) == ""


@pytest.mark.parametrize("folder", ["unrelated", "other/decisions", "owlbear/decisions", "decisions"])
def test_pinned_authority_classifies_non_utf8_filenames_by_layer(authority, folder):
    repo, _rule, path = authority
    rel = path.relative_to(repo.root).as_posix()
    head = repo.git("rev-parse", "HEAD").stdout.strip()
    blob = repo.git("rev-parse", f"HEAD:{rel}").stdout.strip()

    # Real Git trees can hold names that macOS cannot materialize.
    entry = f"100644,{blob},{folder}/unreadable-\udcff.md"
    added = repo.git("update-index", "--add", "--cacheinfo", entry)
    assert added.returncode == 0, added.stderr
    tree = repo.git("write-tree").stdout.strip()
    commit = repo.git("commit-tree", tree, "-p", head, "-m", "unreadable filename").stdout.strip()
    complete = folder in {"unrelated", "other/decisions"}
    refused = decision_authority.inactive(repo, commit, rel, None)
    assert bool(refused) is (not complete)


def test_pinned_pending_read_back_is_not_completion_authority(authority):
    repo, rule, path = authority
    pending = rule.model_copy(
        update={
            "read_back": "pending",
            "read_back_why": "Clarify its remaining intent",
            "read_back_kind": ReadBackKind.UNCERTAIN,
        }
    )
    write(pending, repo.root / "owlbear", expected_revision=rule.revision)
    assert repo.publish(path, "pending question") == ""
    assert "owner questions" in decision_authority.inactive(repo, "HEAD", path.relative_to(repo.root).as_posix(), None)


def test_pinned_authority_validates_competing_links_from_other_projects(authority):
    repo, rule, path = authority
    parent = rule.model_copy(update={"id": new_id(), "title": "Prior report", "state": State.REPLACED})
    link = (Link(type=LinkType.REPLACES, target=parent.id),)
    chosen = rule.model_copy(update={"links": link})
    other = rule.model_copy(update={"id": new_id(), "project": "other", "links": link})
    write(parent, repo.root / "owlbear")
    write(chosen, repo.root / "owlbear", expected_revision=rule.revision)
    write(other, repo.root / "other")
    assert repo.git("add", "--", "owlbear/decisions", "other/decisions").returncode == 0
    assert repo.git("commit", "-qm", "competing project links").returncode == 0
    assert not snapshot(repo.root, "owlbear").active(chosen.id)
    assert "2 in-force decisions" in decision_authority.inactive(
        repo,
        "HEAD",
        path.relative_to(repo.root).as_posix(),
        None,
    )


@pytest.mark.parametrize("condition", [None, 1, "true"])
def test_malformed_decision_condition_holds_without_changing_the_record(authority, condition):
    repo, _rule, path = authority
    with repo.locked():
        publication_hold.hold(
            repo,
            path,
            publication_hold.Requires("active decision", decision_active=True),
            None,
        )
    record = repo.root / ".git" / publication_hold.RECORD
    held = json.loads(record.read_text())
    held["decision_active"] = condition
    record.write_text(json.dumps(held))
    before = record.read_bytes()
    assert "decision-active condition" in publication_hold.check(repo, None, fetch=False)
    assert record.read_bytes() == before
