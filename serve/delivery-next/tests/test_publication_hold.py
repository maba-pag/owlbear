"""A stale automatic config fill stays bound to the shared remote through every push and rebase (R15, FND-01).

Each test runs separate Git checkouts of one bare remote: the winner's fill is checked against the freshly fetched
remote before each push or rebase, wherever the other checkout's completion lands, and once refused it is never pushed
by a later publication, a restart or a raw push. Nothing in Git is undone.
"""

import json
import os
import stat
import subprocess
import sys
import time
from pathlib import Path

import pytest

from owlbear_delivery_next.change_contracts.profile_record import Profile, ProfileEntry
from owlbear_delivery_next.local_system import data_repo, publication_hold
from owlbear_delivery_next.local_system.data_repo import DataRepo, DataRepoError
from owlbear_delivery_next.settings import profile
from owlbear_delivery_next.settings.config import Layer
from owlbear_delivery_next.state_store import config_save, decision_sync, prefs_import, profile_share
from owlbear_delivery_next.state_store.pending_intents import pending_file
from owlbear_delivery_next.state_store.store import Store, StoreError

PROJECT = "shop-site"


@pytest.fixture(autouse=True)
def explicit_bare_policy():
    """Every real-Git fixture runs under the explicit bare-repository policy, including child processes."""
    policy = {
        "GIT_CONFIG_COUNT": "1",
        "GIT_CONFIG_KEY_0": "safe.bareRepository",
        "GIT_CONFIG_VALUE_0": "explicit",
    }
    with pytest.MonkeyPatch.context() as patch:
        for key, value in policy.items():
            patch.setenv(key, value)
        assert {key: os.environ[key] for key in policy} == policy
        yield


def git(where: Path, *args: str) -> str:
    done = subprocess.run(["git", *args], cwd=where, check=True, capture_output=True, text=True)  # noqa: S603, S607
    return done.stdout.strip()


def checkout(remote: Path, tmp_path: Path, name: str) -> Store:
    """A separate clone of *remote*: its own Git folder, index, lock and private store."""
    where = tmp_path / name
    git(tmp_path, "clone", "-q", str(remote), str(where))
    for key, value in (("user.name", "t"), ("user.email", "t@example.com")):
        git(where, "config", key, value)
    return Store(tmp_path / f"{name}-store", DataRepo(where), PROJECT)


def remote_head(remote: Path) -> str:
    return git(remote, "--git-dir=.", "rev-parse", "main")


def remote_has_config(remote: Path) -> bool:
    return bool(git(remote, "--git-dir=.", "ls-tree", "main", "--", f"{PROJECT}/config.json"))


def remote_marker(remote: Path) -> str:
    shown = git(remote, "--git-dir=.", "show", f"main:{PROJECT}/{profile_share.PROFILE}")
    return Profile.model_validate_json(shown).prefs_import


def complete_and_delete(settler: Store) -> None:
    """The other checkout catches up, Settings completes the import, the owner publishes then deletes the config."""
    assert settler.shared.pull() == ""
    assert settler.read_profile().prefs_import == "pending"
    settler.mark_prefs_import("pending", "done")
    settler.config_path.write_text(Layer().model_dump_json(indent=1))
    assert settler.shared.publish(settler.config_path, f"settings: {PROJECT}: project layer") == ""
    settler.config_path.unlink()
    assert settler.shared.publish(settler.config_path, f"settings: {PROJECT}: project layer removed") == ""


def unrelated_advance(other: Store) -> None:
    notes = other.shared.root / "unrelated" / "notes.md"
    notes.parent.mkdir(parents=True, exist_ok=True)
    notes.write_text(f"an unrelated change {time.monotonic_ns()}\n")
    assert other.shared.publish(notes, "unrelated: notes") == ""


@pytest.fixture
def three(shared_repo, tmp_path) -> tuple[Store, Store, Path]:
    """The winner's and the settler's checkouts of a remote whose profile has a confirmed legacy value."""
    root, remote = shared_repo
    seed = Store(tmp_path / "seed-store", DataRepo(root), PROJECT)
    seed.write_profile(
        Profile(entries={profile.POLL: ProfileEntry(state="known", value="45", evidence=profile.CONFIRMED)})
    )
    return checkout(remote, tmp_path, "winner"), checkout(remote, tmp_path, "settler"), remote


def at_git(monkeypatch, winner: Store, when, act) -> list[int]:
    """Run *act* once, before the winner's Git call that *when* picks, while the fill is being saved."""
    real, seen, fired = data_repo._git, [0], []  # noqa: SLF001 - the publisher's own Git calls are the boundary

    def spy(cwd, *args, until=None):
        if not fired and cwd == winner.shared.root and armed and when(args, seen):
            fired.append(True)
            act()
        return real(cwd, *args, until=until)

    armed: list[bool] = []
    fill = winner.update_config

    def arming(change, what="project layer", on_written=None):
        armed.append(True)
        try:
            return fill(change, what, on_written)
        finally:
            armed.clear()

    monkeypatch.setattr(data_repo, "_git", spy)
    monkeypatch.setattr(winner, "update_config", arming)
    return fired


def nth_push(n: int):
    def when(args, seen) -> bool:
        if args[:1] != ("push",):
            return False
        seen[0] += 1
        return seen[0] == n

    return when


def command(args) -> str:
    """The Git subcommand of *args*, past any leading ``-c key=value`` options (the commit runs with some)."""
    rest = list(args)
    while rest[:1] == ["-c"]:
        rest = rest[2:]
    return rest[0] if rest else ""


def after_pull(args, _seen) -> bool:
    return command(args) == "commit"  # the first Git write after the pull and the guards: the remote moves now


def test_a_completion_after_the_winners_pull_holds_the_fill_before_any_push(three, monkeypatch):
    winner, settler, remote = three
    fired = at_git(monkeypatch, winner, after_pull, lambda: complete_and_delete(settler))

    with pytest.raises(StoreError, match="is held because"):
        prefs_import.run(winner)

    assert fired == [True]
    assert remote_head(remote) == git(settler.shared.root, "rev-parse", "HEAD")  # the settler's state, nothing after
    assert not remote_has_config(remote)
    assert remote_marker(remote) == "done"
    assert winner.shared.held()  # the refusal is durable, not one callback's answer


def test_a_completion_at_the_first_push_holds_the_fill_instead_of_rebasing_it(three, monkeypatch):
    winner, settler, remote = three
    fired = at_git(monkeypatch, winner, nth_push(1), lambda: complete_and_delete(settler))
    with pytest.raises(StoreError, match=r"not pushed: .*is held because"):
        prefs_import.run(winner)

    assert fired == [True]
    assert not remote_has_config(remote)
    assert remote_marker(remote) == "done"
    # nothing was undone or rebased: the winner's own fill commit stays on its old base for the owner to review
    root = winner.shared.root
    assert git(root, "diff-tree", "--no-commit-id", "--name-only", "-r", "HEAD") == f"{PROJECT}/config.json"
    rebased = subprocess.run(["git", "merge-base", "--is-ancestor", remote_head(remote), "HEAD"], cwd=root, check=False)  # noqa: S603, S607
    assert rebased.returncode == 1
    assert winner.config_path.exists()


def test_a_completion_between_the_checked_rebase_and_the_second_push_is_held_by_the_retry(three, monkeypatch):
    winner, settler, remote = three
    other = checkout(remote, settler.shared.root.parent, "other")
    real = data_repo._git  # noqa: SLF001 - the publisher's own Git calls are the boundary
    pushes = [0]

    def spy(cwd, *args, until=None):
        if armed and cwd == winner.shared.root and args[:1] == ("push",):
            pushes[0] += 1
            if pushes[0] == 1:
                unrelated_advance(other)  # rejected first push: a healthy, checked rebase follows
            elif pushes[0] == 2:
                complete_and_delete(settler)  # the remote moves again after the check, before the second push
        return real(cwd, *args, until=until)

    armed, fill = [], winner.update_config

    def once(change, what="project layer", on_written=None):
        armed.append(True)
        try:
            return fill(change, what, on_written)
        finally:
            armed.clear()

    monkeypatch.setattr(data_repo, "_git", spy)
    monkeypatch.setattr(winner, "update_config", once)
    with pytest.raises(StoreError, match="the push failed"):
        prefs_import.run(winner)
    assert pushes[0] == 2
    assert not remote_has_config(remote)
    monkeypatch.setattr(data_repo, "_git", real)

    before = remote_head(remote)
    with pytest.raises(StoreError, match="is held because"):
        prefs_import.run(winner)  # the retry's catch-up checks the new remote first and rebases nothing
    assert remote_head(remote) == before
    assert not remote_has_config(remote)
    assert remote_marker(remote) == "done"


