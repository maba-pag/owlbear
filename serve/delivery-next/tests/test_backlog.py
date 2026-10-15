import json
import re
import subprocess
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from owlbear_delivery_next import cli
from owlbear_delivery_next.backlog import BACKLOG, Backlog, BacklogError
from owlbear_delivery_next.store import Store

T0 = datetime(2026, 10, 14, 8, tzinfo=UTC)


def git(cwd: Path, *args: str) -> str:
    who = ["-c", "user.name=t", "-c", "user.email=t@example.com"]
    return subprocess.run(["git", *who, *args], cwd=cwd, check=True, capture_output=True, text=True).stdout.strip()  # noqa: S603, S607


@pytest.fixture
def shared(tmp_path: Path, monkeypatch) -> tuple[Path, Path]:
    remote, root = tmp_path / "remote.git", tmp_path / "owlbear-data"
    git(tmp_path, "init", "-q", "--bare", "-b", "main", str(remote))
    git(tmp_path, "clone", "-q", str(remote), str(root))
    for key, value in (("user.name", "t"), ("user.email", "t@example.com")):
        git(root, "config", key, value)
    git(root, "commit", "-q", "--allow-empty", "-m", "start")
    git(root, "push", "-q", "origin", "HEAD")
    home = tmp_path / "home"
    home.mkdir()
    (home / "common.json").write_text(json.dumps({"repository": str(root)}))
    monkeypatch.setenv("OWLBEAR_HOME", str(home))
    return root, remote


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


def local(tmp_path: Path, clock: Clock | None = None) -> Backlog:
    return Backlog.of(Store(tmp_path / "store"), clock=clock or Clock())


def test_an_entry_is_one_file_in_the_projects_folder_of_the_shared_repository_and_is_published(shared, repo):
    root, remote = shared
    backlog = Backlog.of(Store.open(repo))

    entry, new, notice = backlog.add("Status line hides the step", "the line cuts at 80", "watcher", ["c3 build"])

    assert (new, notice) == (True, "")
    assert re.fullmatch(r"\d{8}-[0-9a-f]{6}", entry.id)
    path = root / "shop-site" / BACKLOG / f"{entry.id}.json"
    assert json.loads(path.read_text())["title"] == "Status line hides the step"
    assert (entry.kind, entry.status, entry.count, entry.evidence) == ("untriaged", "inbox", 1, ["c3 build"])
    assert git(remote, "log", "--format=%s", "main", "--", f"shop-site/{BACKLOG}").startswith("backlog shop-site: add")
    assert git(root, "status", "--porcelain") == ""


def test_a_finding_seen_again_counts_up_its_entry_and_keeps_new_evidence(tmp_path):
    clock = Clock()
    backlog = local(tmp_path, clock)
    first, _, _ = backlog.add("Status line hides the step", source="watcher", evidence=["c3 build"])
    clock.later(30)

    again, new, _ = backlog.add("status line  hides the step!", source="watcher", evidence=["c3 build", "c4 check"])
    other, other_new, _ = backlog.add("Status line hides the step", source="review")

    assert (new, again.id, again.count, again.first_seen, again.last_seen) == (False, first.id, 2, T0, clock.now)
    assert again.evidence == ["c3 build", "c4 check"]
    assert (other_new, other.id != first.id) == (True, True)
    assert len(list((tmp_path / "store" / BACKLOG).glob("*.json"))) == 2


def test_the_inbox_comes_first_then_open_entries_by_when_they_were_last_seen(tmp_path):
    clock = Clock()
    backlog = local(tmp_path, clock)
    ids = {}
    for title in ("old open", "inbox", "new open", "dropped"):
        ids[title] = backlog.add(title)[0].id
        clock.later(5)
    backlog.update(ids["old open"], {"kind": "defect"})
    backlog.update(ids["new open"], {"kind": "idea"})
    backlog.update(ids["dropped"], {"status": "dropped"})

    assert [e.title for e in backlog.entries()] == ["inbox", "new open", "old open", "dropped"]


def test_classifying_an_inbox_entry_opens_it_and_links_hold_on_both_sides(tmp_path):
    backlog = local(tmp_path)
    a, b, c = (backlog.add(t)[0].id for t in ("a", "b", "c"))

    classified, _ = backlog.update(a, {"kind": "improvement", "notes": "after the release", "links": [b, c, b]})
    backlog.update(a, {"links": [c]})

    assert (classified.kind, classified.status, classified.notes) == ("improvement", "open", "after the release")
    found, _ = backlog.read()
    assert (found[a].links, found[b].links, found[c].links) == ([c], [], [a])
    assert backlog.update(b, {"kind": "idea", "status": "inbox"})[0].status == "inbox"


