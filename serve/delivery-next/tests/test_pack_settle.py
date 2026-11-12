"""R04 core for the R16 store copy: a legacy pack record carries its generation into the record before it is copied.

A copy is another file, so a fingerprint taken from it would name another run. ``pack_run_record.settle`` writes the
generation this host saw into the record itself; the copy keeps it, so the lease already held for it, held or
recovered, still covers it wherever the store now lies. A later record carries none and is held anew.
"""

import json
import shutil
from pathlib import Path
from types import SimpleNamespace

import pytest

from owlbear_delivery_next.impeccable_runs import pack_job, pack_state
from owlbear_delivery_next.local_system import maintenance
from owlbear_delivery_next.local_system.slots import Slots
from owlbear_delivery_next.local_system.storage_io import atomic_write
from owlbear_delivery_next.project_host import session_slots
from owlbear_delivery_next.state_store import fd_tree, pack_run_record
from owlbear_delivery_next.state_store.store import Store

STARTED = "2026-10-25T00:00:00+00:00"
IDENTITIES = {
    "no-identity": {},
    "run-only": {"run": "legacy-run"},
    "start-only": {"started_at": STARTED},
    "proven": {"run": "main-run", "started_at": STARTED},
}
SDK_FAILED = {
    "state": "failed",
    "reason": "update: RuntimeError: synthetic SDK failure",
    "stages": [{"name": "update", "label": "Update", "result": "failed", "detail": ""}],
}


def store(tmp_path: Path, name: str, record: dict | None = None) -> Path:
    root = tmp_path / name
    root.mkdir()
    if record is not None:
        (root / pack_state.FILE).write_text(json.dumps(pack_state.blank() | record, indent=1) + "\n")
    return root


def ledger(boot: float = 10.0) -> maintenance.Maintenance:
    """A host's view of the machine's ledger: each instance is a restart, *boot* the boot it runs in."""
    return maintenance.Maintenance(Slots(lambda: 2), boot=lambda: boot, observe=lambda *_args: False)


def copied(source: Path, tmp_path: Path) -> Path:
    """The store copied byte for byte into another folder, as the offline move copies it: each file a new one."""
    target = tmp_path / "home"
    target.mkdir()
    shutil.copy2(source / pack_state.FILE, target / pack_state.FILE)
    return target


def leases(owner: maintenance.Maintenance) -> list[tuple[str, str]]:
    return [(s["id"], s["state"]) for s in owner.read()["sessions"]]


def settle(root: Path, owner: maintenance.Maintenance | None = None) -> bool:
    """Settle *root* as the move would: against *owner*'s ledger for project ``p``, or as a folder no machine knows."""
    if owner is None:
        return pack_run_record.settle(root, receipted=lambda _digest: "")
    return pack_run_record.settle(root, receipted=lambda found: owner.receipted("p", found))


@pytest.mark.parametrize("identity", IDENTITIES.values(), ids=IDENTITIES.keys())
def test_generation_selects_each_partial_and_proven_identity(identity):
    record = pack_state.blank() | {"state": "running", **identity}
    generation = pack_state.generation(record, "file-version")[0]
    if "run" in identity and "started_at" in identity:
        assert generation == f"main-run:{STARTED}"
        assert pack_state.generation(record, "another-file")[0] == generation
    else:
        assert generation
        assert pack_state.generation(record, "another-file")[0] != generation
        assert pack_state.generation(record | {"run": "different-run"}, "file-version")[0] != generation
        assert (
            pack_state.generation(record | {"started_at": "2026-10-26T00:00:00+00:00"}, "file-version")[0] != generation
        )


def test_generation_selection_and_running_settlement(tmp_path):
    root = store(tmp_path, "clone", {"state": "running"})
    before = pack_state.generation(*pack_state.observed(root))[0]
    assert settle(root) is True
    record = pack_state.read_only(root)
    assert (record["state"], record["reason"], record[pack_state.REWRITTEN]) == (
        "failed", pack_state.HOST_STOPPED, before,
    )  # fmt: skip
    assert (pack_state.legacy_uncertain(record), pack_state.generation(*pack_state.observed(root))[0]) == (True, before)
    settled = (root / pack_state.FILE).read_bytes()
    assert settle(root) is False
    assert (root / pack_state.FILE).read_bytes() == settled