@pytest.fixture
def held(three, monkeypatch) -> tuple[Store, Path]:
    """A winner whose stale fill was refused at its first push: committed here, unpushed, the refusal recorded."""
    winner, settler, remote = three
    at_git(monkeypatch, winner, nth_push(1), lambda: complete_and_delete(settler))
    with pytest.raises(StoreError, match="is held because"):
        prefs_import.run(winner)
    monkeypatch.undo()
    return winner, remote


HOLD_CALLERS = ["push", "pull", "rebase", "raw-push", "owned-push"]


def held_call(shared: DataRepo, action: str) -> str:
    until = time.monotonic() + 30
    if action == "push":
        return shared._push(until)  # noqa: SLF001 - the ordinary shared publication path
    if action == "raw-push":
        return shared.git("push", "-q", until=until).stderr
    if action == "owned-push":
        goal = decision_sync.target(shared, until)
        assert goal is not None
        return decision_sync.push_commit(shared, git(shared.root, "rev-parse", "HEAD"), goal, until)
    return getattr(shared, action)(until)


@pytest.mark.parametrize("action", HOLD_CALLERS)
def test_a_dangling_hold_introduced_during_its_git_probe_never_replays_or_pushes_the_stale_fill(
    held, monkeypatch, action
):
    winner, remote = held
    shared, root = winner.shared, winner.shared.root
    record = root / git(root, "rev-parse", "--git-path", publication_hold.RECORD)
    saved = record.with_suffix(".saved")
    raw, before, owner = record.read_bytes(), remote_head(remote), owner_state(root)
    assert "changed on the shared remote" in shared.held()  # a normal refusal precedes the damaged entry
    real, fired, ran = data_repo._git, [], []  # noqa: SLF001

    def at_probe(cwd, *args, until=None):
        if cwd == root:
            if not fired and args == ("rev-parse", "--git-path", publication_hold.RECORD):
                fired.append(True)
                record.rename(saved)
                record.symlink_to("missing-held-publication.json")
            if command(args) in {"pull", "rebase", "push"}:
                ran.append(args)
        return real(cwd, *args, until=until)

    monkeypatch.setattr(data_repo, "_git", at_probe)
    with shared.locked():
        said = held_call(shared, action)

    observed = {
        "remote_has_config": remote_has_config(remote),
        "remote_marker": remote_marker(remote),
        "remote_unchanged": remote_head(remote) == before,
        "owner_unchanged": owner_state(root) == owner,
        "git_writes": ran,
    }
    assert observed == {
        "remote_has_config": False,
        "remote_marker": "done",
        "remote_unchanged": True,
        "owner_unchanged": True,
        "git_writes": [],
    }, said
    assert fired == [True]
    if action == "owned-push":
        assert said.startswith("nothing was pushed or rebased in ")  # the owned publisher keeps only 200 characters
    else:
        assert "held publication record" in said
        assert "cannot be read" in said
    assert publication_hold.recorded(shared, None)
    assert record.is_symlink()
    assert record.readlink() == Path("missing-held-publication.json")
    assert saved.read_bytes() == raw


@pytest.mark.parametrize("damage", ["dangling", "symlink", "directory", "unreadable"])
def test_every_hold_reader_keeps_a_damaged_entry_and_its_original_without_publishing(held, monkeypatch, damage):
    winner, remote = held
    shared, root = winner.shared, winner.shared.root
    record = root / git(root, "rev-parse", "--git-path", publication_hold.RECORD)
    saved = record.with_suffix(".saved")
    raw, before, owner = record.read_bytes(), remote_head(remote), owner_state(root)
    record.rename(saved)
    if damage in {"dangling", "symlink"}:
        record.symlink_to(saved if damage == "symlink" else "missing-held-publication.json")
    elif damage == "directory":
        record.mkdir()
    else:
        record.write_bytes(raw)
        record.chmod(0)
    entry, real, ran = record.lstat(), data_repo._git, []  # noqa: SLF001

    def spy(cwd, *args, until=None):
        if cwd == root and command(args) in {"pull", "rebase", "push"}:
            ran.append(args)
        return real(cwd, *args, until=until)

    monkeypatch.setattr(data_repo, "_git", spy)
    try:
        assert publication_hold.recorded(shared, None)
        for action in HOLD_CALLERS:
            said = held_call(shared, action)
            if action == "owned-push":
                assert said.startswith("nothing was pushed or rebased in ")
            else:
                assert "held publication record" in said
        assert "cannot be read" in publication_hold.check(shared, None, fetch=False)
        assert "cannot be read" in shared.held()
        publication_hold.settled(shared, None)
        requires = publication_hold.Requires("an automatic fill")
        with pytest.raises(DataRepoError, match=r"the automatic change was not written: .*cannot be read"):
            shared.hold(winner.config_path, requires)
        assert os.path.samestat(entry, record.lstat())
        assert saved.read_bytes() == raw
        assert ran == []
        assert remote_head(remote) == before
        assert not remote_has_config(remote)
        assert remote_marker(remote) == "done"
        assert owner_state(root) == owner
    finally:
        if damage == "unreadable":
            record.chmod(0o600)
    if damage == "unreadable":
        assert record.read_bytes() == raw


def test_a_hold_presence_probe_that_is_unreadable_dispatches_to_the_checked_pull(held, monkeypatch):
    winner, remote = held
    shared, root = winner.shared, winner.shared.root
    record = root / git(root, "rev-parse", "--git-path", publication_hold.RECORD)
    raw, before, owner = record.read_bytes(), remote_head(remote), owner_state(root)
    real_stat, real_git, ran = Path.stat, data_repo._git, []  # noqa: SLF001

    def unreadable(self, *args, **kwargs):
        if self == record:
            msg = "synthetic unreadable held entry"
            raise PermissionError(msg)
        return real_stat(self, *args, **kwargs)

    def spy(cwd, *args, until=None):
        if cwd == root and command(args) in {"pull", "rebase", "push"}:
            ran.append(args)
        return real_git(cwd, *args, until=until)

    monkeypatch.setattr(Path, "stat", unreadable)  # both entry-aware lstat and referent-following exists fail
    monkeypatch.setattr(data_repo, "_git", spy)

    assert publication_hold.recorded(shared, None)
    assert "is held because" in shared.pull()
    assert ran == []
    assert record.read_bytes() == raw
    assert remote_head(remote) == before
    assert not remote_has_config(remote)
    assert owner_state(root) == owner


# The batch-file subprocess harness's pattern: a FIFO read can fail this proof, never hang the test process.
HOLD_CHILD = r"""
import json, os, sys, time
from pathlib import Path
from owlbear_delivery_next.local_system import publication_hold
from owlbear_delivery_next.local_system.data_repo import DataRepo
from owlbear_delivery_next.state_store import decision_sync
assert (os.environ["GIT_CONFIG_COUNT"], os.environ["GIT_CONFIG_KEY_0"], os.environ["GIT_CONFIG_VALUE_0"]) == (
    "1", "safe.bareRepository", "explicit")
shared = DataRepo(Path(sys.argv[1]))
assert Path(publication_hold.__file__).resolve().is_relative_to(Path(sys.argv[2]).resolve())
until = time.monotonic() + 10
goal = decision_sync.target(shared, until)
head = shared.git("rev-parse", "HEAD", until=until).stdout.strip()
notices = [
    shared._push(until), shared.pull(until), shared.rebase(until), shared.git("push", "-q", until=until).stderr,
    decision_sync.push_commit(shared, head, goal, until),
    publication_hold.check(shared, until, fetch=False), shared.held(until),
]
publication_hold.settled(shared, until)
try:
    shared.hold(shared.root / "shop-site/config.json", publication_hold.Requires("an automatic fill"), until)
except Exception as exc:
    notices.append(str(exc))
print(json.dumps({"notices": notices, "recorded": publication_hold.recorded(shared, until)}))
"""