@pytest.mark.parametrize(
    ("entry", "fields", "status"),
    [
        ("missing", {"notes": "x"}, 404),
        ("self", {"links": ["self"]}, 422),
        ("self", {"links": ["20260101-000000"]}, 422),
        ("self", {"notes": "x" * 4001}, 422),
    ],
)
def test_unknown_entries_links_and_oversized_fields_are_refused_and_nothing_is_written(tmp_path, entry, fields, status):
    backlog = local(tmp_path)
    me = backlog.add("me")[0]
    target = me.id if entry == "self" else "20990101-abcdef"
    fields = {k: [me.id if i == "self" else i for i in v] if k == "links" else v for k, v in fields.items()}

    with pytest.raises(BacklogError) as caught:
        backlog.update(target, fields)

    assert caught.value.status == status
    assert backlog.read()[0][me.id] == me


def test_taking_entries_into_a_change_records_the_launch_or_changes_nothing(tmp_path):
    backlog = local(tmp_path)
    a, b = (backlog.add(t)[0].id for t in ("a", "b"))

    with pytest.raises(BacklogError):
        backlog.take([a, "20990101-abcdef"], "l1")
    assert backlog.read()[0][a].status == "inbox"

    taken, _ = backlog.take([a, b], "l1")
    assert [(e.status, e.launch) for e in taken] == [("in-change", "l1")] * 2


def test_a_write_is_atomic_and_an_unreadable_file_is_reported_not_lost(tmp_path, monkeypatch):
    backlog = local(tmp_path)
    entry = backlog.add("kept")[0]
    path = tmp_path / "store" / BACKLOG / f"{entry.id}.json"
    before = path.read_text()
    (path.parent / "20260101-000000.json").write_text("{")

    def broken(_self, _target):
        full = "disk full"
        raise OSError(full)

    monkeypatch.setattr(Path, "replace", broken)
    with pytest.raises(OSError, match="disk full"):
        backlog.update(entry.id, {"notes": "lost"})

    assert path.read_text() == before
    assert sorted(p.name for p in path.parent.iterdir() if not p.name.startswith(".backlog")) == [
        "20260101-000000.json",
        path.name,
    ]
    found, bad = backlog.read()
    assert (list(found), bad) == ([entry.id], ["20260101-000000.json"])


@pytest.mark.parametrize("write", ["link", "take"])
def test_a_write_of_several_entries_that_fails_on_the_second_file_leaves_every_entry_as_it_was(
    tmp_path, monkeypatch, write
):
    backlog = local(tmp_path)
    a, b, c = (backlog.add(t)[0].id for t in ("a", "b", "c"))
    folder = tmp_path / "store" / BACKLOG
    before = {p.name: p.read_text() for p in folder.glob("*.json")}
    real, renamed = Path.replace, []

    def second_fails(self, target):
        renamed.append(target)
        if len(renamed) == 2:
            full = "disk full"
            raise OSError(full)
        return real(self, target)

    monkeypatch.setattr(Path, "replace", second_fails)
    with pytest.raises(OSError, match="disk full"):
        backlog.update(a, {"links": [b, c]}) if write == "link" else backlog.take([a, b, c], "l1")

    assert {p.name: p.read_text() for p in folder.glob("*.json")} == before
    assert [p.name for p in folder.iterdir() if p.name.startswith(".tmp-")] == []


def test_without_a_shared_repository_the_backlog_stays_in_the_clones_store(tmp_path):
    store = Store(tmp_path / "store")
    entry, _, notice = Backlog.of(store).add("an idea")
    assert ((store.root / BACKLOG / f"{entry.id}.json").exists(), notice) == (True, "")


def test_the_cli_adds_through_the_same_store_and_counts_a_repeat(shared, repo, capsys):
    root, _ = shared
    args = ["--repo", str(repo), "backlog", "add", "--title", "Flaky check", "--text", "fails one run in five"]
    args += ["--source", "run", "--evidence", "c7 check", "--evidence", "https://ci.example.com/run/1"]

    assert cli.main(args) == 0
    assert cli.main(args) == 0

    out = capsys.readouterr().out.splitlines()
    [entry] = Backlog.of(Store.open(repo)).entries()
    assert out == [f"added {entry.id}: Flaky check", f"seen again {entry.id}: Flaky check (2 times)"]
    assert (entry.source, entry.text, entry.count) == ("run", "fails one run in five", 2)
    assert entry.evidence == ["c7 check", "https://ci.example.com/run/1"]
    assert (root / "shop-site" / BACKLOG / f"{entry.id}.json").exists()