def test_an_uncertain_failure_is_stamped_and_definitive_modern_idle_or_absent_records_are_left_as_they_are(tmp_path):
    root = store(tmp_path, "uncertain", SDK_FAILED)
    before = pack_state.generation(*pack_state.observed(root))[0]
    kept = pack_state.read_only(root)
    assert settle(root) is True
    assert pack_state.read_only(root) == kept | {pack_state.REWRITTEN: before}  # every other field as it was
    for name, record in {
        "definitive": {"state": "failed", "reason": "candidate: RuntimeError: the download failed"},
        "modern": {"state": "running", "workspace": str(tmp_path / "w")},
        "idle": {},
        "passed": {"state": "passed"},
        "publishing": {"state": "running", "context": {"publication": {"commit": "c"}}},
    }.items():
        root = store(tmp_path, name, record)
        unchanged = (root / pack_state.FILE).read_bytes()
        assert (settle(root), (root / pack_state.FILE).read_bytes()) == (False, unchanged)
    assert settle(store(tmp_path, "absent")) is False


def test_a_failed_stamp_leaves_the_record_whole_and_a_retry_carries_the_same_generation(tmp_path):
    root = store(tmp_path, "clone", {"state": "running"})
    before, original = pack_state.generation(*pack_state.observed(root))[0], (root / pack_state.FILE).read_bytes()

    def interrupted(*_args: object, **_kwargs: object) -> None:
        msg = "interrupted descriptor-bound rewrite"
        raise OSError(msg)

    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(fd_tree, "write_at", interrupted)
        with pytest.raises(OSError, match="interrupted descriptor-bound rewrite"):
            settle(root)
    assert (root / pack_state.FILE).read_bytes() == original
    assert settle(root) is True
    assert pack_state.read_only(root)[pack_state.REWRITTEN] == before


@pytest.mark.parametrize("later", ["original-bytes", "fresh-running", "new-proven-run"])
def test_copy_and_later_write_preserve_generation_boundaries(tmp_path, later):
    original = {"state": "running"}
    source = store(tmp_path, "clone", original)
    original_bytes = (source / pack_state.FILE).read_bytes()
    owner = ledger()
    session_slots.restore(owner, "p", source)
    [(a, _state)] = leases(owner)
    assert settle(source, owner)
    target = copied(source, tmp_path)
    ledger(boot=20.0).recover(a, rebooted=True)
    again = ledger(boot=20.0)
    session_slots.restore(again, "p", target)
    assert leases(again) == [(a, "recovered")]
    assert again.slots.counts("p")[2] == 0
    assert not again.pending("pack")
    if later == "original-bytes":  # byte for byte the record as it was before it was settled
        (target / pack_state.FILE).write_bytes(original_bytes)
    elif later == "fresh-running":
        (target / pack_state.FILE).unlink()
        (target / pack_state.FILE).write_text(json.dumps(pack_job._blank() | {"state": "running"}) + "\n")  # noqa: SLF001
    else:
        later_run = SDK_FAILED | {"run": "main-run-b", "started_at": STARTED}
        (target / pack_state.FILE).write_text(json.dumps(pack_job._blank() | later_run) + "\n")  # noqa: SLF001
    owner = ledger(boot=20.0)
    session_slots.restore(owner, "p", target)
    assert leases(owner)[0] == (a, "recovered")
    assert [s for _, s in leases(owner)[1:]] == ["held"]


def test_an_unsettled_copy_of_a_record_without_identity_is_another_file_and_held_anew(tmp_path):
    source = store(tmp_path, "clone", {"state": "running"})
    owner = ledger()
    session_slots.restore(owner, "p", source)
    session_slots.restore(owner, "p", copied(source, tmp_path))
    assert [s for _, s in leases(owner)] == ["held", "held"]


