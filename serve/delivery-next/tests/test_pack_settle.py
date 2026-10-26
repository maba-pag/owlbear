"""R04 core for the R16 store copy: a legacy pack record carries its generation into the record before it is copied.

A copy is another file, so a fingerprint taken from it would name another run. ``pack_state.settle`` writes the
generation this host saw into the record itself; the copy keeps it, so the lease already held for it, held or
recovered, still covers it wherever the store now lies. A later record carries none and is held anew.
"""

import json
import shutil
from pathlib import Path

import pytest

from owlbear_delivery_next.local_system import maintenance
from owlbear_delivery_next.local_system.slots import Slots
from owlbear_delivery_next.local_system.storage_io import atomic_write
from owlbear_delivery_next.pack_runs import pack_job, pack_state
from owlbear_delivery_next.project_host import session_slots

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
        (root / pack_state.FILE).write_text(json.dumps(pack_job._blank() | record, indent=1) + "\n")  # noqa: SLF001
    return root


def ledger(boot: float = 10.0) -> maintenance.Maintenance:
    """A host's view of the machine's ledger: each instance is a restart, *boot* the boot it runs in."""
    return maintenance.Maintenance(Slots(lambda: 2), boot=lambda: boot, observe=lambda *_args: False)


def import_at(owner: maintenance.Maintenance, root: Path) -> None:
    """The read-only import of a project whose store lies at *root*, as a host does when it cannot open it."""
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(session_slots.project_home, "current", lambda _repo: root)
        session_slots.unloaded(owner, "p", root)


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
        return pack_state.settle(root, receipted=lambda _digest: "")
    return pack_state.settle(root, receipted=lambda found: owner.receipted("p", found))


@pytest.mark.parametrize("identity", IDENTITIES.values(), ids=IDENTITIES.keys())
def test_settling_a_running_record_carries_its_generation_and_a_second_settle_writes_nothing(tmp_path, identity):
    root = store(tmp_path, "clone", {"state": "running", **identity})
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
    }.items():
        root = store(tmp_path, name, record)
        unchanged = (root / pack_state.FILE).read_bytes()
        assert (settle(root), (root / pack_state.FILE).read_bytes()) == (False, unchanged)
    assert settle(store(tmp_path, "absent")) is False


def test_a_failed_stamp_leaves_the_record_whole_and_a_retry_carries_the_same_generation(tmp_path):
    root = store(tmp_path, "clone", {"state": "running"})
    before, original = pack_state.generation(*pack_state.observed(root))[0], (root / pack_state.FILE).read_bytes()

    def full(*_args: object) -> None:
        msg = "synthetic: disk full"
        raise OSError(msg)

    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(pack_state, "atomic_write", full)
        with pytest.raises(OSError, match="disk full"):
            settle(root)
    assert (root / pack_state.FILE).read_bytes() == original
    assert settle(root) is True
    assert pack_state.read_only(root)[pack_state.REWRITTEN] == before


def test_an_unreadable_record_is_refused_not_taken_for_settled(tmp_path):
    root = store(tmp_path, "clone")
    (root / pack_state.FILE).write_text("{")
    with pytest.raises(ValueError):  # noqa: PT011 - the reader's own refusal of a damaged record
        settle(root)
    assert (root / pack_state.FILE).read_text() == "{"


def held_then_copied(tmp_path: Path, record: dict, *, recovered: bool) -> tuple[Path, Path, str]:
    """Lease A taken read-only at the clone, held or recovered after a reboot; then settled and copied."""
    source = store(tmp_path, "clone", record)
    first = ledger()
    import_at(first, source)
    [(a, _state)] = leases(first)
    if recovered:
        ledger(boot=20.0).recover(a, rebooted=True)
    assert settle(source, first) is True
    return source, copied(source, tmp_path), a


@pytest.mark.parametrize("recovered", [False, True], ids=["held", "recovered"])
@pytest.mark.parametrize(
    "record",
    [{"state": "running", **identity} for identity in IDENTITIES.values()] + [SDK_FAILED],
    ids=[*IDENTITIES.keys(), "sdk-failed"],
)
def test_a_settled_copy_is_the_lease_already_taken_held_or_recovered_across_restarts(tmp_path, record, recovered):
    _source, target, a = held_then_copied(tmp_path, record, recovered=recovered)
    state = "recovered" if recovered else "held"
    for _ in range(2):
        again = ledger(boot=20.0)
        import_at(again, target)
        assert leases(again) == [(a, state)]
        assert again.slots.counts("p")[2] == (0 if recovered else 1)
        assert again.pending("pack") is not recovered


