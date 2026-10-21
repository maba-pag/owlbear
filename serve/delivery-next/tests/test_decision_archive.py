"""A finished Change's decisions become decision files in its record's commit (TD-419 slice 2, TD-148)."""

from __future__ import annotations

import json
import subprocess
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

import pytest

from owlbear_decisions import Scope, State, new_id, read, validate_repo
from owlbear_delivery_next.change_contracts.curation_records import TestReview
from owlbear_delivery_next.change_contracts.models import Brief, BriefDecision, Change, Decision
from owlbear_delivery_next.change_contracts.profile_record import Profile
from owlbear_delivery_next.change_flow import brief_tools
from owlbear_delivery_next.github.provider import PullRequest
from owlbear_delivery_next.local_system.data_repo import DataRepo
from owlbear_delivery_next.state_store import briefs, change_record

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
    c.decisions.append(
        Decision(id=mint(), text=UI, origin="decided", at=at, words="Not a UI change", paths=["web/app.css"])
    )
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
    assert [(w.text, w.date) for w in limit.owner_words] == [("Yes, 800 characters", AT.date())]
    where = read(root / project / "decisions" / f"{c.brief.approved[0].decisions[1].id}.md")
    assert (where.actor, where.owner_words, where.created_at) == ("shaper", (), AT)
    assert where.source == "Change notes, brief v2 approved 2026-10-15T09:00:00+00:00"
    ui = read(root / change / "decisions" / f"{c.decisions[0].id}.md")
    assert (ui.applies_to.paths, ui.owner_words[0].date, ui.rationale) == (
        ("web/app.css",),
        AT.date(),
        "From Change notes (merged).",
    )
    assert ui.owner_words[0].text == "Not a UI change"  # the owner's answer, not Delivery's signature
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


def test_a_rerun_after_a_crash_before_publishing_publishes_the_same_files_once(store, shared_repo, monkeypatch) -> None:
    root, remote = shared_repo
    c = finished()

    def crash(*_a: object, **_k: object) -> str:
        msg = "power cut"
        raise OSError(msg)

    publish = DataRepo.publish
    monkeypatch.setattr(DataRepo, "publish", crash)
    assert "power cut" in change_record.save(store, c, MERGED, AT)
    written = {p: p.read_text() for p in (root / "shop-site").rglob("decisions/*.md")}
    assert len(written) == 3
    assert git(root, "status", "--porcelain")  # written, never committed
    monkeypatch.setattr(DataRepo, "publish", publish)

    assert change_record.save(store, c, MERGED, AT) == ""
    assert {p: p.read_text() for p in (root / "shop-site").rglob("decisions/*.md")} == written
    assert git(root, "status", "--porcelain") == ""
    count = git(remote, "rev-list", "--count", "main")
    assert change_record.save(store, c, MERGED, AT) == ""  # a third run changes nothing at all
    assert (git(remote, "rev-list", "--count", "main"), len(archived(root))) == (count, 3)


def test_an_older_change_without_ids_loads_and_archives_with_the_same_ids_every_time(store, shared_repo) -> None:
    root, _ = shared_repo
    old = json.loads(finished().model_dump_json())
    for d in [*old["brief"]["approved"][0]["decisions"], *old["decisions"]]:
        del d["id"]
        d.pop("scope", None)
        d.pop("replaces", None)
        d.pop("words", None)
    c = Change.model_validate(old)
    assert [d.id for d in c.brief.approved[0].decisions] == ["", ""]

    assert change_record.save(store, c, MERGED, AT) == ""
    first = sorted(p.name for p in (root / "shop-site").rglob("decisions/*.md"))
    assert change_record.save(store, Change.model_validate(old), MERGED, AT) == ""
    assert sorted(p.name for p in (root / "shop-site").rglob("decisions/*.md")) == first
    assert len(first) == 3
    # an older Change kept no owner's words for Delivery's own decisions: none are claimed (TD-388 allows none)
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


def test_one_decision_that_cannot_be_written_keeps_all_out_and_the_record_still_publishes(store, shared_repo) -> None:
    root, _ = shared_repo
    c = finished()
    assert change_record.save(store, c, None, AT) == ""  # abandoned: withdrawn, and the lasting rule a draft
    before = {p: p.read_text() for p in root.rglob("decisions/*.md")}

    notice = change_record.save(store, c, MERGED, AT)

    assert notice.startswith("no decision of notes was archived"), notice
    assert "cannot go from withdrawn to spent" in notice
    assert {p: p.read_text() for p in root.rglob("decisions/*.md")} == before  # not even the allowed draft move
    assert archived(root)[WHERE][2] is State.DRAFT
    assert json.loads((root / "shop-site" / "changes" / f"{STEM}.json").read_text())["outcome"] == "merged"
    assert git(root, "status", "--porcelain") == ""


def test_an_invalid_decision_is_a_notice_and_nothing_is_archived(store, shared_repo) -> None:
    root, _ = shared_repo
    c = finished()
    c.decisions.append(Decision(id=new_id(AT), text="Paths outside", origin="decided", at=AT, paths=["../x"]))
    notice = change_record.save(store, c, MERGED, AT)
    assert c.decisions[1].id in notice
    assert list(root.rglob("decisions/*.md")) == []
    assert (root / "shop-site" / "changes" / f"{STEM}.json").exists()
