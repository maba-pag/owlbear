"""A finished Change's decisions become decision files in its record's commit (TD-419 slice 2, TD-148)."""

from __future__ import annotations

import json
import subprocess
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

import pytest

from owlbear_decisions import Decision as Rule
from owlbear_decisions import Link, LinkType, Origin, Scope, State, new_id, read, storage, validate_repo, write
from owlbear_delivery_next.change_contracts.curation_records import TestReview
from owlbear_delivery_next.change_contracts.models import Brief, BriefDecision, Change, Decision
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

if TYPE_CHECKING:
    from pathlib import Path

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


def test_a_decision_keeps_its_id_across_brief_versions_and_a_new_question_gets_its_own() -> None:
    def draft(*decisions: tuple[str, str]) -> brief_tools.BriefDraft:
        made = [{"question": q, "answer": a, "origin": "decided", "scope": "project"} for q, a in decisions]
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


def test_a_merged_change_archives_its_decisions_with_the_record_in_one_commit(store, shared_repo) -> None:
    root, remote = shared_repo
    c = finished()
    assert change_record.save(store, c, MERGED, AT + timedelta(days=1)) == ""

    project, change = "shop-site", f"shop-site/changes/{STEM}"
    assert archived(root) == {
        LIMIT: (change, Scope.CHANGE, State.SPENT),
        WHERE: (project, Scope.PROJECT, State.IN_FORCE),
        UI: (change, Scope.CHANGE, State.SPENT),
    }
    limit = read(root / change / "decisions" / f"{c.brief.approved[0].decisions[0].id}.md")
    assert (limit.statement, limit.topic, limit.actor, limit.change) == ("Yes, 800 characters", "Notes", "owner", STEM)
    assert limit.read_back == AT.date().isoformat()  # decided: confirmed at the brief's approval
    where = read(root / project / "decisions" / f"{c.brief.approved[0].decisions[1].id}.md")
    assert (where.actor, where.read_back, where.created_at) == ("shaper", "none", AT)
    assert where.source == "Change notes, brief v2 approved 2026-10-15T09:00:00+00:00"
    ui = read(root / change / "decisions" / f"{c.decisions[0].id}.md")
    assert (ui.read_back, ui.rationale) == (
        (AT + timedelta(hours=1)).date().isoformat(),
        "From Change notes (merged).",
    )
    assert "applies_to" not in ui.content()  # no selectors (TD-460)
    files = "".join(p.read_text(encoding="utf-8") for p in (root / "shop-site").rglob("decisions/*.md"))
    assert "owner_words" not in files
    assert "skip the UI review" not in files  # the owner's answer is never stored (TD-449)
    assert validate_repo(root) == []
    commits = {git(remote, "log", "--format=%H", "main", "--", rel) for rel in (f"{change}.json", change, project)}
    assert len(commits) == 1  # the record and every decision file in the same commit
    assert git(root, "status", "--porcelain") == ""


@pytest.mark.parametrize(
    "ending",
    [
        (MERGED, False, "merged", State.SPENT, State.IN_FORCE),
        (None, True, "unchanged", State.SPENT, State.IN_FORCE),
        (None, False, "abandoned", State.WITHDRAWN, State.DRAFT),
    ],
)
def test_each_ending_gives_its_states(store, shared_repo, ending) -> None:
    root, _ = shared_repo
    pr, unchanged, outcome, brief, lasting = ending
    assert change_record.save(store, finished(unchanged=unchanged), pr, AT) == ""
    found = archived(root)
    assert {title: state for title, (_, _, state) in found.items()} == {LIMIT: brief, WHERE: lasting, UI: brief}
    assert read(next((root / "shop-site" / "decisions").iterdir())).rationale == f"From Change notes ({outcome})."
    assert validate_repo(root) == []


def test_a_crash_before_publishing_stays_interrupted_until_the_owner_finishes_it_once(
    store, shared_repo, monkeypatch
) -> None:
    root, remote = shared_repo
    c = finished()

    real_publish = decision_sync.publish

    def crash(*_a: object, **_k: object):
        msg = "power cut"
        raise OSError(msg)

    monkeypatch.setattr(decision_sync, "publish", crash)
    assert "power cut" in change_record.save(store, c, MERGED, AT)
    written = {p: p.read_text() for p in (root / "shop-site").rglob("decisions/*.md")}
    assert len(written) == 3
    assert git(root, "status", "--porcelain")  # written, never committed
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


