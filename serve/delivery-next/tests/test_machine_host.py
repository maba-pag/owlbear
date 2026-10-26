import asyncio
import io
import json
import os
import re
import signal
import subprocess
import threading
import time
import urllib.error
import urllib.parse
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace

import psutil
import pytest
import uvicorn
from fastapi.testclient import TestClient

from owlbear_delivery_next.change_contracts.chat_contract import HostFound
from owlbear_delivery_next.change_contracts.decision_records import DecisionBaseline
from owlbear_delivery_next.change_contracts.models import Change, Environment, Step, StepKind
from owlbear_delivery_next.commands import chat_client, cli, mcp_server, replay_client, setup
from owlbear_delivery_next.local_system import codebase, maintenance
from owlbear_delivery_next.local_system.data_repo import DataRepo
from owlbear_delivery_next.machine_host import app, project, serve
from owlbear_delivery_next.machine_host.machine import Machine
from owlbear_delivery_next.pack_runs import pack_job, pack_replay, pack_run
from owlbear_delivery_next.project_host import api
from owlbear_delivery_next.project_host.host import ENDING, Host, HostRecord, RunnerRecord, running
from owlbear_delivery_next.state_store import decision_store, project_home, registry
from owlbear_delivery_next.state_store.store import Store

AUTH = {"authorization": "Bearer t"}


def clone(path: Path) -> Path:
    for args in (["init", "-q", str(path)], ["-C", str(path), "commit", "-q", "--allow-empty", "-m", "i"]):
        subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t", *args], check=True)  # noqa: S603, S607
    return path.resolve()


@pytest.fixture
def machine(monkeypatch):
    monkeypatch.setattr(project.readiness, "ready", lambda _store, _repo: [])
    monkeypatch.setattr(Host, "_spawn", lambda _self, slug: pytest.fail(f"no runner starts in these tests ({slug})"))
    now = datetime.now(UTC)
    record = HostRecord(url="http://127.0.0.1:9/", token="t", pid=1, started_at=now, code=codebase.CURRENT)  # noqa: S106
    m = Machine(record)
    yield m
    m.stop_all()


@pytest.fixture
def http(machine):
    return TestClient(app.create(machine), base_url="http://127.0.0.1", headers=AUTH)


def add(http, path: Path) -> dict:
    r = http.post("/api/next/projects", json={"path": str(path)})
    assert r.status_code == 200, r.text
    return r.json()


def test_one_host_serves_each_project_under_its_id_and_each_clone_finds_it(tmp_path, http, machine):
    a, b = add(http, clone(tmp_path / "a")), add(http, clone(tmp_path / "b"))
    listed = http.get("/api/next/projects").json()
    assert (listed["paused"], [(p["name"], p["state"]) for p in listed["projects"]]) == (
        True, [("a", "loaded"), ("b", "loaded")]
    )  # fmt: skip
    for p in (a, b):
        assert http.get(f"/p/{p['id']}/api/next/changes").json() == []
        rec = running(Store.open(Path(p["path"])))
        assert (rec.url, rec.token, rec.project, rec.pid) == ("http://127.0.0.1:9/", "t", p["id"], os.getpid())
        assert api.link(rec) == f"http://127.0.0.1:9/?project={p['id']}#token=t"
    assert http.get("/p/0123456789abcdef/api/next/changes").json() == {"detail": "no such project"}
    assert TestClient(http.app, base_url="http://127.0.0.1").get(f"/p/{a['id']}/api/next/changes").status_code == 401
    assert http.get(f"/p/{a['id']}/api/next/changes", headers={"host": "evil.test"}).status_code == 403
    second = project.Project(registry.load().projects[0])  # a per-clone host can never start beside it
    second.load(machine.record, lambda: True)
    assert (second.state, second.reason) == (
        "failed",
        f"another Delivery host (process {os.getpid()}) serves it; stop that one",
    )
    assert second.store is not None  # its layer still counts for this machine's settings (TD-336)


def test_the_chat_server_calls_its_projects_api_on_the_machine_host(tmp_path, http, monkeypatch):
    p = add(http, clone(tmp_path / "a"))
    sent = []

    class Answer(io.BytesIO):
        status = 200

    class Opener:
        def open(self, request, **_kw):
            sent.append((request.full_url, request.headers.get("X-owlbear-chat")))
            if request.full_url.endswith("/chat/contract"):
                return Answer(b'{"supported": [1]}')
            raise OSError

    monkeypatch.setattr(chat_client, "_LOCAL", Opener())
    chat = chat_client.workspace(Path(p["path"]))
    chat.call("GET", "/changes")
    assert sent == [("http://127.0.0.1:9/api/next/chat/contract", "1"),
                    (f"http://127.0.0.1:9/p/{p['id']}/api/next/changes", "1")]  # fmt: skip


class Answer(io.BytesIO):
    def __init__(self, data: bytes, status: int) -> None:
        super().__init__(data)
        self.status = status


class Loopback:
    """The chat server's opener, answered in-process by the machine host."""

    def __init__(self, http: TestClient, replied=lambda *_a: None) -> None:
        self.http, self.replied = http, replied

    def open(self, request, **_kw):
        url = urllib.parse.urlsplit(request.full_url)
        r = self.http.request(request.get_method(), f"{url.path}?{url.query}", content=request.data,
                              headers=dict(request.header_items()))  # fmt: skip
        if r.status_code >= 400:
            raise urllib.error.HTTPError(request.full_url, r.status_code, "", r.headers, io.BytesIO(r.content))
        self.replied(request.get_method(), url.path, r.json())
        return Answer(r.content, r.status_code)


def chat_tool(name: str, **args: object) -> dict:
    return asyncio.run(mcp_server.mcp.call_tool(name, args)).structured_content


def origin(path: Path, url: str) -> Path:
    subprocess.run(["git", "-C", str(path), "remote", "add", "origin", url], check=True)  # noqa: S603, S607
    return path


