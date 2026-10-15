import copy
import json
import subprocess
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from owlbear_delivery_next import backlog as backlog_module
from owlbear_delivery_next import backlog_migrate, cli
from owlbear_delivery_next.backlog import Backlog, BacklogError
from owlbear_delivery_next.backlog_issues import Issues
from owlbear_delivery_next.common import Common
from owlbear_delivery_next.store import Store

T0 = datetime(2026, 10, 14, 8, tzinfo=UTC)


def git(cwd: Path, *args: str) -> str:
    who = ["-c", "user.name=t", "-c", "user.email=t@example.com"]
    return subprocess.run(["git", *who, *args], cwd=cwd, check=True, capture_output=True, text=True).stdout.strip()  # noqa: S603, S607


@pytest.fixture
def shared(shared_repo, tmp_path: Path, monkeypatch) -> tuple[Path, Path]:
    home = tmp_path / "home"
    home.mkdir()
    (home / "common.json").write_text(json.dumps({"repository": str(shared_repo[0])}))
    monkeypatch.setenv("OWLBEAR_HOME", str(home))
    return shared_repo


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    path = tmp_path / "shop"
    git(tmp_path, "init", "-q", "-b", "main", str(path))
    git(path, "commit", "--allow-empty", "-qm", "start")
    git(path, "remote", "add", "origin", "git@github.com:acme/shop-site.git")
    return path


class Clock:
    def __init__(self) -> None:
        self.now = T0

    def __call__(self) -> datetime:
        return self.now

    def later(self, minutes: int) -> None:
        self.now += timedelta(minutes=minutes)


def view(root: Path, clock: Clock | None = None) -> Backlog:
    return Backlog(Common(root), "shop-site", clock or Clock())


def names(issue) -> list[str]:
    return [label["name"] for label in issue["labels"]]


def test_a_finding_is_one_issue_with_a_readable_body_and_labels_and_nothing_is_written_locally(shared, github):
    root, _ = shared
    refs = ["c3 build", "https://ci.example.com/1"]

    entry, new = view(root).add("Status line hides the step", "the line cuts at 80", "watcher", refs)

    assert (new, entry.id, entry.scope, entry.project, entry.status) == (True, "1", "unassigned", "shop-site", "inbox")
    [issue] = github.issues.values()
    assert (issue["title"], names(issue)) == ("Status line hides the step", ["scope:unassigned", "class:untriaged"])
    body = issue["body"]
    head = "**Class:** untriaged · **Scope:** unassigned (shop-site) · **Source:** watcher · **State:** inbox"
    assert body.startswith(f"the line cuts at 80\n\n{head}\n\n### Evidence\n\n- c3 build\n- https://ci.example.com/1")
    assert "\n\n**Repeats:** seen 1 time · first 2026-10-14 08:00 UTC · last 2026-10-14 08:00 UTC\n\n<!-- " in body
    assert {n: label["color"] for n, label in github.labels.items()} == {
        "scope:unassigned": "A67C52",
        "class:untriaged": "A67C52",
    }
    assert view(root).read(fresh=True) == ({"1": entry}, [])
    assert (git(root, "status", "--porcelain"), sorted(p.name for p in root.iterdir())) == ("", [".git"])


def test_a_finding_seen_again_counts_up_its_issue_and_comments_only_new_evidence(shared, github):
    clock = Clock()
    backlog = view(shared[0], clock)
    first, _ = backlog.add("Status line hides the step", source="watcher", evidence=["c3 build"])
    clock.later(30)

    again, new = backlog.add("status line  hides the step!", source="watcher", evidence=["c3 build", "c4 check"])
    clock.later(30)
    third, _ = backlog.add("Status line hides the step", source="watcher", evidence=["c4 check"])
    other, other_new = backlog.add("Status line hides the step", source="review")

    assert (new, again.id, again.count, again.first_seen, again.last_seen) == (
        False,
        first.id,
        2,
        T0,
        clock.now - timedelta(minutes=30),
    )
    assert (third.count, third.evidence) == (3, ["c3 build", "c4 check"])
    assert (other_new, other.id, len(github.issues)) == (True, "2", 2)
    assert github.comments == [(1, "New evidence:\n\n- c4 check")]
    body = github.issues[1]["body"]
    assert "**Repeats:** seen 3 times · first 2026-10-14 08:00 UTC · last 2026-10-14 09:00 UTC" in body
    assert (body.count("**Repeats:**"), github.issues[1]["title"]) == (1, "Status line hides the step")


