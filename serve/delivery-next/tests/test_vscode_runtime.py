import asyncio
import json
import signal
import stat
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from types import SimpleNamespace

import psutil
import pytest
from mcp import Client, StdioServerParameters

from owlbear_delivery_next import ahp, cli, leftovers, sdk_adapter, sessions, step_mcp, tools, vscode_adapter
from owlbear_delivery_next import window_files as wf
from owlbear_delivery_next.models import StepKind
from owlbear_delivery_next.permissions import Policy
from owlbear_delivery_next.process_probe import WorktreeProcessScanError
from owlbear_delivery_next.profile_record import Profile
from owlbear_delivery_next.results import Gate
from owlbear_delivery_next.session_result import Run
from owlbear_delivery_next.step_inbox import Inbox
from owlbear_delivery_next.store import Store
from owlbear_delivery_next.tools import Worktree

HEAD, BASE = "a" * 40, "b" * 40
GOOD = {"summary": "Added greet().", "changed_paths": ["src/greet.ts"], "checks": []}


def git(cwd: Path, *args: str) -> str:
    done = subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True)  # noqa: S603, S607
    return done.stdout.strip()


@pytest.fixture(autouse=True)
def git_env(tmp_path, monkeypatch):
    (tmp_path / "gitconfig").write_text("")
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", str(tmp_path / "gitconfig"))
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")
    for who in ("AUTHOR", "COMMITTER"):
        monkeypatch.setenv(f"GIT_{who}_NAME", "t")
        monkeypatch.setenv(f"GIT_{who}_EMAIL", "t@t")


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    path = tmp_path / "wt"
    path.mkdir()
    git(path, "init", "-q", "-b", "main")
    (path / "README.md").write_text("x\n")
    git(path, "add", "-A")
    git(path, "commit", "-qm", "init")
    return path


def session(**kw) -> sdk_adapter.Session:
    fields = {
        "kind": StepKind.BUILD,
        "worktree": Path(),
        "session_id": "s1",
        "message": "m",
        "resume": False,
        "policy": Policy(Path(), ()),
        "observe": lambda: Worktree(HEAD, BASE, changed=("src/greet.ts",)),
        "checks": (),
    }
    return sdk_adapter.Session(**(fields | kw))


def test_window_files_never_reach_a_commit_and_are_restored(repo: Path) -> None:
    (repo / ".vscode").mkdir()
    (repo / ".vscode" / "settings.json").write_text('{ // team\n  "a": 1,\n}\n')
    git(repo, "add", "-A")
    git(repo, "commit", "-qm", "settings")
    placed = [
        wf.place(repo, wf.SETTINGS, wf.settings("gpt-6-luna")),
        wf.place(repo, wf.MCP, wf.mcp(Path("/inbox.json"))),
        wf.place(repo, wf.agent_path("builder"), wf.agent("builder", Path("/inbox.json"))),
    ]
    assert '"chat.defaultModel": "gpt-6-luna"' in (repo / wf.SETTINGS).read_text()
    assert "name: owlbear-builder" in (repo / wf.agent_path("builder")).read_text()
    assert git(repo, "status", "--porcelain") == ""
    (repo / "a.txt").write_text("a\n")
    git(repo, "add", "-A")
    git(repo, "commit", "-qm", "agent")
    assert git(repo, "show", "--name-only", "--format=", "HEAD") == "a.txt"

    assert wf.restore(repo, placed) == []
    assert (repo / wf.SETTINGS).read_text() == '{ // team\n  "a": 1,\n}\n'
    assert not (repo / wf.MCP).exists()
    assert not (repo / wf.agent_path("builder")).exists()
    assert git(repo, "ls-files", "-v", wf.SETTINGS).startswith("H ")
    assert git(repo, "status", "--porcelain") == ""


