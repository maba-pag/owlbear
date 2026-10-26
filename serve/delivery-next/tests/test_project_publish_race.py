"""A project's discovery file is never left behind by a readiness publish that overlaps its stop.

The readiness thread publishes ``host.json`` in three steps: write, then restrict permissions. A stop removes the file.
These tests pause the publisher between the write and the chmod, stop the project meanwhile, then release it.
"""

import json
import subprocess
import threading
from datetime import UTC, datetime
from pathlib import Path

import pytest

from owlbear_delivery_next.local_system import codebase
from owlbear_delivery_next.machine_host import project, registry
from owlbear_delivery_next.machine_host.machine import Machine
from owlbear_delivery_next.project_host.host import Host, HostRecord

WAIT = 10.0


@pytest.fixture(autouse=True)
def home(tmp_path: Path, monkeypatch) -> Path:
    path = tmp_path / "home"
    path.mkdir()
    monkeypatch.setenv("HOME", str(path))
    return path


@pytest.fixture
def thread_errors(monkeypatch) -> list[BaseException]:
    errors: list[BaseException] = []

    def record(args) -> None:
        errors.append(args.exc_value)

    monkeypatch.setattr(threading, "excepthook", record)
    return errors


@pytest.fixture
def machine(monkeypatch):
    monkeypatch.setattr(Host, "_spawn", lambda _self, slug: pytest.fail(f"no runner starts in these tests ({slug})"))
    record = HostRecord(
        url="http://127.0.0.1:9/",
        token="t",  # noqa: S106
        pid=1,
        started_at=datetime.now(UTC),
        code=codebase.CURRENT,
    )
    m = Machine(record)
    m.slots.total = lambda: 1
    yield m
    m.stop_all()


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    path = (tmp_path / "shop").resolve()
    for args in (["init", "-q", str(path)], ["-C", str(path), "commit", "-q", "--allow-empty", "-m", "i"]):
        subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t", *args], check=True)  # noqa: S603, S607
    return path


def _loaded(machine: Machine, repo: Path, monkeypatch, ready_go: threading.Event):
    """Load the project with its readiness check held until *ready_go* is set, so its publish is the one under test."""

    def held_ready(_store, _repo) -> list:
        ready_go.wait(WAIT)
        return []

    monkeypatch.setattr(project.readiness, "ready", held_ready)
    entry = registry.register(repo)
    machine.load_all()
    p = machine.projects[entry.id]
    assert p.state == "loaded", p.reason
    return p


def _host_json(p) -> Path:
    return p.store.root / "host.json"


def test_a_healthy_project_publishes_its_discovery_file_on_load_and_removes_it_on_stop(
    machine, repo, monkeypatch, thread_errors
):
    ready_go = threading.Event()
    ready_go.set()
    p = _loaded(machine, repo, monkeypatch, ready_go)
    assert p.scheduler is not None
    for t in [t for t in threading.enumerate() if t.name == f"readiness-{p.entry.id}"]:
        t.join(WAIT)
    assert json.loads(_host_json(p).read_text())["project"] == p.entry.id
    assert p.stop(drain=0) == []
    assert not _host_json(p).exists()
    assert p.state == "stopped"
    assert thread_errors == []


def test_a_stop_during_a_publish_paused_after_the_write_leaves_no_discovery_file_and_no_thread_error(
    machine, repo, monkeypatch, thread_errors
):
    written, resume, stop_attempted = threading.Event(), threading.Event(), threading.Event()
    real_write = project.atomic_write
    pauses: list[str] = []

    def paused_write(path, text) -> None:
        real_write(path, text)
        if threading.current_thread().name.startswith("readiness-"):  # the publish under test, not load's own write
            pauses.append(path.name)
            written.set()
            assert resume.wait(WAIT), "the test never released the paused publisher"

    ready_go = threading.Event()
    monkeypatch.setattr(project, "atomic_write", paused_write)
    p = _loaded(machine, repo, monkeypatch, ready_go)
    assert not written.is_set()
    stopper = threading.Thread(target=p.stop, kwargs={"drain": 0}, daemon=True)
    publish_lock = p.publish_lock

    class ObservedLock:
        def __enter__(self):
            if threading.current_thread() is stopper:
                stop_attempted.set()
            return publish_lock.__enter__()

        def __exit__(self, *args):
            return publish_lock.__exit__(*args)

    monkeypatch.setattr(p, "publish_lock", ObservedLock())
    try:
        ready_go.set()
        assert written.wait(WAIT), "the readiness publish never reached the pause after its write"
        assert pauses == ["host.json"]
        stopper.start()
        assert stop_attempted.wait(WAIT), "stop never attempted the publication mutex"
        assert p.host is not None
        assert p.host.stopped.is_set()
        assert stopper.is_alive(), "the removal must wait for the publish holding the lock"
    finally:
        resume.set()
        if stopper.ident is not None:
            stopper.join(WAIT)
        ready_threads = [t for t in threading.enumerate() if t.name == f"readiness-{p.entry.id}"]
        for thread in ready_threads:
            thread.join(WAIT)
    assert not any(thread.is_alive() for thread in ready_threads)
    assert not stopper.is_alive()
    assert thread_errors == []
    assert not _host_json(p).exists()
    assert p.state == "stopped"


def test_a_late_publish_after_the_stop_writes_nothing(machine, repo, monkeypatch, thread_errors):
    ready_go = threading.Event()
    ready_go.set()
    p = _loaded(machine, repo, monkeypatch, ready_go)
    for t in [t for t in threading.enumerate() if t.name == f"readiness-{p.entry.id}"]:
        t.join(WAIT)
    assert p.stop(drain=0) == []
    assert not _host_json(p).exists()

    late = threading.Thread(target=p._ready, daemon=True)  # noqa: SLF001
    late.start()
    late.join(WAIT)
    assert not late.is_alive()
    assert thread_errors == []
    assert not _host_json(p).exists()