def test_a_repeat_counts_up_only_its_own_project_s_entry_and_another_project_s_is_a_new_one_to_link(shared, github):
    root, title = shared[0], "Status line hides the step"
    shop, docs = view(root), Backlog(Common(root), "docs-site", Clock())
    first = shop.add(title, source="watcher")[0]

    elsewhere, new = docs.add(title, source="watcher")
    assert (new, elsewhere.id, elsewhere.project, len(github.issues)) == (True, "2", "docs-site", 2)
    assert [shop.add(title, source="watcher")[0].id, docs.add(title, source="watcher")[0].id] == ["1", "2"]

    shop.update(first.id, {"scope": "global", "links": [elsewhere.id]})  # shared: linked as connected entries
    assert (shop.add(title, source="watcher")[0].count, docs.add(title, source="watcher")[0].count) == (3, 3)
    docs.update(elsewhere.id, {"scope": "project", "project": "shop-site"})  # its project is now shop-site's
    moved, new = docs.add(title, source="watcher")
    assert (new, moved.id, names(github.issues[2])[-1]) == (True, "3", "project:shop-site")
    assert docs.read(fresh=True)[0]["1"].links == ["2"]


def test_missing_labels_are_created_once_in_owlbears_colour_and_other_labels_are_left_alone(shared, github):
    root, _ = shared
    github.labels["scope:unassigned"] = {"name": "scope:unassigned", "color": "000000"}
    github.labels["help wanted"] = {"name": "help wanted", "color": "008672"}
    a = view(root).add("a")[0]
    view(root).add("b")
    github.issues[1]["labels"].append({"name": "help wanted"})
    github.issues[1]["updated_at"] = "2099-01-01"

    view(root).update(a.id, {"kind": "defect", "scope": "project"})

    made = [body["name"] for method, endpoint, body in github.calls if method == "POST" and endpoint.endswith("labels")]
    assert made == ["class:untriaged", "scope:project", "class:defect", "project:shop-site"]
    assert names(github.issues[1]) == ["help wanted", "scope:project", "class:defect", "project:shop-site"]
    assert {n: label["color"] for n, label in github.labels.items()} == {
        "scope:unassigned": "000000",
        "help wanted": "008672",
    } | dict.fromkeys(made, "A67C52")
    issues = Issues(Common(root))
    issues.ensure_labels([])
    github.labels["scope:global"] = {"name": "scope:global", "color": "0e8a16"}  # made by another writer meanwhile
    issues.ensure_labels(["scope:global"])
    assert (len(github.labels), github.labels["scope:global"]["color"]) == (7, "0e8a16")


@pytest.mark.usefixtures("github")
def test_the_inbox_comes_first_then_open_entries_by_when_they_were_last_seen(shared):
    clock = Clock()
    backlog = view(shared[0], clock)
    ids = {}
    for title in ("old open", "inbox", "new open", "dropped"):
        ids[title] = backlog.add(title)[0].id
        clock.later(5)
    backlog.update(ids["old open"], {"kind": "defect"})
    backlog.update(ids["new open"], {"kind": "idea"})
    backlog.update(ids["dropped"], {"status": "dropped"})

    assert [e.title for e in view(shared[0]).entries()] == ["inbox", "new open", "old open", "dropped"]


