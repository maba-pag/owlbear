"""A finished Change's decisions become decision files in its record's commit (TD-419 slice 2, TD-148)."""

from __future__ import annotations

import json
import os
import subprocess
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from owlbear_decisions import Decision as Rule
from owlbear_decisions import (
    DecisionError,
    Link,
    LinkType,
    Origin,
    Scope,
    State,
    new_id,
    read,
    storage,
    write,
)
from owlbear_delivery_next.change_contracts.curation_records import TestReview
from owlbear_delivery_next.change_contracts.models import Brief, BriefDecision, Change, Decision, Exit, Step, StepKind
from owlbear_delivery_next.change_contracts.profile_record import Profile
from owlbear_delivery_next.change_flow import brief_tools
from owlbear_delivery_next.github.provider import PullRequest
from owlbear_delivery_next.local_system.data_repo import DataRepo
from owlbear_delivery_next.state_store import (
    briefs,
    change_record,
    decision_archive,
    decision_batch,
    decision_recovery,
    decision_store,
    decision_sync,
)
from owlbear_delivery_next.state_store.store import Lock
from owlbear_delivery_next.state_store.store import Store as LocalStore
from owlbear_delivery_next.workflow_steps import cleanup, engine

AT = datetime(2026, 10, 15, 9, tzinfo=UTC)
STEM = "20261015-090000-notes"
LIMIT, WHERE, UI = "Limit the notes?", "Where do notes live?", "Not a UI change (brief v2, UI paths 1a2b)"
MERGED = PullRequest(
    repository="acme/shop-site", number=7, node_id="n", url="https://x/pull/7", head_branch="owlbear/notes",
    head_sha="a" * 40, base_branch="main", draft=False, state="closed", merged=True, merge_commit_sha="b" * 40,
)  # fmt: skip


class Store:
    """What a record needs of the clone's store: the shared repository and the project's folder in it."""

    def __init__(self, root: Path) -> None:
        self.shared, self.name = DataRepo(root), "shop-site"


def git(cwd: Path, *args: str) -> str:
    if (cwd / "HEAD").is_file():  # a bare repository: safe.bareRepository=explicit wants it named
        args = ("--git-dir=.", *args)
    return subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True).stdout.strip()  # noqa: S603, S607


@pytest.fixture
def store(shared_repo) -> Store:
    return Store(shared_repo[0])


def finished(*, ids: bool = True, unchanged: bool = False) -> Change:
    mint = (lambda: new_id(AT)) if ids else (lambda: "")
    decided = BriefDecision(id=mint(), question=LIMIT, answer="Yes, 800 characters", origin="decided")
    lasting = BriefDecision(id=mint(), question=WHERE, answer="One SQLite table", origin="autonomous", scope="project")
    approved = Brief(version=2, title="Notes", outcome="Owners keep notes", decisions=[decided, lasting])
    c = Change(slug="notes", handle="c4", brief=Brief(version=2, approved_at=AT, approved=[approved]))
    at = AT + timedelta(hours=1)
    c.decisions.append(Decision(id=mint(), text=UI, origin="decided", at=at, paths=["web/app.css"]))
    c.tests = TestReview(commit="c" * 40, packages=[], shares=[], unchanged=True) if unchanged else None
    return c


def archived(root: Path) -> dict[str, tuple[str, Scope, State]]:
    """Each decision file by title: its path under the project's folder, scope and state."""
    found = {}
    for path in sorted((root / "shop-site").rglob("decisions/*.md")):
        d = read(path)
        found[d.title] = (path.parent.parent.relative_to(root).as_posix(), d.scope, d.state)
    return found