def test_a_proven_run_written_again_by_its_producer_after_settling_is_still_its_lease(tmp_path):
    """main writes every run it starts with its run and start, so a later write of that run keeps its generation."""
    source = store(tmp_path, "clone", {"state": "running", "run": "main-run", "started_at": STARTED})
    first = ledger()
    session_slots.restore(first, "p", source)
    [(a, _state)] = leases(first)
    settle(source, first)
    continued = SDK_FAILED | {"run": "main-run", "started_at": STARTED}  # main's own later write: no carried field
    (source / pack_state.FILE).write_text(json.dumps(pack_job._blank() | continued) + "\n")  # noqa: SLF001
    owner = ledger()
    session_slots.restore(owner, "p", copied(source, tmp_path))
    assert leases(owner) == [(a, "held")]


def test_a_proven_generation_matches_only_within_its_project_and_kind_and_an_empty_one_stays_strict(tmp_path):
    owner = ledger()
    a = owner.adopt_uncertain("p:one", "p", "pack", workspace=str(tmp_path / "one"), generation="run:t")
    assert owner.adopt_uncertain("p:two", "p", "pack", workspace=str(tmp_path / "two"), generation="run:t").id == a.id
    assert owner.adopt_uncertain("q:one", "q", "pack", workspace=str(tmp_path / "one"), generation="run:t").id != a.id
    curation = owner.adopt_uncertain("p:c", "p", "curation", workspace=str(tmp_path / "one"), generation="run:t")
    assert curation.id != a.id
    held = owner.adopt_uncertain("p:legacy", "p", "pack", workspace=str(tmp_path / "one"))
    assert owner.adopt_uncertain("p:legacy", "p", "pack", workspace=str(tmp_path / "two")).id != held.id
    assert owner.adopt_uncertain("p:legacy", "p", "pack", workspace=str(tmp_path / "one")).id == held.id
    kept = next(s for s in owner.read()["sessions"] if s["id"] == a.id)
    assert (kept["workspace"], kept["state"]) == (str(tmp_path / "one"), "held")  # its own workspace and history


def test_the_carried_generation_counts_only_on_an_uncertain_failed_legacy_record():
    stamped = SDK_FAILED | {pack_state.REWRITTEN: "observed:a"}
    assert pack_state.generation(stamped, "v1")[0] == "observed:a"
    for other in (
        {"state": "running"},
        {"workspace": "/w"},
        {"reason": "candidate: RuntimeError: x", "stages": []},
        {"reason": "update: PackError: the updater ended with error: no result"},
    ):
        assert pack_state.generation(stamped | other, "v1")[0] != "observed:a"


def receipted_rewrite(tmp_path: Path, *, recovered: bool) -> tuple[Path, str, str]:
    """8dfa's state: A held for a running record with no identity, then its Job's rewrite and that rewrite's receipt.

    The rewrite carries no generation, as 8dfa wrote it; the ledger's receipt maps its file version to A's.
    """
    root = store(tmp_path, "clone", {"state": "running"})
    owner = ledger()
    session_slots.restore(owner, "p", root)
    [(a, _state)] = leases(owner)
    g0 = pack_state.generation(*pack_state.observed(root))[0]
    record, _version = pack_state.observed(root)
    pack_state.ended(record, "failed", pack_state.HOST_STOPPED)
    version = pack_state.version_of(atomic_write(root / pack_state.FILE, json.dumps(record, indent=1) + "\n"))
    owner.receipt("p", pack_state.digest(version), g0)
    if recovered:
        ledger(boot=20.0).recover(a, rebooted=True)
    return root, a, g0


def test_receipt_is_bound_to_exact_observed_bytes(tmp_path):
    """Review on 7679: settling resolves the generation as restoration does, the receipt for this very version first."""
    root, a, g0 = receipted_rewrite(tmp_path, recovered=True)
    assert settle(root, ledger(boot=20.0)) is True
    assert pack_state.read_only(root)[pack_state.REWRITTEN] == g0
    target = copied(root, tmp_path)
    owner = ledger(boot=20.0)
    session_slots.restore(owner, "p", target)
    assert leases(owner) == [(a, "recovered")]
    write_record(target, SDK_FAILED | {"run": "later", "started_at": STARTED})
    assert settle(target, owner)
    assert pack_state.read_only(target)[pack_state.REWRITTEN] == f"later:{STARTED}"
    session_slots.restore(owner, "p", target)
    assert [s for _, s in leases(owner)] == ["recovered", "held"]