def test_a_decision_confirmed_in_owlbears_unregistered_workspace_is_in_force_and_found_from_a_project(  # noqa: PLR0913, PLR0917 - its fixtures
    tmp_path, http, machine, shared_repo, monkeypatch, chat_replied
):
    """TD-435, TD-450: a chat server on OwlBear's own clone writes OwlBear's folder through the machine host."""
    (shared_repo[0] / "owlbear").mkdir()
    monkeypatch.setenv("OWLBEAR_DATA", str(shared_repo[0]))
    monkeypatch.setattr(chat_client.OwlBear, "record", lambda _self: machine.record)
    monkeypatch.setattr(chat_client, "_LOCAL", Loopback(http, chat_replied))
    p = add(http, clone(tmp_path / "shop"))
    own = origin(clone(tmp_path / "owlbear"), "https://github.com/maba-pag/owlbear.git")
    monkeypatch.setitem(mcp_server._STATE, "chat", chat_client.workspace(own))  # noqa: SLF001 - the server's chat

    got = chat_tool("record_decision", title="Pages", statement="Pages are plain HTML.", confirmed=True)

    saved = decision_store.load(DataRepo(shared_repo[0]), "owlbear").snapshot.get(got["receipts"][0]["id"]).decision
    assert (saved.project, str(saved.state), str(saved.origin)) == ("owlbear", "in_force", "decided")
    assert chat_tool("show_status") == {"error": chat_client.NO_CHANGES}
    assert not (own / ".git" / "owlbear-delivery").exists()  # OwlBear's repository stays unregistered
    monkeypatch.setitem(mcp_server._STATE, "chat", chat_client.workspace(Path(p["path"])))  # noqa: SLF001
    assert [d["title"] for d in chat_tool("find_decisions", where="owlbear")["decisions"]] == ["Pages"]
    machine.updating = "an update runs"  # fenced as a project's API is
    refused = http.post("/api/next/owlbear/decisions/propose", json={"title": "x", "statement": "x"})
    assert refused.status_code == 503


def test_only_the_registry_makes_a_clone_a_project_never_an_id_and_folder_left_behind(tmp_path, http):
    """TD-435: OwlBear's clone with a leftover clone id and project folder still gets OwlBear's own tools."""
    own = origin(clone(tmp_path / "owlbear"), "https://github.com/maba-pag/owlbear.git")
    pid = project_home.ensure_id(project_home.clone_dir(own))
    project_home.home(pid).mkdir(parents=True)
    p = add(http, clone(tmp_path / "shop"))

    assert type(chat_client.workspace(own)) is chat_client.OwlBear
    assert type(chat_client.workspace(Path(p["path"]))) is chat_client.Chat


def test_a_folder_that_is_no_owlbear_project_gets_every_tool_refused_and_nothing_written(
    tmp_path, shared_repo, monkeypatch, http, machine
):
    monkeypatch.setenv("OWLBEAR_DATA", str(shared_repo[0]))
    other = origin(clone(tmp_path / "other"), "https://github.com/acme/other.git")
    head = DataRepo(shared_repo[0]).git("rev-parse", "HEAD").stdout
    monkeypatch.setitem(mcp_server._STATE, "chat", chat_client.workspace(other))  # noqa: SLF001 - the server's chat

    said = [chat_tool("record_decision", title="x", statement="x", confirmed=True), chat_tool("find_decisions"),
            chat_tool("retire_decision", decision="x", revision="0" * 64, reason="r", confirmed=True),
            chat_tool("show_status")]  # fmt: skip

    assert said == [{"error": chat_client.NOT_OWLBEAR.format(repo=other)}] * 4
    monkeypatch.setattr(chat_client.OwlBear, "record", lambda _self: machine.record)
    monkeypatch.setattr(chat_client, "_LOCAL", Loopback(http))
    monkeypatch.setattr(chat_client.chat_contract, "CHAT", 0)  # a contract this host does not serve
    own = origin(clone(tmp_path / "owlbear"), "https://github.com/maba-pag/owlbear.git")
    monkeypatch.setitem(mcp_server._STATE, "chat", chat_client.workspace(own))  # noqa: SLF001
    stale = chat_tool("find_decisions")["error"]
    for message in (said[0]["error"], stale):  # only the chat's own server needs a fresh start
        assert "new Copilot-runtime chat" in message
        assert "MCP: List Servers → owlbear-delivery → Stop Server, then Start Server" in message
        assert "Restart Local Agent Host" not in message
    unsupported = "OwlBear does not serve this chat's owlbear-delivery server (chat contract 0; it serves 1)"
    assert stale.startswith(unsupported)  # the chat asks the host's contracts first
    chat = mcp_server._STATE["chat"]  # noqa: SLF001
    chat.checked = (machine.record.pid, machine.record.started_at.isoformat())  # past the contract check
    assert chat_tool("find_decisions")["error"].startswith(unsupported)  # the host refuses before any route runs
    assert DataRepo(shared_repo[0]).git("rev-parse", "HEAD").stdout == head
    assert not (other / ".git" / "owlbear-delivery").exists()


def test_a_project_that_fails_to_load_is_listed_with_its_reason_beside_a_working_one(tmp_path, http, machine):
    bad, good = registry.register(clone(tmp_path / "bad")), registry.register(clone(tmp_path / "good"))
    (Path(bad.path) / ".git" / "owlbear-delivery" / "format").write_text("99\n")
    machine.load_all()
    shown = {p["name"]: p for p in http.get("/api/next/projects").json()["projects"]}
    assert (shown["bad"]["state"], "newer than" in shown["bad"]["reason"], shown["good"]["state"]) == (
        "failed", True, "loaded"
    )  # fmt: skip
    assert "bad is failed" in http.get(f"/p/{bad.id}/api/next/changes").json()["detail"]
    assert http.get(f"/p/{good.id}/api/next/changes").status_code == 200
    (Path(bad.path) / ".git" / "owlbear-delivery" / "format").unlink()
    machine.retry()
    assert http.get(f"/p/{bad.id}/api/next/changes").status_code == 200


def running_step(path: Path, sessions: int = 0) -> Path:
    store = Store.open(path)
    with store.lock("c1") as lock:
        store.write(lock, Change(slug="c1", step=Step(kind=StepKind.BUILD)))
    me = psutil.Process(os.getpid())
    rec = RunnerRecord(pid=me.pid, created=me.create_time(), started_at=datetime.now(UTC), sessions=sessions)
    path = store.root / "changes" / "c1" / "runner.json"
    path.write_text(rec.model_dump_json())
    return path