def test_a_locally_edited_tracked_file_is_refused_and_kept(repo: Path) -> None:
    (repo / ".mcp.json").write_text("{}\n")
    git(repo, "add", "-A")
    git(repo, "commit", "-qm", "mcp")
    (repo / ".mcp.json").write_text('{"mcpServers": {}}\n')
    with pytest.raises(wf.SettingsError, match="local edits"):
        wf.place(repo, wf.MCP, wf.mcp(Path("/inbox.json")))
    assert (repo / ".mcp.json").read_text() == '{"mcpServers": {}}\n'
    assert git(repo, "ls-files", "-v", wf.MCP).startswith("H ")


def test_a_closed_gate_accepts_nothing_more() -> None:
    g = gate()
    assert g.finish("deadline", None, "step deadline") is False
    assert g.call(tools.SUBMIT, GOOD) == ("The step has already ended. Stop now.", False)
    assert (g.run.ending, g.run.head, g.run.payload) == ("deadline", None, None)


def test_a_second_placement_is_undone_back_to_the_first_state(repo: Path) -> None:
    first = wf.place(repo, wf.SETTINGS, wf.settings("gpt-6-luna"))
    second = wf.place(repo, wf.SETTINGS, wf.settings("gpt-6.1-sol"))
    assert wf.restore(repo, [first, second]) == []
    assert not (repo / wf.SETTINGS).exists()


def test_a_window_file_is_never_written_through_a_link(repo: Path, tmp_path: Path) -> None:
    away = tmp_path / "away"
    away.mkdir()
    (repo / ".vscode").symlink_to(away)
    with pytest.raises(wf.SettingsError, match="symbolic link"):
        wf.place(repo, wf.SETTINGS, wf.settings("gpt-6-luna"))
    assert list(away.iterdir()) == []


def test_the_relay_entry_keeps_the_projects_servers() -> None:
    text = wf.mcp(Path("/s/x.json"))('{"mcpServers": {"mine": {"command": "a"}}}')
    assert '"mine"' in text
    assert '"--inbox",\n        "/s/x.json"' in text


def test_each_step_names_its_relay_server_apart() -> None:
    """The agent host disables a server whose name an earlier window's session still holds (P21)."""
    first = json.loads(wf.mcp(Path("/s/1a2b3c4d5e6f7a8b9c.json"))(None))["mcpServers"]
    second = json.loads(wf.mcp(Path("/s/9f8e7d6c5b4a3f2e1d.json"))(None))["mcpServers"]
    assert list(first) == ["owlbear-step-1a2b3c4d5e6f7a8b"]
    assert list(second) == ["owlbear-step-9f8e7d6c5b4a3f2e"]


def gate(log: list | None = None, observe=None) -> Gate:
    cfg = session(**({"observe": observe} if observe else {}))
    return Gate(cfg, Run("s1"), lambda **e: (log if log is not None else []).append(e), lambda: None)


def request(where: dict, path: str, token: str) -> int:
    req = urllib.request.Request(where["url"] + path, headers={"Authorization": f"Bearer {token}"})  # noqa: S310
    try:
        with urllib.request.build_opener(urllib.request.ProxyHandler({})).open(req, timeout=5) as r:
            return r.status
    except urllib.error.HTTPError as exc:
        return exc.code


def test_the_inbox_serves_only_with_its_token_and_vanishes_with_the_step(tmp_path: Path) -> None:
    g, path = gate(), tmp_path / "steps" / "one.json"
    with Inbox(g, path):
        assert stat.S_IMODE(path.stat().st_mode) == 0o600
        where = json.loads(path.read_text())
        assert request(where, "/tools", where["token"]) == 200
        assert request(where, "/tools", "guess") == 401
        listed = step_mcp.forward(path, "GET", "/tools")
        assert [t["name"] for t in listed["tools"]] == [
            "submit_result",
            "ask_question",
            "report_wrong_premise",
            "report_missing_tool",
        ]
        bad = step_mcp.forward(path, "POST", "/call", {"name": "submit_result", "arguments": {"summary": "x"}})
        assert (bad["ok"], bad["text"].startswith("Rejected.")) == (False, True)
        good = step_mcp.forward(path, "POST", "/call", {"name": "submit_result", "arguments": GOOD})
        assert good == {"text": "Accepted. Your step has ended: stop now and start nothing else.", "ok": True}
    assert not path.exists()
    assert step_mcp.forward(path, "GET", "/tools") is None
    assert (g.run.ending, g.run.head, g.run.invalid) == ("result", HEAD, 1)