def test_triage_opens_an_entry_links_both_issues_and_done_or_dropped_closes_the_issue(shared, github):
    backlog = view(shared[0])
    a, b, c = (backlog.add(t)[0].id for t in ("a", "b", "c"))

    classified = backlog.update(a, {"kind": "improvement", "notes": "after the release", "links": [b, c, b]})
    backlog.update(a, {"links": [c]})
    backlog.update(b, {"status": "done"})
    backlog.update(c, {"status": "dropped"})

    assert (classified.kind, classified.status, classified.notes) == ("improvement", "open", "after the release")
    found, _ = backlog.read()
    assert (found[a].links, found[b].links, found[c].links) == ([c], [], [a])
    assert "### Owner's notes\n\nafter the release" in github.issues[1]["body"]
    assert "### Connected entries\n\n- #3" in github.issues[1]["body"]
    closed = [(github.issues[n]["state"], github.issues[n]["state_reason"]) for n in (1, 2, 3)]
    assert closed == [("open", None), ("closed", "completed"), ("closed", "not_planned")]
    assert (backlog.update(c, {"status": "inbox"}).status, github.issues[3]["state"]) == ("inbox", "open")


def test_github_holds_the_title_class_scope_and_state_and_an_issue_without_a_readable_entry_is_reported(shared, github):
    backlog = view(shared[0])
    backlog.add("a")
    backlog.add("b")
    github.issues[1] |= {"title": "renamed", "state": "closed", "state_reason": "not_planned"}
    github.issues[1] |= {"labels": [{"name": "scope:global"}, {"name": "class:idea"}], "updated_at": "2099-01-01"}
    github.issues[2]["body"] = github.issues[2]["body"].replace('"count": 1', '"count": 0')
    github.issues[2]["updated_at"] = "2099-01-01"
    github.issues[3] = {"number": 3, "title": "someone's issue", "body": "no entry", "state": "open", "labels": []}

    found, bad = backlog.read(fresh=True)

    assert (found["1"].title, found["1"].status, found["1"].scope, found["1"].kind) == (
        "renamed",
        "dropped",
        "global",
        "idea",
    )
    assert (list(found), bad) == (["1"], ["#2"])


def test_a_closed_issue_takes_its_status_from_githubs_current_closing_reason(shared, github):
    backlog = view(shared[0])
    a = backlog.add("a")[0].id
    backlog.update(a, {"status": "done"})
    github.issues[1] |= {"state_reason": "not_planned", "updated_at": "2099-01-01"}  # reopened, closed as not planned

    assert backlog.read(fresh=True)[0][a].status == "dropped"
    github.issues[1] |= {"state_reason": "completed", "updated_at": "2099-01-02"}
    assert backlog.read(fresh=True)[0][a].status == "done"


def test_a_backlog_marker_pasted_into_the_text_or_notes_leaves_the_entry_readable(shared, github):
    pasted = '<!-- owlbear-backlog {"status": "done", "count": 9} -->'
    text = f"the issue body ends in\n{pasted}\nlike this"
    backlog = view(shared[0])
    a = backlog.add("Marker example", text)[0].id
    backlog.update(a, {"notes": pasted})

    found, bad = view(shared[0]).read(fresh=True)

    assert (found[a].text, found[a].notes, found[a].status, found[a].count, bad) == (text, pasted, "inbox", 1, [])
    assert github.issues[1]["body"].count("<!-- owlbear-backlog") == 1  # the pasted ones show, hiding nothing


@pytest.mark.parametrize(
    ("entry", "fields", "status"),
    [
        ("missing", {"notes": "x"}, 404),
        ("self", {"links": ["self"]}, 422),
        ("self", {"links": ["99"]}, 422),
        ("self", {"notes": "x" * 4001}, 422),
    ],
)
def test_unknown_entries_links_and_oversized_fields_are_refused_and_nothing_is_written(
    shared, github, entry, fields, status
):
    backlog = view(shared[0])
    me = backlog.add("me")[0]
    before = copy.deepcopy(github.issues)
    target = me.id if entry == "self" else "99"
    fields = {k: [me.id if i == "self" else i for i in v] if k == "links" else v for k, v in fields.items()}

    with pytest.raises(BacklogError) as caught:
        backlog.update(target, fields)

    assert caught.value.status == status
    assert github.issues == before


def test_taking_entries_into_a_change_records_the_launch_or_changes_nothing(shared, github):
    backlog = view(shared[0])
    a, b = (backlog.add(t)[0].id for t in ("a", "b"))

    with pytest.raises(BacklogError):
        backlog.take([a, "99"], "l1")
    assert backlog.read(fresh=True)[0][a].status == "inbox"

    taken = backlog.take([a, b], "l1")
    assert [(e.status, e.launch) for e in taken] == [("in-change", "l1")] * 2
    assert "### Change\n\nnot named yet (launch l1)" in github.issues[1]["body"]