def test_a_fifo_hold_is_refused_by_every_caller_without_waiting(held):
    winner, remote = held
    root = winner.shared.root
    record = root / git(root, "rev-parse", "--git-path", publication_hold.RECORD)
    saved = record.with_suffix(".saved")
    raw, before, owner = record.read_bytes(), remote_head(remote), owner_state(root)
    record.rename(saved)
    os.mkfifo(record)
    entry = record.lstat()
    env = {**os.environ, "PYTHONPATH": os.pathsep.join(p for p in sys.path if p)}
    done = subprocess.run(  # noqa: S603 - a fixed script, this interpreter and disposable fixtures
        [sys.executable, "-c", HOLD_CHILD, str(root), str(Path(__file__).resolve().parents[3])],
        capture_output=True, text=True, timeout=15, env=env, check=False,
    )  # fmt: skip
    assert done.returncode == 0, done.stderr
    said = json.loads(done.stdout.strip().splitlines()[-1])
    assert said["recorded"]
    assert len(said["notices"]) == 8
    assert said["notices"][4].startswith("nothing was pushed or rebased in ")
    assert all("cannot be read" in notice for i, notice in enumerate(said["notices"]) if i != 4), said
    assert stat.S_ISFIFO(record.lstat().st_mode)
    assert os.path.samestat(entry, record.lstat())
    assert saved.read_bytes() == raw
    assert remote_head(remote) == before
    assert not remote_has_config(remote)
    assert remote_marker(remote) == "done"
    assert owner_state(root) == owner


@pytest.mark.parametrize("alias", ["none", "checkout", "ancestor"])
def test_absent_and_valid_regular_holds_still_publish_through_preexisting_checkout_aliases(three, tmp_path, alias):
    winner, _, remote = three
    root = winner.shared.root
    if alias != "none":
        link = tmp_path / "checkout-alias"
        link.symlink_to(root if alias == "checkout" else root.parent, target_is_directory=True)
        root = link if alias == "checkout" else link / root.name
    shared = DataRepo(root)
    record = root / git(root, "rev-parse", "--git-path", publication_hold.RECORD)
    assert not publication_hold.recorded(shared, None)
    assert publication_hold._load(record) is None  # noqa: SLF001 - genuine absence alone permits the ordinary path
    assert shared.pull() == ""
    watch = shared.project_path(PROJECT)
    requires = publication_hold.Requires("an automatic config fill")
    with shared.locked():
        shared.hold(watch, requires)
        raw = record.read_bytes()
        watch.write_text(Layer().model_dump_json(indent=1))
        assert shared.commit(watch, "settings: an automatic config fill") == ""
        assert publication_hold.recorded(shared, None)
        assert publication_hold.check(shared, None, fetch=True) == ""
        assert record.read_bytes() == raw  # the valid, unpushed change keeps its record
        assert held_call(shared, "push") == ""
    assert remote_has_config(remote)
    assert remote_head(remote) == git(root, "rev-parse", "HEAD")
    assert not publication_hold.recorded(shared, None)  # its successful publication retires the regular record
    assert not shared.held()


def test_no_later_publication_of_the_held_checkout_pushes_its_stale_fill(held, tmp_path):
    winner, remote = held
    root, before = winner.shared.root, remote_head(remote)
    head = git(root, "rev-parse", "HEAD")
    (root / "owner-wip.txt").write_text("the owner's untracked work\n")

    with winner.shared.locked():  # the completion retry: config first, recorded as pending only when not held
        assert "is held because" in profile_share.publish_config_unlocked(winner)
    assert not pending_file(winner).exists()

    memory = winner.shared.memory_path(PROJECT) / "note.md"
    memory.parent.mkdir(parents=True, exist_ok=True)
    memory.write_text("a memory\n")
    with winner.shared.locked():
        assert "is held because" in winner.shared.publish(memory, "memory: note")
    assert "is held because" in winner.write_profile(winner.read_profile())

    restarted = Store(tmp_path / "winner-store", DataRepo(root), PROJECT)  # a new process: only the record remains
    with restarted.shared.locked():
        assert "is held because" in restarted.shared.publish(memory, "memory: note")
        assert "is held because" in restarted.shared.pull()
        assert "is held because" in restarted.shared.rebase()
        until = time.monotonic() + 30  # the decision sync's own push: an explicit commit to its captured target
        goal = decision_sync.target(restarted.shared, until)
        sent = decision_sync.push_commit(restarted.shared, git(root, "rev-parse", "HEAD"), goal, until)
        assert sent.startswith(f"nothing was pushed or rebased in {root}")
    assert restarted.shared.git("push", "-q").returncode == 1
    with pytest.raises(StoreError, match="is held because"):
        prefs_import.run(restarted)

    assert remote_head(remote) == before
    assert not remote_has_config(remote)
    assert remote_marker(remote) == "done"
    assert git(root, "merge-base", "--is-ancestor", head, "HEAD") == ""  # every commit kept, none undone
    assert (root / "owner-wip.txt").read_text() == "the owner's untracked work\n"


def test_once_the_owner_removes_the_held_change_the_checkout_catches_up_and_stays_settled(held):
    winner, remote = held
    root = winner.shared.root
    git(root, "reset", "-q", "--hard", "@{upstream}")  # the owner's own review and removal, by hand

    prefs_import.run(winner)

    assert not winner.shared.held()
    assert not publication_hold.recorded(winner.shared, None)
    assert winner.read_profile().prefs_import == "done"
    assert not winner.config_path.exists()
    assert not remote_has_config(remote)


def test_a_healthy_unrelated_advance_at_the_first_push_is_checked_and_published(three, monkeypatch):
    winner, other, remote = three
    fired = at_git(monkeypatch, winner, nth_push(1), lambda: unrelated_advance(other))

    prefs_import.run(winner)

    assert fired == [True]
    assert remote_marker(remote) == "done"
    assert remote_has_config(remote)
    assert winner.read_config().prefs.ci_poll_seconds == 45
    assert not publication_hold.recorded(winner.shared, None)  # the record lapsed with its publication


def test_an_owner_rebase_in_progress_is_left_alone_by_an_automatic_save(three):
    winner, other, _ = three
    root = winner.shared.root
    (root / "shared.txt").write_text("base\n")
    winner.shared.publish(root / "shared.txt", "base")
    assert other.shared.pull() == ""
    (other.shared.root / "shared.txt").write_text("theirs\n")
    assert other.shared.publish(other.shared.root / "shared.txt", "theirs") == ""
    (root / "shared.txt").write_text("mine\n")
    git(root, "commit", "-qam", "owner: mine")
    stopped = subprocess.run(["git", "pull", "-q", "--rebase"], cwd=root, capture_output=True, check=False)  # noqa: S607
    assert stopped.returncode
    admin = Path(git(root, "rev-parse", "--absolute-git-dir"))
    head, status = git(root, "rev-parse", "HEAD"), git(root, "status", "--porcelain")
    basis = profile_share.config_digest(winner.config_path)

    def widths(cur: Layer) -> Layer:
        return cur.model_copy(update={"widths": [1300]})

    assert winner.update_config(config_save.Prepared(basis, widths), "automatic") == config_save.REBASING

    assert (admin / "rebase-merge").exists() or (admin / "rebase-apply").exists()
    assert (git(root, "rev-parse", "HEAD"), git(root, "status", "--porcelain")) == (head, status)
    assert not winner.config_path.exists()


def test_every_added_git_step_of_the_automatic_save_shares_the_saves_one_deadline(three, monkeypatch):
    winner, _, _ = three
    real, untils = data_repo._git, []  # noqa: SLF001
    added = {("rev-parse", "--git-path"), ("hash-object", "--"), ("pull", "-q"), ("push", "-q"), ("rebase", "-q")}

    def spy(cwd, *args, until=None):
        bare = tuple(a for a in args if a not in ("-c", "rebase.autoStash=false"))
        if cwd == winner.shared.root and bare[:2] in added:
            untils.append(until)
        return real(cwd, *args, until=until)

    fill = winner.update_config

    def watched(change, what="project layer", on_written=None):
        monkeypatch.setattr(data_repo, "_git", spy)
        try:
            return fill(change, what, on_written)
        finally:
            monkeypatch.setattr(data_repo, "_git", real)

    monkeypatch.setattr(winner, "update_config", watched)
    prefs_import.run(winner)

    assert len(untils) >= 5
    assert None not in untils
    assert len(set(untils)) == 1