def test_brief_question_identity_and_successor_rules(tmp_path) -> None:
    def draft(*decisions: tuple[str, str], scope="project") -> brief_tools.BriefDraft:
        made = [{"question": q, "answer": a, "origin": "decided", "scope": scope} for q, a in decisions]
        fields = {"title": "Notes", "outcome": "Owners keep notes on a page.", "criteria": ["A note keeps 800 chars"]}
        return brief_tools.BriefDraft(**fields, scope=["web"], decisions=made)

    c = briefs.drafted(None, draft((LIMIT, "Yes"), (WHERE, "SQLite")), "notes", "c4", Profile())
    first = {d.question: d.id for d in c.brief.decisions}
    c = briefs.drafted(
        c, draft((WHERE, "Postgres"), (LIMIT, "Yes"), ("Which colour?", "Blue")), "notes", "c4", Profile()
    )
    second = {d.question: d.id for d in c.brief.decisions}

    assert (second[LIMIT], second[WHERE]) == (first[LIMIT], first[WHERE])  # a changed answer keeps the identity
    assert second["Which colour?"] not in first.values()
    assert all(i.startswith("D-") for i in second.values())
    assert {d.scope for d in c.brief.decisions} == {"project"}
    repeated = draft((LIMIT, "Yes"), ("  limit the NOTES? ", "Yes"))
    assert any(e.startswith("decisions: a question repeats") for e in brief_tools.check_brief(repeated))
    c = briefs.drafted(None, draft((LIMIT, "Yes, 800"), scope="change"), "notes", "c4", Profile())
    c.brief = c.brief.model_copy(update={"approved_at": AT, "approved": [c.brief.model_copy()]})
    first = c.brief.decisions[0]
    c = briefs.drafted(c, draft((LIMIT, "Yes, 1000"), scope="change"), "notes", "c4", Profile())
    second = c.brief.decisions[0]
    assert (second.id != first.id, second.replaces) == (True, first.id)
    c = briefs.drafted(c, draft((LIMIT, "Yes, 1200"), scope="change"), "notes", "c4", Profile())
    assert (c.brief.decisions[0].id, c.brief.decisions[0].replaces) == (second.id, first.id)
    c = briefs.drafted(c, draft((LIMIT, "Yes, 800"), scope="change"), "notes", "c4", Profile())
    assert (c.brief.decisions[0].id, c.brief.decisions[0].replaces) == (first.id, "")
    c = briefs.drafted(c, draft((LIMIT, "Yes, 1000"), scope="change"), "notes", "c4", Profile())
    c.brief = c.brief.model_copy(update={"approved": [*c.brief.approved, c.brief.model_copy(update={"approved": []})]})
    planned, problems = decision_archive.plan(tmp_path, "shop-site", c, STEM, "merged")
    assert problems == []
    old, new = [d for d, _, _ in planned]
    assert (old.state, old.statement, new.state, new.statement) == (
        State.REPLACED, "Yes, 800", State.SPENT, "Yes, 1000"
    )
    assert [(link.type, link.target) for link in new.links] == [("replaces", first.id)]
    assert list(tmp_path.rglob("*")) == []


@pytest.mark.parametrize(
    "ending",
    [
        (MERGED, False, "merged", State.SPENT, State.IN_FORCE),
        (None, True, "unchanged", State.SPENT, State.IN_FORCE),
        (None, False, "abandoned", State.WITHDRAWN, State.DRAFT),
    ],
)
def test_archive_plan_endings_scope_and_provenance(tmp_path, ending) -> None:
    _pr, unchanged, outcome, brief, lasting = ending
    c, why = finished(unchanged=unchanged), "One table keeps the notes in the backup with the rest"
    c.brief.approved[0].decisions[1].reason = why
    planned, problems = decision_archive.plan(tmp_path, "shop-site", c, STEM, outcome)
    assert problems == []
    limit, where, ui = [d for d, _, _ in planned]
    assert {d.title: d.state for d, _, _ in planned} == {LIMIT: brief, WHERE: lasting, UI: brief}
    assert [(d.scope, d.change) for d, _, _ in planned] == [
        (Scope.CHANGE, STEM), (Scope.PROJECT, ""), (Scope.CHANGE, STEM)
    ]
    assert (limit.statement, limit.topic, limit.actor, limit.read_back) == (
        "Yes, 800 characters", "Notes", "owner", AT.date().isoformat()
    )
    assert (where.actor, where.read_back, where.created_at) == ("shaper", "none", AT)
    assert where.source == "Change notes, brief v2 approved 2026-10-15T09:00:00+00:00"
    assert where.rationale == f"From Change notes ({outcome}).\n\n{why}"
    (published,) = decision_archive.lasting("shop-site", c, STEM)
    assert why in published.rationale
    assert (ui.read_back, ui.rationale) == (
        (AT + timedelta(hours=1)).date().isoformat(), f"From Change notes ({outcome})."
    )
    for d, _, _ in planned:
        assert "applies_to" not in d.content()
        assert "owner_words" not in storage.serialize(d)
        assert "skip the UI review" not in storage.serialize(d)
    assert list(tmp_path.rglob("*")) == []