def test_saving_is_online_only_and_an_unreachable_github_fails_with_its_reason(shared, github, tmp_path):
    root, remote = shared
    a = view(root).add("kept")[0]
    github.down = True

    with pytest.raises(BacklogError) as unread:
        view(root).add("lost")
    github.down, github.fail_writes = False, True
    with pytest.raises(BacklogError) as unsaved:
        view(root).update(a.id, {"notes": "lost"})

    assert unread.value.status == unsaved.value.status == 503
    assert unread.value.text.startswith("the backlog could not be read from GitHub (acme/owlbear-data)")
    assert "error connecting to api.github.com" in unread.value.text
    assert unsaved.value.text.startswith("GitHub (acme/owlbear-data) did not confirm the save; check its issues")
    github.fail_writes = False
    assert (len(github.issues), view(root).read(fresh=True)[0][a.id]) == (1, a)
    assert (sorted(p.name for p in root.iterdir()), git(remote, "log", "--format=%s", "main")) == ([".git"], "start")
    with pytest.raises(BacklogError, match="no shared repository is set up"):
        Backlog.of(Store(tmp_path / "store"))


@pytest.mark.parametrize(
    ("visibility", "said"),
    [
        ("public", "it is public, not private"),
        ("internal", "it is internal, not private"),
        ("unread", "its visibility is unknown (repo_visibility: Not Found (HTTP 404))"),
    ],
)
def test_nothing_is_written_unless_github_says_the_shared_repository_is_private(shared, github, visibility, said):
    root, _ = shared
    github.visibility, answer = visibility, github.answer
    if visibility == "unread":
        github.answer = lambda method, parts, *rest: (404, "Not Found") if not parts else answer(method, parts, *rest)

    with pytest.raises(BacklogError) as refused:
        view(root).add("a report")

    assert refused.value.status == 503
    said = f"not saved to GitHub (acme/owlbear-data): repo_visibility: {said}; the backlog is written only to a "
    assert refused.value.text == said + "private repository"
    assert (github.issues, github.labels, [m for m, *_ in github.calls if m != "GET"]) == ({}, {}, [])


def test_a_private_repository_is_checked_once_for_a_while_before_the_first_write(shared, github):
    root, _ = shared
    a = view(root).add("a")[0]
    view(root).add("b")
    view(root).update(a.id, {"notes": "n"})

    assert [endpoint for _, endpoint, _ in github.calls].count("repos/acme/owlbear-data") == 1
    first_write = next(i for i, (method, *_) in enumerate(github.calls) if method != "GET")
    assert github.calls[first_write - 1][1] == "repos/acme/owlbear-data"


def test_an_issue_github_does_not_list_yet_is_read_from_the_write_and_a_repeat_still_counts_up(shared, github):
    root, _ = shared
    a = view(root).add("Flaky check", source="run")[0]
    github.hidden = {1}

    again, new = view(root).add("Flaky check", source="run")
    triaged = view(root).update(a.id, {"kind": "defect"})

    assert (new, again.id, again.count, triaged.status, len(github.issues)) == (False, "1", 2, "open", 1)
    assert [(e.id, e.count, e.kind) for e in view(root).entries()] == [("1", 2, "defect")]


def test_an_edit_on_github_wins_over_this_process_s_own_write_and_every_change_starts_from_the_issue_as_it_is(
    shared, github
):
    root, _ = shared
    a = view(root).add("a")[0].id
    github.issues[1]["title"] = "renamed on GitHub"  # in the same second as the write: an equal updated_at

    assert view(root).read(fresh=True)[0][a].title == "renamed on GitHub"
    github.hidden = {1}  # the listing lags behind a later edit; the cached write would be older still
    github.issues[1] |= {"title": "renamed again", "labels": [{"name": "help wanted"}], "updated_at": "2099-01-01"}
    view(root).update(a, {"notes": "kept"})
    assert (github.issues[1]["title"], names(github.issues[1])[0]) == ("renamed again", "help wanted")
    assert view(root).read(fresh=True)[0][a].notes == "kept"