def test_a_remote_profile_that_is_not_utf8_holds_the_fill_with_a_notice(three, monkeypatch):
    winner, other, remote = three
    root = winner.shared.root

    def malformed() -> None:
        assert other.shared.pull() == ""
        target = profile_share.path(other)
        target.write_bytes(b'{"prefs_import": "\xff\xfe pending"}\n')
        assert other.shared.publish(target, "settings: a profile that is not UTF-8") == ""

    fired = at_git(monkeypatch, winner, nth_push(1), malformed)
    with pytest.raises(
        StoreError, match=r"not pushed: .*is held because .*profile.json on the shared remote is unreadable"
    ):
        prefs_import.run(winner)

    assert fired == [True]
    assert remote_head(remote) == git(other.shared.root, "rev-parse", "HEAD")  # the fill never reached it
    assert not remote_has_config(remote)
    assert git(root, "diff-tree", "--no-commit-id", "--name-only", "-r", "HEAD") == f"{PROJECT}/config.json"
    assert git(root, "status", "--porcelain") == ""  # nothing rebased, staged or rewritten
    assert "unreadable" in winner.shared.held()  # the refusal is kept, so no pending intent is recorded
    assert not pending_file(winner).exists()
    with winner.shared.locked():
        assert "unreadable" in winner.shared.pull()


def test_identical_bytes_from_another_lineage_never_retire_the_hold_of_an_unpushed_fill(three, monkeypatch):
    winner, settler, remote = three
    steps: list[str] = []
    real = data_repo._git  # noqa: SLF001 - the publisher's own Git calls are the boundary

    def copy_the_fill_then_complete() -> None:
        exact = winner.config_path.read_bytes()  # the fill is written here, about to be committed, not pushed
        assert settler.shared.pull() == ""
        settler.config_path.write_text(Layer().model_dump_json(indent=1))
        assert settler.shared.publish(settler.config_path, "owner: initial config") == ""
        settler.config_path.write_bytes(exact)  # the same bytes, by a separate commit of another lineage
        assert settler.shared.publish(settler.config_path, "owner: preferred config") == ""
        settler.mark_prefs_import("pending", "done")

    def delete() -> None:
        settler.config_path.unlink()
        assert settler.shared.publish(settler.config_path, "owner: config removed") == ""
        steps.append("deleted")

    def spy(cwd, *args, until=None):
        if armed and cwd == winner.shared.root:
            if not steps and command(args) == "commit":
                steps.append("copied")
                copy_the_fill_then_complete()
            elif steps == ["copied"] and args[:1] == ("push",):
                delete()  # only reachable when the hold was retired before the first push
        return real(cwd, *args, until=until)

    armed, fill = [], winner.update_config

    def once(change, what="project layer", on_written=None):
        armed.append(True)
        try:
            return fill(change, what, on_written)
        finally:
            armed.clear()

    monkeypatch.setattr(data_repo, "_git", spy)
    monkeypatch.setattr(winner, "update_config", once)
    with pytest.raises(StoreError, match="is held because"):
        prefs_import.run(winner)
    assert steps == ["copied"]  # refused at the check: the first push never ran
    assert publication_hold.recorded(winner.shared, None)

    monkeypatch.setattr(data_repo, "_git", real)
    delete()  # the owner's deletion happens all the same, after the refusal
    assert not remote_has_config(remote)
    with pytest.raises(StoreError, match="is held because"):
        prefs_import.run(winner)  # the retry is held: the fill is still unpushed here
    memory = winner.shared.memory_path(PROJECT) / "later.md"
    memory.parent.mkdir(parents=True, exist_ok=True)
    memory.write_text("a later unrelated publication\n")
    with winner.shared.locked():
        assert "is held because" in winner.shared.publish(memory, "memory: later")
    assert not remote_has_config(remote)
    assert remote_marker(remote) == "done"


def test_a_hold_that_never_wrote_lapses_with_the_next_healthy_publication(three):
    winner, _, remote = three
    root = winner.shared.root
    requires = publication_hold.Requires("a claim", profile_share.path(winner), {"prefs_import": "pending"})
    with winner.shared.locked():
        winner.shared.hold(winner.config_path, requires)  # recorded, then nothing was written
    notes = root / "unrelated" / "notes.md"
    notes.parent.mkdir(parents=True, exist_ok=True)
    notes.write_text("a healthy change\n")
    with winner.shared.locked():
        assert winner.shared.publish(notes, "unrelated: notes") == ""
    assert not publication_hold.recorded(winner.shared, None)
    assert remote_head(remote) == git(root, "rev-parse", "HEAD")


def mutate(record: dict, case: str) -> bytes:
    import json  # noqa: PLC0415

    if case == "not json":
        return b"{ not json"
    changed = dict(record)
    edits = {
        "watch null": ("watch", None),
        "watch number": ("watch", 7),
        "watch escapes": ("watch", "../outside/config.json"),
        "watch absolute": ("watch", "/etc/config.json"),
        "watch in git": ("watch", ".git/config"),
        "watch dot": ("watch", "."),
        "watch nul": ("watch", f"{PROJECT}/config.json\x00x"),
        "watch doubled slash": ("watch", f"{PROJECT}//config.json"),
        "watch leading dot": ("watch", f"./{PROJECT}/config.json"),
        "file nul": ("file", f"{PROJECT}/profile.json\x00"),
        "file null": ("file", None),
        "base shape": ("base", "not-a-blob"),
        "base number": ("base", 0),
        "since null": ("since", None),
        "since short": ("since", "abc123"),
        "fields list": ("fields", ["prefs_import"]),
        "field number": ("fields", {"prefs_import": 1}),
        "fields empty": ("fields", {}),
        "what null": ("what", None),
        "refused null": ("refused", None),
    }
    if case == "missing key":
        del changed["base"]
    elif case == "extra key":
        changed["filled"] = "anything"
    else:
        key, value = edits[case]
        changed[key] = value
    return json.dumps(changed).encode()


MALFORMED = [
    "watch null",
    "watch number",
    "watch escapes",
    "watch absolute",
    "watch in git",
    "watch dot",
    "watch nul",
    "watch doubled slash",
    "watch leading dot",
    "file nul",
    "file null",
    "base shape",
    "base number",
    "since null",
    "since short",
    "fields list",
    "field number",
    "fields empty",
    "what null",
    "refused null",
    "missing key",
    "extra key",
    "not json",
]
VALID = {
    "watch": f"{PROJECT}/config.json",
    "base": publication_hold.ABSENT,
    "since": "0" * 40,
    "file": f"{PROJECT}/{profile_share.PROFILE}",
    "fields": {"prefs_import": "pending"},
    "what": "a claim",
    "refused": "the remote changed",
}


@pytest.mark.parametrize("case", MALFORMED)
def test_a_malformed_held_record_is_refused_and_kept_as_it_is(tmp_path, case):
    record = tmp_path / publication_hold.RECORD
    record.write_text(json.dumps(VALID))
    assert publication_hold._load(record) == VALID  # noqa: SLF001 - the record's reader is the unit
    raw = mutate(VALID, case)
    record.write_bytes(raw)
    with pytest.raises(publication_hold._UnknownError, match="held publication record"):  # noqa: SLF001
        publication_hold._load(record)  # noqa: SLF001
    assert record.read_bytes() == raw


@pytest.mark.parametrize("case", ["watch escapes", "missing key", "not json"])
def test_a_malformed_held_record_stays_held_with_its_bytes_and_never_lapses(held, case):
    import json  # noqa: PLC0415

    winner, remote = held
    root, before = winner.shared.root, remote_head(remote)
    record = root / git(root, "rev-parse", "--git-path", publication_hold.RECORD)
    raw = mutate(json.loads(record.read_bytes()), case)
    record.write_bytes(raw)
    head = git(root, "rev-parse", "HEAD")

    with winner.shared.locked():
        assert "held publication record" in winner.shared.pull()
        memory = winner.shared.memory_path(PROJECT) / "note.md"
        memory.parent.mkdir(parents=True, exist_ok=True)
        memory.write_text("a memory\n")
        assert "held publication record" in winner.shared.publish(memory, "memory: note")
    assert "held publication record" in winner.shared.held()

    assert record.read_bytes() == raw
    assert remote_head(remote) == before
    assert not remote_has_config(remote)
    assert git(root, "merge-base", "--is-ancestor", head, "HEAD") == ""


def publish_memory(store: Store, name: str) -> str:
    memory = store.shared.memory_path(PROJECT) / name
    memory.parent.mkdir(parents=True, exist_ok=True)
    memory.write_text(f"{name}\n")
    with store.shared.locked():
        return store.shared.publish(memory, f"memory: {name}")