def test_an_older_change_without_ids_loads_and_archives_with_the_same_ids_every_time(store, shared_repo) -> None:
    root, _ = shared_repo
    old = json.loads(finished().model_dump_json())
    for d in [*old["brief"]["approved"][0]["decisions"], *old["decisions"]]:
        del d["id"]
        d.pop("scope", None)
        d.pop("replaces", None)
    c = Change.model_validate(old)
    assert [d.id for d in c.brief.approved[0].decisions] == ["", ""]

    assert change_record.save(store, c, MERGED, AT) == ""
    first = sorted(p.name for p in (root / "shop-site").rglob("decisions/*.md"))
    assert change_record.save(store, Change.model_validate(old), MERGED, AT) == ""
    assert sorted(p.name for p in (root / "shop-site").rglob("decisions/*.md")) == first
    assert len(first) == 3
    assert validate_repo(root) == []


def test_older_changes_of_two_projects_never_share_an_id(shared_repo) -> None:
    root, _ = shared_repo
    old = json.loads(finished().model_dump_json())
    for d in [*old["brief"]["approved"][0]["decisions"], *old["decisions"]]:
        d["id"] = ""
    for name in ("shop-site", "shop-app"):
        other = Store(root)
        other.name = name
        assert change_record.save(other, Change.model_validate(old), MERGED, AT) == ""
    names = [p.name for p in root.rglob("decisions/*.md")]
    assert len(names) == len(set(names)) == 6
    assert not [f for f in validate_repo(root) if f.rule == "duplicate-id"]


def test_an_older_changes_words_are_dropped_on_loading_and_never_written_back(tmp_path) -> None:
    old = json.loads(finished().model_dump_json())
    old["decisions"][0]["words"] = "Right, skip the UI review"
    c = Change.model_validate(old)
    local = LocalStore(tmp_path / "store")

    local.write(Lock(c.slug), c)

    assert "words" not in c.decisions[0].model_dump()
    written = [p.read_bytes() for p in (tmp_path / "store").rglob("*") if p.is_file()]
    assert not [b for b in written if b"skip the UI review" in b]
    assert local.read(c.slug).decisions[0].text == UI


def test_each_decided_answer_is_confirmed_on_the_approval_of_the_latest_version_holding_it(store, shared_repo):
    root, _ = shared_repo
    one, two, three = AT - timedelta(days=5), AT - timedelta(days=2), AT
    dropped = BriefDecision(id=new_id(AT), question=LIMIT, answer="Yes, 800 characters", origin="decided")
    kept = BriefDecision(id=new_id(AT), question=WHERE, answer="One SQLite table", origin="decided", scope="project")
    versions = [Brief(version=1, title="Notes", approved_at=one, decisions=[dropped, kept]),
                Brief(version=2, title="Notes", approved_at=two, decisions=[dropped, kept]),
                Brief(version=3, title="Notes", approved_at=three, decisions=[kept])]  # fmt: skip
    c = Change(slug="notes", handle="c4", brief=Brief(version=3, approved_at=three, approved=versions))

    assert change_record.save(store, c, MERGED, AT) == ""

    early, late = (read(next(root.rglob(f"decisions/{d.id}.md"))) for d in (dropped, kept))
    assert (early.read_back, late.read_back) == (two.date().isoformat(), three.date().isoformat())
    assert early.created_at == late.created_at == three  # its record's time stays the brief's approval