def test_reads_are_reused_briefly_and_every_write_reads_github_afresh(shared, github):
    root, _ = shared
    view(root).add("a")

    def lists() -> int:
        return sum(method == "GET" and "/issues?" in endpoint for method, endpoint, _ in github.calls)

    before = lists()
    view(root).read()
    view(root).read()
    assert lists() == before + 1
    view(root).add("b")
    assert lists() == before + 2
    view(root).read()
    assert lists() == before + 3


@pytest.mark.usefixtures("shared", "github")
def test_the_cli_adds_an_issue_and_counts_a_repeat(repo, capsys):
    args = ["--repo", str(repo), "backlog", "add", "--title", "Flaky check", "--text", "fails one run in five"]
    args += ["--source", "run", "--evidence", "c7 check", "--evidence", "https://ci.example.com/run/1"]

    assert cli.main(args) == 0
    assert cli.main(args) == 0

    out = capsys.readouterr().out.splitlines()
    [entry] = Backlog.of(Store.open(repo)).entries()
    assert out == ["added #1: Flaky check", "seen again #1: Flaky check (2 times)"]
    assert (entry.source, entry.text, entry.count, entry.project) == ("run", "fails one run in five", 2, "shop-site")
    assert entry.evidence == ["c7 check", "https://ci.example.com/run/1"]


def old_file(root: Path, entry_id: str, title: str, **fields) -> Path:
    at = "2026-10-14T16:54:28.175115Z"
    data = {"id": entry_id, "title": title, "text": "", "source": "run", "kind": "untriaged", "status": "inbox"}
    data |= {"notes": "", "links": [], "evidence": [], "change": "", "launch": "", "count": 1}
    data |= {"first_seen": at, "last_seen": at, "updated_at": at} | fields
    path = root / "owlbear" / "backlog" / f"{entry_id}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=1) + "\n")
    return path


def committed(root: Path, *paths: Path) -> list[Path]:
    git(root, "add", "--", *map(str, paths))
    git(root, "commit", "-qm", "backlog files")
    git(root, "push", "-q")
    return list(paths)


def test_migration_moves_each_file_into_one_issue_verifies_then_deletes_and_pushes_the_files(shared, github):
    root, remote = shared
    a, b = "20261014-1fec46", "20261014-26f37e"
    committed(
        root,
        old_file(root, a, "Code index", text="detail", evidence=[".owlbear/ideas.md: Code index"], links=[b]),
        old_file(root, b, "Visual judges", kind="defect", status="done", notes="fixed", count=2, links=[a]),
    )
    answer = github.answer

    def lagging(method, parts, params, body):  # GitHub lists no issue made during the run
        out = answer(method, parts, params, body)
        if method == "POST" and parts == ["issues"]:
            github.hidden.add(out[1]["number"])
        return out

    github.answer = lagging
    said = []

    assert backlog_migrate.migrate(Common(root), said.append) == 0
    github.answer, github.hidden = answer, set()

    assert said == [
        f"created #1: {a} Code index",
        f"created #2: {b} Visual judges",
        "verified 2 issues in acme/owlbear-data; deleted 2 files",
    ]
    assert names(github.issues[1]) == ["scope:project", "class:untriaged", "project:owlbear"]
    assert (names(github.issues[2])[1], github.issues[2]["state"], github.issues[2]["state_reason"]) == (
        "class:defect",
        "closed",
        "completed",
    )
    found = Backlog(Common(root)).read(fresh=True)[0]
    assert [(e.legacy, e.links, e.count, e.status) for e in sorted(found.values(), key=lambda e: int(e.id))] == [
        (a, ["2"], 1, "inbox"),
        (b, ["1"], 2, "done"),
    ]
    assert not (root / "owlbear" / "backlog").exists()
    assert git(remote, "log", "-1", "--format=%s", "main") == "backlog: 2 entries moved to GitHub issues (TD-103)"
    assert "backlog" not in git(remote, "ls-tree", "-r", "--name-only", "main")
    again = []
    assert (backlog_migrate.migrate(Common(root), again.append), again, len(github.issues)) == (
        0,
        ["no file entries to migrate"],
        2,
    )


