"""The clone's id is created exclusively with no temporary name.

A race, a link or a cut-short write is refused, never deleted.
"""

import errno
import os

import pytest

from owlbear_delivery_next.state_store import fd_tree, project_home
from owlbear_delivery_next.state_store.database import StoreError


@pytest.fixture
def store(tmp_path):
    return tmp_path / "owlbear-delivery"


def names(folder):
    return sorted(p.name for p in folder.iterdir())


def test_a_new_clone_leaves_only_its_id_and_reuses_it(store):
    first = project_home.ensure_id(store)
    assert names(store) == ["clone-id"]
    assert (store / "clone-id").read_text() == first + "\n"
    assert project_home.ensure_id(store) == first


def test_an_existing_id_is_reused_and_never_rewritten(store):
    store.mkdir()
    (store / "clone-id").write_text("abc123\n")
    assert project_home.ensure_id(store) == "abc123"
    assert (store / "clone-id").read_text() == "abc123\n"
    assert names(store) == ["clone-id"]


def test_a_concurrent_opener_id_wins_and_is_not_overwritten(store, monkeypatch):
    real_create = fd_tree.create_at

    def race(dfd, name, text):
        fd = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600, dir_fd=dfd)  # the other opener, first
        with os.fdopen(fd, "w") as fh:
            fh.write("theirs\n")
        return real_create(dfd, name, text)

    monkeypatch.setattr(fd_tree, "create_at", race)
    assert project_home.ensure_id(store) == "theirs"
    assert (store / "clone-id").read_text() == "theirs\n"
    assert names(store) == ["clone-id"]


def test_a_link_at_the_id_name_is_refused_and_its_target_is_untouched(store, tmp_path):
    store.mkdir()
    target = tmp_path / "foreign"
    target.write_text("keep me\n")
    (store / "clone-id").symlink_to(target)
    with pytest.raises(StoreError, match="unreadable"):
        project_home.ensure_id(store)
    assert target.read_text() == "keep me\n"
    assert (store / "clone-id").is_symlink()


def test_a_cut_short_id_is_refused_and_kept(store):
    store.mkdir()
    (store / "clone-id").write_text("abc")  # no newline: the writer never finished
    with pytest.raises(StoreError, match="incomplete"):
        project_home.ensure_id(store)
    assert (store / "clone-id").read_text() == "abc"
    assert names(store) == ["clone-id"]


def test_an_unfinished_create_is_kept_in_place_and_adopted_on_retry(store, monkeypatch):
    real_fsync = os.fsync
    calls = []

    def failing_once(fd):
        calls.append(fd)
        if len(calls) == 1:
            raise OSError(errno.EIO, "Input/output error")
        return real_fsync(fd)

    monkeypatch.setattr(fd_tree.os, "fsync", failing_once)
    with pytest.raises(StoreError, match="was not finished"):
        project_home.ensure_id(store)
    assert names(store) == ["clone-id"]  # kept, not unlinked, and no temporary name
    kept = (store / "clone-id").read_text().strip()
    assert kept
    assert (store / "clone-id").read_text().endswith("\n")
    assert project_home.ensure_id(store) == kept