def test_an_unsettled_copy_of_a_record_without_identity_is_another_file_and_held_anew(tmp_path):
    """Why the generation must be carried before the copy: a fingerprint of the copy names another run."""
    source = store(tmp_path, "clone", {"state": "running"})
    owner = ledger()
    import_at(owner, source)
    import_at(owner, copied(source, tmp_path))
    assert [s for _, s in leases(owner)] == ["held", "held"]


@pytest.mark.parametrize("recovered", [False, True], ids=["held", "recovered"])
@pytest.mark.parametrize("later", ["original-bytes", "fresh-running", "new-proven-run"])
def test_a_later_record_after_the_copy_carries_no_generation_and_is_held_anew(tmp_path, recovered, later):
    original = {"state": "running"}
    _source, target, a = held_then_copied(tmp_path, original, recovered=recovered)
    if later == "original-bytes":  # byte for byte the record as it was before it was settled
        (target / pack_state.FILE).write_text(json.dumps(pack_job._blank() | original, indent=1) + "\n")  # noqa: SLF001
    elif later == "fresh-running":
        (target / pack_state.FILE).unlink()
        (target / pack_state.FILE).write_text(json.dumps(pack_job._blank() | {"state": "running"}) + "\n")  # noqa: SLF001
    else:
        later_run = SDK_FAILED | {"run": "main-run-b", "started_at": STARTED}
        (target / pack_state.FILE).write_text(json.dumps(pack_job._blank() | later_run) + "\n")  # noqa: SLF001
    owner = ledger(boot=20.0)
    import_at(owner, target)
    assert leases(owner)[0] == (a, "recovered" if recovered else "held")
    assert [s for _, s in leases(owner)[1:]] == ["held"]


def test_a_proven_run_written_again_by_its_producer_after_settling_is_still_its_lease(tmp_path):
    """main writes every run it starts with its run and start, so a later write of that run keeps its generation."""
    source = store(tmp_path, "clone", {"state": "running", "run": "main-run", "started_at": STARTED})
    first = ledger()
    import_at(first, source)
    [(a, _state)] = leases(first)
    settle(source, first)
    continued = SDK_FAILED | {"run": "main-run", "started_at": STARTED}  # main's own later write: no carried field
    (source / pack_state.FILE).write_text(json.dumps(pack_job._blank() | continued) + "\n")  # noqa: SLF001
    owner = ledger()
    import_at(owner, copied(source, tmp_path))
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
    import_at(owner, root)
    [(a, _state)] = leases(owner)
    g0 = pack_state.generation(*pack_state.observed(root))[0]
    record, _version = pack_state.observed(root)
    pack_state.ended(record, "failed", pack_state.HOST_STOPPED)
    version = pack_state.version_of(atomic_write(root / pack_state.FILE, json.dumps(record, indent=1) + "\n"))
    owner.receipt("p", pack_state.digest(version), g0)
    if recovered:
        ledger(boot=20.0).recover(a, rebooted=True)
    return root, a, g0


@pytest.mark.parametrize("recovered", [False, True], ids=["held", "recovered"])
def test_settling_a_receipted_rewrite_carries_the_receipted_run_so_neither_a_reread_nor_a_copy_holds_it_again(
    tmp_path, recovered
):
    """Review on 7679: settling resolves the generation as restoration does, the receipt for this very version first."""
    root, a, g0 = receipted_rewrite(tmp_path, recovered=recovered)
    state = "recovered" if recovered else "held"
    assert settle(root, ledger(boot=20.0)) is True
    assert pack_state.read_only(root)[pack_state.REWRITTEN] == g0
    for at in (root, copied(root, tmp_path)):  # read again where it is, then from its byte copy
        for _ in range(2):
            again = ledger(boot=20.0)
            import_at(again, at)
            assert leases(again) == [(a, state)]
    later = tmp_path / "home"
    (later / pack_state.FILE).unlink()
    (later / pack_state.FILE).write_text(json.dumps(pack_job._blank() | {"state": "running"}) + "\n")  # noqa: SLF001
    owner = ledger(boot=20.0)
    import_at(owner, later)
    assert [s for _, s in leases(owner)] == [state, "held"]


def test_settling_against_a_ledger_that_cannot_be_read_fails_closed_and_changes_nothing(tmp_path):
    root, _a, _g0 = receipted_rewrite(tmp_path, recovered=False)
    before = (root / pack_state.FILE).read_bytes()
    owner = ledger()
    owner.path.write_text('{"format": 1}')  # its sessions and receipts are missing: not an empty ledger
    with pytest.raises(maintenance.MaintenanceError):
        settle(root, owner)
    assert (root / pack_state.FILE).read_bytes() == before