def test_a_project_that_did_not_load_counts_its_runners_until_a_host_confirms_them(tmp_path, http, machine):
    """TD-336, Sol: no host confirms them gone, so their sessions count, even a dead runner's, and removal waits."""
    bad = registry.register(clone(tmp_path / "bad"))
    runner = running_step(Path(bad.path), sessions=2)
    (Path(bad.path) / ".git" / "owlbear-delivery" / "format").write_text("99\n")
    machine.load_all()
    assert (machine.projects[bad.id].state, machine.slots.counts(bad.id)[2]) == ("failed", 2)
    refused = http.delete(f"/api/next/projects/{bad.id}")
    assert (refused.status_code, refused.json()["detail"]) == (
        409, "bad has steps of c1 not confirmed ended; it must load again to check them"
    )  # fmt: skip
    runner.unlink()  # as a host's check of its processes does
    assert http.delete(f"/api/next/projects/{bad.id}").json() == {"removed": bad.id}
    assert machine.slots.counts(bad.id)[2] == 0


def legacy_pack_folder(tmp_path, name: str, *, format_too_new: bool = True) -> tuple[dict, Path]:
    """A registered clone whose store will not open (format 99), with its store folder for a pre-ledger pack record."""
    entry = registry.register(clone(tmp_path / name))
    folder = Path(entry.path) / ".git" / "owlbear-delivery"
    if format_too_new:
        (folder / "format").write_text("99\n")
    return entry, folder


def legacy_pack_record(folder: Path, state: str, *, updater: bool = True) -> Path:
    """The last pack run as a pre-ledger host left it, with its SDK stage uncertain and no PID map."""
    stage = {"name": "update", "label": "Update", "result": "running", "detail": ""}
    record = pack_job._blank() | {  # noqa: SLF001 - the record's own shape
        "state": state, "stage": "update", "stages": [stage], "started_at": "2026-10-24T00:00:00+00:00", "run": "r1",
    }  # fmt: skip
    (folder / pack_job.FILE).write_text(json.dumps(record), encoding="utf-8")
    if updater:
        (folder / pack_run.UPDATER).mkdir(exist_ok=True)
    return folder / pack_run.UPDATER


def test_a_project_whose_store_did_not_open_holds_its_legacy_running_pack_before_another_project_can_take_the_slot(
    tmp_path, machine
):
    """HIGH review: an unloaded project's readable legacy running record keeps the machine's one session."""
    bad, folder = legacy_pack_folder(tmp_path, "bad")
    good = registry.register(clone(tmp_path / "good"))
    updater = legacy_pack_record(folder, "running")
    machine.slots.total = lambda: 1
    machine.load_all()
    assert machine.projects[bad.id].state == "failed"
    assert machine.slots.counts(bad.id)[2] == 1
    assert machine.slots.take(good.id, "probe", 1, 1) == 0  # the other project waits behind the uncertain update
    assert (updater.is_dir(), (folder / pack_job.FILE).is_file()) == (True, True)  # workspace and record are kept


def test_an_unloaded_project_whose_pack_record_is_finished_holds_nothing_and_another_project_takes_the_slot(
    tmp_path, machine
):
    bad, folder = legacy_pack_folder(tmp_path, "bad")
    good = registry.register(clone(tmp_path / "good"))
    legacy_pack_record(folder, "up-to-date", updater=False)
    machine.slots.total = lambda: 1
    machine.load_all()
    assert (machine.projects[bad.id].state, machine.slots.counts(bad.id)[2]) == ("failed", 0)
    assert machine.slots.take(good.id, "probe", 1, 1) == 1


def test_an_unreadable_pack_record_of_an_unloaded_project_is_held_not_taken_for_empty(tmp_path, machine):
    bad, folder = legacy_pack_folder(tmp_path, "bad")
    good = registry.register(clone(tmp_path / "good"))
    (folder / pack_job.FILE).write_text("{not json", encoding="utf-8")
    machine.slots.total = lambda: 1
    machine.load_all()
    assert machine.slots.counts(bad.id)[2] == 1
    assert machine.slots.take(good.id, "probe", 1, 1) == 0


class _LoopbackToApp:
    """The CLI's local transport, answered by the machine app's own handler instead of a socket."""

    def __init__(self, client: TestClient) -> None:
        self.client = client

    def open(self, request, timeout):  # noqa: ARG002 - urllib's opener signature
        out = self.client.post(urllib.parse.urlsplit(request.full_url).path)
        if out.status_code >= 400:
            raise urllib.error.HTTPError(
                request.full_url, out.status_code, out.reason_phrase, out.headers, io.BytesIO(out.content)
            )
        return io.BytesIO(out.content)


def test_a_manual_replay_of_another_project_waits_for_a_failed_projects_legacy_pack_even_with_a_free_slot(
    tmp_path, http, machine, monkeypatch, capsys
):
    """Route and CLI: the ledger's uncertain pack refuses before any SDK, although a machine slot is free."""
    monkeypatch.setattr(pack_replay, "sdk_run", lambda _cfg: pytest.fail("no SDK session starts"))
    bad, folder = legacy_pack_folder(tmp_path, "bad")
    good = registry.register(clone(tmp_path / "good"))
    updater = legacy_pack_record(folder, "running")
    machine.slots.total = lambda: 2
    machine.load_all()
    assert (machine.projects[bad.id].state, machine.projects[good.id].state) == ("failed", "loaded")
    assert machine.slots.counts(bad.id)[2] == 1  # one slot is held
    assert machine.slots.counts(good.id)[1] == 2  # one slot still free

    refused = http.post(f"/p/{good.id}/api/next/design-pack/replay")
    assert refused.status_code == 409
    reason = "an earlier design pack session is unproven; recover it on the Maintenance page first"
    assert refused.json()["detail"] == reason

    monkeypatch.setattr(replay_client.project_home, "clone_id", lambda _dir: good.id)
    record = HostFound(url="http://127.0.0.1:9/", token="t", pid=1, started_at=datetime.now(UTC), project=good.id)  # noqa: S106
    monkeypatch.setattr(replay_client.host, "running_at", lambda _root, _model: record)
    loopback = _LoopbackToApp(TestClient(app.create(machine), base_url="http://127.0.0.1", headers=AUTH))
    monkeypatch.setattr(replay_client, "_LOCAL", loopback)
    assert cli.main(["--repo", str(good.path), "design-pack", "--replay"]) == 1
    assert capsys.readouterr().out.splitlines()[-1] == reason  # the host's own log lines come first

    assert machine.slots.counts(bad.id)[2] == 1  # the reservation stays
    assert updater.is_dir()  # the workspace stays
    assert (folder / pack_job.FILE).is_file()  # and the record stays