def test_a_crash_before_publishing_stays_interrupted_until_the_owner_finishes_it_once(
    store, shared_repo, monkeypatch
) -> None:
    root, remote = shared_repo
    c = finished()

    real_publish = decision_sync.publish

    def crash(*_a: object, **_k: object):
        msg = "publish call interrupted"
        raise OSError(msg)

    monkeypatch.setattr(decision_sync, "publish", crash)
    assert "publish call interrupted" in change_record.save(store, c, MERGED, AT)
    written = {p: p.read_text() for p in (root / "shop-site").rglob("decisions/*.md")}
    assert len(written) == 3
    assert git(root, "status", "--porcelain")  # written, never committed
    assert decision_batch.pending(store.shared) is not None
    with pytest.raises(decision_store.DecisionsUnavailable, match="interrupted decision batch"):
        decision_store.load(store.shared, "shop-site")
    monkeypatch.setattr(decision_sync, "publish", real_publish)

    # an unknown publication is not retried
    assert "interrupted decision batch" in change_record.save(store, c, MERGED, AT)
    assert {p: p.read_text() for p in (root / "shop-site").rglob("decisions/*.md")} == written
    batch = decision_batch.pending(store.shared)
    assert decision_recovery.finish(store.shared, batch.generation).done
    assert {p: p.read_text() for p in (root / "shop-site").rglob("decisions/*.md")} == written
    assert git(root, "status", "--porcelain") == ""
    count = git(remote, "rev-list", "--count", "main")
    assert change_record.save(store, c, MERGED, AT) == ""  # a further run changes nothing at all
    assert (git(remote, "rev-list", "--count", "main"), len(archived(root))) == (count, 3)


def test_legacy_change_identity_and_privacy_survive_reopen(tmp_path) -> None:
    old = json.loads(finished().model_dump_json())
    for d in [*old["brief"]["approved"][0]["decisions"], *old["decisions"]]:
        del d["id"]
        d.pop("scope", None)
        d.pop("replaces", None)
    c = Change.model_validate(old)
    assert [d.id for d in c.brief.approved[0].decisions] == ["", ""]
    ids = []
    for name in ("shop-site", "shop-app"):
        first, problems = decision_archive.plan(tmp_path, name, c, STEM, "merged")
        assert problems == []
        assert decision_archive.plan(tmp_path, name, Change.model_validate(old), STEM, "merged") == (first, [])
        assert len(first) == 3
        ids.extend(d.id for d, _, _ in first)
    assert len(ids) == len(set(ids)) == 6
    assert list(tmp_path.rglob("*")) == []
    old["decisions"][0]["words"] = "Right, skip the UI review"
    c = Change.model_validate(old)
    local = LocalStore(tmp_path / "store")

    local.write(Lock(c.slug), c)

    assert "words" not in c.decisions[0].model_dump()
    written = [p.read_bytes() for p in (tmp_path / "store").rglob("*") if p.is_file()]
    assert not [b for b in written if b"skip the UI review" in b]
    assert local.read(c.slug).decisions[0].text == UI


