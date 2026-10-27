"""Finish rechecks its issued witnesses after the last blocking sync, before publishing SWITCHED."""

import errno
import json
import os
import subprocess
from pathlib import Path

import pytest

from owlbear_delivery_next.commands import cli
from owlbear_delivery_next.state_store import fd_tree, format_marker, offline_protocol, project_home, project_move
from owlbear_delivery_next.state_store.database import MARKER, FormatTooNewError

BEFORE = "AAAAAAAA-0000-4000-8000-000000000001"
AFTER = "BBBBBBBB-0000-4000-8000-000000000002"
OWNER_BOOT = "CCCCCCCC-0000-4000-8000-000000000003"
pytestmark = pytest.mark.usefixtures("current_binding")


@pytest.fixture
def prepared(tmp_path, monkeypatch):
    repo = tmp_path / "shop"
    subprocess.run(["git", "init", "-q", str(repo)], check=True, capture_output=True)  # noqa: S603, S607
    source = project_home.clone_dir(repo)
    source.mkdir()
    (source / MARKER).write_text("7")
    (source / project_move.CLONE_ID).write_text("owned\n")
    (source / "config.json").write_text(json.dumps({"format": 1, "widths": [1600]}))
    monkeypatch.setattr(offline_protocol, "boot_session", lambda: BEFORE)
    assert cli.main(["--repo", str(repo), "prepare"]) == 0
    monkeypatch.setattr(offline_protocol, "boot_session", lambda: AFTER)
    return repo, source


def snapshot(folder):
    return {
        p.name: p.read_bytes()
        for p in folder.iterdir()
        if p.is_file() and not p.name.startswith((".tmp-", fd_tree.QUARANTINE))
    }


def record(source):
    return json.loads((source / project_move.MOVE_RECORD).read_text())


def at_sync(monkeypatch, source, when, change):
    """Run the real durability operation first; mutate only at its matching final publication boundary."""
    fired = []
    real_sync = project_move._sync_published  # noqa: SLF001 - exercise the real target durability boundary
    real_fsync = os.fsync

    def after_sync(pfd, target, tfd):
        real_sync(pfd, target, tfd)
        if not fired:
            fired.append(True)
            change(target)

    def after_fsync(fd):
        real_fsync(fd)
        if fired:
            return
        for temp in source.glob(f".tmp-{project_move.MOVE_RECORD}-*"):
            if os.path.samestat(temp.stat(), os.fstat(fd)):
                pending = json.loads(temp.read_text())
                if pending["phase"] == project_move.SWITCHED:
                    fired.append(True)
                    change(Path(pending["target"]))

    if when == "target":
        monkeypatch.setattr(project_move, "_sync_published", after_sync)
    else:
        monkeypatch.setattr(os, "fsync", after_fsync)
    return fired


def change_owner(source, target, change):
    source_at = source
    target_at = target
    if change == "payload":
        (source / "config.json").write_text(json.dumps({"format": 1, "widths": [987]}))
    elif change == "preparation":
        prepared = json.loads((source / project_move.PREPARED).read_text())
        prepared["boot"] = OWNER_BOOT
        (source / project_move.PREPARED).write_text(json.dumps(prepared) + "\n")
    elif change == "clone-id":
        (source / project_move.CLONE_ID).write_text("owner-rebound\n")
    elif change == "fence":
        (source / MARKER).write_text("6\n")
    elif change == "source-path":
        source_at = source.with_name("source-aside")
        source.rename(source_at)
        source.mkdir()
        (source / "owner").write_text("foreign source\n")
    elif change == "target-path":
        target_at = target.with_name("target-aside")
        target.rename(target_at)
        target.mkdir()
        (target / "owner").write_text("foreign target\n")
    elif change == "proof":
        (target / project_move.MOVE_PROOF).write_text("owner proof\n")
    elif change == "content":
        (target / "config.json").write_text(json.dumps({"format": 1, "widths": [654]}))
    else:
        assert change == "marker"
        (target / MARKER).write_text("6\n")
    return source_at, target_at