def test_settling_against_a_ledger_that_cannot_be_read_fails_closed_and_changes_nothing(tmp_path):
    root, _a, _g0 = receipted_rewrite(tmp_path, recovered=False)
    before = (root / pack_state.FILE).read_bytes()
    owner = ledger()
    owner.path.write_text('{"format": 1}')  # its sessions and receipts are missing: not an empty ledger
    with pytest.raises(maintenance.MaintenanceError):
        settle(root, owner)
    assert (root / pack_state.FILE).read_bytes() == before


@pytest.mark.parametrize("saved", [False, True], ids=["before-save", "after-save"])
def test_receipt_save_interruption_does_not_duplicate_adoption(tmp_path, monkeypatch, saved):
    root = store(tmp_path, "clone", {"state": "running"})
    workspace = root / pack_job.UPDATER
    workspace.mkdir()
    sentinel = workspace / "retained.txt"
    sentinel.write_text("kept")
    first = ledger()
    session_slots.restore(first, "p", root)
    [a] = ledger_sessions(first)
    ledger(boot=20.0).recover(a["id"], rebooted=True)
    job = pack_job.Job(Store(root))
    job.maintenance = ledger(boot=20.0)
    real_save, faults = maintenance.Maintenance._save, []  # noqa: SLF001 - the donor's receipt-save fault boundary

    def interrupted(self, data):
        if faults or not any(":receipt:" in mark for mark in data.imported):
            return real_save(self, data)
        faults.append(True)
        if saved:
            real_save(self, data)
        msg = "interrupted receipt save"
        raise maintenance.MaintenanceError(msg)

    with monkeypatch.context() as patch:
        patch.setattr(maintenance.Maintenance, "_save", interrupted)
        with pytest.raises(maintenance.MaintenanceError, match="interrupted receipt save"):
            session_slots.interrupted(job, "p")
    assert faults == [True]
    job.maintenance = ledger(boot=20.0)
    session_slots.interrupted(job, "p")
    again = ledger(boot=20.0)
    session_slots.restore(again, "p", root)
    [kept] = ledger_sessions(again)
    assert (kept["id"], kept["state"], kept["workspace"]) == (a["id"], "recovered", a["workspace"])
    assert again.receipted("p", pack_state.digest(job.version)) == a["generation"]
    assert sentinel.read_text() == "kept"


def rewritten_in_place_while_read(root: Path, record: dict) -> pytest.MonkeyPatch:
    """A producer rewrites the run file in place, same inode, after the reader stat it and before it decodes.

    The patch writes *record* through another descriptor just before the reader's own decode, then decodes as usual.
    """
    real_load = pack_run_record.json.load
    patch = pytest.MonkeyPatch()

    def load(source, *args: object, **kwargs: object) -> object:
        with (root / pack_state.FILE).open("r+", encoding="utf-8") as same:  # the same inode, rewritten in place
            same.write(json.dumps(pack_job._blank() | record, indent=1) + "\n")  # noqa: SLF001
            same.truncate()
        return real_load(source, *args, **kwargs)

    patch.setattr(pack_run_record.json, "load", load)
    return patch


@pytest.mark.parametrize("recovered", [False, True], ids=["a-held", "a-recovered"])
def test_a_run_rewritten_in_place_while_restoration_reads_it_is_held_not_taken_for_the_receipted_run(
    tmp_path, recovered
):
    """Review 4377372587: the payload read must be the version its receipt names, or the observation is refused.

    A is receipted to the rewrite's file version. A producer starts B in that very file, in place, while restoration
    reads it: B's payload would pair with A's version and borrow A's receipt. The changed observation is unreadable,
    held conservatively, and another project gets no slot.
    """
    root, a, _g0 = receipted_rewrite(tmp_path, recovered=recovered)
    owner = ledger(boot=20.0)
    patch = rewritten_in_place_while_read(root, {"state": "running"})  # B: a new run, no identity
    try:
        session_slots.restore(owner, "p", root)
    finally:
        patch.undo()
    states = dict(leases(owner))
    assert states[a] == ("recovered" if recovered else "held")
    assert [s for i, s in leases(owner) if i != a] == ["held"]  # B's observation, held as unreadable
    assert owner.slots.take("other", "probe", 1, 2) == (1 if recovered else 0)  # two slots: B's hold is counted
    assert owner.pending("pack") is True