def test_each_decided_answer_is_confirmed_on_the_approval_of_the_latest_version_holding_it(tmp_path):
    one, two, three = AT - timedelta(days=5), AT - timedelta(days=2), AT
    dropped = BriefDecision(id=new_id(AT), question=LIMIT, answer="Yes, 800 characters", origin="decided")
    kept = BriefDecision(id=new_id(AT), question=WHERE, answer="One SQLite table", origin="decided", scope="project")
    versions = [Brief(version=1, title="Notes", approved_at=one, decisions=[dropped, kept]),
                Brief(version=2, title="Notes", approved_at=two, decisions=[dropped, kept]),
                Brief(version=3, title="Notes", approved_at=three, decisions=[kept])]  # fmt: skip
    c = Change(slug="notes", handle="c4", brief=Brief(version=3, approved_at=three, approved=versions))

    planned, problems = decision_archive.plan(tmp_path, "shop-site", c, STEM, "merged")
    assert problems == []
    early, late = [d for d, _, _ in planned]
    assert (early.read_back, late.read_back) == (two.date().isoformat(), three.date().isoformat())
    assert early.created_at == late.created_at == three  # its record's time stays the brief's approval


def test_one_decision_that_cannot_be_written_keeps_all_out_and_the_record_is_unchanged(
    store, shared_repo, monkeypatch
) -> None:
    root, _ = shared_repo
    c = finished()
    assert change_record.save(store, c, None, AT) == ""  # abandoned: withdrawn, and the lasting rule a draft
    before = {p: p.read_text() for p in root.rglob("decisions/*.md")}
    record = root / "shop-site" / "changes" / f"{STEM}.json"
    record_before, head_before = record.read_bytes(), git(root, "rev-parse", "HEAD")
    begun = []
    monkeypatch.setattr(decision_batch, "begin", lambda *args, **_: begun.append(args))

    notice = change_record.save(store, c, MERGED, AT)

    assert notice.startswith("the record of notes was not saved; no decision of notes was archived"), notice
    assert "cannot go from withdrawn to spent" in notice
    assert {p: p.read_text() for p in root.rglob("decisions/*.md")} == before  # not even the allowed draft move
    assert archived(root)[WHERE][2] is State.DRAFT
    assert (
        record.read_bytes() == record_before
    )  # the abandoned record stays exactly as it was, not republished as merged
    assert git(root, "rev-parse", "HEAD") == head_before
    assert git(root, "status", "--porcelain") == ""
    assert begun == []


@pytest.mark.parametrize("kind", ["invalid-id", "two-successors"])
def test_archive_planning_refuses_the_whole_plan_without_writes(tmp_path, kind) -> None:
    root, c = tmp_path, finished()
    if kind == "invalid-id":
        c.decisions.append(Decision(id="D-NOTANID", text="A malformed id", origin="decided", at=AT))
        planned, problems = decision_archive.plan(root, "shop-site", c, STEM, "merged")
        assert any(c.decisions[1].id in problem for problem in problems)
        assert list(root.rglob("*")) == []
        written, refused = decision_archive.write_plan(planned, problems, c.slug)
        assert written == []
        assert refused
        assert list(root.rglob("*")) == []
        return
    said = {"title": "Notes", "statement": "Notes live in SQLite.", "scope": Scope.PROJECT, "project": "shop-site",
            "origin": Origin.AUTONOMOUS, "actor": "shaper", "created_at": AT}  # fmt: skip
    old = Rule(id=new_id(AT), state=State.REPLACED, **said)
    later = Rule(id=new_id(AT), state=State.IN_FORCE, links=(Link(type=LinkType.REPLACES, target=old.id),), **said)
    for d in (old, later):
        write(d, root / "shop-site")
    rivals = {p: p.read_text() for p in root.rglob("decisions/*.md")}
    decisions = c.brief.approved[0].decisions
    decisions[1] = lasting = decisions[1].model_copy(update={"replaces": old.id})  # a second in-force successor
    _, problems = decision_archive.plan(root, "shop-site", c, STEM, "merged")
    assert any(f"decision {lasting.id}, {old.id} of notes: two-successors" in problem for problem in problems)
    assert {p: p.read_text() for p in root.rglob("decisions/*.md")} == rivals  # rival rules untouched
    assert not (root / "shop-site" / "changes" / f"{STEM}.json").exists()