def test_a_manual_replay_of_a_project_whose_legacy_pack_finished_is_not_refused_by_the_ledger(
    tmp_path, http, machine, monkeypatch
):
    """Control: with the failed project's pack finished, the same replay passes the guard and reaches its own checks."""
    monkeypatch.setattr(pack_replay, "sdk_run", lambda _cfg: pytest.fail("no SDK session starts"))
    bad, folder = legacy_pack_folder(tmp_path, "bad")
    good = registry.register(clone(tmp_path / "good"))
    legacy_pack_record(folder, "up-to-date", updater=False)
    machine.slots.total = lambda: 2
    machine.load_all()
    assert machine.slots.counts(bad.id)[2] == 0

    reached = http.post(f"/p/{good.id}/api/next/design-pack/replay")
    assert reached.status_code == 422  # pack_replay's own check: no shared repository, before any SDK session
    assert "shared repository" in reached.json()["detail"]


def older_failed_pack(folder: Path, reason: str, *, run: str = "legacy-run") -> None:
    """The record an older host left when its SDK session may still run: failed, with no workspace or PIDs."""
    stage = {"name": "update", "label": "Update", "result": "failed", "detail": ""}
    record = pack_job._blank() | {  # noqa: SLF001 - the record's own shape
        "state": "failed", "stages": [stage], "started_at": "2026-10-25T00:00:00+00:00", "run": run, "reason": reason,
    }  # fmt: skip
    folder.mkdir(parents=True, exist_ok=True)
    (folder / pack_job.FILE).write_text(json.dumps(record), encoding="utf-8")


REPLAY_UNCERTAIN = (
    "replay: ReplayError: the replay judge replay-0123abcd may still be running; stop it before replaying again"
)
REFUSED = "an earlier design pack session is unproven; recover it on the Maintenance page first"


def test_a_manual_replay_of_another_project_refuses_an_unloaded_projects_older_failed_uncertain_pack_with_a_free_slot(
    tmp_path, http, machine, monkeypatch
):
    """An older failed replay record, updater directory gone, holds its project's slot before any SDK."""
    monkeypatch.setattr(pack_replay, "sdk_run", lambda _cfg: pytest.fail("no SDK session starts"))
    bad, folder = legacy_pack_folder(tmp_path, "bad")
    good = registry.register(clone(tmp_path / "good"))
    older_failed_pack(folder, REPLAY_UNCERTAIN)
    machine.slots.total = lambda: 2
    machine.load_all()
    assert (machine.projects[bad.id].state, machine.slots.counts(bad.id)[2]) == ("failed", 1)

    refused = http.post(f"/p/{good.id}/api/next/design-pack/replay")
    assert (refused.status_code, refused.json()["detail"]) == (409, REFUSED)
    assert machine.slots.counts(bad.id)[2] == 1  # the reservation stays
    assert machine.slots.counts(good.id)[2] == 0
    assert (folder / pack_job.FILE).is_file()


def test_a_loaded_projects_older_failed_uncertain_pack_holds_its_slot_and_refuses_its_own_replay(
    tmp_path, http, machine, monkeypatch
):
    """The loaded path: the same older record is adopted through the project's job before a replay can start."""
    monkeypatch.setattr(pack_replay, "sdk_run", lambda _cfg: pytest.fail("no SDK session starts"))
    good = registry.register(clone(tmp_path / "good"))
    # the store folder, as the project opens it
    older_failed_pack(project_home.located(Path(good.path)), REPLAY_UNCERTAIN)
    machine.slots.total = lambda: 2
    machine.load_all()
    assert (machine.projects[good.id].state, machine.slots.counts(good.id)[2]) == ("loaded", 1)

    refused = http.post(f"/p/{good.id}/api/next/design-pack/replay")
    assert (refused.status_code, refused.json()["detail"]) == (409, REFUSED)


@pytest.mark.parametrize("project_kind", ["loaded", "unloaded"])
def test_an_empty_legacy_import_receipt_never_suppresses_repair_of_an_older_failed_uncertain_pack(
    tmp_path, http, machine, monkeypatch, project_kind
):
    """An earlier import marker with no lease behind it is not evidence that the older record was handled."""
    monkeypatch.setattr(pack_replay, "sdk_run", lambda _cfg: pytest.fail("no SDK session starts"))
    bad, folder = legacy_pack_folder(tmp_path, "bad")
    good = registry.register(clone(tmp_path / "good"))
    project = good if project_kind == "loaded" else bad
    if project_kind == "loaded":
        older_failed_pack(project_home.located(Path(good.path)), REPLAY_UNCERTAIN)
    else:
        older_failed_pack(folder, REPLAY_UNCERTAIN)
    # an older import receipt
    machine.maintenance._save(maintenance.Ledger(imported=[f"{project.id}:legacy"]))  # noqa: SLF001
    machine.slots.total = lambda: 2
    machine.load_all()
    refused = http.post(f"/p/{good.id}/api/next/design-pack/replay")
    assert (refused.status_code, refused.json()["detail"]) == (409, REFUSED)
    assert (machine.slots.counts(project.id)[2], len(machine.maintenance.read()["sessions"])) == (1, 1)