def test_the_harness_reaches_the_step_through_the_stdio_relay(tmp_path: Path) -> None:
    g, path = gate(), tmp_path / "steps" / "two.json"
    params = StdioServerParameters(
        command=sys.executable, args=["-m", "owlbear_delivery_next.step_mcp", "--inbox", str(path)], cwd=str(tmp_path)
    )

    async def talk() -> tuple[list[str], object, object]:
        async with Client(params) as client:
            names = [t.name for t in (await client.list_tools()).tools]
            done = await client.call_tool("submit_result", GOOD)
            late = await client.call_tool("submit_result", GOOD)
            return names, done, late

    with Inbox(g, path):
        names, done, late = asyncio.run(talk())
    assert names == ["submit_result", "ask_question", "report_wrong_premise", "report_missing_tool"]
    assert (done.is_error, late.is_error) == (False, True)
    assert late.content[0].text == "The step has already ended. Stop now."
    assert g.run.payload.summary == "Added greet()."


def test_a_relay_without_a_step_offers_nothing(tmp_path: Path) -> None:
    params = StdioServerParameters(
        command=sys.executable, args=["-m", "owlbear_delivery_next.step_mcp", "--inbox", str(tmp_path / "gone.json")]
    )

    async def talk() -> tuple[list, object]:
        async with Client(params) as client:
            return (await client.list_tools()).tools, await client.call_tool("submit_result", GOOD)

    listed, call = asyncio.run(talk())
    assert listed == []
    assert (call.is_error, call.content[0].text) == (True, step_mcp.NOT_RUNNING)


class FakeProc:
    def __init__(self, name: str, exe: str, parent: FakeProc | None = None, ppid: int = 2) -> None:
        self._name, self._exe, self.parent, self._ppid = name, exe, parent, ppid

    def name(self) -> str:
        return self._name

    def exe(self) -> str:
        return self._exe

    def ppid(self) -> int:
        return self._ppid

    def parents(self) -> list:
        out, p = [], self.parent
        while p:
            out.append(p)
            p = p.parent
        return out


@pytest.mark.parametrize(
    ("chain", "expected"),
    [
        ([("node", "/opt/node"), ("zsh", "/bin/zsh"), ("Code Helper", "/Applications/Visual Studio Code.app/x")], True),
        ([("ruff", "/u/.vscode/extensions/ruff/bin/ruff"), ("zsh", "/bin/zsh")], False),
        (
            [("biome", "/wt/node_modules/biome"), ("Code Helper (Plugin)", "/Applications/Visual Studio Code.app/x")],
            False,
        ),
        ([("copilot-runtime", "/Applications/Visual Studio Code.app/r"), ("zsh", "/bin/zsh")], False),
    ],
)
def test_only_what_a_shell_started_counts_as_the_agents(monkeypatch, chain, expected) -> None:
    parent = None
    for name, exe in reversed(chain):
        parent = FakeProc(name, exe, parent)
    monkeypatch.setattr(leftovers.psutil, "Process", lambda _pid: parent)
    assert leftovers.agent_started(1234) is expected


@pytest.mark.parametrize(
    ("exe", "expected"), [("/opt/node", True), ("/usr/bin/git", True), ("/usr/libexec/lsd", False), ("", False)]
)
def test_a_detached_process_counts_unless_it_is_the_systems(monkeypatch, exe, expected) -> None:
    monkeypatch.setattr(leftovers.psutil, "Process", lambda _pid: FakeProc("x", exe, FakeProc("launchd", ""), ppid=1))
    assert leftovers.agent_started(1234) is expected