@pytest.mark.parametrize("when", ["target", "receipt"])
@pytest.mark.parametrize(
    "change",
    ["payload", "preparation", "clone-id", "fence", "source-path", "target-path", "proof", "content", "marker"],
)
def test_finish_refuses_late_witness_changes_without_switching_or_overwriting_owners(
    prepared, monkeypatch, capsys, when, change
):
    repo, source = prepared
    owners = {}
    held_source = []

    def changed(target):
        source_at, target_at = change_owner(source, target, change)
        held_source.append(source_at)
        for path in {source, source_at, target, target_at}:
            owners[path] = snapshot(path)

    fired = at_sync(monkeypatch, source, when, changed)
    code = cli.main(["--repo", str(repo), "finish"])
    capsys.readouterr()

    assert fired == [True], f"the real {when} sync was not reached"
    assert code == 1, f"Finish admitted {change} changed at the {when} durability boundary"
    assert record(held_source[0])["phase"] == project_move.COPYING
    assert {path: snapshot(path) for path in owners} == owners
    if when == "receipt":
        quarantined = list(held_source[0].glob(f"{fd_tree.QUARANTINE}*"))
        assert len(quarantined) == 1
        assert json.loads(quarantined[0].read_text())["phase"] == project_move.SWITCHED


@pytest.mark.parametrize("when", ["target", "receipt"])
@pytest.mark.parametrize("replacement", ["owner-text", "different-proof"])
def test_finish_keeps_a_receipt_replaced_during_its_durability_work(prepared, monkeypatch, when, replacement):
    repo, source = prepared
    owners = {}

    def changed(target):
        text = '{"owner":"concurrent metadata repair"}\n'
        if replacement == "different-proof":
            text = json.dumps(record(source) | {"proof": "f" * 32}) + "\n"
        (source / project_move.MOVE_RECORD).write_text(text)
        owners.update({source: snapshot(source), target: snapshot(target)})

    fired = at_sync(monkeypatch, source, when, changed)

    code = cli.main(["--repo", str(repo), "finish"])
    assert fired == [True]
    assert code == 1
    assert {path: snapshot(path) for path in owners} == owners
    quarantined = list(source.glob(f"{fd_tree.QUARANTINE}*"))
    assert len(quarantined) == 1
    assert json.loads(quarantined[0].read_text())["phase"] == project_move.SWITCHED


@pytest.mark.parametrize("after", ["marker", "source-digest"])
def test_finish_rechecks_its_receipt_after_the_final_validator_reads(prepared, monkeypatch, after):
    repo, source = prepared
    owners, changed = {}, []
    owner = '{"owner":"replacement during final validation"}\n'

    def enable(target):
        module = format_marker if after == "marker" else project_move
        name = "written_format" if after == "marker" else "_source_unchanged"
        real = getattr(module, name)

        def late(*args, **kwargs):
            result = real(*args, **kwargs)
            changed.append(True)
            (source / project_move.MOVE_RECORD).write_text(owner)
            owners.update({source: snapshot(source), target: snapshot(target)})
            return result

        monkeypatch.setattr(module, name, late)

    fired = at_sync(monkeypatch, source, "receipt", enable)
    code = cli.main(["--repo", str(repo), "finish"])

    assert fired == [True]
    assert changed == [True]
    assert code == 1
    assert (source / project_move.MOVE_RECORD).read_text() == owner
    assert {path: snapshot(path) for path in owners} == owners


def test_finish_keeps_a_receipt_atomically_replaced_during_its_terminal_predicate(prepared, monkeypatch):
    repo, source = prepared
    owner = '{"owner":"atomic replacement during the receipt predicate"}\n'
    checks, active, changed = [], [], []
    owners = {}

    def enable(target):
        real_holds, real_read = fd_tree.holds_text_at, os.read

        def holds(dfd, name, text):
            if name != project_move.MOVE_RECORD:
                return real_holds(dfd, name, text)
            checks.append(True)
            active.append(len(checks))
            try:
                return real_holds(dfd, name, text)
            finally:
                active.pop()

        def read(fd, count):
            data = real_read(fd, count)
            if data and active == [2] and not changed:
                changed.append(True)
                replacement = source / "owner-receipt"
                replacement.write_text(owner)
                replacement.replace(source / project_move.MOVE_RECORD)
                owners.update({source: snapshot(source), target: snapshot(target)})
            return data

        monkeypatch.setattr(fd_tree, "holds_text_at", holds)
        monkeypatch.setattr(os, "read", read)

    fired = at_sync(monkeypatch, source, "receipt", enable)
    code = cli.main(["--repo", str(repo), "finish"])

    assert fired == [True]
    assert changed == [True]
    assert code == 1
    assert {path: snapshot(path) for path in owners} == owners
    assert (source / project_move.MOVE_RECORD).read_text() == owner


