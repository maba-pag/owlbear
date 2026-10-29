"""Update checks (D-01M63CCVRK8ZKFENY9F4A2K11A, D-01M63CD5PR0D5Q5BJS9KTZHVY9): OwlBear, PDS and Impeccable at the start
and each at its own interval; a failure shows after two in a row; offline is unknown, never current."""

import json
import threading
from datetime import UTC, datetime, timedelta
from email.message import Message
from types import SimpleNamespace
from urllib.error import HTTPError

import pytest
from fastapi.testclient import TestClient

from owlbear_delivery_next.impeccable import pack_files, pack_update
from owlbear_delivery_next.local_system import codebase, local_home
from owlbear_delivery_next.machine_host import app, update_checks
from owlbear_delivery_next.machine_host.machine import Machine
from owlbear_delivery_next.machine_host.update_checks import CHECKS, Checks, Failed
from owlbear_delivery_next.project_host import pages
from owlbear_delivery_next.project_host.host import HostRecord
from owlbear_delivery_next.state_store import machine_settings, registry

AUTH = {"authorization": "Bearer " + "t"}  # the token of the record below
FOUND = {"newer": False, "current": "1", "latest": "1", "detail": ""}


class Clock:
    def __init__(self) -> None:
        self.at = datetime(2026, 11, 2, 9, tzinfo=UTC)

    def __call__(self) -> datetime:
        return self.at

    def passes(self, hours: float) -> None:
        self.at += timedelta(hours=hours)


def answering(body: bytes):
    return lambda _url, _seconds: body


def refusing(url: str, _seconds: float) -> bytes:
    raise HTTPError(url, 503, "unavailable", Message(), None)


def offline(url: str, _seconds: float) -> bytes:
    msg = f"no route to {url}"
    raise OSError(msg)


def stub() -> SimpleNamespace:
    """A machine for the checks alone: what they say, and its stop."""
    return SimpleNamespace(say=lambda _line: None, stopping=threading.Event())


def hours(**each: int) -> None:
    """This machine's own interval settings."""
    with registry.locked():
        saved = registry.load()
        saved.settings = saved.settings.model_copy(update={f"update_check_hours_{n}": h for n, h in each.items()})
        registry.save(saved)


def shown(checks: Checks, name: str) -> dict:
    return next(u for u in checks.read()["updates"] if u["name"] == name)


def test_pds_is_newer_unchanged_offline_or_refused_against_the_vendored_release(monkeypatch):
    pinned = pages.pds_version()
    monkeypatch.setattr(pack_files, "fetch", answering(b'{"version": "99.0.0"}'))
    assert update_checks.pds() == {"newer": True, "current": pinned, "latest": "99.0.0", "detail": ""}
    monkeypatch.setattr(pack_files, "fetch", answering(json.dumps({"version": pinned}).encode()))
    assert update_checks.pds()["newer"] is False
    monkeypatch.setattr(pack_files, "fetch", answering(b'{"version": "4.9.10"}'))
    assert update_checks.pds()["newer"] is False  # by number, not by text: 4.9.10 is older than 4.10.1
    for body, said in ((b"[]", "names no version"), (b'{"version": "latest"}', "names no version: latest")):
        monkeypatch.setattr(pack_files, "fetch", answering(body))
        with pytest.raises(Failed, match=said) as failed:
            update_checks.pds()
        assert failed.value.offline is False
    monkeypatch.setattr(pack_files, "fetch", refusing)
    with pytest.raises(Failed, match="npm answered 503 unavailable") as failed:
        update_checks.pds()
    assert failed.value.offline is False
    monkeypatch.setattr(pack_files, "fetch", offline)
    with pytest.raises(Failed, match="npm was not reached") as failed:
        update_checks.pds()
    assert failed.value.offline is True


def test_impeccable_is_one_component_its_notice_kept_for_the_other_pages_and_offline_unknown(monkeypatch):
    pinned = pack_files.manifest()["upstream"]["tag"]
    newer = [{"tag_name": "skill-v998.0.0"}, {"tag_name": "skill-v999.0.0"}, {"tag_name": pinned}]
    monkeypatch.setattr(pack_files, "fetch", answering(json.dumps(newer).encode()))
    found = update_checks.impeccable_skill()
    assert found == {"newer": True, "current": pinned, "latest": "skill-v999.0.0", "detail": "2 newer releases"}
    assert pack_update.said(pack_update.notice(refresh=False)).endswith(": 2 releases behind")
    monkeypatch.setattr(pack_files, "fetch", answering(json.dumps([{"tag_name": pinned}]).encode()))
    assert update_checks.impeccable_skill() == {"newer": False, "current": pinned, "latest": pinned, "detail": ""}
    monkeypatch.setattr(pack_files, "fetch", answering(b'{"message": "rate limited"}'))
    with pytest.raises(Failed, match="no list of releases") as failed:
        update_checks.impeccable_skill()
    assert failed.value.offline is False
    monkeypatch.setattr(pack_files, "fetch", offline)
    with pytest.raises(Failed, match="GitHub was not reached") as failed:
        update_checks.impeccable_skill()
    assert failed.value.offline is True


