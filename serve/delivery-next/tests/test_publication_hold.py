"""A stale automatic config fill stays bound to the shared remote through every push and rebase (R15, FND-01).

Each test runs separate Git checkouts of one bare remote: the winner's fill is checked against the freshly fetched
remote before each push or rebase, wherever the other checkout's completion lands, and once refused it is never pushed
by a later publication, a restart or a raw push. Nothing in Git is undone.
"""

import subprocess
import time
from pathlib import Path

import pytest

from owlbear_delivery_next.change_contracts.profile_record import Profile, ProfileEntry
from owlbear_delivery_next.local_system import data_repo, publication_hold
from owlbear_delivery_next.local_system.data_repo import DataRepo
from owlbear_delivery_next.settings import profile
from owlbear_delivery_next.settings.config import Layer
from owlbear_delivery_next.state_store import config_save, decision_sync, prefs_import, profile_share
from owlbear_delivery_next.state_store.pending_intents import pending_file
from owlbear_delivery_next.state_store.store import Store, StoreError

PROJECT = "shop-site"


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


def after_pull(args, _seen) -> bool:
    return args[:1] == ("commit",)  # the first Git write after the pull and the guards: the remote moves now


def test_a_completion_after_the_winners_pull_holds_the_fill_before_any_push(three, monkeypatch):
    winner, settler, remote = three
    fired = at_git(monkeypatch, winner, after_pull, lambda: complete_and_delete(settler))

    with pytest.raises(StoreError, match="is held because the legacy preference import claim"):
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
        sent = decision_sync.publish(restarted.shared, [memory], "decision: raw push", time.monotonic() + 30)
        assert "is held because" in sent.notice
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