def test_a_changed_answer_after_approval_is_a_successor_and_both_are_archived(store, shared_repo) -> None:
    root, _ = shared_repo

    def draft(answer: str) -> brief_tools.BriefDraft:
        made = [{"question": LIMIT, "answer": answer, "origin": "decided"}]
        fields = {"title": "Notes", "outcome": "Owners keep notes on a page.", "criteria": ["A note keeps 800 chars"]}
        return brief_tools.BriefDraft(**fields, scope=["web"], decisions=made)

    c = briefs.drafted(None, draft("Yes, 800"), "notes", "c4", Profile())
    c.brief = c.brief.model_copy(update={"approved_at": AT, "approved": [c.brief.model_copy()]})
    first = c.brief.decisions[0]
    c = briefs.drafted(c, draft("Yes, 1000"), "notes", "c4", Profile())
    second = c.brief.decisions[0]
    assert (second.id != first.id, second.replaces) == (True, first.id)
    c = briefs.drafted(c, draft("Yes, 1200"), "notes", "c4", Profile())
    assert (c.brief.decisions[0].id, c.brief.decisions[0].replaces) == (second.id, first.id)  # still one successor
    c = briefs.drafted(c, draft("Yes, 800"), "notes", "c4", Profile())
    assert (c.brief.decisions[0].id, c.brief.decisions[0].replaces) == (first.id, "")  # back to the approved answer
    c = briefs.drafted(c, draft("Yes, 1000"), "notes", "c4", Profile())
    c.brief = c.brief.model_copy(update={"approved": [*c.brief.approved, c.brief.model_copy(update={"approved": []})]})

    assert change_record.save(store, c, MERGED, AT) == ""
    old, new = (read(next(root.rglob(f"decisions/{d.id}.md"))) for d in (first, c.brief.decisions[0]))
    assert (old.state, old.statement, new.state, new.statement) == (
        State.REPLACED,
        "Yes, 800",
        State.SPENT,
        "Yes, 1000",
    )
    assert [(link.type, link.target) for link in new.links] == [("replaces", first.id)]
    assert validate_repo(root) == []


def test_a_repeated_question_is_refused() -> None:
    made = [{"question": q, "answer": "Yes", "origin": "decided"} for q in (LIMIT, "  limit the NOTES? ")]
    fields = {"title": "Notes", "outcome": "Owners keep notes on a page.", "criteria": ["A note keeps 800 chars"]}
    errors = brief_tools.check_brief(brief_tools.BriefDraft(**fields, scope=["web"], decisions=made))
    assert any(e.startswith("decisions: a question repeats") for e in errors)


def test_an_autonomous_choices_reason_is_its_rationale_when_published_and_archived(store, shared_repo) -> None:
    root, _ = shared_repo
    c, why = finished(), "One table keeps the notes in the backup with the rest"
    approved = c.brief.approved[0]
    shaped = [approved.decisions[0], approved.decisions[1].model_copy(update={"reason": why})]
    c.brief.approved[0] = approved.model_copy(update={"decisions": shaped})

    (published,) = decision_archive.lasting("shop-site", c, STEM)
    assert why in published.rationale
    assert change_record.save(store, c, MERGED, AT) == ""
    assert why in read(root / "shop-site" / "decisions" / f"{shaped[1].id}.md").rationale


def test_one_decision_that_cannot_be_written_keeps_all_out_and_the_record_is_unchanged(store, shared_repo) -> None:
    root, _ = shared_repo
    c = finished()
    assert change_record.save(store, c, None, AT) == ""  # abandoned: withdrawn, and the lasting rule a draft
    before = {p: p.read_text() for p in root.rglob("decisions/*.md")}
    record = root / "shop-site" / "changes" / f"{STEM}.json"
    record_before, head_before = record.read_bytes(), git(root, "rev-parse", "HEAD")

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


def test_an_invalid_decision_is_a_notice_and_nothing_is_archived(store, shared_repo) -> None:
    root, _ = shared_repo
    c = finished()
    c.decisions.append(Decision(id="D-NOTANID", text="A malformed id", origin="decided", at=AT))
    head_before = git(root, "rev-parse", "HEAD")
    notice = change_record.save(store, c, MERGED, AT)
    assert c.decisions[1].id in notice
    assert list(root.rglob("decisions/*.md")) == []
    assert not (root / "shop-site" / "changes" / f"{STEM}.json").exists()  # no record without its decisions
    assert git(root, "rev-parse", "HEAD") == head_before
    assert git(root, "status", "--porcelain") == ""