def test_every_reader_refuses_a_run_rewritten_in_place_while_it_read_it_and_closes_its_descriptor(
    tmp_path, monkeypatch
):
    root = store(tmp_path, "clone", SDK_FAILED)
    files, real_fdopen = [], pack_run_record.os.fdopen

    def captured(fd, *args, **kwargs):
        source = real_fdopen(fd, *args, **kwargs)
        files.append(source)
        return source

    monkeypatch.setattr(pack_run_record, "os", SimpleNamespace(**(vars(pack_run_record.os) | {"fdopen": captured})))
    patch = rewritten_in_place_while_read(root, {"state": "running"})
    try:
        with pytest.raises(ValueError, match="changed while it was read"):
            pack_state.observed(root)
        assert pack_state.read_version(root / pack_state.FILE) == (pack_state.blank(), "")
    finally:
        patch.undo()
    assert len(files) == 2
    assert all(source.closed for source in files)
    kept, version = pack_state.observed(root)  # control: read again unchanged, it is the new run, whole
    assert (kept["state"], version != "") == ("running", True)


def overwritten_after_publish(record: dict | None) -> pytest.MonkeyPatch:
    """The run file is overwritten in place, same inode, right after the Job's rewrite is renamed into place and
    before the writer reads its descriptor's version; with no *record*, nothing interleaves."""
    real_replace = Path.replace
    patch = pytest.MonkeyPatch()

    def replace(self: Path, target: Path) -> Path:
        done = real_replace(self, target)
        if record is not None and Path(target).name == pack_state.FILE:
            with Path(target).open("r+", encoding="utf-8") as same:
                same.write(json.dumps(pack_job._blank() | record, indent=1) + "\n")  # noqa: SLF001
                same.truncate()
        return done

    patch.setattr(Path, "replace", replace)
    return patch


@pytest.mark.parametrize("recovered", [False, True], ids=["a-held", "a-recovered"])
def test_a_run_written_over_the_constructors_rewrite_before_its_version_is_read_is_not_receipted_to_it(
    tmp_path, recovered
):
    """Review 4377585375: the rewrite's version is receipted to A only when the file holds A's rewrite at that version.

    B overwrites the file in place between the rename and the writer's own stat: the version the writer got is B's.
    No receipt maps it to A; B is held under its own lease as A's rewrite is restored, and a later stable read of B
    finds that same lease, A as it was.
    """
    root = store(tmp_path, "store", {"state": "running"})  # A: no run id, no start
    patch = overwritten_after_publish({"state": "running", "stage": "update"})  # B: also unidentified
    try:
        job = pack_job.Job(Store(root))
    finally:
        patch.undo()
    first = ledger()
    job.maintenance = first
    session_slots.interrupted(job, "p")
    a = next(s["id"] for s in ledger_sessions(first) if s["generation"] == job.interrupted["generation"])
    assert ([s for i, s in leases(first) if i != a], first.receipted("p", pack_state.digest(job.version))) == (
        ["held"],
        "",
    )  # B held at once; the version is B's, never receipted to A
    if recovered:
        ledger(boot=20.0).recover(a, rebooted=True)
    owner = ledger(boot=20.0)
    session_slots.restore(owner, "p", root)  # B, read whole and stable: the lease it already has
    assert dict(leases(owner))[a] == ("recovered" if recovered else "held")
    assert [s for i, s in leases(owner) if i != a] == ["held"]
    assert owner.slots.take("other", "probe", 1, 2) == (1 if recovered else 0)


def ledger_sessions(owner: maintenance.Maintenance) -> list[dict]:
    return json.loads(owner.path.read_text())["sessions"]


