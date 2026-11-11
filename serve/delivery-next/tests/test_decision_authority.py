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


@pytest.mark.parametrize("ending", ["\n", "\r\n", "\r"])
def test_pinned_authority_reads_unequal_native_blobs_once_not_the_changed_worktree(authority, monkeypatch, ending):
    repo, rule, path = authority
    another = rule.model_copy(
        update={
            "id": new_id(),
            "title": "Another report",
            "rationale": ("Résumé of the other report.\n" * 100).rstrip(),
        }
    )
    write(another, repo.root / "owlbear")
    other_path = decision_path(another, repo.root / "owlbear")
    for candidate, decision in ((path, rule), (other_path, another)):
        candidate.write_bytes(serialize(decision).replace("\n", ending).encode())
    assert len(path.read_bytes()) != len(other_path.read_bytes())
    assert repo.publish([path, other_path], "native unequal decision records") == ""
    commit = repo.git("rev-parse", "HEAD").stdout.strip()
    assert snapshot(repo.root, "owlbear").active(rule.id)
    write(rule.model_copy(update={"conflict": True}), repo.root / "owlbear", expected_revision=rule.revision)
    assert not snapshot(repo.root, "owlbear").active(rule.id)
    real, calls = repo.git, []

    def observe(_repo, *args, **kwargs):
        calls.append(args[0])
        return real(*args, **kwargs)

    monkeypatch.setattr(DataRepo, "git", observe)
    assert decision_authority.inactive(repo, commit, path.relative_to(repo.root).as_posix(), None) == ""
    assert calls.count("show") == 1
    assert "grep" not in calls


@pytest.mark.parametrize("where", ["own", "global", "foreign"])
@pytest.mark.parametrize(
    "damage",
    [
        "empty",
        "malformed",
        "symlink",
        "non-markdown",
        "wrong-name",
        "directory",
        "invalid-utf8",
        "carriage-return",
        "missing-final-newline",
    ],
)
def test_pinned_unreadable_authority_matches_snapshot_scope(authority, where, damage):
    repo, rule, path = authority
    folders = {"own": repo.root / "owlbear", "global": repo.root, "foreign": repo.root / "other"}
    broken = folders[where] / "decisions" / f"{new_id()}.md"
    broken.parent.mkdir(parents=True, exist_ok=True)
    if damage == "non-markdown":
        broken = broken.with_suffix(".txt")
        broken.write_text("an unfinished entry\n")
    elif damage in {"wrong-name", "missing-final-newline"}:
        candidate = rule.model_copy(
            update={
                "id": broken.stem if damage == "missing-final-newline" else new_id(),
                "scope": Scope.GLOBAL if where == "global" else Scope.PROJECT,
                "project": "" if where == "global" else folders[where].name,
            }
        )
        content = serialize(candidate)
        broken.write_text(content.removesuffix("\n") if damage == "missing-final-newline" else content)
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
    if damage == "invalid-utf8" and not complete:
        with pytest.raises(UnicodeDecodeError) as cause:
            b"unreadable \xff\n".decode("utf-8")
        assert f"{str(broken)!r} at {commit}: UnicodeDecodeError: {cause.value}" in refused


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