def test_a_recovered_legacy_pack_generation_is_not_resurrected_by_an_empty_receipt_on_restart(tmp_path, machine):
    good = registry.register(clone(tmp_path / "good"))
    older_failed_pack(project_home.located(Path(good.path)), REPLAY_UNCERTAIN)
    machine.slots.total = lambda: 2
    machine.load_all()
    [session] = machine.maintenance.read()["sessions"]
    booted = machine.maintenance.boot
    machine.maintenance.boot = lambda: booted() + 1  # the computer rebooted since the failed session
    machine.maintenance.recover(session["id"], rebooted=True)
    for _ in range(2):
        machine.load_all()
        sessions = machine.maintenance.read()["sessions"]
        assert (len(sessions), sessions[0]["state"], machine.slots.counts(good.id)[2]) == (1, "recovered", 0)


def test_an_unconfirmed_pack_run_keeps_the_machine_busy_and_not_left_until_its_reboot_recovery(machine):
    """The pack ledger holds at machine scope even with no loaded project, so an update or stop waits for it."""
    ident = machine.maintenance.begin("unloaded", "pack:unloaded", "pack", "", now=datetime.now(UTC))
    machine.maintenance.failed(ident, RuntimeError("synthetic unconfirmed run"))
    assert (bool(machine.busy()), bool(machine.left())) == (True, True)
    booted = machine.maintenance.boot
    machine.maintenance.boot = lambda: booted() + 1  # the computer rebooted since the unconfirmed run
    machine.maintenance.recover(ident, rebooted=True)
    assert (machine.busy(), machine.left()) == ([], [])


def test_a_modern_failed_uncertain_pack_with_its_workspace_recorded_is_not_adopted_as_older_work(tmp_path, machine):
    """Control: a run that recorded its workspace is ledger-owned already, so nothing is imported from its record."""
    good = registry.register(clone(tmp_path / "good"))
    root = project_home.located(Path(good.path))
    older_failed_pack(root, REPLAY_UNCERTAIN)
    record = json.loads((root / pack_job.FILE).read_text(encoding="utf-8"))
    record["workspace"] = str(root / "runs" / "legacy-run")
    (root / pack_job.FILE).write_text(json.dumps(record), encoding="utf-8")
    machine.slots.total = lambda: 2
    machine.load_all()
    assert (
        machine.projects[good.id].state,
        machine.slots.counts(good.id)[2],
        machine.maintenance.read()["sessions"],
    ) == ("loaded", 0, [])


def test_removal_is_refused_while_a_step_runs_and_then_stops_the_project_before_forgetting_it(tmp_path, http, machine):
    p = add(http, clone(tmp_path / "a"))
    runner = running_step(Path(p["path"]))
    refused = http.delete(f"/api/next/projects/{p['id']}")
    assert (refused.status_code, refused.json()["detail"]) == (
        409, f"a still runs c1: a running step (process {os.getpid()}); remove it once they end"
    )  # fmt: skip
    assert http.get(f"/p/{p['id']}/api/next/changes").status_code == 200  # admitted again
    held = machine.projects[p["id"]]
    runner.unlink()
    assert http.delete(f"/api/next/projects/{p['id']}").json() == {"removed": p["id"]}
    assert (held.host.stopped.is_set(), held.scheduler.is_alive(), running(held.store)) == (True, False, None)
    assert (registry.load().projects, http.get(f"/p/{p['id']}/api/next/changes").status_code) == ([], 404)


def test_a_closed_gate_admits_nothing_and_starts_no_runner_even_after_resume(tmp_path, http, machine):
    p = add(http, clone(tmp_path / "a"))
    held = machine.projects[p["id"]]
    assert http.post("/api/next/resume").json() == {"paused": False}
    assert (held.host.paused(), registry.load().resumed_at is not None) == (False, True)
    assert held.gate.enter()
    assert held.gate.close(0.05) == 1  # the admitted request still runs after the wait
    assert held.host.paused()
    assert http.get(f"/p/{p['id']}/api/next/changes").status_code == 503
    held.gate.leave()
    assert held.gate.close(0) == 0


def test_a_stop_when_idle_waits_for_a_running_step_refuses_a_launch_and_resume_cancels_it(
    tmp_path, http, machine, monkeypatch
):
    """TD-288: a plain Pause never stops OwlBear; a stop when idle names what it waits for, then stops."""
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    (bin_dir / "code").write_text("#!/bin/sh\nexit 1\n")
    (bin_dir / "code").chmod(0o755)
    monkeypatch.setenv("PATH", f"{bin_dir}{os.pathsep}{os.environ['PATH']}")  # never run: the launch is refused
    p = add(http, clone(tmp_path / "a"))
    stopped = []
    machine.on_stop = lambda: stopped.append(True)
    machine.resume()
    assert http.post("/api/next/pause").json() == {"paused": True}
    assert (machine.projects[p["id"]].host.paused(), machine.idle_stop()) == (True, False)
    assert http.post("/api/next/pause-stop").json() == {"paused": True, "ending": True}
    http.post("/api/next/resume")
    assert (machine.idle_stop(), machine.paused, http.get("/api/next/projects").json()["ending"]) == (
        False, False, False
    )  # fmt: skip
    http.post("/api/next/pause-stop")
    runner = running_step(Path(p["path"]))
    listed = http.get("/api/next/projects").json()
    assert (listed["ending"], listed["left"]) == (True, [f"a: c1: a running step (process {os.getpid()})"])
    refused = http.post(f"/p/{p['id']}/api/next/new-change")
    assert (refused.status_code, refused.json()["detail"]) == (409, ENDING)
    assert (machine.idle_stop(), stopped) == (False, [])
    runner.unlink()
    assert (machine.idle_stop(), stopped) == (True, [True])


def test_a_project_loaded_during_a_stop_when_idle_has_the_machines_guards_from_its_first_pass(
    tmp_path, http, machine, monkeypatch
):
    seen = []
    monkeypatch.setattr(Host, "run", lambda self: seen.append((self.draining(), self.closed())))
    machine.ending = True
    p = machine.projects[add(http, clone(tmp_path / "a"))["id"]]
    p.scheduler.join(5)
    assert seen == [(True, False)]