def test_a_decision_that_would_break_the_repositorys_rules_keeps_all_out_and_the_record_is_not_written(
    store, shared_repo
) -> None:
    root, _ = shared_repo
    said = {"title": "Notes", "statement": "Notes live in SQLite.", "scope": Scope.PROJECT, "project": "shop-site",
            "origin": Origin.AUTONOMOUS, "actor": "shaper", "created_at": AT}  # fmt: skip
    old = Rule(id=new_id(AT), state=State.REPLACED, **said)
    later = Rule(id=new_id(AT), state=State.IN_FORCE, links=(Link(type=LinkType.REPLACES, target=old.id),), **said)
    for d in (old, later):
        write(d, root / "shop-site")
    git(root, "add", "-A")
    git(root, "commit", "-qm", "replaced in another Change")
    rivals = {p: p.read_text() for p in root.rglob("decisions/*.md")}
    head_before = git(root, "rev-parse", "HEAD")
    c = finished()
    decisions = c.brief.approved[0].decisions
    decisions[1] = lasting = decisions[1].model_copy(update={"replaces": old.id})  # a second in-force successor

    notice = change_record.save(store, c, MERGED, AT)

    assert notice.startswith("the record of notes was not saved; no decision of notes was archived"), notice
    assert f"decision {lasting.id}, {old.id} of notes: two-successors" in notice
    assert {p: p.read_text() for p in root.rglob("decisions/*.md")} == rivals  # rival rules untouched
    assert not (root / "shop-site" / "changes" / f"{STEM}.json").exists()
    assert git(root, "rev-parse", "HEAD") == head_before
    assert git(root, "status", "--porcelain") == ""


def test_a_project_answer_narrowed_to_the_change_is_withdrawn_and_its_successor_relates_to_it(store, shared_repo):
    root, _ = shared_repo
    first = BriefDecision(id=new_id(AT), question=WHERE, answer="One SQLite table", origin="decided", scope="project")
    second = BriefDecision(id=new_id(AT), question=WHERE, answer="SQLite for this Change only", origin="decided",
                           replaces=first.id)  # fmt: skip
    versions = [Brief(version=n, title="Notes", decisions=[d]) for n, d in ((1, first), (2, second))]
    c = Change(slug="notes", handle="c4", brief=Brief(version=2, approved_at=AT, approved=versions))

    assert change_record.save(store, c, MERGED, AT) == ""

    old, new = (read(next(root.rglob(f"decisions/{d.id}.md"))) for d in (first, second))
    assert (old.scope, old.state, new.scope, new.state) == (Scope.PROJECT, State.WITHDRAWN, Scope.CHANGE, State.SPENT)
    assert [(link.type, link.target) for link in new.links] == [(LinkType.RELATED_TO, first.id)]
    assert validate_repo(root) == []


def test_a_write_failing_midway_puts_every_file_back_and_the_record_is_refused(store, shared_repo, monkeypatch):
    root, _ = shared_repo
    replaced, real = [], storage._replace

    def full(path: Path, text: str) -> None:
        if replaced:
            msg = "disk full"
            raise OSError(msg)
        replaced.append(path)
        real(path, text)

    monkeypatch.setattr(storage, "_replace", full)

    notice = change_record.save(store, finished(), MERGED, AT)

    assert notice.startswith("the record of notes was not saved; no decision of notes was archived"), notice
    assert "disk full" in notice
    assert len(replaced) == 1  # one file was in place before the second failed
    assert list(root.rglob("decisions/*.md")) == []
    assert not (root / "shop-site" / "changes" / f"{STEM}.json").exists()  # F2: no record commit without its archive
    assert git(root, "status", "--porcelain") == ""


def test_a_publish_lost_after_the_record_and_archive_are_written_is_never_partial_authority(
    store, shared_repo, monkeypatch
) -> None:
    root, _ = shared_repo

    def lost(*_a: object, **_k: object) -> str:
        msg = "power cut"
        raise OSError(msg)

    monkeypatch.setattr(decision_sync, "publish", lost)
    assert "power cut" in change_record.save(store, finished(), MERGED, AT)

    assert len(archived(root)) == 3  # the files are on disk, unpublished
    assert decision_batch.pending(store.shared) is not None
    with pytest.raises(decision_store.DecisionsUnavailable, match="interrupted decision batch"):
        decision_store.load(store.shared, "shop-site")


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
        [],
        [],
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
            msg = "power cut after the first file"
            raise RuntimeError(msg)
        real_write(*args, **kwargs)

    monkeypatch.setattr(decision_store, "write", first_then_crash)
    with pytest.raises(RuntimeError, match="power cut"):
        decision_archive.archive(root, "shop-site", finished(), STEM, "merged")

    assert len(archived(root)) == 1  # the prefix reached disk
    assert decision_batch.pending(store.shared) is not None
    with pytest.raises(decision_store.DecisionsUnavailable, match="interrupted decision batch"):
        decision_store.load(store.shared, "shop-site")


def test_an_archive_is_published_while_its_batch_is_still_pending(store, monkeypatch) -> None:
    root = store.shared.root
    pending_at_publish: list[bool] = []

    def lost_publish(_repo, _paths, _message, _until, _head):
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
