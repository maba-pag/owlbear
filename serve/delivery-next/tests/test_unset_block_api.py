"""The machine's API names each project's block and starts no work for a blocked project (#808).

One machine host serves two registered clones over its real app; the shared repository and GitHub are local fakes,
and only the chat launch is recorded instead of opening VS Code.
"""

from __future__ import annotations

import contextlib
import subprocess
import threading
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING

import pytest
from fastapi.testclient import TestClient

from owlbear_delivery_next.local_system import codebase, local_home
from owlbear_delivery_next.machine_host import app, project
from owlbear_delivery_next.machine_host.machine import Machine
from owlbear_delivery_next.project_host import api
from owlbear_delivery_next.project_host.host import Host, HostRecord
from owlbear_delivery_next.settings import config
from owlbear_delivery_next.settings.config import Layer, Prefs
from owlbear_delivery_next.state_store import machine_settings, registry
from owlbear_delivery_next.state_store.backlog import Backlog
from owlbear_delivery_next.workflow_steps import curation

if TYPE_CHECKING:
    from owlbear_delivery_next.state_store.store import Store

AUTH = {"authorization": "Bearer t"}
GAP = "prefs.ci_poll_seconds"
UNSET = f"settings unset: {GAP}; fill them in on the Settings page"


def _clone(path: Path) -> Path:
    """A clone whose ``main`` holds one package of tests, so a test review can start in it."""
    (path / "tests").mkdir(parents=True)
    (path / "pyproject.toml").write_text("")
    (path / "tests" / "test_a.py").write_text("a\n" * 3)
    for args in (["init", "-q", "-b", "main"], ["add", "-A"], ["commit", "-qm", "base"]):
        subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t", *args], cwd=path, check=True,  # noqa: S603, S607
                       capture_output=True)  # fmt: skip
    return path.resolve()


@dataclass
class Host2:
    """One machine host's app, its machine and the clones a shaping chat was launched in."""

    client: TestClient
    machine: Machine
    launched: list[Path]

    def store(self, pid: str) -> Store:
        st = self.machine.projects[pid].store
        assert st is not None
        return st


@pytest.fixture
def host(monkeypatch):
    """The launch boundary is recorded instead of opening VS Code, replaced before any project's app is made."""
    launched: list[Path] = []

    def launch(repo, _shaper, _prompt) -> dict[str, str]:
        launched.append(repo)
        return {"state": "open"}

    monkeypatch.setitem(api.create_app.__kwdefaults__, "launch", launch)
    monkeypatch.setitem(api.create_app.__kwdefaults__, "which", lambda _n: "/bin/code")
    monkeypatch.setattr(project.readiness, "ready", lambda _store, _repo, **_kwargs: [])
    monkeypatch.setattr(Host, "_spawn", lambda _self, slug: pytest.fail(f"no runner starts in these tests ({slug})"))
    record = HostRecord(url="http://127.0.0.1:9/", token="t", pid=1, started_at=datetime.now(UTC),  # noqa: S106
                        code=codebase.CURRENT)  # fmt: skip
    m = Machine(record)
    try:
        yield Host2(TestClient(app.create(m), base_url="http://127.0.0.1", headers=AUTH), m, launched)
    finally:
        m.stop_all()


@pytest.fixture
def a_b(tmp_path, monkeypatch, shared_repo, host) -> tuple[str, str]:
    """Projects A and B registered on one machine; A's own layer leaves the CI poll interval unset, B's sets it."""
    prefs = config.BASE.prefs.model_copy(update={"ci_poll_seconds": None})
    monkeypatch.setattr(config, "BASE", config.BASE.model_copy(update={"prefs": prefs}))
    monkeypatch.setenv("OWLBEAR_DATA", str(shared_repo[0]))
    ids = []
    for name in ("a", "b"):
        r = host.client.post("/api/next/projects", json={"path": str(_clone(tmp_path / name))})
        assert r.status_code == 200, r.text
        ids.append(r.json()["id"])
    a, b = (host.store(pid) for pid in ids)
    assert a.save(a.config_path, Layer, lambda la: la.model_copy(update={"prefs": Prefs()}), "t", owner=True) == ""
    assert b.save(b.config_path, Layer, lambda la: la.model_copy(update={"prefs": Prefs(ci_poll_seconds=20)}), "t",
                  owner=True) == ""  # fmt: skip
    assert (a.settings().missing, b.settings().missing, machine_settings.current().missing) == ([GAP], [], [])
    return ids[0], ids[1]


def _unset(store: Store) -> None:
    said = store.save(store.config_path, Layer, lambda la: la.model_copy(update={"prefs": Prefs()}), "t", owner=True)
    assert said == ""  # the CI poll interval is unset again