def test_a_failure_shows_after_two_in_a_row_and_offline_is_never_current(monkeypatch):
    outcomes = iter([
        Failed("npm was not reached", offline=True), Failed("npm was not reached", offline=True), FOUND,
        Failed("npm answered 503", offline=False), Failed("npm answered 503", offline=False),
        FOUND | {"newer": True, "latest": "2"},
    ])  # fmt: skip

    def pds() -> dict:
        outcome = next(outcomes)
        if isinstance(outcome, Failed):
            raise outcome
        return outcome

    monkeypatch.setitem(CHECKS, "pds", pds)
    checks, seen = Checks(stub(), Clock(), lambda work: work()), []
    for _ in range(6):
        checks.start("pds")
        said = shown(checks, "pds")
        seen.append((said["state"], said["reason"], said["failures"]))
    assert seen == [
        ("unknown", "", 1),  # one failure, none found before: unknown, not yet a failure
        ("unknown", "npm was not reached", 2),  # offline twice: unknown with its reason, never current
        ("current", "", 0),
        ("current", "", 1),  # one failure: the last success stands
        ("failed", "npm answered 503", 2),
        ("newer", "", 0),
    ]
    assert checks.read()["available"] == 0  # PDS has no update action yet: it counts once it has
    monkeypatch.setitem(CHECKS, "impeccable", lambda: FOUND | {"newer": True})
    monkeypatch.setitem(CHECKS, "owlbear", lambda: FOUND | {"newer": True})
    for name in ("impeccable", "owlbear"):
        checks.start(name)
    assert checks.read()["available"] == 2  # one per component that can be run, whatever its number of releases
    assert Checks(stub()).read() == checks.read()  # kept across restarts in update-checks.json
    assert json.loads((local_home.root() / update_checks.STATE).read_text())["pds"]["success"]["latest"] == "2"


def test_each_update_is_checked_at_the_start_and_then_only_at_its_own_set_interval(monkeypatch):
    ran: list[str] = []
    for name in CHECKS:
        monkeypatch.setitem(CHECKS, name, lambda name=name: ran.append(name) or FOUND)
    clock, machine = Clock(), stub()
    checks = Checks(machine, clock, lambda work: work())
    machine.stopping.set()  # the loop's start only
    checks.loop()
    assert ran == ["owlbear", "pds", "impeccable"]  # at the start, all three intervals unset
    clock.passes(24 * 30)
    checks.tick()
    assert ran == ["owlbear", "pds", "impeccable"]  # unset: no timed check
    assert [(u["hours"], u["next_at"]) for u in checks.read()["updates"]] == [(None, None)] * 3

    hours(owlbear=6, pds=3)
    ran.clear()
    checks.tick()
    assert ran == ["owlbear", "pds"]  # last checked a month ago; Impeccable's stays unset
    clock.passes(2)
    checks.tick()
    clock.passes(1)
    checks.tick()
    assert ran == ["owlbear", "pds", "pds"]
    clock.passes(3)
    checks.tick()
    assert ran == ["owlbear", "pds", "pds", "owlbear", "pds"]
    assert shown(checks, "pds")["next_at"] == (clock.at + timedelta(hours=3)).isoformat()

    def unreached() -> dict:
        ran.append("pds failed")
        msg = "npm was not reached"
        raise Failed(msg, offline=True)

    monkeypatch.setitem(CHECKS, "pds", unreached)
    hours(pds=24)
    clock.passes(24)
    ran.clear()
    checks.tick()
    clock.passes(1)  # after a failure: again within the hour, not the interval
    checks.tick()
    assert ran == ["owlbear", "pds failed", "pds failed"]


def test_with_its_versions_unset_the_owlbear_check_fails_with_why(monkeypatch):
    monkeypatch.setattr(machine_settings, "BASE", None)
    checks = Checks(stub(), Clock(), lambda work: work())
    for _ in range(2):
        checks.start("owlbear")
    said = shown(checks, "owlbear")
    assert (said["state"], "versions this machine takes are unset" in said["reason"]) == ("failed", True)


@pytest.fixture
def http():
    now = datetime.now(UTC)
    machine = Machine(HostRecord(url="http://127.0.0.1:9/", token="t", pid=1, started_at=now, code=codebase.CURRENT))  # noqa: S106
    machine.checks.spawn = lambda work: work()
    yield TestClient(app.create(machine), base_url="http://127.0.0.1", headers=AUTH)
    machine.stop_all()


def test_search_for_updates_runs_by_hand_while_its_interval_is_unset_and_get_reads_all_three(http):
    assert [(u["name"], u["state"], u["hours"]) for u in http.get("/api/next/updates").json()["updates"]] == [
        ("owlbear", "unknown", None), ("pds", "unknown", None), ("impeccable", "unknown", None),
    ]  # fmt: skip
    for _ in range(2):
        said = http.post("/api/next/updates/pds/check").json()
    pds = next(u for u in said["updates"] if u["name"] == "pds")
    assert (pds["state"], pds["failures"], pds["reason"].startswith("npm was not reached")) == ("unknown", 2, True)
    assert http.get("/api/next/updates").json() == said
    assert http.post("/api/next/updates/nothing/check").status_code == 404
