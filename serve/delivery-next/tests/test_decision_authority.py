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
@pytest.mark.parametrize("damage", ["empty", "malformed", "symlink"])
def test_pinned_unreadable_authority_matches_snapshot_scope(authority, where, damage):
    repo, _rule, path = authority
    folders = {"own": repo.root / "owlbear", "global": repo.root, "foreign": repo.root / "other"}
    broken = folders[where] / "decisions" / f"{new_id()}.md"
    broken.parent.mkdir(parents=True, exist_ok=True)
    if damage == "symlink":
        broken.symlink_to("missing")
        rel = broken.relative_to(repo.root).as_posix()
        assert repo.git("add", "--", rel).returncode == 0
        assert repo.git("commit", "-qm", "seed nonregular authority").returncode == 0
        assert repo.git("ls-tree", "HEAD", "--", rel).stdout.startswith("120000 ")
    else:
        broken.write_text("" if damage == "empty" else "not a decision\n")
        assert repo.publish(broken, "seed unreadable authority") == ""
    commit = repo.git("rev-parse", "HEAD").stdout.strip()
    complete = snapshot(repo.root, "owlbear").complete
    refused = decision_authority.inactive(repo, commit, path.relative_to(repo.root).as_posix(), None)
    assert complete is (where == "foreign")
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