def test_a_stop_when_idle_waits_for_a_launch_admitted_before_it(tmp_path, http, machine):
    p = machine.projects[add(http, clone(tmp_path / "a"))["id"]]
    stopped, held, release, looked = [], threading.Event(), threading.Event(), []
    machine.on_stop = lambda: stopped.append(True)

    def admit():
        with p.host.launching:  # a runner that passed its pause check before the intent
            held.set()
            release.wait(5)
            running_step(Path(p.entry.path))  # recorded before the lock is released

    admitting = threading.Thread(target=admit)
    admitting.start()
    held.wait(5)
    pausing = threading.Thread(target=machine.pause_stop)
    pausing.start()
    while not machine.ending:
        time.sleep(0.01)
    looking = threading.Thread(target=lambda: looked.append(machine.idle_stop()))
    looking.start()
    time.sleep(0.2)  # the look waits behind the barrier
    release.set()
    for t in (admitting, pausing, looking):
        t.join(5)
    assert (looked, stopped) == ([False], [])


def test_a_stop_when_idle_waits_for_what_is_not_confirmed_gone(tmp_path, http, machine):
    """An ended step's runner record, a block on surviving processes and a launch without PIDs keep OwlBear up."""
    p = machine.projects[add(http, clone(tmp_path / "a"))["id"]]
    p.host.stopped.set()
    p.host.wake.set()
    p.scheduler.join(5)  # no pass confirms anything in between
    runner = running_step(Path(p.entry.path))
    rec = RunnerRecord.model_validate_json(runner.read_text())
    runner.write_text(rec.model_copy(update={"created": rec.created - 100}).model_dump_json())  # its process ended
    now = datetime.now(UTC)
    with p.store.lock("c1") as lock:
        c = p.store.read("c1")
        url = "http://127.0.0.1:1/"
        c.env = Environment(check="preview", command="x", directory=".", ready_url=url, launched_at=now)
        p.store.write(lock, c)
    ended = ["c1: the processes of its ended step", "c1: a check environment"]
    assert (p.working(), p.working(stopping=True)) == ([], ended)
    runner.unlink()
    with p.store.lock("c1") as lock:
        c = p.store.read("c1")
        c.env = None
        p.host.mark(c, {4242: "sleep"}, now)
        p.store.write(lock, c)
    machine.ending = True
    assert (p.working(), machine.left(), machine.idle_stop()) == ([], [f"a: c1: {c.blocked.reason}"], False)


def test_every_change_that_would_continue_is_counted_until_resume(tmp_path, http):
    p = add(http, clone(tmp_path / "a"))
    store = Store.open(Path(p["path"]))
    with store.lock("c1") as lock:
        store.write(lock, Change(slug="c1", step=Step(kind=StepKind.BUILD)))
    assert http.get("/api/next/projects").json()["waiting"] == 1
    assert http.get(f"/p/{p['id']}/api/next/changes").json()[0]["action"] == "Resume Delivery"


def test_a_reclone_is_shown_replaced_until_adopted(tmp_path, http, machine):
    work = clone(tmp_path / "a")
    old = add(http, work)
    machine.remove(old["id"])
    registry.register(work)  # registered again without the host, then re-cloned at the same path
    subprocess.run(["rm", "-rf", str(work)], check=True)  # noqa: S603, S607
    clone(work)
    machine.load_all()
    pid = registry.load().projects[0].id
    assert http.get("/api/next/projects").json()["projects"][0]["state"] == "replaced"
    machine.slots.restore(pid, {"c1": 2})  # counted while it failed to load (TD-336)
    adopted = http.post(f"/api/next/projects/{pid}/adopt").json()
    assert (adopted["state"], adopted["id"] != pid) == ("loaded", True)
    assert machine.slots.counts(pid)[2] == 0  # Sol: the old id holds nothing once the new clone takes its place


def test_clones_sharing_a_settings_folder_are_each_others_peers(machine):
    def clone_of(folder, root="/shared"):
        store = SimpleNamespace(shared=SimpleNamespace(root=Path(root)), name=folder)
        return SimpleNamespace(store=store, host=object())

    a, b, other, elsewhere = clone_of("shop"), clone_of("shop"), clone_of("blog"), clone_of("shop", "/other")
    machine.projects = {"a": a, "b": b, "c": other, "d": elsewhere}
    found = (machine.sharing(a), machine.sharing(other))
    machine.projects = {}  # none of them is a loaded project to stop
    assert found == ([b.host], [])


def test_a_project_whose_lock_cannot_be_taken_fails_alone(tmp_path, http, machine):
    bad = registry.register(clone(tmp_path / "bad"))
    registry.register(clone(tmp_path / "good"))
    lock = Path(bad.path) / ".git" / "owlbear-delivery" / "host.lock"
    lock.symlink_to(tmp_path / "elsewhere")
    machine.load_all()
    shown = {p["name"]: p for p in http.get("/api/next/projects").json()["projects"]}
    assert (shown["bad"]["state"], "host.lock cannot be locked" in shown["bad"]["reason"]) == ("failed", True)
    assert shown["good"]["state"] == "loaded"


def test_a_stop_waits_for_work_started_in_the_background_and_closing_closes_every_gate(tmp_path, http, machine, capsys):
    p = machine.projects[add(http, clone(tmp_path / "a"))["id"]]
    until = time.monotonic() + 0.5
    p.app.state.busy = lambda: ["a shaping chat opening"] if time.monotonic() < until else []
    p.stop(drain=5)
    assert (time.monotonic() >= until, p.state) == (True, "stopped")
    q = machine.projects[add(http, clone(tmp_path / "b"))["id"]]
    server = serve.Server(uvicorn.Config(app.create(machine)), machine)
    capsys.readouterr()
    server.handle_exit(signal.SIGTERM, None)
    assert (q.gate.open, q.host.paused(), server.should_exit) == (False, True, True)
    assert http.post("/api/next/stop").json() == {"stopping": True}
    q.host.say("still here")
    stamp = r"\d\d:\d\d:\d\dZ "  # UTC, and says so
    lines = capsys.readouterr().out.splitlines()  # project threads may log between these
    for said in ("stopping: SIGTERM received", "stopping: asked through the stop route", ".*still here"):
        assert any(re.fullmatch(stamp + said, line) for line in lines), said