def test_an_owner_merge_that_keeps_the_remote_deletion_does_not_hide_the_unpushed_fill(held, tmp_path, monkeypatch):
    winner, remote = held
    root, config = winner.shared.root, f"{PROJECT}/config.json"
    git(root, "merge", "-q", "--no-ff", "--no-commit", "@{upstream}")  # the owner merges the remote by hand
    git(root, "rm", "-q", "--", config)  # and keeps its deletion
    git(root, "commit", "-q", "-m", "owner: merge the remote, keeping its deletion")
    assert git(root, "log", "--format=%h", "@{upstream}..HEAD", "--", config) == ""  # simplified history hides it
    assert git(root, "log", "--full-history", "--format=%h", "@{upstream}..HEAD", "--", config)
    other = checkout(remote, tmp_path, "other")
    real, advanced = data_repo._git, []  # noqa: SLF001 - the publisher's own Git calls are the boundary

    def spy(cwd, *args, until=None):
        if not advanced and cwd == root and args[:1] == ("push",):
            advanced.append(True)
            unrelated_advance(other)  # the remote moves: a rejected push would rebase, flattening the merge
        return real(cwd, *args, until=until)

    monkeypatch.setattr(data_repo, "_git", spy)
    assert "is held because" in publish_memory(winner, "first.md")
    monkeypatch.setattr(data_repo, "_git", real)
    if not advanced:
        unrelated_advance(other)  # held before any push: the remote still moves on independently
    assert "is held because" in publish_memory(winner, "later.md")
    assert not remote_has_config(remote)
    assert remote_marker(remote) == "done"
    assert git(root, "rev-list", "--merges", "--count", "@{upstream}..HEAD") == "1"  # the owner's merge is kept


def test_an_unpushed_revert_of_the_fill_stays_held_because_a_replay_could_delete_a_remote_config(held):
    winner, remote = held
    root, before = winner.shared.root, remote_head(remote)
    git(root, "revert", "--no-edit", "HEAD")  # the fill and its revert both stay in unpushed history

    assert "is held because" in publish_memory(winner, "after-revert.md")
    assert remote_head(remote) == before
    assert git(root, "rev-list", "--count", "@{upstream}..HEAD") == "3"  # fill, revert and memory: all kept


def forked_publication(three, tmp_path) -> tuple[Store, Path, Path, Profile]:
    """The importer checks its claim on origin but Git sends its pushes to a fork where the import was settled."""
    from owlbear_delivery_next.state_store.profile_share import ABSENT  # noqa: PLC0415

    _, settler, remote = three
    settler.mark_prefs_import("", "pending", ABSENT, "first")
    settler.mark_prefs_import("pending", "done")
    settler.config_path.write_text(Layer().model_dump_json(indent=1))
    assert settler.shared.publish(settler.config_path, f"settings: {PROJECT}: project layer") == ""
    settler.config_path.unlink()
    assert settler.shared.publish(settler.config_path, f"settings: {PROJECT}: project layer removed") == ""
    publication = tmp_path / "publication.git"
    git(tmp_path, "clone", "-q", "--bare", str(remote), str(publication))  # the fork: done, config deleted
    _, notice, applied = settler.mark_prefs_import("done", "pending", ABSENT, "fresh")  # a fresh claim on origin only
    assert (notice, applied) == ("", True)
    importer = checkout(remote, tmp_path, "importer")
    root = importer.shared.root
    git(root, "remote", "add", "publication", str(publication))
    git(root, "config", "branch.main.pushRemote", "publication")
    git(root, "config", "push.default", "current")
    git(root, "fetch", "-q", "publication")  # the importer's own disposable checkout knows the fork's branch
    assert git(root, "rev-parse", "--symbolic-full-name", "@{upstream}") == "refs/remotes/origin/main"
    assert git(root, "rev-parse", "--symbolic-full-name", "@{push}") == "refs/remotes/publication/main"
    claim = importer.read_profile()
    assert (claim.prefs_import, claim.prefs_claim) == ("pending", "fresh")
    return importer, remote, publication, claim


def test_a_held_fill_is_never_pushed_to_another_remote_than_the_one_its_claim_was_checked_on(three, tmp_path):
    from owlbear_delivery_next.settings.prefs_import import plan  # noqa: PLC0415
    from owlbear_delivery_next.state_store.profile_share import ABSENT  # noqa: PLC0415

    importer, remote, publication, claim = forked_publication(three, tmp_path)
    fork_before, origin_before = remote_head(publication), remote_head(remote)
    fields = {"prefs_import": "pending", "prefs_claim": "fresh", "prefs_basis": ABSENT}
    requires = publication_hold.Requires("the import claim", profile_share.path(importer), fields)
    prepared = config_save.Prepared(ABSENT, lambda cur: plan(cur, claim), requires)

    notice = importer.update_config(prepared, "legacy preferences carried")
    assert "would be pushed to publication (refs/remotes/publication/main), not to its upstream origin" in notice
    assert "would be pushed to publication" in importer.update_config(prepared, "legacy preferences carried")
    _, done, _ = importer.mark_prefs_import("pending", "done")
    assert "would be pushed to publication" in done
    raw = importer.shared.git("push", "-q", "publication", "HEAD:refs/heads/main")
    assert raw.returncode == 1
    assert "would be pushed to publication" in raw.stderr

    assert remote_head(publication) == fork_before
    assert remote_marker(publication) == "done"
    assert not remote_has_config(publication)
    assert remote_head(remote) == origin_before
    assert not remote_has_config(remote)
    assert publication_hold.recorded(importer.shared, None)


def test_a_full_import_through_a_non_default_remote_that_pushes_where_it_fetches_completes(three):
    winner, _, remote = three
    root = winner.shared.root
    git(root, "remote", "rename", "origin", "authority")
    git(root, "config", "branch.main.pushRemote", "authority")
    git(root, "config", "push.default", "current")
    assert git(root, "rev-parse", "--symbolic-full-name", "@{upstream}") == "refs/remotes/authority/main"

    prefs_import.run(winner)

    assert remote_marker(remote) == "done"
    assert remote_has_config(remote)
    assert winner.read_config().prefs.ci_poll_seconds == 45
    assert not publication_hold.recorded(winner.shared, None)


def spaced_forks(three, tmp_path) -> tuple[Store, Path, Path, config_save.Prepared]:
    """A pending source fork and a settled destination fork whose paths differ only in their inner spaces."""
    from owlbear_delivery_next.settings.prefs_import import plan  # noqa: PLC0415
    from owlbear_delivery_next.state_store.profile_share import ABSENT  # noqa: PLC0415

    _, settler, remote = three
    settler.mark_prefs_import("", "pending", ABSENT, "first")
    settler.mark_prefs_import("pending", "done")
    settler.config_path.write_text(Layer().model_dump_json(indent=1))
    assert settler.shared.publish(settler.config_path, f"settings: {PROJECT}: project layer") == ""
    settler.config_path.unlink()
    assert settler.shared.publish(settler.config_path, f"settings: {PROJECT}: project layer removed") == ""
    dest = tmp_path / "authority  repo.git"  # two spaces: settled, config deleted
    git(tmp_path, "clone", "-q", "--bare", str(remote), str(dest))
    settler.mark_prefs_import("done", "pending", ABSENT, "fresh")
    source = tmp_path / "authority repo.git"  # one space: the fresh claim
    git(tmp_path, "clone", "-q", "--bare", str(remote), str(source))
    importer = checkout(source, tmp_path, "importer")
    claim = importer.read_profile()
    fields = {"prefs_import": "pending", "prefs_claim": "fresh", "prefs_basis": ABSENT}
    requires = publication_hold.Requires("the import claim", profile_share.path(importer), fields)
    return importer, source, dest, config_save.Prepared(ABSENT, lambda cur: plan(cur, claim), requires)


def test_a_push_address_that_differs_only_in_inner_spaces_is_another_repository(three, tmp_path):
    importer, source, dest, prepared = spaced_forks(three, tmp_path)
    root = importer.shared.root
    git(root, "config", "remote.origin.pushurl", str(dest))
    assert git(root, "rev-parse", "--symbolic-full-name", "@{push}") == "refs/remotes/origin/main"
    source_before, dest_before = remote_head(source), remote_head(dest)

    assert "is not exactly the one address its state was read from" in importer.update_config(prepared, "carried")
    _, done, _ = importer.mark_prefs_import("pending", "done")
    assert "is not exactly the one address" in done
    assert importer.shared.git("push", "-q", "origin", "HEAD:refs/heads/main").returncode == 1

    assert (remote_head(source), remote_head(dest)) == (source_before, dest_before)
    assert remote_marker(dest) == "done"
    assert not remote_has_config(dest)
    assert not remote_has_config(source)


def test_a_push_address_with_spaces_that_is_exactly_the_fetched_one_publishes(three, tmp_path):
    importer, source, dest, prepared = spaced_forks(three, tmp_path)
    git(importer.shared.root, "config", "remote.origin.pushurl", str(source))  # the same path, spaces and all
    dest_before = remote_head(dest)

    assert importer.update_config(prepared, "carried") == ""

    assert remote_has_config(source)
    assert remote_head(dest) == dest_before