def test_finish_rejects_a_preparation_atomically_replaced_during_its_final_read(prepared, monkeypatch):
    repo, source = prepared
    owners, reads, active, changed = {}, [], [], []

    def enable(target):
        real_read_at, real_read = fd_tree.read_at, os.read

        def read_at(dfd, name):
            if name != project_move.PREPARED:
                return real_read_at(dfd, name)
            reads.append(True)
            active.append(len(reads))
            try:
                return real_read_at(dfd, name)
            finally:
                active.pop()

        def read(fd, count):
            data = real_read(fd, count)
            if data and active == [2] and not changed:
                changed.append(True)
                replacement = source / "owner-preparation"
                value = json.loads((source / project_move.PREPARED).read_text())
                value["boot"] = OWNER_BOOT
                replacement.write_text(json.dumps(value))
                replacement.replace(source / project_move.PREPARED)
                owners.update({source: snapshot(source), target: snapshot(target)})
            return data

        monkeypatch.setattr(fd_tree, "read_at", read_at)
        monkeypatch.setattr(os, "read", read)

    fired = at_sync(monkeypatch, source, "receipt", enable)
    code = cli.main(["--repo", str(repo), "finish"])

    assert fired == [True]
    assert changed == [True]
    assert code == 1
    assert record(source)["phase"] == project_move.COPYING
    assert {path: snapshot(path) for path in owners} == owners


def test_finish_refuses_source_payload_replaced_inside_its_final_hash(prepared, monkeypatch):
    repo, source = prepared
    before = (source / "config.json").stat()
    owners, changed = {}, []

    def enable(target):
        real_fdopen = os.fdopen

        class Reader:
            def __init__(self, stream):
                self.stream = stream

            def __getattr__(self, name):
                return getattr(self.stream, name)

            def __enter__(self):
                self.stream.__enter__()
                return self

            def __exit__(self, *args):
                return self.stream.__exit__(*args)

            def read(self, size):
                data = self.stream.read(size)
                if data and not changed:
                    changed.append(True)
                    replacement = source / "owner-config"
                    replacement.write_text(json.dumps({"format": 1, "widths": [987]}))
                    replacement.replace(source / "config.json")
                    owners.update({source: snapshot(source), target: snapshot(target)})
                return data

        def opened(fd, *args, **kwargs):
            stream = real_fdopen(fd, *args, **kwargs)
            return Reader(stream) if os.path.samestat(os.fstat(fd), before) else stream

        monkeypatch.setattr(os, "fdopen", opened)

    fired = at_sync(monkeypatch, source, "receipt", enable)
    code = cli.main(["--repo", str(repo), "finish"])

    assert fired == [True]
    assert changed == [True]
    assert code == 1
    assert record(source)["phase"] == project_move.COPYING
    assert {path: snapshot(path) for path in owners} == owners


@pytest.mark.parametrize("change", ["preparation", "proof", "marker"])
def test_finish_rechecks_cheap_authority_witnesses_after_final_source_hashing(prepared, monkeypatch, change):
    repo, source = prepared
    owners, changed = {}, []

    def enable(target):
        real = project_move._source_unchanged  # noqa: SLF001 - mutate only after the actual final payload digest

        def late(dfd, rec, *args, **kwargs):
            valid = real(dfd, rec, *args, **kwargs)
            changed.append(True)
            change_owner(source, target, change)
            owners.update({source: snapshot(source), target: snapshot(target)})
            return valid

        monkeypatch.setattr(project_move, "_source_unchanged", late)

    fired = at_sync(monkeypatch, source, "receipt", enable)
    code = cli.main(["--repo", str(repo), "finish"])

    assert fired == [True]
    assert changed == [True]
    assert code == 1
    assert record(source)["phase"] == project_move.COPYING
    assert {path: snapshot(path) for path in owners} == owners