def test_a_clone_without_its_chat_server_shows_the_setup_it_needs(tmp_path, http):
    work = clone(tmp_path / "a")
    listed = add(http, work)
    assert listed["setup"] == f"owlbear setup --repo {work}"
    (work / ".mcp.json").write_text(json.dumps(setup.with_server({}, "/py", work)))
    assert "setup" not in http.get("/api/next/projects").json()["projects"][0]
    (work / ".mcp.json").unlink()
    setup.user_mcp(Path.home()).parent.mkdir(parents=True)
    servers = setup.with_server({}, "/py", work)["mcpServers"]
    setup.user_mcp(Path.home()).write_text("// mine\n" + json.dumps({"servers": servers}))
    assert setup.registered(work)


def test_nothing_loads_or_is_admitted_once_the_machine_stops(tmp_path, http, machine):
    p = machine.projects[add(http, clone(tmp_path / "a"))["id"]]
    machine.resume()
    machine.closing()
    assert (p.host.paused(), http.get(f"/p/{p.entry.id}/api/next/changes").status_code) == (True, 503)
    late = http.post("/api/next/projects", json={"path": str(clone(tmp_path / "b"))})
    assert (late.status_code, late.json()["detail"]) == (503, "OwlBear is stopping")


def test_a_project_that_fails_while_starting_releases_its_lock(tmp_path, machine, monkeypatch):
    entry = registry.register(clone(tmp_path / "a"))
    real, broken = project.api.create_app, [True]

    def create_app(*args):
        if broken[0]:
            msg = "boom"
            raise RuntimeError(msg)
        return real(*args)

    monkeypatch.setattr(project.api, "create_app", create_app)
    machine.load_all()
    failed = machine.projects[entry.id]
    assert (failed.state, failed.reason, failed.lock_fd) == ("failed", "it could not start: RuntimeError: boom", None)
    broken[0] = False
    machine.retry()
    again = machine.projects[entry.id]
    assert (again.state, again.reason) == ("loaded", "")  # the lock was free again
    unstarted = project.Project(entry)
    unstarted.scheduler = threading.Thread(target=lambda: None)
    assert (unstarted.stop(drain=0), unstarted.state) == ([], "stopped")


def test_malformed_or_unrelated_server_entries_never_count_as_setup(tmp_path):
    work = clone(tmp_path / "a")
    (work / ".mcp.json").write_text(json.dumps({"mcpServers": {setup.SERVER: {"args": None}}}))
    assert setup.registered(work) is False
    setup.user_mcp(Path.home()).parent.mkdir(parents=True)
    unrelated = {"x": {"args": ["-m", "owlbear_delivery_next", "mcp", "--repo", "/other"]}, "y": {"args": [str(work)]}}
    setup.user_mcp(Path.home()).write_text(json.dumps({"servers": unrelated}))
    assert setup.registered(work) is False


def test_each_project_line_in_the_log_names_its_project(tmp_path, http, machine, capsys):
    p = machine.projects[add(http, clone(tmp_path / "shop"))["id"]]
    p.host.say("c1: runner 7 started")
    assert capsys.readouterr().out.endswith(" shop: c1: runner 7 started\n")


def test_the_machine_s_own_values_are_read_apart_from_any_settings_layer(http, machine, monkeypatch):
    """TD-243: the Settings page's machine section; the login item as launchctl reports it, on a Mac only."""
    monkeypatch.setattr(app.sys, "platform", "darwin")
    monkeypatch.setattr(app.control, "autostarts", lambda: "on")
    paused = http.get("/api/next/machine").json()
    machine.resume()
    resumed = http.get("/api/next/machine").json()
    monkeypatch.setattr(app.sys, "platform", "linux")
    assert (paused["paused"], paused["login_item"], resumed["paused"], resumed["resumed_at"] is not None) == (
        True, "on", False, True
    )  # fmt: skip
    assert http.get("/api/next/machine").json()["login_item"] == "not available on this system"


def test_the_machine_s_settings_are_saved_against_the_revision_the_page_read(http):
    """TD-288, TD-300, TD-336: channel, the two update switches and the sessions at once, refused when another page
    saved first."""
    read = http.get("/api/next/machine").json()
    chosen = {
        "channel": "major", "update_when_idle": False, "update_while_paused": True, "curate_after_merge": "paused",
        "curate_when_idle": "off", "sessions": 3,
    }  # fmt: skip
    saved = http.put("/api/next/machine/settings", json={"rev": read["settings_rev"], "settings": chosen})
    stale = http.put("/api/next/machine/settings", json={"rev": read["settings_rev"], "settings": chosen})
    wrong = http.put("/api/next/machine/settings", json={"rev": "x", "settings": {"channel": "nightly"}})
    assert (read["settings"]["channel"], read["resolved"]["channel"], read["resolved"]["sources"]["channel"]) == (
        None, "minor", "default"
    )  # fmt: skip
    unset = dict.fromkeys(("spotter_budget", "retro_budget", "retro_verbose_cap", "retro_after_change",
                           "retro_when_idle", "enrolled_chats"))  # Improvement's: none chosen here  # fmt: skip
    assert (saved.json()["settings"], registry.load().settings.channel) == (chosen | unset, "major")
    assert saved.json()["resolved"]["sources"]["channel"] == "machine"
    assert (stale.status_code, "changed since" in stale.json()["detail"], wrong.status_code) == (409, True, 422)
    inherit = http.put("/api/next/machine/settings", json={"rev": saved.json()["settings_rev"],
                                                           "settings": chosen | {"channel": None}})  # fmt: skip
    assert (inherit.json()["settings"]["channel"], inherit.json()["resolved"]["channel"]) == (None, "minor")


def test_a_decision_lists_the_changes_of_every_loaded_project_whose_baseline_pins_it(tmp_path, http, machine):
    """TD-419 slice 5a: the Decisions page's affected Changes come from every project the host serves."""
    a, b = add(http, clone(tmp_path / "a")), add(http, clone(tmp_path / "b"))
    decision, now = "D-01JQZ8V6M3K5T1W9X2Y4Z7A8B0", datetime.now(UTC)
    for p, pins in ((a, {decision: "r" * 64}), (b, {})):
        store = machine.projects[p["id"]].store
        with store.lock("c1") as lock:
            pin = DecisionBaseline(commit="c", at=now, revisions=pins)
            store.write(lock, Change(slug="c1", step=Step(kind=StepKind.BUILD), decisions_baseline=pin))
    got = http.get(f"/api/next/decisions/{decision}/changes").json()["changes"]
    assert [(c["project"], c["pid"], c["slug"], c["applies"]) for c in got] == [("a", a["id"], "c1", False)]
    anonymous = TestClient(http.app, base_url="http://127.0.0.1")
    assert anonymous.get(f"/api/next/decisions/{decision}/changes").status_code == 401


