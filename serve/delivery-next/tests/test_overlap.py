import subprocess
from datetime import UTC, datetime, timedelta

import pytest

from owlbear_delivery_next import loop, overlap
from owlbear_delivery_next.loop import StepResult
from owlbear_delivery_next.models import (
    AnswerItem,
    Brief,
    Change,
    Exit,
    Overlap,
    Plan,
    Question,
    Step,
    StepKind,
    Task,
)
from owlbear_delivery_next.status import Activity, card
from owlbear_delivery_next.store import Store

NOW = datetime(2026, 10, 10, 12, tzinfo=UTC)
K = StepKind


def git(cwd, *args, check=True):
    done = subprocess.run(["git", *args], cwd=cwd, check=check, capture_output=True, text=True)  # noqa: S603, S607
    return done.stdout.strip()


@pytest.fixture(autouse=True)
def git_env(tmp_path, monkeypatch):
    (tmp_path / "gitconfig").write_text("")
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", str(tmp_path / "gitconfig"))
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")
    for who in ("AUTHOR", "COMMITTER"):
        monkeypatch.setenv(f"GIT_{who}_NAME", "t")
        monkeypatch.setenv(f"GIT_{who}_EMAIL", "t@t")


def plan(*scope: str) -> Plan:
    return Plan(tasks=[Task(id="t1", title="one", scope=list(scope))])


def integrating(**fields) -> Change:
    brief = Brief(title="Speed", outcome="pages load in 1 s")
    return Change(**{"slug": "c1", "brief": brief, "plan": plan("src"), "step": Step(kind=K.INTEGRATE)} | fields)


@pytest.fixture
def conflicted(tmp_path):
    """A Change branch whose update with main conflicts on src/app.ts (and also changes a lockfile)."""
    repo = tmp_path / "repo"
    repo.mkdir()
    git(repo, "init", "-q", "-b", "main")
    (repo / "src").mkdir()
    for text, msg in [("a", "base")]:
        (repo / "src/app.ts").write_text(text)
        (repo / "uv.lock").write_text(text)
        git(repo, "add", ".")
        git(repo, "commit", "-qm", msg)
    git(repo, "switch", "-qc", "change")
    (repo / "src/app.ts").write_text("mine")
    (repo / "uv.lock").write_text("mine")
    git(repo, "commit", "-qam", "mine")
    git(repo, "switch", "-q", "main")
    (repo / "src/app.ts").write_text("theirs")
    (repo / "uv.lock").write_text("theirs")
    git(repo, "commit", "-qam", "theirs")
    git(repo, "switch", "-q", "change")
    start = git(repo, "rev-parse", "HEAD")
    git(repo, "merge", "-q", "main", check=False)
    return repo, start


def test_overlapping_plans_are_recorded_as_information_on_the_card():
    others = {"c2": ["packages/app"], "c3": ["packages/web"], "c4": ["."]}
    assert overlap.found(plan("packages/app/src"), others) == [
        Overlap(other="c2", paths=["packages/app/src"]),
        Overlap(other="c4", paths=["packages/app/src"]),
    ]
    c = loop.apply(integrating(step=Step(kind=K.PLAN), plan=None), StepResult(exit=Exit.DONE, plan=plan("x")), NOW)
    assert (c.step.kind, loop.open_question(c)) == (K.BUILD, None)  # planning continues
    c.overlaps = [Overlap(other="c3", paths=["src/app.ts"])]
    alive = Activity(host_up=True, runner_alive=True, last_event_at=NOW)
    assert card(c, alive, [], NOW)["overlaps"] == ["overlaps with c3: src/app.ts"]


@pytest.mark.parametrize(
    "shared", [["README.md"], ["docs/guide"], ["uv.lock"], ["web/package-lock.json"], ["dist"], ["a/app.min.js"]]
)
def test_docs_lockfiles_and_generated_output_are_no_overlap(shared):
    assert overlap.found(plan(*shared), {"c2": shared}) == []


def test_linguist_generated_paths_are_no_overlap(tmp_path):
    (tmp_path / ".gitattributes").write_text("# x\napi/gen/** linguist-generated\n*.pb.go linguist-generated=true\n")
    patterns = overlap.generated(tmp_path)
    assert overlap.found(plan("api/gen/client.ts", "x/y.pb.go"), {"c2": ["api", "x"]}, patterns) == []


def test_a_resolved_conflict_on_another_changes_scope_asks_naming_both_outcomes(conflicted):
    repo, start = conflicted
    (repo / "src/app.ts").write_text("both")
    (repo / "uv.lock").write_text("both")
    git(repo, "commit", "-qam", "merge main")
    paths = overlap.collided(repo, start, resolved=True)
    assert paths == ["src/app.ts", "uv.lock"]
    near = [overlap.Neighbour("c3", ["src", "uv.lock"], "cache pages", merged=True)]
    asked = overlap.collision(integrating(), paths, near)
    q = asked.question
    assert (asked.exit, q.step, [o.id for o in q.options]) == (Exit.ASK, K.INTEGRATE, ["keep", "adopt", "pause"])
    assert "c3 on src/app.ts." in q.text  # the lockfile is incidental
    assert ("pages load in 1 s" in q.text, "c3 (merged) wants: cache pages" in q.text) == (True, True)
    assert overlap.collision(integrating(), paths, [overlap.Neighbour("c4", ["lib"], "x", merged=False)]) is None


def test_an_unfinished_update_on_another_changes_scope_asks_once_and_the_answer_continues(conflicted, tmp_path):
    repo, start = conflicted
    store = Store(tmp_path / "store")
    other = Change(slug="c3", handle="c3", brief=Brief(outcome="cache pages"), plan=plan("src/app.ts"))
    with store.lock("c3") as lock:
        store.write(lock, other)
    said = StepResult(exit=Exit.ASK, question=Question(step=K.INTEGRATE, text="checks fail after the update"))
    c = integrating()
    asked = overlap.integrated(store, c, repo, (start, "ask"), said)
    assert "The Builder said: checks fail after the update" in asked.question.text
    assert overlap.integrated(store, c, repo, (start, "timeout"), said) is said
    c = loop.apply(c, asked, NOW)
    q = loop.open_question(c)
    keep, step = loop.schedule(c, [AnswerItem(at=NOW, question=q.id, option="keep")], NOW)
    assert step.kind == K.INTEGRATE
    assert overlap.integrated(store, keep, repo, (start, "ask"), said) is said  # answered: not asked again
    paused, step = loop.schedule(c, [AnswerItem(at=NOW, question=q.id, option="pause")], NOW)
    assert (step, paused.intent.paused_at) == (None, NOW)


def test_neighbours_are_other_open_or_recently_merged_changes(tmp_path):
    store = Store(tmp_path / "store")
    old, recent = NOW - overlap.RECENT - timedelta(seconds=1), NOW - timedelta(days=1)
    for slug, finished in [("c1", None), ("c2", None), ("c3", recent), ("c4", old)]:
        with store.lock(slug) as lock:
            store.write(lock, Change(slug=slug, plan=plan(f"{slug}/x"), finished_at=finished))
    near = overlap.neighbours(store, "c1", NOW)
    assert [(n.handle, n.scope, n.merged) for n in near] == [("c2", ["c2/x"], False), ("c3", ["c3/x"], True)]