def test_the_constructors_own_rewrite_is_still_receipted_to_its_run_and_read_again_as_it(tmp_path):
    """Control: with nothing interleaving, the rewrite is receipted to A, once, and a reread holds nothing new."""
    root = store(tmp_path, "store", {"state": "running"})
    patch = overwritten_after_publish(None)
    try:
        job = pack_job.Job(Store(root))
    finally:
        patch.undo()
    owner = ledger()
    job.maintenance = owner
    for _ in range(2):
        session_slots.interrupted(job, "p")
    [(a, _state)] = leases(owner)
    assert owner.receipted("p", pack_state.digest(job.version)) == job.interrupted["generation"]
    again = ledger()
    session_slots.restore(again, "p", root)
    assert leases(again) == [(a, "held")]


B_RUN = {"state": "running", "stage": "update"}  # a run with no identity, written once the Job had read the file


def write_record(root: Path, record: dict) -> None:
    (root / pack_state.FILE).write_text(json.dumps(pack_job._blank() | record, indent=1) + "\n")  # noqa: SLF001


def started(job: pack_job.Job) -> maintenance.Maintenance:
    """The Job's startup restoration against a fresh ledger at one slot."""
    owner = maintenance.Maintenance(Slots(lambda: 1), boot=lambda: 10.0, observe=lambda *_args: False)
    job.maintenance = owner
    session_slots.interrupted(job, "p")
    return owner


def test_a_fresh_store_with_no_record_holds_nothing_at_its_startup(tmp_path):
    """Control: no record, then or now: no hold, the slot free."""
    owner = started(pack_job.Job(Store(store(tmp_path, "store"))))
    assert (leases(owner), owner.slots.take("other", "probe", 1, 1)) == ([], 1)


PUBLISHING = {  # a run stopped while it was published: the Job's startup sets it waiting, with no hold of its own
    "state": "running", "run": "pub-a", "started_at": STARTED, "stage": "pull-request",
    "context": {
        "tag": "v9", "why": "Impeccable: v8 to v9", "diff": "", "golden": "", "pins": {}, "manifest": "",
        "notice": "", "baseline": {}, "checkout": {}, "start": {}, "sid": "s",
        "publication": {"root": "/r", "repository": "o/r", "base": "b", "branch": "pack/v9", "body": "the PR text"},
    },
}  # fmt: skip


@pytest.mark.parametrize("snapshot", ["absent", "unreadable", "publishing"])
def test_startup_restores_changed_record_not_constructor_snapshot(tmp_path, snapshot):
    root = store(tmp_path, "store", PUBLISHING if snapshot == "publishing" else None)
    if snapshot == "unreadable":
        (root / pack_state.FILE).write_text("{")
    job = pack_job.Job(Store(root))
    if snapshot == "publishing":
        assert job.state["state"] == "waiting"
    else:
        assert job.version == ("absent" if snapshot == "absent" else "")
    if (root / pack_state.FILE).exists():
        (root / pack_state.FILE).unlink()
    write_record(root, B_RUN)
    owner = started(job)
    assert [s for _, s in leases(owner)] == (["held", "held"] if snapshot == "unreadable" else ["held"])
    assert owner.slots.take("other", "probe", 1, 1) == 0


def test_a_run_observed_at_startup_stays_held_when_the_file_is_gone_before_it_is_restored(tmp_path):
    """Review on c963: what the startup observed is what it restores; a later removal does not erase it."""
    root = store(tmp_path, "store", PUBLISHING)
    job = pack_job.Job(Store(root))
    assert job.state["state"] == "waiting"
    write_record(root, B_RUN)  # B over the publication the Job set waiting
    real_read_fd, reads = pack_run_record.read_fd, []

    def read_then_gone(fd: int) -> tuple[dict, str]:
        got = real_read_fd(fd)
        if not reads:
            reads.append(got)
            (root / pack_state.FILE).unlink()  # gone right after the startup's own read
        return got

    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(pack_run_record, "read_fd", read_then_gone)
        owner = started(job)
    assert (reads[0][0]["stage"], [s for _, s in leases(owner)]) == ("update", ["held"])
    assert owner.slots.take("other", "probe", 1, 1) == 0
