"""Update checks (D-01M63CCVRK8ZKFENY9F4A2K11A, D-01M63CD5PR0D5Q5BJS9KTZHVY9): OwlBear, PDS and Impeccable at the start
and each at its own interval; a failure shows after two in a row; offline is unknown, never current."""

import json
import threading
import time
from datetime import UTC, datetime, timedelta
from email.message import Message
from pathlib import Path
from types import SimpleNamespace
from urllib.error import HTTPError

import pytest
from fastapi.testclient import TestClient

from owlbear_delivery_next.impeccable import pack_files, pack_update
from owlbear_delivery_next.local_system import codebase, local_home
from owlbear_delivery_next.machine_host import app, impeccable, update_checks, versions
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


def outcomes(monkeypatch, name: str, *each: dict | Failed) -> None:
    """*name*'s check answers *each* in turn; the installed versions are 1.0.0, OwlBear's v1."""
    for n in CHECKS:
        monkeypatch.setitem(update_checks.INSTALLED, n, lambda n=n: "v1" if n == "owlbear" else "1.0.0")
    answers = iter(each)

    def check() -> dict:
        outcome = next(answers)
        if isinstance(outcome, Failed):
            raise outcome
        return outcome

    monkeypatch.setitem(CHECKS, name, check)


UNREACHED, REFUSED = Failed("npm was not reached", offline=True), Failed("npm answered 503", offline=False)
CURRENT = {"newer": False, "current": "1.0.0", "latest": "1.0.0", "detail": ""}
NEWER = {"newer": True, "current": "1.0.0", "latest": "2.0.0", "detail": ""}


def seen(checks: Checks, name: str, times: int) -> list[tuple]:
    said = []
    for _ in range(times):
        checks.start(name)
        u = shown(checks, name)
        said.append((u["state"], u["reason"], u["failures"], u["available"]))
    return said


def test_a_failure_shows_after_two_in_a_row_and_offline_is_never_current(monkeypatch):
    outcomes(monkeypatch, "impeccable", UNREACHED, UNREACHED, CURRENT, UNREACHED, CURRENT, REFUSED, REFUSED, NEWER)
    checks = Checks(stub(), Clock(), lambda work: work())
    assert seen(checks, "impeccable", 8) == [
        ("unknown", "", 1, False),  # one failure, none found before: unknown, its reason not yet shown
        ("unknown", "npm was not reached", 2, False),  # offline twice: unknown with its reason
        ("current", "", 0, False),
        ("unknown", "", 1, False),  # offline after a success: unknown at once, never current (Sol F1)
        ("current", "", 0, False),
        ("current", "", 1, False),  # refused once: the last success stands
        ("failed", "npm answered 503", 2, False),
        ("newer", "", 0, True),
    ]
    assert Checks(stub()).read() == checks.read()  # kept across restarts in update-checks.json
    assert (
        json.loads((local_home.root() / update_checks.STATE).read_text())["impeccable"]["success"]["latest"] == "2.0.0"
    )


def test_a_newer_version_stays_available_through_failures_until_withdrawn_or_applied(monkeypatch):
    """Commitment 15: the mark clears when the update is applied or no longer offered; a failed check says neither."""
    outcomes(monkeypatch, "impeccable", NEWER, REFUSED, REFUSED, UNREACHED, CURRENT)
    checks = Checks(stub(), Clock(), lambda work: work())
    assert [s[0::3] for s in seen(checks, "impeccable", 5)] == [
        ("newer", True), ("newer", True), ("failed", True), ("unknown", True), ("current", False),
    ]  # Sol F2  # fmt: skip

    outcomes(monkeypatch, "impeccable", NEWER, UNREACHED)
    seen(checks, "impeccable", 1)
    monkeypatch.setitem(update_checks.INSTALLED, "impeccable", lambda: "2.0.0")  # applied, then a launch offline
    said = seen(checks, "impeccable", 1)[0]
    assert said == ("unknown", "", 1, False)  # Sol F3: never offers what is installed, never says current offline
    assert (shown(checks, "impeccable")["current"], checks.read()["available"]) == ("2.0.0", 0)


def test_available_counts_each_runnable_component_once_and_pds_not_yet(monkeypatch):
    checks = Checks(stub(), Clock(), lambda work: work())
    outcomes(monkeypatch, "pds", NEWER)
    seen(checks, "pds", 1)
    assert (shown(checks, "pds")["state"], checks.read()["available"]) == ("newer", 0)  # no PDS update action yet
    outcomes(monkeypatch, "impeccable", NEWER | {"detail": "5 newer releases"})
    outcomes(monkeypatch, "owlbear", {"newer": True, "current": "v1", "latest": "v3", "detail": "", "channel": "minor"})
    for name in ("impeccable", "owlbear"):
        checks.start(name)
    assert checks.read()["available"] == 2  # one per component that can be run, whatever its number of releases


def test_each_update_is_checked_at_the_start_and_then_only_at_its_own_set_interval(monkeypatch):
    ran: list[str] = []
    for name in CHECKS:
        monkeypatch.setitem(CHECKS, name, lambda name=name: ran.append(name) or FOUND)
    clock, machine = Clock(), stub()
    checks = Checks(machine, clock, lambda work: work())
    monkeypatch.setattr(machine.stopping, "wait", lambda _seconds: True)  # the loop's start only
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


def channel(name: str) -> None:
    with registry.locked():
        saved = registry.load()
        saved.settings = saved.settings.model_copy(update={"channel": name})
        registry.save(saved)