def test_a_real_shell_child_is_the_agents() -> None:
    proc = subprocess.Popen(["sh", "-c", "sleep 30; true"])  # noqa: S607
    try:
        for _ in range(100):
            if children := psutil.Process(proc.pid).children():
                break
            time.sleep(0.02)
        assert children
        assert leftovers.agent_started(children[0].pid)
    finally:
        for child in psutil.Process(proc.pid).children():
            child.kill()
        proc.kill()
        proc.wait()


def test_settle_terminates_leftovers_and_confirms_only_an_empty_scan(tmp_path: Path) -> None:
    proc = subprocess.Popen(["sleep", "30"])  # noqa: S607

    def find(_root, _since) -> list[int]:
        return [] if proc.poll() is not None else [proc.pid]

    def wait(_s: float) -> None:
        proc.wait(timeout=5)

    t = leftovers.settle(tmp_path, None, find=find, wait=wait)
    assert (t.confirmed, t.survivors, proc.returncode) == (True, (), -signal.SIGTERM)
    stuck = leftovers.settle(tmp_path, None, find=lambda *_: [999999], wait=lambda _s: None)
    assert (stuck.confirmed, stuck.survivors) == (False, (999999,))

    def broken(*_a) -> list[int]:
        message = "process table could not be scanned"
        raise WorktreeProcessScanError(message)

    failed = leftovers.settle(tmp_path, None, find=broken)
    assert (failed.confirmed, failed.problems) == (False, ("process table could not be scanned",))


def test_the_profile_runtime_chooses_where_sessions_run(tmp_path: Path, monkeypatch) -> None:
    store, calls = Store(tmp_path), []
    monkeypatch.setattr(sessions.vscode_adapter, "run", lambda _cfg, inbox: calls.append(("vscode", inbox)) or Run("v"))

    async def sdk(_cfg) -> Run:
        calls.append(("sdk", None))
        return Run("s")

    monkeypatch.setattr(sessions.sdk_adapter, "run", sdk)
    sessions.run(store, session())
    store.write_profile(Profile(runtime="vscode"))
    sessions.run(store, session())
    sessions.run(store, session(attachments=({"type": "blob"},)))
    assert [c[0] for c in calls] == ["sdk", "vscode", "vscode"]  # screenshots follow the runtime too (C7)
    inbox = calls[1][1]
    assert (inbox.parent, inbox.suffix) == (tmp_path / "steps", ".json")


def test_the_cli_switches_the_runtime_and_shows_it(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(cli.profile, "detect", lambda _r, _g, prev: prev or Profile())
    monkeypatch.setattr(cli.profile, "provider", lambda *_a: SimpleNamespace())
    store = Store(tmp_path)
    assert cli.show_profile(store, tmp_path, [], None, "vscode").endswith("Runtime: vscode")
    assert store.read_profile().runtime == "vscode"
    assert cli.show_profile(store, tmp_path, []).endswith("Runtime: vscode")
    with pytest.raises(SystemExit):
        cli.main(["profile", "--runtime", "auto"])


def test_connect_uses_a_running_host_without_opening_a_window(tmp_path, monkeypatch):
    calls: list[object] = []
    monkeypatch.setattr(ahp, "endpoint", lambda: "entry")
    monkeypatch.setattr(ahp, "connect", lambda entry, _client, _token: calls.append(("connect", entry)) or "conn")
    monkeypatch.setattr(vscode_adapter, "_token", lambda: "t")
    monkeypatch.setattr(vscode_adapter, "launch_code_chat", lambda args, cwd: calls.append(("open", args, cwd)))

    assert vscode_adapter.connect(tmp_path) == "conn"
    assert calls == [("connect", "entry")]