def _listed(client: TestClient) -> dict[str, dict]:
    r = client.get("/api/next/projects")
    assert r.status_code == 200, r.text
    return {p["id"]: p for p in r.json()["projects"]}


def test_the_project_list_names_each_block_also_with_a_broken_layer_or_registry(host, a_b) -> None:
    a, b = a_b
    listed = _listed(host.client)
    assert [(listed[p]["unset"], listed[p]["unset_reason"]) for p in (a, b)] == [([GAP], ""), ([], "")]
    assert [listed[p]["blocked"] for p in (a, b)] == [f"settings unset: {GAP}; fill them in on the Settings page", ""]

    host.store(a).config_path.write_text("{")
    listed = _listed(host.client)
    assert (listed[a]["unset"], listed[a]["unset_reason"]) == ([], "state of config is unreadable")
    assert listed[a]["blocked"] == "settings can't be read: state of config is unreadable"
    assert (listed[b]["unset"], listed[b]["unset_reason"]) == ([], "")

    (local_home.root() / registry.MACHINE).write_text("{")
    listed = _listed(host.client)
    assert all(listed[p]["unset_reason"] for p in (a, b))  # this machine's settings can't be read: both wait


def test_the_curation_list_names_each_folders_block(host, shared_repo, a_b) -> None:
    names = [host.store(p).name for p in a_b]
    for name in names:
        (shared_repo[0] / name / "memory").mkdir(parents=True, exist_ok=True)
    rows = {f["folder"]: f["blocked"] for f in host.client.get("/api/next/curation").json()["folders"]}
    assert (rows[names[0]], rows[names[1]]) == (UNSET, "")


@pytest.mark.usefixtures("github")
def test_new_change_and_a_backlog_change_start_no_chat_for_a_blocked_project(host, a_b) -> None:
    client, (a, b) = host.client, a_b
    entry = Backlog.of(host.store(a)).add("Wider status line")[0]

    refused = [
        client.post(f"/p/{a}/api/next/new-change").json(),
        client.post(f"/p/{a}/api/next/backlog/change", json={"ids": [entry.id]}).json(),
    ]
    assert [(r["started"], r["reason"], "command" in r) for r in refused] == [(False, UNSET, False)] * 2
    assert host.launched == []

    started = client.post(f"/p/{b}/api/next/new-change").json()
    assert started["started"] is True
    for _ in range(250):
        if host.launched:
            break
        time.sleep(0.02)
    assert host.launched == [Path(host.machine.projects[b].entry.path)]


def test_a_test_review_for_a_blocked_project_is_refused_before_any_change_exists(host, a_b) -> None:
    client, (a, b) = host.client, a_b
    refused = client.post(f"/p/{a}/api/next/maintenance/test-review", json={"packages": ["."]})
    assert (refused.status_code, refused.json()["detail"]) == (409, UNSET)
    assert client.get(f"/p/{a}/api/next/changes").json() == []

    started = client.post(f"/p/{b}/api/next/maintenance/test-review", json={"packages": ["."]})
    assert started.status_code == 200, started.text
    assert [c["slug"] for c in client.get(f"/p/{b}/api/next/changes").json()] == [started.json()["slug"]]


@pytest.mark.usefixtures("github")
def test_a_setting_unset_while_new_change_waits_for_the_launch_lock_opens_no_chat(host, a_b, monkeypatch) -> None:
    b, admitted = a_b[1], api.admitted

    @contextlib.contextmanager
    def late(h):  # the owner unsets it after the first check, while the request waits for the lock
        _unset(host.store(b))
        with admitted(h):
            yield

    monkeypatch.setattr(api, "admitted", late)
    assert host.client.post(f"/p/{b}/api/next/new-change").json() == {"started": False, "reason": UNSET}
    time.sleep(0.2)
    assert host.launched == []


def test_a_setting_unset_while_a_test_review_waits_for_its_turn_starts_no_change(host, a_b, monkeypatch) -> None:
    b, lock = a_b[1], threading.Lock()

    class Late:
        def __enter__(self) -> None:  # the owner unsets it while the start waits for the one before it
            _unset(host.store(b))
            lock.acquire()

        def __exit__(self, *_: object) -> None:
            lock.release()

    monkeypatch.setattr(curation, "STARTING", Late())
    refused = host.client.post(f"/p/{b}/api/next/maintenance/test-review", json={"packages": ["."]})
    assert (refused.status_code, refused.json()["detail"]) == (409, UNSET)
    assert host.client.get(f"/p/{b}/api/next/changes").json() == []