@pytest.mark.parametrize(
    ("where", "witness"),
    [
        ("source", project_move.PREPARED),
        ("source", MARKER),
        ("source", project_move.CLONE_ID),
        ("source", project_move.MOVE_RECORD),
        ("target", project_move.MOVE_RECORD),
    ],
)
def test_finish_refuses_paths_replaced_during_its_terminal_witness_reads(prepared, monkeypatch, where, witness):
    repo, source = prepared
    owners, reads, changed = {}, [], []
    kept_source = []

    def enable(target):
        predicate = witness == project_move.MOVE_RECORD
        name = "holds_text_at" if predicate else "read_at"
        real = getattr(fd_tree, name)

        def read(dfd, entry, *args):
            result = real(dfd, entry, *args)
            if entry == witness and os.path.samestat(os.fstat(dfd), source.stat()):
                reads.append(True)
                if len(reads) == 2:
                    changed.append(True)
                    folder = source if where == "source" else target
                    detached = folder.with_name(f"owner-kept-{where}")
                    folder.rename(detached)
                    folder.mkdir()
                    (folder / "owner").write_text(f"replacement {where}\n")
                    kept_source.append(detached if where == "source" else source)
                    owners.update({path: snapshot(path) for path in (source, detached, target)})
            return result

        monkeypatch.setattr(fd_tree, name, read)

    fired = at_sync(monkeypatch, source, "receipt", enable)
    code = cli.main(["--repo", str(repo), "finish"])

    assert fired == [True]
    assert changed == [True]
    assert code == 1
    assert record(kept_source[0])["phase"] == project_move.COPYING
    assert {path: snapshot(path) for path in owners} == owners
    quarantined = list(kept_source[0].glob(f"{fd_tree.QUARANTINE}*"))
    assert len(quarantined) == 1
    assert json.loads(quarantined[0].read_text())["phase"] == project_move.SWITCHED


@pytest.mark.parametrize("when", ["target", "receipt"])
@pytest.mark.parametrize("where", ["source", "target"])
def test_a_late_future_marker_stays_typed_and_keeps_the_owner_bytes(prepared, monkeypatch, when, where):
    repo, source = prepared
    changed = []

    def future(target):
        path = (source if where == "source" else target) / MARKER
        path.write_text("1000\n")
        changed.append(path)

    fired = at_sync(monkeypatch, source, when, future)
    with pytest.raises(FormatTooNewError):
        offline_protocol.finish_clone(repo)

    assert fired == [True]
    assert changed[0].read_text() == "1000\n"
    assert record(source)["phase"] == project_move.COPYING


@pytest.mark.parametrize(
    ("boundary", "change"),
    [
        ("receipt", "preparation"),
        ("receipt", "clone-id"),
        ("receipt", "future-fence"),
        ("receipt", "proof"),
        ("receipt", "future-target"),
        (MARKER, "preparation"),
        (project_move.CLONE_ID, "preparation"),
    ],
)
def test_finish_keeps_its_witness_set_stable_through_the_last_content_read(prepared, monkeypatch, boundary, change):
    repo, source = prepared
    owners, reads, changed = {}, [], []
    source_id = source.stat()

    def enable(target):
        predicate = boundary == "receipt"
        name = "holds_text_at" if predicate else "read_at"
        wanted = project_move.MOVE_RECORD if predicate else boundary
        real = getattr(fd_tree, name)

        def read(dfd, entry, *args):
            value = real(dfd, entry, *args)
            if entry == wanted and os.path.samestat(os.fstat(dfd), source_id):
                reads.append(True)
                if len(reads) == 2:
                    changed.append(True)
                    if change.startswith("future-"):
                        folder = source if change == "future-fence" else target
                        (folder / MARKER).write_text("1000\n")
                    else:
                        change_owner(source, target, change)
                    owners.update({source: snapshot(source), target: snapshot(target)})
            return value

        monkeypatch.setattr(fd_tree, name, read)

    fired = at_sync(monkeypatch, source, "receipt", enable)
    error = FormatTooNewError if change.startswith("future-") else project_move.StoreError
    with pytest.raises(error):
        offline_protocol.finish_clone(repo)

    assert fired == [True]
    assert changed == [True]
    assert record(source)["phase"] == project_move.COPYING
    assert {path: snapshot(path) for path in owners} == owners