def test_a_project_answer_narrowed_to_the_change_is_withdrawn_and_its_successor_relates_to_it(tmp_path):
    first = BriefDecision(id=new_id(AT), question=WHERE, answer="One SQLite table", origin="decided", scope="project")
    second = BriefDecision(id=new_id(AT), question=WHERE, answer="SQLite for this Change only", origin="decided",
                           replaces=first.id)  # fmt: skip
    versions = [Brief(version=n, title="Notes", decisions=[d]) for n, d in ((1, first), (2, second))]
    c = Change(slug="notes", handle="c4", brief=Brief(version=2, approved_at=AT, approved=versions))

    planned, problems = decision_archive.plan(tmp_path, "shop-site", c, STEM, "merged")
    assert problems == []
    old, new = [d for d, _, _ in planned]
    assert (old.scope, old.state, new.scope, new.state) == (Scope.PROJECT, State.WITHDRAWN, Scope.CHANGE, State.SPENT)
    assert [(link.type, link.target) for link in new.links] == [(LinkType.RELATED_TO, first.id)]
    assert list(tmp_path.rglob("*")) == []


def test_a_write_failing_midway_puts_every_file_back_and_the_record_is_refused(store, shared_repo, monkeypatch):
    root, _ = shared_repo
    replaced, real = [], storage._replace

    def refused(path: Path, text: str, *fence) -> None:
        if replaced:
            msg = "permission denied"
            raise PermissionError(msg)
        replaced.append(path)
        real(path, text, *fence)

    monkeypatch.setattr(storage, "_replace", refused)

    notice = change_record.save(store, finished(), MERGED, AT)

    assert notice.startswith("the record of notes was not saved; no decision of notes was archived"), notice
    assert "permission denied" in notice
    assert len(replaced) == 1  # one file was in place before the second failed
    assert list(root.rglob("decisions/*.md")) == []
    assert not (root / "shop-site" / "changes" / f"{STEM}.json").exists()  # F2: no record commit without its archive
    assert git(root, "status", "--porcelain") == ""


def test_a_known_refusal_puts_the_record_and_its_decisions_back(store, shared_repo, monkeypatch) -> None:
    root, _ = shared_repo
    monkeypatch.setattr(
        decision_sync,
        "publish",
        lambda *_a, **_k: decision_sync.Sent(notice="saved, but not committed: refused", uncommitted=True),
    )

    notice = change_record.save(store, finished(), MERGED, AT)

    assert "refused" in notice
    assert archived(root) == {}
    assert not (root / "shop-site" / "changes" / f"{STEM}.json").exists()
    assert decision_batch.pending(store.shared) is None
    assert decision_store.load(store.shared, "shop-site").snapshot is not None
    assert git(root, "status", "--porcelain") == ""


def test_a_raw_archive_is_refused_while_a_batch_is_interrupted(store) -> None:
    root = store.shared.root
    generation = decision_batch.begin(
        store.shared,
        "shop-site",
        decision_store._head(store.shared),  # noqa: SLF001
        "decisions: left",
        ["D-LEFT"],
        [("shop-site/decisions/D-LEFT.md", None, b"left\n")],  # the smallest valid batch: one new file, by its id
    )

    with pytest.raises(decision_store.DecisionsUnavailable, match="interrupted decision batch"):
        decision_archive.archive(root, "shop-site", finished(), STEM, "merged")
    assert archived(root) == {}
    assert decision_batch.pending(store.shared).generation == generation


def test_a_crash_after_the_first_archived_file_leaves_readers_blocked(store, monkeypatch) -> None:
    root = store.shared.root
    real_write = decision_store.write
    calls: list[int] = []

    def first_then_crash(*args, **kwargs):
        calls.append(1)
        if len(calls) > 1:
            msg = "call interrupted after the first file"
            raise RuntimeError(msg)
        real_write(*args, **kwargs)

    monkeypatch.setattr(decision_store, "write", first_then_crash)
    with pytest.raises(RuntimeError, match="call interrupted"):
        decision_archive.archive(root, "shop-site", finished(), STEM, "merged")

    assert len(archived(root)) == 1  # the prefix reached disk
    assert decision_batch.pending(store.shared) is not None
    with pytest.raises(decision_store.DecisionsUnavailable, match="interrupted decision batch"):
        decision_store.load(store.shared, "shop-site")