def test_an_owlbear_version_found_on_another_channel_is_unknown_until_checked_again(monkeypatch):
    """A channel change can withdraw the version found; with its interval unset it would otherwise stay offered."""
    channel("minor")
    minor = {"newer": True, "current": "v1", "latest": "v1.1", "detail": "", "channel": "minor"}
    outcomes(monkeypatch, "owlbear", minor, minor | {"newer": False, "latest": "v1", "channel": "major"})
    checks = Checks(stub(), Clock(), lambda work: work())
    checks.start("owlbear")
    assert (shown(checks, "owlbear")["state"], checks.read()["available"]) == ("newer", 1)
    channel("major")
    said = shown(checks, "owlbear")
    assert (said["state"], said["latest"], said["detail"], checks.read()["available"]) == (
        "unknown", "v1", "the update channel changed since the last check", 0,
    )  # fmt: skip
    checks.start("owlbear")
    assert (shown(checks, "owlbear")["state"], checks.read()["available"]) == ("current", 0)


def test_with_its_versions_unset_the_owlbear_check_fails_with_why(monkeypatch):
    monkeypatch.setattr(machine_settings, "BASE", None)
    checks = Checks(stub(), Clock(), lambda work: work())
    for _ in range(2):
        checks.start("owlbear")
    said = shown(checks, "owlbear")
    assert (said["state"], "versions this machine takes are unset" in said["reason"]) == ("failed", True)


def homes(tmp_path, monkeypatch) -> tuple[Path, Path]:
    """Two homes, the first in use: the second stands for the one a test's teardown puts back (#804)."""
    a, b = tmp_path / "a" / ".owlbear", tmp_path / "b" / ".owlbear"
    for home in (a, b):
        home.mkdir(parents=True)
    move(monkeypatch, a)
    return a, b


def move(monkeypatch, home: Path) -> None:
    monkeypatch.setattr(local_home, "root", lambda: home)
    monkeypatch.setenv("HOME", str(home.parent))


def workers() -> list[threading.Thread]:
    return [t for t in threading.enumerate() if t.name == "update-check"]


def test_a_check_ending_after_its_home_moved_writes_only_in_the_home_its_host_started_with(tmp_path, monkeypatch):
    """#804: a worker still fetching when a test's teardown puts the real home back wrote into it when it ended."""
    a, b = homes(tmp_path, monkeypatch)
    entered, release = threading.Event(), threading.Event()

    def fetching(_channel=None):
        entered.set()
        release.wait(10)
        msg = "offline"
        raise versions.VersionError(msg)

    monkeypatch.setattr(versions, "target", fetching)
    checks = Checks(stub())  # its own worker threads, as the host's
    assert checks.start("owlbear")
    assert entered.wait(5)
    move(monkeypatch, b)  # the teardown
    release.set()
    for t in workers():
        t.join(10)
    assert not workers()
    released = Path(pack_files.PACKS) / impeccable.RELEASED
    assert [(home / f).exists() for home in (b, a) for f in (update_checks.STATE, released)] == [False] * 2 + [True] * 2
    assert json.loads((a / update_checks.STATE).read_text())["owlbear"]["failures"] == 1


def test_the_hosts_stop_waits_a_while_for_its_checks_and_then_starts_none(tmp_path, monkeypatch):
    """#804: the stop waits up to DRAIN for the checks, says when one did not end, and starts no check after it."""
    _a, b = homes(tmp_path, monkeypatch)
    release, entered, ran = threading.Event(), {n: threading.Event() for n in ("pds", "impeccable")}, []

    def blocked(name: str):
        def check() -> dict:
            ran.append(name)
            entered[name].set()
            release.wait(10)
            return FOUND

        return check

    for name in CHECKS:
        monkeypatch.setitem(CHECKS, name, blocked(name))
    monkeypatch.setattr(update_checks, "DRAIN", 1.0)
    now = datetime.now(UTC)
    machine = Machine(HostRecord(url="http://127.0.0.1:9/", token="t", pid=1, started_at=now, code=codebase.CURRENT))  # noqa: S106
    said: list[str] = []
    machine.say = said.append
    try:
        assert (machine.checks.start("pds"), machine.checks.start("impeccable")) == (True, True)
        assert all(e.wait(5) for e in entered.values())
        assert not machine.checks.start("pds")  # being checked
        began = time.monotonic()
        machine.stop_all()
        took = time.monotonic() - began
        assert 0.9 <= took < 1.8, took
        assert any("the update checks did not end within 1 s" in line for line in said)
        assert not machine.checks.start("owlbear")  # stopping
        move(monkeypatch, b)
        release.set()
        assert machine.checks.drain(5)
        assert sorted(ran) == ["impeccable", "pds"]  # once each; OwlBear's never started
        assert not (b / update_checks.STATE).exists()
    finally:
        release.set()
        for t in workers():
            t.join(10)


def test_a_check_whose_record_cannot_be_written_still_ends_and_says_why(monkeypatch):
    def refused(path, _text):
        msg = f"read-only: {path}"
        raise OSError(msg)

    said: list[str] = []
    machine = stub()
    machine.say = said.append
    monkeypatch.setattr(update_checks, "atomic_write", refused)
    outcomes(monkeypatch, "pds", NEWER)
    checks = Checks(machine, Clock(), lambda work: work())
    assert checks.start("pds")
    assert (shown(checks, "pds")["state"], shown(checks, "pds")["checking"]) == ("newer", False)
    assert any("could not be written: read-only" in line for line in said)


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