def test_the_maintenance_button_curates_a_memory_folder_now_also_while_paused(http, machine, shared_repo, monkeypatch):
    """Item 5 slice 4: the machine's curation lists the shared repository's memory folders and runs one at once."""
    from owlbear_delivery_next.change_contracts.memory_curation_tools import MemoryCurationResult  # noqa: PLC0415
    from owlbear_delivery_next.local_system.processes import Termination  # noqa: PLC0415
    from owlbear_delivery_next.runtimes.session_result import Run  # noqa: PLC0415

    (shared_repo[0] / "shop" / "memory").mkdir(parents=True)
    monkeypatch.setenv("OWLBEAR_DATA", str(shared_repo[0]))
    machine.slots.open()
    report = MemoryCurationResult(summary="nothing pending", entries=[])
    machine.curation.run = lambda cfg: Run(cfg.session_id, ending="result", payload=report,
                                           termination=Termination(confirmed=True))  # fmt: skip
    assert machine.paused  # the button runs also while paused (the owner, 2026-10-22)

    listed = http.get("/api/next/curation").json()
    unknown = http.post("/api/next/curation", json={"folder": "nowhere"})
    machine.updating = "an update runs"
    fenced = http.post("/api/next/curation", json={"folder": "shop"})
    machine.updating = ""
    started = http.post("/api/next/curation", json={"folder": "shop"})
    for _ in range(200):
        if not machine.curation.working():
            break
        time.sleep(0.02)

    assert [f["folder"] for f in listed["folders"]] == ["shop"]
    assert (unknown.status_code, fenced.status_code, started.json()["started"]) == (409, 503, ["shop"])
    assert http.get("/api/next/curation").json()["folders"][0]["summary"] == "nothing pending"


HELD_SLOT = "0123456789abcdef"


def _curation_runs(machine, shared_repo, monkeypatch, gate=None) -> list:
    """Machine curation with a synthetic run that records each start; *gate* holds it open until set."""
    from owlbear_delivery_next.change_contracts.memory_curation_tools import MemoryCurationResult  # noqa: PLC0415
    from owlbear_delivery_next.local_system.processes import Termination  # noqa: PLC0415
    from owlbear_delivery_next.runtimes.session_result import Run  # noqa: PLC0415

    (shared_repo[0] / "shop" / "memory").mkdir(parents=True)
    monkeypatch.setenv("OWLBEAR_DATA", str(shared_repo[0]))
    machine.slots.open()
    ran = []

    def run(cfg) -> Run:
        ran.append(cfg.session_id)
        if gate is not None:
            gate.wait(5)
        return Run(cfg.session_id, ending="result", payload=MemoryCurationResult(summary="ok", entries=[]),
                   termination=Termination(confirmed=True))  # fmt: skip

    machine.curation.run = run
    return ran


def _curation_finished(machine) -> None:
    for _ in range(200):
        if not machine.curation.working():
            return
        time.sleep(0.02)
    pytest.fail("the curation did not finish")


def test_a_curate_now_queued_behind_a_step_never_starts_once_a_stop_when_idle_is_asked(
    machine, shared_repo, monkeypatch
):
    ran = _curation_runs(machine, shared_repo, monkeypatch)
    assert machine.slots.take(HELD_SLOT, "a-change", 1, 1) == 1  # a step holds the only slot
    machine.curation.start("shop")  # queued behind it
    machine.pause_stop()
    machine.slots.give(HELD_SLOT, "a-change")
    _curation_finished(machine)
    shop = {f["folder"]: f for f in machine.curation.read()["folders"]}["shop"]
    assert (ran, shop["state"], machine.idle_stop()) == ([], "failed", True)


def test_a_stop_when_idle_landing_right_after_a_curation_grant_stops_it_before_its_run(
    machine, shared_repo, monkeypatch
):
    ran = _curation_runs(machine, shared_repo, monkeypatch)
    assert machine.slots.take(HELD_SLOT, "a-change", 1, 1) == 1
    grant = machine.slots.take

    def take_then_stop(project, key, want, limit, wake=None):  # the stop lands between the grant and the run
        got = grant(project, key, want, limit, wake=wake)
        if got and key.startswith("curate:"):
            machine.pause_stop()
        return got

    monkeypatch.setattr(machine.slots, "take", take_then_stop)
    machine.curation.start("shop")
    machine.slots.give(HELD_SLOT, "a-change")
    _curation_finished(machine)
    assert (ran, machine.idle_stop()) == ([], True)


def test_a_curation_admitted_before_a_stop_when_idle_stays_pinned_and_finishes(machine, shared_repo, monkeypatch):
    gate = threading.Event()
    ran = _curation_runs(machine, shared_repo, monkeypatch, gate)
    machine.curation.start("shop")
    for _ in range(200):
        if ran:
            break
        time.sleep(0.02)
    machine.pause_stop()
    waited = machine.idle_stop()  # the admitted run is counted: the stop waits for it
    gate.set()
    _curation_finished(machine)
    shop = {f["folder"]: f for f in machine.curation.read()["folders"]}["shop"]
    assert (len(ran), waited, shop["state"], machine.idle_stop()) == (1, False, "done", True)


@pytest.mark.parametrize(("old", "both"), [(False, "on"), (True, "paused"), ("false", "on"), ("true", "paused")])
def test_format_4s_one_curation_switch_becomes_a_setting_per_trigger(old, both) -> None:
    raw = {"channel": "minor", "update_when_idle": True, "update_while_paused": True, "curate_while_paused": old,
           "sessions": 4}  # fmt: skip
    settings = registry.Settings.model_validate(raw)
    assert (settings.curate_after_merge, settings.curate_when_idle) == (both, both)
    assert "curate_while_paused" not in settings.model_dump()