FORCED = "+refs/heads/main:refs/heads/main"  # the owner's configured push refspec: a plain push is forced


def config_bytes(store: Store) -> bytes:
    return (Path(git(store.shared.root, "rev-parse", "--absolute-git-dir")) / "config").read_bytes()


def test_a_configured_forced_push_never_overwrites_a_remote_that_moved_after_the_check(three, monkeypatch):
    winner, settler, remote = three
    git(winner.shared.root, "config", "remote.origin.push", FORCED)
    before = config_bytes(winner)
    fired = at_git(monkeypatch, winner, nth_push(1), lambda: complete_and_delete(settler))

    with pytest.raises(StoreError, match="is held because"):
        prefs_import.run(winner)

    assert fired == [True]
    assert remote_head(remote) == git(settler.shared.root, "rev-parse", "HEAD")  # not overwritten
    assert remote_marker(remote) == "done"
    assert not remote_has_config(remote)
    assert config_bytes(winner) == before  # the owner's push configuration stays as it is
    assert winner.shared.git("push", "-q").returncode == 1  # a raw plain push is held too
    assert remote_head(remote) == git(settler.shared.root, "rev-parse", "HEAD")


def test_a_configured_forced_push_of_a_held_fill_keeps_a_healthy_remote_advance(three, tmp_path, monkeypatch):
    winner, other, remote = three
    git(winner.shared.root, "config", "remote.origin.push", FORCED)
    fired = at_git(monkeypatch, winner, nth_push(1), lambda: unrelated_advance(other))

    prefs_import.run(winner)  # the forced refspec would overwrite the advance; the bound push is rejected instead

    assert fired == [True]
    assert remote_marker(remote) == "done"
    assert remote_has_config(remote)
    fresh = checkout(remote, tmp_path, "fresh")
    assert (fresh.shared.root / "unrelated" / "notes.md").exists()  # the other clone's commit was not overwritten


def test_an_explicit_push_is_still_checked_whatever_push_refspec_is_configured(held):
    winner, remote = held
    git(winner.shared.root, "config", "remote.origin.push", FORCED)
    before = remote_head(remote)
    for args in (("push", "-q", "origin", "+HEAD:refs/heads/main"), ("push", "-q", "origin", "HEAD:refs/heads/main")):
        said = winner.shared.git(*args)
        assert said.returncode == 1
        assert "nothing was pushed" in said.stderr
    assert remote_head(remote) == before


def old_roles(store: Store, roles_: dict) -> None:
    store.root.mkdir(parents=True, exist_ok=True)
    (store.root / profile_share.PROFILE).write_text(json.dumps({"format": 1, "roles": roles_}))


@pytest.fixture
def two_movers(shared_repo, tmp_path) -> tuple[Store, Store, Path]:
    """Two checkouts of a remote whose project config is published empty; the first has old role overrides."""
    root, remote = shared_repo
    seed = Store(tmp_path / "seed-store", DataRepo(root), PROJECT)
    seed.config_path.parent.mkdir(parents=True, exist_ok=True)
    seed.config_path.write_text(Layer().model_dump_json(indent=1))
    assert seed.shared.publish(seed.config_path, f"settings: {PROJECT}: project layer") == ""
    a, b = checkout(remote, tmp_path, "mover-a"), checkout(remote, tmp_path, "mover-b")
    old_roles(a, {"builder": {"model": "m-1", "effort": "low"}})
    return a, b, remote


def remote_config(remote: Path) -> Layer:
    return Layer.model_validate_json(git(remote, "--git-dir=.", "show", f"main:{PROJECT}/config.json"))


def move_then_clear(b: Store) -> None:
    """The other checkout moves its own, different old roles, then the owner clears them; both are published."""
    from owlbear_delivery_next.state_store import roles_move  # noqa: PLC0415

    assert b.shared.pull() == ""
    old_roles(b, {"reviewer": {"model": "r-9", "effort": "max"}})
    roles_move.move_roles(b)
    assert b.read_config().agents
    assert (
        b.save(b.config_path, Layer, lambda cur: cur.model_copy(update={"agents": {}}), "owner clear", owner=True) == ""
    )


def test_a_role_move_never_restores_overrides_another_checkout_moved_and_cleared_first(two_movers, monkeypatch):
    from owlbear_delivery_next.state_store import roles_move  # noqa: PLC0415

    a, b, remote = two_movers
    fired = at_git(monkeypatch, a, nth_push(1), lambda: move_then_clear(b))

    roles_move.move_roles(a)  # applied here with its receipt; its publication is held, as Settings shows

    assert fired == [True]
    published = remote_config(remote)
    assert published.roles_moved is True
    assert published.agents == {}  # the owner's clear dominates
    assert remote_head(remote) == git(b.shared.root, "rev-parse", "HEAD")
    assert "an automatic change is held" in a.shared.pending()
    assert "changed on the shared remote" in a.shared.held()
    assert "is held because" in publish_memory(a, "later.md")  # a later publication never sends the move
    assert remote_config(remote).agents == {}


def test_a_role_move_over_an_unchanged_remote_config_publishes_its_overrides_and_receipt(two_movers):
    from owlbear_delivery_next.state_store import roles_move  # noqa: PLC0415

    a, _, remote = two_movers
    roles_move.move_roles(a)

    published = remote_config(remote)
    assert published.roles_moved is True
    assert published.agents["builder"].model == "m-1"
    assert (a.root / profile_share.ROLES_MOVED).exists()
    assert not publication_hold.recorded(a.shared, None)


@pytest.fixture
def absent_movers(shared_repo, tmp_path) -> tuple[Store, Store, Path]:
    """Two checkouts of a remote with no project config yet; the first has old role overrides."""
    root, remote = shared_repo
    seed = Store(tmp_path / "seed-store", DataRepo(root), PROJECT)
    seed.write_profile(Profile())
    a, b = checkout(remote, tmp_path, "mover-a"), checkout(remote, tmp_path, "mover-b")
    old_roles(a, {"builder": {"model": "m-1", "effort": "low"}})
    return a, b, remote


def move_then_delete(b: Store) -> None:
    """The other checkout moves its own, different old roles; the owner then deletes the config: absent again."""
    from owlbear_delivery_next.state_store import roles_move  # noqa: PLC0415

    assert b.shared.pull() == ""
    old_roles(b, {"reviewer": {"model": "r-9", "effort": "max"}})
    roles_move.move_roles(b)
    assert remote_has_config(b.shared.root.parent / "remote.git")
    b.config_path.unlink()
    assert b.shared.publish(b.config_path, f"settings: {PROJECT}: project layer removed") == ""


def test_a_role_move_is_held_when_the_config_came_and_went_on_the_remote_meanwhile(absent_movers, monkeypatch):
    from owlbear_delivery_next.state_store import roles_move  # noqa: PLC0415

    a, b, remote = absent_movers
    fired = at_git(monkeypatch, a, nth_push(1), lambda: move_then_delete(b))

    roles_move.move_roles(a)

    assert fired == [True]
    assert not remote_has_config(remote)  # the owner's deletion stands: nothing restores the moved overrides
    assert remote_head(remote) == git(b.shared.root, "rev-parse", "HEAD")
    assert "an automatic change is held" in a.shared.pending()
    assert "is held because" in publish_memory(a, "later.md")
    assert not remote_has_config(remote)


def test_the_automatic_publications_after_a_retired_hold_never_force_over_another_checkout(three, monkeypatch):
    winner, settler, remote = three
    git(winner.shared.root, "config", "remote.origin.push", FORCED)
    before = config_bytes(winner)
    real, pushes, owner_head = data_repo._git, [], []  # noqa: SLF001 - the publisher's own Git calls are the boundary

    def spy(cwd, *args, until=None):
        if armed and cwd == winner.shared.root and args[:1] == ("push",):
            pushes.append(args)
            if len(pushes) == 1:  # the fill landed; this is the run's next automatic push
                assert remote_has_config(remote)  # the checked fill was published, so its hold retired
                assert not publication_hold.recorded(winner.shared, None)
                complete_and_delete(settler)
                owner_head.append(git(settler.shared.root, "rev-parse", "HEAD"))
        return real(cwd, *args, until=until)

    armed, fill = [], winner.update_config

    def after_the_fill(change, what="project layer", on_written=None):
        done = fill(change, what, on_written)
        armed.append(True)
        return done

    monkeypatch.setattr(winner, "update_config", after_the_fill)
    monkeypatch.setattr(data_repo, "_git", spy)
    prefs_import.run(winner)  # its rejected non-forced push rebases onto the other checkout's state: a safe resync

    assert owner_head  # the other checkout's completion and deletion really landed in between
    assert git(remote, "--git-dir=.", "merge-base", "--is-ancestor", owner_head[0], "main") == ""  # not overwritten
    assert remote_marker(remote) == "done"
    assert not remote_has_config(remote)  # the owner's deletion stands
    assert config_bytes(winner) == before
    assert pushes
    assert all(args[-1] == "HEAD:refs/heads/main" and "+" not in " ".join(args) for args in pushes)