def test_an_archive_is_published_while_its_batch_is_still_pending(store, monkeypatch) -> None:
    root = store.shared.root
    pending_at_publish: list[bool] = []

    def lost_publish(_repo, _paths, _message, _until, _head, *_cont):
        pending_at_publish.append(decision_batch.pending(store.shared) is not None)
        msg = "publish lost after the files were written"
        raise RuntimeError(msg)

    monkeypatch.setattr(decision_sync, "publish", lost_publish)
    with pytest.raises(RuntimeError, match="publish lost"):
        decision_archive.archive(root, "shop-site", finished(), STEM, "merged")

    assert pending_at_publish == [True]
    assert decision_batch.pending(store.shared) is not None
    with pytest.raises(decision_store.DecisionsUnavailable, match="interrupted decision batch"):
        decision_store.load(store.shared, "shop-site")


OWNER_WIP = b"the owner's edit, not yet committed\n"


def _published_once(root: Path, store: Store, c: Change, *, record: bool) -> Path:
    """Publish *c* once through the record or the archive, then give it one more decision: the next publication plans
    every earlier decision unchanged and only the new one changed. The path of an unchanged project decision."""
    if record:
        assert change_record.save(store, c, MERGED, AT) == ""
    else:
        assert decision_archive.archive(root, "shop-site", c, STEM, "merged")[0]
    at = AT + timedelta(hours=2)
    c.decisions.append(Decision(id=new_id(AT), text="Notes keep their order", origin="decided", at=at, paths=["a.css"]))
    return root / "shop-site" / "decisions" / f"{c.brief.approved[0].decisions[1].id}.md"


def _spy_archive(
    monkeypatch, root: Path, unchanged: Path, *, owner_edit: bool
) -> tuple[list[set[str]], list[set[str]]]:
    """Record each journal's files and each `write_plan` result; with *owner_edit*, the owner edits *unchanged* during
    the fsync of a changed file's temporary, so a commit of every planned path would publish that edit."""
    journals: list[set[str]] = []
    written: list[set[str]] = []
    real_begin, real_plan, real_fsync = decision_batch.begin, decision_archive.write_plan, os.fsync
    changes = root / "shop-site" / "changes" / STEM / "decisions"

    def begin(*args):
        journals.append({rel for rel, _, _ in args[-1]})  # the journal's files, its last argument
        return real_begin(*args)

    def write_plan(*args, **kwargs):
        files, left = real_plan(*args, **kwargs)
        written.append({p.relative_to(root).as_posix() for p in files})
        return files, left

    def fsync_then_owner_edits(descriptor):
        real_fsync(descriptor)
        if not owner_edit or not changes.is_dir() or unchanged.read_bytes() == OWNER_WIP:
            return
        found = os.fstat(descriptor)
        if any(os.path.samestat(found, p.stat()) for p in changes.iterdir() if p.name.endswith(".tmp")):
            unchanged.write_bytes(OWNER_WIP)

    monkeypatch.setattr(decision_batch, "begin", begin)
    monkeypatch.setattr(decision_archive, "write_plan", write_plan)
    monkeypatch.setattr(os, "fsync", fsync_then_owner_edits)
    return journals, written


def _committed(root: Path) -> set[str]:
    return set(git(root, "show", "--name-only", "--format=", "HEAD").split())


def test_a_record_publishes_only_the_decision_files_it_journalled(store, shared_repo, monkeypatch) -> None:
    """The owner edits an unchanged decision file while the record is written; no healthy case is needed beside it,
    as its asserts are a superset of a healthy run's."""
    root, _ = shared_repo
    c = finished()
    unchanged = _published_once(root, store, c, record=True)
    published = unchanged.read_bytes()

    with monkeypatch.context() as m:
        journals, written = _spy_archive(m, root, unchanged, owner_edit=True)
        assert change_record.save(store, c, MERGED, AT) == ""

    (journal,) = journals
    record = f"shop-site/{decision_archive.CHANGES}/{STEM}.json"
    assert unchanged.relative_to(root).as_posix() not in journal  # planned unchanged, so never journalled
    assert _committed(root) == journal  # the commit holds exactly the journalled files
    assert written == [journal - {record}]  # and the files write_plan returns are the journal's, no more
    assert decision_batch.pending(store.shared) is None
    rel = unchanged.relative_to(root).as_posix()
    shown = subprocess.run(["git", "show", f"HEAD:{rel}"], cwd=root, check=True, capture_output=True)  # noqa: S603, S607
    assert shown.stdout == published  # HEAD still holds the published bytes
    assert unchanged.read_bytes() == OWNER_WIP  # the owner's edit stays theirs, unpublished
    assert git(root, "status", "--porcelain").split() == ["M", unchanged.relative_to(root).as_posix()]