def test_finish_switches_after_a_failed_real_receipt_sync_is_retried(prepared, monkeypatch, capsys):
    repo, source = prepared

    def fail(_target):
        raise OSError(errno.EIO, "injected receipt durability failure")

    fired = at_sync(monkeypatch, source, "receipt", fail)
    assert cli.main(["--repo", str(repo), "finish"]) == 1
    capsys.readouterr()
    assert fired == [True]
    assert record(source)["phase"] == project_move.COPYING
    assert len(list(source.glob(f"{fd_tree.QUARANTINE}*"))) == 1

    # Quarantine requires an explicit owner action, not an automatic deletion or adoption on retry.
    kept = next(source.glob(f"{fd_tree.QUARANTINE}*"))
    kept.rename(source.parent / "owner-kept-receipt")
    assert cli.main(["--repo", str(repo), "finish"]) == 0
    capsys.readouterr()
    assert record(source)["phase"] == project_move.SWITCHED
    target = Path(record(source)["target"])
    assert json.loads((target / "config.json").read_text())["widths"] == [1600]
    assert json.loads((source / "config.json").read_text())["widths"] == [1600]
    assert (source / MARKER).read_text() == f"{project_move.FENCE}\n"


@pytest.mark.parametrize(
    "mutation",
    [
        ("offline_proof.py", "    require_identity(folder, folder_fd, proof)", "    pass"),
        ("project_move.py", "before_replace=unchanged)", "before_replace=None)"),
        ("fd_tree.py", "            before_replace()", "            pass"),
    ],
)
def test_a_changed_publication_guard_is_an_unknown_build_not_an_offline_proof(
    prepared, current_package, capsys, mutation
):
    repo, source = prepared
    module, old, new = mutation
    before = snapshot(source)
    path = current_package / "state_store" / module
    text = path.read_text()
    assert text.count(old) == 1
    path.write_text(text.replace(old, new))
    who = ["-c", "user.name=fixture", "-c", "user.email=fixture@example.invalid"]
    commit = ["git", "-C", str(current_package), *who, "commit", "-qam", "changed guard"]
    subprocess.run(commit, check=True, capture_output=True)  # noqa: S603 - only the synthetic binding's checkout

    assert cli.main(["--repo", str(repo), "finish"]) == 1

    assert "current family modules differ from the candidate" in capsys.readouterr().err
    assert snapshot(source) == before
    assert not (source / project_move.MOVE_RECORD).exists()


@pytest.mark.parametrize("edit_earlier", [False, True], ids=["control", "edited"])
def test_finish_refuses_an_earlier_sibling_edited_during_a_later_hash(prepared, monkeypatch, capsys, edit_earlier):
    repo, source = prepared
    payload = source / "payload"
    payload.mkdir()
    (payload / "a").write_text("old\n")
    (payload / "b").write_text("later\n")
    later = (payload / "b").stat()
    real_fdopen = os.fdopen
    owners, edited = {}, []

    def enable(target):
        def change():
            if edit_earlier and not edited:
                edited.append(True)
                (payload / "a").write_text("edited while b was hashed\n")
                owners.update({source: snapshot(source), target: snapshot(target)})

        def opened(fd, *args, **kwargs):
            stream = real_fdopen(fd, *args, **kwargs)
            return DigestReader(stream, change) if os.path.samestat(os.fstat(fd), later) else stream

        monkeypatch.setattr(os, "fdopen", opened)

    fired = at_sync(monkeypatch, source, "receipt", enable)
    code = cli.main(["--repo", str(repo), "finish"])
    error = capsys.readouterr().err
    target = Path(record(source)["target"])

    assert fired == [True]
    assert (source / "payload" / "b").read_text() == (target / "payload" / "b").read_text() == "later\n"
    assert (target / "payload" / "a").read_text() == "old\n"
    if not edit_earlier:
        assert code == 0, error
        assert record(source)["phase"] == project_move.SWITCHED
        return
    assert edited == [True]
    assert code == 1, error
    assert record(source)["phase"] == project_move.COPYING
    assert (source / "payload" / "a").read_text() == "edited while b was hashed\n"
    assert {path: snapshot(path) for path in owners} == owners
    quarantined = list(source.glob(f"{fd_tree.QUARANTINE}*"))
    assert len(quarantined) == 1
    assert json.loads(quarantined[0].read_text())["phase"] == project_move.SWITCHED


class DigestReader:
    def __init__(self, stream, change):
        self.stream, self.change = stream, change

    def __getattr__(self, name):
        return getattr(self.stream, name)

    def __enter__(self):
        self.stream.__enter__()
        return self

    def __exit__(self, *args):
        return self.stream.__exit__(*args)

    def read(self, size):
        data = self.stream.read(size)
        if data:
            self.change()
        return data