# The decision batch barrier (R06) and the held change (R15) on one shared checkout: neither bypasses the other.


def interrupt_a_batch(store: Store, how: str) -> None:
    """Leave a decision batch interrupted in *store*'s checkout: a readable journal in flight, or a corrupt one."""
    from owlbear_decisions import new_id  # noqa: PLC0415
    from owlbear_delivery_next.state_store import decision_batch  # noqa: PLC0415

    if how == "corrupt":
        decision_batch.journal_path(store.shared).write_text("{not json")
        return
    decision_id = new_id()
    head = git(store.shared.root, "rev-parse", "HEAD")
    files = [(f"{PROJECT}/decisions/{decision_id}.md", None, b"in flight\n")]
    decision_batch.begin(store.shared, PROJECT, head, "decisions: in flight", [decision_id], files)


@pytest.mark.parametrize("how", ["pending", "corrupt"])
def test_an_interrupted_decision_batch_stops_the_import_before_its_pull_or_any_push(three, monkeypatch, how):
    winner, other, remote = three
    unrelated_advance(other)  # the import's catch-up would rebase onto this
    interrupt_a_batch(winner, how)
    before, head = remote_head(remote), git(winner.shared.root, "rev-parse", "HEAD")
    real, ran = data_repo._git, []  # noqa: SLF001 - the publisher's own Git calls are the boundary

    def spy(cwd, *args, until=None):
        if cwd == winner.shared.root and command(args) in {"push", "pull", "rebase"}:
            ran.append(args)
        return real(cwd, *args, until=until)

    monkeypatch.setattr(data_repo, "_git", spy)
    with pytest.raises(StoreError, match="decision batch"):
        prefs_import.run(winner)

    assert ran == []  # neither rebased nor pushed: the barrier comes first
    assert remote_head(remote) == before
    root = winner.shared.root  # the claim is committed here, on top of what was there; nothing was filled
    assert git(root, "merge-base", "--is-ancestor", head, "HEAD") == ""
    assert git(root, "ls-tree", "HEAD", "--", f"{PROJECT}/config.json") == ""
    assert not winner.config_path.exists()
    assert not remote_has_config(remote)


def test_an_interrupted_decision_batch_comes_before_a_held_change_in_every_ordinary_publication(held):
    winner, remote = held
    interrupt_a_batch(winner, "pending")
    before = remote_head(remote)

    notice = publish_memory(winner, "later.md")
    assert "decision batch" in notice
    assert "is held because" not in notice  # the barrier answers before the hold is even checked
    with winner.shared.locked():
        assert "decision batch" in winner.shared.pull()
    assert remote_head(remote) == before


def test_an_owned_decision_push_never_sends_a_held_stale_fill(held):
    winner, remote = held
    shared, before = winner.shared, remote_head(remote)
    until = time.monotonic() + 30
    goal = decision_sync.target(shared, until)
    assert goal is not None

    said = decision_sync.push_commit(shared, git(shared.root, "rev-parse", "HEAD"), goal, until)

    # the explicit SHA and captured target are checked against the hold too (R06 keeps 200 characters of the notice)
    assert said.startswith(f"nothing was pushed or rebased in {shared.root}")
    assert remote_head(remote) == before
    assert not remote_has_config(remote)
    assert shared.held()  # the kept refusal still names why


@pytest.mark.parametrize("remote_name", ["origin", "authority"])
def test_a_healthy_owned_decision_push_lands_on_its_target_within_one_deadline(three, monkeypatch, remote_name):
    winner, _, remote = three
    root = winner.shared.root
    if remote_name != "origin":
        git(root, "remote", "rename", "origin", remote_name)
    git(root, "config", "remote.origin.push" if remote_name == "origin" else f"remote.{remote_name}.push", FORCED)
    notes = root / "unrelated" / "decision-notes.md"
    notes.parent.mkdir(parents=True, exist_ok=True)
    notes.write_text("an owned batch's commit\n")
    git(root, "add", "--", "unrelated/decision-notes.md")
    git(root, "commit", "-qm", "decisions: owned batch")
    made = git(root, "rev-parse", "HEAD")
    real, untils = data_repo._git, []  # noqa: SLF001

    def spy(cwd, *args, until=None):
        if cwd == root:
            untils.append(until)
        return real(cwd, *args, until=until)

    until = time.monotonic() + 30
    goal = decision_sync.target(winner.shared, until)
    assert goal is not None
    assert (goal.remote, goal.ref) == (remote_name, "refs/heads/main")
    monkeypatch.setattr(data_repo, "_git", spy)

    assert decision_sync.push_commit(winner.shared, made, goal, until) == ""

    assert remote_head(remote) == made  # a fast-forward of exactly the owned commit, never forced
    assert untils
    assert set(untils) == {until}


def test_with_nothing_held_an_explicit_push_is_still_never_forced_or_sent_to_another_address(three, tmp_path):
    winner, _, remote = three
    root, before = winner.shared.root, remote_head(remote)
    assert not publication_hold.recorded(winner.shared, None)
    forced = winner.shared.git("push", "-q", "origin", "+HEAD:refs/heads/main")
    assert forced.returncode == 1
    assert "names no single remote and branch to check" in forced.stderr
    git(root, "config", "remote.origin.pushurl", str(tmp_path / "another.git"))
    aliased = winner.shared.git("push", "-q", "origin", "HEAD:refs/heads/main")
    assert aliased.returncode == 1
    assert "is not exactly the one address" in aliased.stderr
    assert remote_head(remote) == before


def remote_refs(remote: Path) -> str:
    return git(remote, "--git-dir=.", "for-each-ref", "--format=%(refname) %(objectname)")


def owner_state(root: Path) -> tuple[str, ...]:
    admin = Path(git(root, "rev-parse", "--absolute-git-dir"))
    return (
        git(root, "symbolic-ref", "HEAD"),
        git(root, "rev-parse", "HEAD"),
        git(root, "status", "--porcelain", "--untracked-files=all"),
        git(root, "ls-files", "--stage"),
        (admin / "config").read_text(),
    )


@pytest.mark.parametrize(
    "refspec",
    ["refs/heads/*:refs/heads/*", "refs/heads/*:refs/heads/main", "HEAD:refs/heads/*", "main*:refs/heads/main"],
)
def test_an_explicit_pattern_push_never_sends_more_than_one_captured_branch(three, monkeypatch, refspec):
    winner, _, remote = three
    root = winner.shared.root
    for name in ("side", "other"):  # local branches a pattern would create on the remote along with main
        git(root, "branch", name)
    (root / "owner-wip.txt").write_text("the owner's untracked work\n")
    assert not publication_hold.recorded(winner.shared, None)
    before, owner = remote_refs(remote), owner_state(root)
    checked = []
    real = publication_hold.pushing

    def seen(repo, push, until):
        checked.append(tuple(push))
        return real(repo, push, until)

    monkeypatch.setattr(publication_hold, "pushing", seen)

    said = winner.shared.git("push", "-q", "origin", refspec)  # the application's own wrapper, not raw Git

    assert checked == [("push", "-q", "origin", refspec)]
    assert remote_refs(remote) == before  # no remote ref was created or moved
    assert said.returncode == 1
    assert "names no single remote and branch to check" in said.stderr
    assert owner_state(root) == owner


def test_a_single_explicit_sha_push_to_a_captured_branch_still_publishes(three):
    winner, _, remote = three
    root = winner.shared.root
    git(root, "commit", "-q", "--allow-empty", "-m", "an owned commit")
    made = git(root, "rev-parse", "HEAD")

    assert winner.shared.git("push", "-q", "origin", f"{made}:refs/heads/main").returncode == 0

    assert remote_head(remote) == made