def test_an_archive_publishes_only_the_decision_files_it_journalled(store, shared_repo, monkeypatch):
    """As the record's: the owner's edit during the archive proves everything a healthy archive would."""
    root, _ = shared_repo
    c = finished()
    unchanged = _published_once(root, store, c, record=False)

    with monkeypatch.context() as m:
        journals, written = _spy_archive(m, root, unchanged, owner_edit=True)
        files, left = decision_archive.archive(root, "shop-site", c, STEM, "merged")

    (journal,) = journals
    assert unchanged.relative_to(root).as_posix() not in journal
    assert _committed(root) == journal
    assert {p.relative_to(root).as_posix() for p in files} == journal
    assert written[-1] == journal
    assert not left
    assert decision_batch.pending(store.shared) is None
    assert unchanged.read_bytes() == OWNER_WIP


def test_an_archive_with_nothing_to_change_journals_and_publishes_nothing(shared_repo, monkeypatch) -> None:
    root, _ = shared_repo
    c = finished()
    assert decision_archive.archive(root, "shop-site", c, STEM, "merged")[0]  # every file written and published once
    head = git(root, "rev-parse", "HEAD")

    with monkeypatch.context() as m:
        journals, written = _spy_archive(m, root, root / "unused", owner_edit=False)
        files, left = decision_archive.archive(root, "shop-site", c, STEM, "merged")

    assert (files, left, journals, written) == ([], [], [], [set()])
    assert git(root, "rev-parse", "HEAD") == head
    assert git(root, "status", "--porcelain") == ""


@pytest.mark.parametrize("owner", [True, False], ids=["owner-changes-a-file-as-it-is-staged", "healthy"])
@pytest.mark.parametrize("producer", ["record", "archive"])
def test_a_record_or_archive_commit_that_does_not_hold_the_batch_is_never_pushed(
    store, shared_repo, monkeypatch, producer, owner
):
    """Just before Git stages the batch, the owner writes a third image into its first file: the commit then holds it
    instead of the journalled image, so it stays local and unpushed and the batch stays interrupted."""
    root, remote = shared_repo

    def remote_main() -> str:
        return git(root, "--git-dir", str(remote), "rev-parse", "main")

    published, fired = remote_main(), []
    third = b"the owner's own third image\n"
    real_commit = DataRepo.commit

    def commit(self, paths, message, until=None):
        if owner and not fired:
            fired.append(next(iter(paths)))
            fired[0].write_bytes(third)
        return real_commit(self, paths, message, until)

    with monkeypatch.context() as m:
        m.setattr(DataRepo, "commit", commit)
        if producer == "record":
            said = change_record.save(store, finished(), MERGED, AT)
        else:
            said = "; ".join(decision_archive.archive(root, "shop-site", finished(), STEM, "merged")[1])

    if not owner:
        assert said == ""
        assert remote_main() != published
        assert decision_batch.pending(store.shared) is None
        return
    assert "not pushed" in said
    assert remote_main() == published  # nothing pushed
    assert fired[0].read_bytes() == third  # the owner's bytes are kept
    assert decision_batch.pending(store.shared) is not None