def test_a_migration_stopped_midway_keeps_every_file_and_a_rerun_creates_only_the_missing_issues(shared, github):
    root, _ = shared
    files = committed(root, *(old_file(root, f"20261014-00000{n}", f"entry {n}") for n in (1, 2, 3)))
    answer = github.answer

    def second_create_fails(method, parts, params, body):
        if method == "POST" and parts == ["issues"] and len(github.issues) == 1:
            return 502, "Server Error"
        return answer(method, parts, params, body)

    github.answer = second_create_fails
    said = []
    assert backlog_migrate.migrate(Common(root), said.append) == 1
    assert said[0] == "created #1: 20261014-000001 entry 1"
    assert said[1].startswith("stopped, no file deleted: GitHub (acme/owlbear-data) did not confirm the save")
    assert all(p.exists() for p in files)

    github.answer = answer
    said = []
    assert backlog_migrate.migrate(Common(root), said.append) == 0
    assert said[:3] == [
        "already #1: 20261014-000001 entry 1",
        "created #2: 20261014-000002 entry 2",
        "created #3: 20261014-000003 entry 3",
    ]
    assert (len(github.issues), [p.exists() for p in files]) == (3, [False] * 3)


class Crash(BaseException):
    """The migrating process dies."""


def test_a_fresh_run_after_a_crash_finds_the_issues_made_before_it_while_github_does_not_list_them(
    shared, github, monkeypatch
):
    root, _ = shared
    files = committed(root, *(old_file(root, f"20261014-00000{n}", f"entry {n}", status="done") for n in (1, 2, 3)))
    answer = github.answer

    def crash_at_the_third(method, parts, params, body):  # GitHub lists no issue made during the test
        if method == "POST" and parts == ["issues"] and len(github.issues) == 2:
            raise Crash
        out = answer(method, parts, params, body)
        if method == "POST" and parts == ["issues"]:
            github.hidden.add(out[1]["number"])
        return out

    github.answer = crash_at_the_third
    with pytest.raises(Crash):
        backlog_migrate.migrate(Common(root), [].append)
    assert (json.loads((root / backlog_migrate.JOURNAL).read_text()), git(root, "status", "--porcelain")) == (
        {"20261014-000001": "1", "20261014-000002": "2"},
        "",
    )
    for name in ("_cache", "_recent"):  # a fresh process: none of the first one's writes are remembered
        monkeypatch.setattr(backlog_module, name, {})
    github.answer = answer  # #1 and #2 still not listed

    said = []
    assert backlog_migrate.migrate(Common(root), said.append) == 0
    assert said[:3] == [
        "already #1: 20261014-000001 entry 1",
        "already #2: 20261014-000002 entry 2",
        "created #3: 20261014-000003 entry 3",
    ]
    assert (len(github.issues), [github.issues[n]["state"] for n in (1, 2, 3)]) == (3, ["closed"] * 3)
    assert ([p.exists() for p in files], (root / backlog_migrate.JOURNAL).exists()) == ([False] * 3, False)


def test_an_issue_that_does_not_read_back_as_its_file_or_an_unreadable_file_blocks_every_deletion(shared, github):
    root, _ = shared
    files = committed(
        root, old_file(root, "20261014-000001", "a", notes="context"), old_file(root, "20261014-000002", "b")
    )
    edit = github.edit

    def lossy(issue, body):
        out = edit(issue, body)
        issue["body"] = issue["body"].replace('"notes": "context"', '"notes": ""')
        return out

    github.edit = lossy
    said = []
    assert backlog_migrate.migrate(Common(root), said.append) == 1
    assert said[-1] == "not verified, no file deleted: 20261014-000001 (#1): notes differ"
    (root / "owlbear" / "backlog" / "20261014-000003.json").write_text("{")
    said = []
    assert backlog_migrate.migrate(Common(root), said.append) == 1
    assert said[0].startswith("unreadable: owlbear/backlog/20261014-000003.json")
    assert all(p.exists() for p in files)