def repointed(three, tmp_path: Path, name: str = "fork-b.git") -> tuple[Store, Path, Path, str, object]:
    """A checkout whose owned commit was captured for its origin, repository A; then origin, both its fetch and its
    push address, is pointed at repository B, a separate copy, while branch, remote branch and commit stay as they were.
    """
    winner, _, remote = three
    root = winner.shared.root
    fork = tmp_path / name
    git(tmp_path, "clone", "-q", "--bare", str(remote), str(fork))
    git(root, "commit", "-q", "--allow-empty", "-m", "decisions: an owned batch")
    made = git(root, "rev-parse", "HEAD")
    goal = decision_sync.target(winner.shared, time.monotonic() + 30)
    assert goal is not None
    git(root, "remote", "set-url", "origin", str(fork))  # the actor's deliberate change, after the capture
    git(root, "config", "remote.origin.pushurl", str(fork))
    assert publication_hold.check(winner.shared, None, fetch=False) == ""  # no hold: only the target can refuse
    return winner, remote, fork, made, goal


def test_an_owned_decision_push_never_goes_to_a_remote_repointed_after_its_target_was_read(three, tmp_path):
    winner, remote, fork, made, goal = repointed(three, tmp_path)
    root = winner.shared.root
    refs, owner = (remote_refs(remote), remote_refs(fork)), owner_state(root)

    said = decision_sync.push_commit(winner.shared, made, goal, time.monotonic() + 30)
    retried = decision_sync.push_commit(winner.shared, made, goal, time.monotonic() + 30)

    assert (remote_refs(remote), remote_refs(fork)) == refs  # neither repository got the commit
    assert said == retried
    assert said == "the remote origin points elsewhere than when this publication began, so nothing was pushed"
    assert str(fork) not in said
    assert owner_state(root) == owner
    assert decision_sync.target(winner.shared, time.monotonic() + 30) != goal  # the guards' equality sees it too


def test_a_continuation_never_proves_its_commit_on_a_remote_repointed_to_another_repository(three, tmp_path):
    from owlbear_delivery_next.state_store.decision_target import Continuation  # noqa: PLC0415

    winner, remote, fork, made, goal = repointed(three, tmp_path)
    git(winner.shared.root, "push", "-q", str(fork), f"{made}:refs/heads/main")  # B already has it, A does not
    refs = (remote_refs(remote), remote_refs(fork))

    assert not decision_sync.proved(winner.shared, made, time.monotonic() + 30, Continuation(made, goal))

    assert (remote_refs(remote), remote_refs(fork)) == refs
    assert remote_head(remote) != made


def test_a_repoint_during_the_proof_fetch_never_proves_another_repositorys_commit(three, tmp_path, monkeypatch):
    from owlbear_delivery_next.state_store.decision_target import Continuation  # noqa: PLC0415

    winner, remote, fork, made, goal = repointed(three, tmp_path)
    root = winner.shared.root
    git(root, "push", "-q", str(fork), f"{made}:refs/heads/main")  # B holds it; the captured repository A does not
    git(root, "remote", "set-url", "origin", str(remote))
    git(root, "config", "remote.origin.pushurl", str(remote))
    before, fired, owner, real_git = (remote_refs(remote), remote_refs(fork)), [], [], DataRepo.git

    def fetch_after_repoint(self, *args, until=None):
        if self.root == root and args[:1] == ("fetch",) and not fired:
            fired.append(True)
            git(root, "remote", "set-url", "origin", str(fork))
            git(root, "config", "remote.origin.pushurl", str(fork))
            owner.append(owner_state(root))
        return real_git(self, *args, until=until)

    monkeypatch.setattr(DataRepo, "git", fetch_after_repoint)
    proved = decision_sync.proved(winner.shared, made, time.monotonic() + 30, Continuation(made, goal))
    assert fired == [True]
    assert not proved
    assert (remote_refs(remote), remote_refs(fork)) == before
    assert owner_state(root) == owner[0]


def test_a_proof_with_unreadable_repository_addresses_is_not_known_or_fetched(three, monkeypatch):
    from owlbear_delivery_next.state_store import decision_target  # noqa: PLC0415

    winner, _, remote = three
    root = winner.shared.root
    head = git(root, "rev-parse", "HEAD")
    assert remote_head(remote) == head
    calls, real_git = [], DataRepo.git

    def record(self, *args, until=None):
        if self.root == root:
            calls.append(args)
        return real_git(self, *args, until=until)

    monkeypatch.setattr(decision_target, "addresses", lambda *_args: None)
    monkeypatch.setattr(DataRepo, "git", record)
    assert not decision_sync.proved(winner.shared, head, time.monotonic() + 30)
    assert not [args for args in calls if args[:1] in {("fetch",), ("push",)}]


def test_an_owned_decision_push_to_an_unchanged_address_with_spaces_lands(three, tmp_path):
    winner, _, remote = three
    root = winner.shared.root
    spaced = tmp_path / "authority  repo.git"
    git(tmp_path, "clone", "-q", "--bare", str(remote), str(spaced))
    git(root, "remote", "set-url", "origin", str(spaced))
    git(root, "fetch", "-q")
    git(root, "commit", "-q", "--allow-empty", "-m", "decisions: an owned batch")
    made = git(root, "rev-parse", "HEAD")
    until = time.monotonic() + 30
    goal = decision_sync.target(winner.shared, until)
    assert goal is not None
    assert goal.fetch == str(spaced)

    assert decision_sync.push_commit(winner.shared, made, goal, until) == ""

    assert remote_head(spaced) == made


def an_owned_decision(picking) -> object:
    from datetime import UTC, datetime  # noqa: PLC0415

    from owlbear_decisions import Decision, Origin, Scope, State, new_id  # noqa: PLC0415

    return Decision(
        id=new_id(), title="Notes live in SQLite", statement="Notes live in one SQLite table.", scope=Scope.PROJECT,
        project=picking.PROJECT, origin=Origin.AUTONOMOUS, actor="shaper", state=State.IN_FORCE,
        created_at=datetime(2026, 10, 26, tzinfo=UTC),
    )  # fmt: skip


@pytest.mark.parametrize("push", ["initial", "rebased-retry"])
def test_a_repoint_during_the_shared_checkouts_own_push_probes_sends_nothing_to_the_other_repository(
    picking, shared_repo, tmp_path, monkeypatch, push
):
    """The owned push checked its captured remote's addresses, then the shared checkout's own probes run (the held
    publication record's lookup first); origin is pointed at repository B during that lookup. The push still goes
    nowhere: its captured addresses are checked again at the push itself, after those probes."""
    from owlbear_delivery_next.state_store import decision_store  # noqa: PLC0415

    shared, remote = picking.shared, shared_repo[1]
    root = shared.root
    fork = tmp_path / "fork-b.git"
    git(tmp_path, "clone", "-q", "--bare", str(remote), str(fork))
    other = tmp_path / "other"
    pushes, fired, owner, real = [], [], [], DataRepo.git

    def repoint() -> None:
        fired.append(True)
        git(root, "remote", "set-url", "origin", str(fork))
        git(root, "config", "remote.origin.pushurl", str(fork))
        owner.append(owner_state(root))

    def spy(self, *args, **kwargs):
        if self.root == root and args[:1] == ("push",) and len(args) == 4:
            pushes.append(args)
            if push == "rebased-retry" and len(pushes) == 1:  # another clone moves A on: this first push is refused
                git(tmp_path, "clone", "-q", str(remote), str(other))
                (other / "unrelated.txt").write_text("another clone\n")
                git(other, "add", "-A")
                git(other, "-c", "user.name=t", "-c", "user.email=t@e", "commit", "-qm", "other")
                git(other, "push", "-q")
        armed = pushes and (push == "initial" or len(pushes) == 2)
        if armed and not fired and args[:2] == ("rev-parse", "--git-path") and args[2] == publication_hold.RECORD:
            repoint()  # during the lower absent-hold probe, after the push's own address check passed
        return real(self, *args, **kwargs)

    monkeypatch.setattr(DataRepo, "git", spy)
    fork_refs, before = remote_refs(fork), remote_head(remote)
    receipts = decision_store.save_all(shared, [(an_owned_decision(picking), None)], message="decisions: one")

    assert fired == [True]
    assert remote_refs(fork) == fork_refs  # repository B never got the commit
    assert len(pushes) == (1 if push == "initial" else 2)
    assert not any(r.published for r in receipts)
    if push == "initial":
        assert remote_head(remote) == before  # nor did A: nothing was sent anywhere
    else:
        assert remote_head(remote) == git(other, "rev-parse", "HEAD")  # only the other clone's commit
    assert owner_state(root) == owner[0]  # nothing moved after the actor's repoint
