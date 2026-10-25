import subprocess
import sys

import pytest

from owlbear_delivery_next.state_store import offline_protocol as op
from owlbear_delivery_next.state_store.database import MARKER, STORE_FORMAT, StoreError

BOOT_A = "F045833C-37D3-44BA-A5B0-4E9EAFDBDEFA"
BOOT_B = "11111111-2222-3333-4444-555555555555"
NO_GAPS = ()


def snapshot(folder):
    return {p.name: p.read_bytes() for p in sorted(folder.iterdir()) if p.is_file()}


@pytest.fixture
def folder(tmp_path):
    f = tmp_path / "owlbear-delivery"
    f.mkdir()
    (f / "delivery.db").write_text("db")
    (f / MARKER).write_text(f"{STORE_FORMAT}\n")
    return f


@pytest.fixture
def boot(monkeypatch):
    seen = {"value": BOOT_A}
    monkeypatch.setattr(op, "boot_session", lambda: seen["value"])
    return seen


def test_the_boot_session_is_read_from_the_darwin_facility_and_checked():
    if sys.platform != "darwin":
        pytest.skip("Darwin boot-session facility")
    assert op.UUID.fullmatch(op.boot_session())


def test_a_missing_malformed_or_unreadable_boot_session_refuses(monkeypatch):
    monkeypatch.setattr(sys, "platform", "darwin")
    monkeypatch.setattr(
        subprocess, "run", lambda _argv, **_kw: subprocess.CompletedProcess(_argv, 0, "not-a-uuid\n", "")
    )
    with pytest.raises(StoreError, match="missing or malformed"):
        op.boot_session()
    monkeypatch.setattr(subprocess, "run", lambda _argv, **_kw: subprocess.CompletedProcess(_argv, 1, "", "denied"))
    with pytest.raises(StoreError, match="missing or malformed"):
        op.boot_session()

    def boom(_argv, **_kw):
        msg = "no sysctl"
        raise OSError(msg)

    monkeypatch.setattr(subprocess, "run", boom)
    with pytest.raises(StoreError, match="unreadable"):
        op.boot_session()


def test_a_platform_without_the_facility_refuses(monkeypatch):
    monkeypatch.setattr(sys, "platform", "linux")
    with pytest.raises(StoreError, match="no boot-session facility"):
        op.boot_session()


@pytest.mark.usefixtures("boot")
def test_production_prepare_refuses_on_unfenced_legacy_producers_and_changes_nothing(folder):
    before = snapshot(folder)
    with pytest.raises(StoreError, match="not proven fenced") as err:
        op.prepare(folder)
    assert "binding" in str(err.value)
    assert snapshot(folder) == before
    assert not (folder / op.PREPARED).exists()


def test_prepare_then_reboot_then_finish_binds_the_fence_and_the_folder(folder, boot):
    record = op.prepare(folder, gaps=lambda: NO_GAPS)
    assert record["boot"] == BOOT_A
    assert (folder / MARKER).read_text() == f"{op.FENCE}\n"
    boot["value"] = BOOT_B  # a different boot session, as after a reboot
    proof = op.finish(folder, gaps=lambda: NO_GAPS)
    assert proof.folder == folder


@pytest.mark.usefixtures("boot")
def test_finish_in_the_same_boot_session_refuses_before_any_change(folder):
    op.prepare(folder, gaps=lambda: NO_GAPS)
    before = snapshot(folder)
    with pytest.raises(StoreError, match="reboot before finishing"):
        op.finish(folder, gaps=lambda: NO_GAPS)
    assert snapshot(folder) == before


def test_finish_refuses_a_missing_or_unreadable_boot_session(folder, monkeypatch):
    op.prepare(folder, gaps=lambda: NO_GAPS)
    before = snapshot(folder)
    before = snapshot(folder)

    def unreadable():
        msg = "boot-session UUID is unreadable: refusing the offline move"
        raise StoreError(msg)

    monkeypatch.setattr(op, "boot_session", unreadable)
    with pytest.raises(StoreError, match="unreadable"):
        op.finish(folder, gaps=lambda: NO_GAPS)
    assert snapshot(folder) == before


def test_finish_refuses_when_the_fence_was_altered_or_the_folder_replaced(folder, boot):
    op.prepare(folder, gaps=lambda: NO_GAPS)
    boot["value"] = BOOT_B
    (folder / MARKER).write_text(f"{STORE_FORMAT}\n")  # the fence was removed or edited
    with pytest.raises(StoreError, match="fence on"):
        op.finish(folder, gaps=lambda: NO_GAPS)
    (folder / MARKER).write_text(f"{op.FENCE}\n")
    (folder / op.PREPARED).unlink()
    with pytest.raises(StoreError, match="missing"):
        op.finish(folder, gaps=lambda: NO_GAPS)


def test_finish_refuses_a_replaced_folder_identity(folder, boot, tmp_path):
    op.prepare(folder, gaps=lambda: NO_GAPS)
    boot["value"] = BOOT_B
    moved = tmp_path / "moved"
    folder.rename(moved)
    folder.mkdir()
    (folder / MARKER).write_text(f"{op.FENCE}\n")
    (folder / op.PREPARED).write_text((moved / op.PREPARED).read_text())
    with pytest.raises(StoreError, match="not the folder that was prepared"):
        op.finish(folder, gaps=lambda: NO_GAPS)


def test_finish_refuses_while_any_legacy_producer_is_unfenced(folder, boot):
    op.prepare(folder, gaps=lambda: NO_GAPS)
    boot["value"] = BOOT_B
    before = snapshot(folder)
    with pytest.raises(StoreError, match="not proven fenced"):
        op.finish(folder)  # production inventory
    assert snapshot(folder) == before


def test_a_record_of_another_shape_is_refused(folder):
    (folder / op.PREPARED).write_text('{"boot": "x"}')
    with pytest.raises(StoreError, match="not a preparation record"):
        op.finish(folder, gaps=lambda: NO_GAPS)