@pytest.mark.parametrize("nested", [False, True], ids=["top-level", "nested"])
def test_finish_retains_payload_images_through_the_terminal_receipt_read(prepared, monkeypatch, nested):
    repo, source = prepared
    entry = source / "config.json"
    if nested:
        entry = source / "payload" / "nested" / "a"
        entry.parent.mkdir(parents=True)
        entry.write_text("old\n")
    old = entry.read_bytes()
    relative = entry.relative_to(source)
    owner = b'{"format":1,"widths":[987]}\n'
    checks, changed, owners = [], [], {}

    def enable(target):
        real = fd_tree.holds_text_at

        def holds(dfd, name, text):
            valid = real(dfd, name, text)
            if name == project_move.MOVE_RECORD:
                checks.append(True)
                if len(checks) == 2:
                    changed.append(True)
                    entry.write_bytes(owner)
                    owners.update({source: snapshot(source), target: snapshot(target)})
            return valid

        monkeypatch.setattr(fd_tree, "holds_text_at", holds)

    fired = at_sync(monkeypatch, source, "receipt", enable)
    with pytest.raises(project_move.StoreError):
        offline_protocol.finish_clone(repo)

    assert fired == [True]
    assert changed == [True]
    assert record(source)["phase"] == project_move.COPYING
    target = Path(record(source)["target"])
    assert entry.read_bytes() == owner
    assert (target / relative).read_bytes() == old
    assert {path: snapshot(path) for path in owners} == owners


@pytest.mark.parametrize("nested", [False, True], ids=["top-level", "nested"])
@pytest.mark.parametrize("boundary", ["source-hash", "receipt"])
def test_finish_retains_target_payload_images_through_later_reads(prepared, monkeypatch, nested, boundary):
    repo, source = prepared
    entry = source / "config.json"
    if nested:
        entry = source / "payload" / "nested" / "a"
        entry.parent.mkdir(parents=True)
        entry.write_text("old\n")
    old, relative = entry.read_bytes(), entry.relative_to(source)
    owner = b'{"format":1,"widths":[987]}\n'
    checks, changed, owners = [], [], {}

    def enable(target):
        def change():
            changed.append(True)
            (target / relative).write_bytes(owner)
            owners.update({source: snapshot(source), target: snapshot(target)})

        if boundary == "source-hash":
            real = project_move._source_unchanged  # noqa: SLF001 - mutate after real source hashing

            def hashed(*args, **kwargs):
                valid = real(*args, **kwargs)
                change()
                return valid

            monkeypatch.setattr(project_move, "_source_unchanged", hashed)
        else:
            real = fd_tree.holds_text_at

            def holds(dfd, name, text):
                valid = real(dfd, name, text)
                if name == project_move.MOVE_RECORD:
                    checks.append(True)
                    if len(checks) == 2:
                        change()
                return valid

            monkeypatch.setattr(fd_tree, "holds_text_at", holds)

    fired = at_sync(monkeypatch, source, "receipt", enable)
    with pytest.raises(project_move.StoreError):
        offline_protocol.finish_clone(repo)

    assert fired == [True]
    assert changed == [True]
    assert record(source)["phase"] == project_move.COPYING
    target = Path(record(source)["target"])
    assert entry.read_bytes() == old
    assert (target / relative).read_bytes() == owner
    assert {path: snapshot(path) for path in owners} == owners


def test_finish_refuses_target_payload_changes_before_the_first_target_marker_write(prepared, monkeypatch):
    repo, source = prepared
    real_commit, real_holds = project_move._commit, fd_tree.holds_text_at  # noqa: SLF001 - public pre-write boundary
    active, changed, owners = [], [], {}

    def commit(*args, **kwargs):
        active.append(args[2])
        try:
            return real_commit(*args, **kwargs)
        finally:
            active.pop()

    def holds(dfd, name, text):
        valid = real_holds(dfd, name, text)
        if active and not changed and name == project_move.MOVE_PROOF:
            target = active[-1]
            assert os.path.samestat(os.fstat(dfd), target.stat())
            changed.append(True)
            (target / "config.json").write_text('{"format":1,"widths":[987]}\n')
            owners.update({source: snapshot(source), target: snapshot(target)})
        return valid

    monkeypatch.setattr(project_move, "_commit", commit)
    monkeypatch.setattr(project_move, "_holds_text_at", holds)
    with pytest.raises(project_move.StoreError):
        offline_protocol.finish_clone(repo)

    assert changed == [True]
    assert record(source)["phase"] == project_move.COPYING
    assert {path: snapshot(path) for path in owners} == owners