def test_a_journal_failure_inside_a_record_save_is_a_notice_and_keeps_the_journal(store, shared_repo, monkeypatch):
    """The batch lock fails as the record's batch completes, after the guard passed: the save returns a notice for
    its caller to log, never raises, and the journal is left as it was."""
    root, _ = shared_repo
    real_complete = decision_batch.complete

    def complete(repo, generation):
        lock = decision_batch.journal_path(store.shared).parent / decision_batch.LOCK
        lock.unlink(missing_ok=True)
        lock.symlink_to(root.parent / "elsewhere.lock")
        return real_complete(repo, generation)

    with monkeypatch.context() as m:
        m.setattr(decision_batch, "complete", complete)
        said = change_record.save(store, finished(), MERGED, AT)

    assert said.startswith("the record of notes was not saved")
    assert "batch lock" in said
    assert decision_batch.journal_path(store.shared).exists()


@pytest.mark.parametrize("refusal", ["unsettled", "planning"])
def test_a_change_record_failure_is_logged_whole(shared_repo, tmp_path, monkeypatch, whole_error, refusal) -> None:
    """The notice cleanup logs as the "change-record" event: an unreadable journal behind the guard, or planning
    refused by the decision history; each names the whole error."""
    if refusal == "unsettled":

        def unreadable(_shared):
            raise decision_batch.JournalError(whole_error)

        monkeypatch.setattr(decision_batch, "pending", unreadable)
        expected = f"the record of notes was not saved: Unsettled: JournalError: {whole_error}"
    else:

        def unreadable_history(*_args):
            raise OSError(whole_error)

        monkeypatch.setattr(decision_archive, "_history", unreadable_history)
        expected = (f"the record of notes was not saved; no decision of notes was archived; "
                    f"decision history of notes: OSError: {whole_error}")  # fmt: skip

    local = LocalStore(tmp_path / "store", DataRepo(shared_repo[0]), "shop-site")
    local.root.mkdir(parents=True)
    c = finished()
    c.step = Step(kind=StepKind.CLEANUP, mode="abandon")
    _, result = cleanup.run(engine.Ctx(local, Lock(c.slug), tmp_path, Profile(version=1, entries={}), object(), AT), c)
    assert result.exit == Exit.DONE, result.reason
    assert [e["notice"] for e in local.events(c.slug) if e["event"] == "change-record"] == [expected]


@pytest.mark.parametrize("site", ["published", "planned", "unreadable-repo", "graph"])
def test_each_archive_refusal_names_its_whole_error(store, monkeypatch, whole_error, site) -> None:
    """Each reason a decision is refused, from the brief's validation to the repository's graph, as said whole."""
    from pydantic import ValidationError  # noqa: PLC0415

    from owlbear_decisions.validate import Finding  # noqa: PLC0415

    c = finished()
    ui = c.decisions[0].id
    refusal = "the record of notes was not saved; no decision of notes was archived"
    if site == "published":
        invalid = ValidationError.from_exception_data(
            "Decision",
            [{"type": "value_error", "loc": ("statement",), "input": "", "ctx": {"error": ValueError(whole_error)}}],
        )

        def unpublishable(*_args):
            raise invalid

        monkeypatch.setattr(decision_archive, "_as_decision", unpublishable)
        lasting = c.brief.approved[0].decisions[1].id
        with pytest.raises(DecisionError) as refused:
            decision_archive.lasting("shop-site", c, STEM)
        assert str(refused.value) == f"decision {lasting} of notes cannot be published: ValidationError: {invalid}"
        return
    if site == "planned":
        real = decision_archive.check_write

        def refusing(current, decision, expected):
            if decision.id == ui:
                raise DecisionError(whole_error)
            return real(current, decision, expected)

        monkeypatch.setattr(decision_archive, "check_write", refusing)
        expected = f"{refusal}; decision {ui} of notes: DecisionError: {whole_error}"
    elif site == "unreadable-repo":

        def unreadable(*_args):
            raise OSError(whole_error)

        monkeypatch.setattr(decision_archive, "read_repo", unreadable)
        expected = (
            f"{refusal}; the decisions of notes cannot be checked against {store.shared.root}: OSError: {whole_error}"
        )
    else:
        monkeypatch.setattr(decision_archive, "check", lambda _entries: [Finding("x.md", "rule", whole_error, (ui,))])
        expected = f"{refusal}; decision {ui} of notes: rule: {whole_error}"

    assert change_record.save(store, c, MERGED, AT) == expected
