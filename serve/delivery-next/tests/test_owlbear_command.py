import io
import json
import os
import plistlib
import signal
import socket
import subprocess
import sys
import threading
import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from owlbear_delivery_next.commands import cli
from owlbear_delivery_next.local_system import data_repo, local_home
from owlbear_delivery_next.machine_host import app, command, control, install
from owlbear_delivery_next.runtimes import settings_read
from owlbear_delivery_next.state_store import registry


def test_help_and_completion_load_no_command_module() -> None:
    code = (
        "import sys; from owlbear_delivery_next.machine_host import command; command.app(['--help']); "
        "command.app.generate_completion(shell='zsh'); "
        "print(sorted(m for m in sys.modules if m.startswith('owlbear_delivery_next.')))"
    )
    done = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, check=True)  # noqa: S603
    loaded = done.stdout.strip().splitlines()[-1]
    assert loaded == (
        "['owlbear_delivery_next.commands', 'owlbear_delivery_next.commands.project_commands', "
        "'owlbear_delivery_next.machine_host', 'owlbear_delivery_next.machine_host.command']"
    )


def test_owlbear_help_and_completion_show_the_project_commands_options(capsys) -> None:
    command.app(["setup", "--help"])
    assert "--local-files" in capsys.readouterr().out
    script = command.app.generate_completion(shell="zsh")  # noqa: S604 - the script's shell; it is static
    assert ("--local-files" in script, "--person-check" in script) == (True, True)


def test_owlbear_next_refuses_a_usage_error_and_takes_the_repo_before_the_command(monkeypatch, capsys) -> None:
    with pytest.raises(SystemExit) as exc:
        cli.main(["setup", "--local-files", "bad"])
    assert (exc.value.code, "--local-files" in capsys.readouterr().err) == (2, True)
    ran = []
    monkeypatch.setattr(cli, "run", lambda a: ran.append(a) or 7)
    assert cli.main(["--repo=/r", "home"]) == 7
    assert (ran[0].command, ran[0].repo) == ("home", Path("/r"))
    assert cli.main(["profile", "--role", "builder=gpt-5:high"]) == 7
    assert (ran[1].role[0][0], ran[1].role[0][1].effort) == ("builder", "high")
    assert cli.main(["--repo", "/a", "--repo", "/b", "setup", "--yes", "--yes", "--folder", "a", "--folder=b"]) == 7
    assert (ran[2].repo, ran[2].yes, ran[2].folder) == (Path("/b"), True, "b")


@pytest.mark.parametrize(
    "argv", [[], ["--repo", "/r"], ["cases"], ["backlog"], ["improvement"], ["improvement", "retro"]]
)
def test_owlbear_next_without_a_command_exits_2_and_runs_nothing(monkeypatch, argv) -> None:
    monkeypatch.setattr(cli, "run", pytest.fail)
    with pytest.raises(SystemExit) as exc:
        cli.main(argv)
    assert exc.value.code == 2
    assert cli.main([*argv, "--help"]) == 0


def test_machine_commands_get_their_options_and_return_their_exit_code(monkeypatch) -> None:
    called = []
    monkeypatch.setattr(sys, "platform", "darwin")
    monkeypatch.setattr(control, "logs", lambda _say, lines: called.append(lines) or 0)
    monkeypatch.setattr(control, "autostart", lambda _say, *, on: called.append(on) or 1)
    assert (command.main(["logs", "-n", "5"]), command.main(["logs"]), command.main(["autostart", "off"])) == (0, 0, 1)
    assert called == [5, 40, False]


def test_project_commands_run_as_owlbear_next_with_the_repo_before_them(monkeypatch) -> None:
    called = []
    monkeypatch.setattr(sys, "platform", "darwin")  # CI runs on Linux, which the command refuses
    monkeypatch.setattr(cli, "main", lambda argv: called.append(argv) or 0)
    command.main(["setup", "--yes", "--repo", "/r"])
    command.main(["status", "--repo", "/r"])
    command.main(["home"])
    assert called == [["--repo", "/r", "setup", "--yes"], ["--repo", "/r", "status"], ["home"]]


def test_other_systems_are_refused(monkeypatch, capsys) -> None:
    monkeypatch.setattr(sys, "platform", "linux")
    assert command.main(["start"]) == 2
    assert "macOS only" in capsys.readouterr().err


def test_install_writes_the_completion_and_asks_before_each_change(monkeypatch) -> None:
    said, asked, items = [], [], []
    assert install.install(said.append, pytest.fail, command.app) == 1  # not the installed runtime
    monkeypatch.setattr(install, "runtime", lambda: Path(sys.executable).parent.parent)
    monkeypatch.setattr(control, "autostart", lambda _say, *, on: items.append(on) or 0)
    answers = iter([True, True, False])
    assert install.install(said.append, lambda q: asked.append(q) or next(answers), command.app) == 0
    completion = local_home.root() / install.COMPLETION
    script = completion.read_text()
    assert ("#compdef owlbear" in script, (Path.home() / ".zshrc").exists()) == (True, False)
    assert "paused until you press Resume" in script  # a description per command
    assert "How many lines to show" in script  # and per option
    assert "__complete" not in script  # static: TAB never starts Python (TD-263)
    assert "\n_cyclopts_owlbear() {" in script  # sourcing registers the function the script defines
    assert script.rstrip().splitlines()[-1].startswith("compdef _cyclopts_owlbear owlbear ")
    assert (install.link_path().readlink(), items, len(asked)) == (Path(sys.executable).parent / "owlbear", [], 3)
    agent, skill = (
        Path.home() / ".copilot" / p for p in ("agents/owlbear-shaper.agent.md", "skills/owlbear-change-shaping")
    )
    assert ("save_brief" in (skill / "SKILL.md").read_text(), agent.resolve().is_file()) == (True, True)  # TD-335
    (other := Path.home() / ".copilot" / "agents" / "mine.agent.md").write_text("someone else's")
    assert install.uninstall(said.append) == 0
    assert (install.link_path().is_symlink(), completion.exists(), items) == (False, False, [False])
    assert (agent.is_symlink(), skill.is_symlink(), other.exists()) == (False, False, True)
    skill.mkdir(parents=True)
    assert install.install(said.append, lambda q: "shaper" in q, command.app) == 0
    assert (said[-1], skill.is_symlink(), agent.is_symlink()) == (
        f"{skill} exists and is no link; left as it is",
        False,
        True,
    )
    agent.unlink()
    agent.symlink_to(Path.home() / "my-checkout" / agent.name)  # the owner's own link, even a dangling one
    assert (install.uninstall(said.append), agent.is_symlink()) == (0, True)


def test_install_without_a_terminal_says_each_choice_was_not_done(monkeypatch, capsys) -> None:
    monkeypatch.setattr(install, "runtime", lambda: Path(sys.executable).parent.parent)
    monkeypatch.setattr(control, "autostart", lambda *_a, **_k: pytest.fail("the login item was touched"))
    monkeypatch.setattr(sys, "stdin", io.StringIO())  # no terminal: an agent's shell
    assert install.install(command.say, command.ask_tty, command.app) == 0
    lines = capsys.readouterr().out.splitlines()
    assert [line for line in lines if line.startswith("not done, no terminal to answer: ")] == [
        f"not done, no terminal to answer: {q} Run `owlbear install` in a terminal to answer it."
        for q in (
            f"Link {install.link_path()} to {Path(sys.executable).parent / 'owlbear'}, so `owlbear` runs in any shell?",
            f"Link the shaper and its skill into {Path.home() / '.copilot'}, so New Change finds them anywhere?",
            "Start OwlBear at login, paused until you press Resume?",
        )
    ]
    assert not install.link_path().is_symlink()
    assert not (Path.home() / ".copilot" / "agents" / "owlbear-shaper.agent.md").is_symlink()


def test_the_login_item_runs_the_machine_host_with_this_path_and_a_refusal_is_said(monkeypatch, tmp_path) -> None:
    calls, said = [], []
    refuse = [0]

    def launchctl(args, **_kw):
        calls.append(args[1])
        return subprocess.CompletedProcess(args, refuse[0] if args[1] == "bootstrap" else 0, b"", b"denied")

    monkeypatch.setattr(control.subprocess, "run", launchctl)
    path = os.pathsep.join(["/opt/homebrew/bin", str(tmp_path / "fnm_multishells" / "1_2" / "bin"), "/usr/bin"])
    monkeypatch.setenv("PATH", path)
    monkeypatch.delenv("COPILOT_CLI_PATH", raising=False)
    assert (control.saved_env(), control.autostart(said.append, on=True)) == (None, 0)
    item = plistlib.loads(control.plist_path().read_bytes())
    assert (item["ProgramArguments"], control.saved_env()) == (control.argv(), {"PATH": path})
    assert item["ProgramArguments"][-1] == "machine"  # a login start is paused (TD-350)
    assert (item["RunAtLoad"], calls) == (True, ["bootout", "bootstrap"])
    monkeypatch.setenv("COPILOT_CLI_PATH", "/opt/copilot/copilot")
    assert control.autostart(said.append, on=True) == 0
    assert control.saved_env() == {"PATH": path, "COPILOT_CLI_PATH": "/opt/copilot/copilot"}
    refuse[0] = 1
    assert control.autostart(said.append, on=True) == 1
    assert "macOS refused to load it (denied)" in said[-1]
    assert control.autostart(said.append, on=False) == 0
    assert not control.plist_path().exists()


def test_doctor_runs_each_tool_and_checks_the_login_items_path(monkeypatch, tmp_path) -> None:
    def tool(folder: Path, name: str, code: int = 0) -> None:
        folder.mkdir(exist_ok=True)
        (folder / name).write_text(f"#!/bin/sh\necho {name} says {code}\nexit {code}\n")
        (folder / name).chmod(0o755)

    bin_, shim = tmp_path / "bin", tmp_path / "copilot-shim"
    for name in ("git", "gh", "uv", "copilot"):
        tool(bin_, name)
    tool(shim, "copilot", 1)
    monkeypatch.setenv("PATH", f"{shim}:{bin_}")
    monkeypatch.delenv("COPILOT_CLI_PATH", raising=False)
    said = []
    assert (install.doctor(said.append, []), said) == (0, ["all checks passed"])
    control.plist_path().parent.mkdir(parents=True)
    control.plist_path().write_bytes(plistlib.dumps({"EnvironmentVariables": {"PATH": f"{shim}:{bin_}"}}))
    tool(bin_, "uv", 2)
    (bin_ / "copilot").unlink()
    (bin_ / "gh").rename(tmp_path / "gh")  # only this shell's PATH has it
    monkeypatch.setenv("PATH", f"{shim}:{bin_}:{tmp_path}")
    said.clear()
    assert install.doctor(said.append, []) == 1
    assert said[:2] == [
        f"uv: {bin_ / 'uv'} does not run: uv says 2 · fix: reinstall it",
        f"copilot: Copilot CLI not found: only VS Code's shim {shim / 'copilot'}, which is not the CLI. "
        + install.copilot_cli.FIX,
    ]
    assert [line.split(" · ")[0] for line in said[2:]] == [
        f"login item: {name} not found" for name in ("gh", "copilot")
    ] + ["4 problems found"]
    real = tmp_path / "real"
    tool(real, "copilot")
    monkeypatch.setenv("COPILOT_CLI_PATH", str(tmp_path / "elsewhere"))  # this shell's override is not the login item's
    item = {"PATH": f"{shim}:{bin_}:{tmp_path}", "COPILOT_CLI_PATH": str(real / "copilot")}
    control.plist_path().write_bytes(plistlib.dumps({"EnvironmentVariables": item}))

    def login_item() -> list[str]:
        said.clear()
        install.doctor(said.append, [])
        return [line.split(" · ")[0] for line in said if line.startswith("login item:")]

    assert login_item() == []
    (real / "copilot").unlink()
    assert login_item() == [f"login item: copilot at its COPILOT_CLI_PATH {real / 'copilot'} not found"]


def shared_data() -> Path:
    """The default shared checkout, holding one file only it has."""
    data = local_home.root() / local_home.DATA
    subprocess.run(["git", "init", "-q", str(data)], check=True)  # noqa: S603, S607
    (data / "note.md").write_text("only here\n")
    return data


def test_uninstall_keeps_the_shared_data_and_says_what_only_it_holds(monkeypatch) -> None:
    monkeypatch.setattr(control, "autostart", lambda *_a, **_k: 0)
    data, said = shared_data(), []

    assert install.uninstall(said.append) == 0

    assert said[-2:] == [
        f"kept: your shared data at {data.resolve()}; uninstalling never removes it",
        "  only there: 1 file(s) not committed, 1 of them never added",
    ]
    assert (data / "note.md").read_text() == "only here\n"


def test_doctor_counts_a_shared_data_repository_it_cannot_use(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(install, "_tools", lambda _say: 0)
    monkeypatch.setattr(install, "_login_item", lambda _say: 0)
    monkeypatch.setenv("PATH", str(tmp_path))  # no gh
    (local_home.root() / "data.json").write_text(f'{{"repository": "{tmp_path / "gone"}"}}')
    said = []

    assert install.doctor(said.append, []) == 1

    assert said[0].startswith("shared data: problem: ")
    assert said[0].endswith(" · fix: `owlbear data` shows it")
    assert said[1:] == ["1 problem found"]


def test_status_says_the_shared_data_with_the_host_down_and_no_project() -> None:
    data, said = shared_data(), []

    assert control.status(said.append) == 0

    assert said == [
        "OwlBear is not running; `owlbear start` starts it",
        f"shared data: {data.resolve()} (default)",
        "login item: off",
    ]


@pytest.fixture
def no_host_left(monkeypatch, tmp_path):
    """A test that starts real hosts stops what it left running, even when it fails partway.

    The hosts are child processes, which this process's stubs never reach: their start read finds no Copilot CLI and
    no way to GitHub, and fails at once.
    """
    with socket.socket() as closed:
        closed.bind(("127.0.0.1", 0))
        port = closed.getsockname()[1]
    monkeypatch.setenv("COPILOT_CLI_PATH", str(tmp_path / "no-copilot"))
    for name in ("https_proxy", "HTTPS_PROXY"):
        monkeypatch.setenv(name, f"http://127.0.0.1:{port}")
    for name in ("no_proxy", "NO_PROXY"):
        monkeypatch.setenv(name, "")
    yield
    if control.serve.running() is not None:
        control.stop(lambda _said: None)


@pytest.mark.usefixtures("no_host_left")
def test_start_runs_one_detached_host_and_stop_ends_it() -> None:
    said = []
    assert control.start(said.append) == 0
    rec = control.serve.running()
    assert said[-1] == f"OwlBear started, running: {rec.url}#token={rec.token}"
    assert control.start(said.append, paused=True) == 0
    assert said[-1].startswith("OwlBear is running")
    listed = control.projects()
    assert listed is not None
    assert listed | {"update": None, "pack": None, "reads": None} == {
        "paused": False, "waiting": 0, "projects": [], "ending": False, "left": [], "update_while_paused": False,
        "update": None, "updated": "", "announce": None, "pack": None, "reads": None,
    }  # fmt: skip  # a real host: no Global and nothing set here, so it never updates while paused (2026-10-23)
    assert listed["update"]["phase"] == "idle"
    assert set(listed["pack"]) == {"install", "release"}  # its content depends on this machine's own pack
    end = time.monotonic() + 30
    while (reads := control.projects()["reads"])["read_at"] is None:  # the start read, against the outside world
        assert time.monotonic() < end, "the host never read at its start"
        time.sleep(0.2)
    assert (reads["failed"], reads["succeeded_at"], reads["notices"]) == (
        [settings_read.IMPECCABLE, settings_read.MODELS], None, []
    )  # fmt: skip
    assert control.stop(said.append) == 0
    assert (control.serve.running(), said[-1]) == (None, "OwlBear stopped; running steps finish on their own")
    logged = (local_home.root() / control.LOG).read_text()
    assert ("· running" in logged, "stopped: every project closed" in logged) == (True, True)


# TD-350: only a login start, a start after a crash and one asked for paused wait for Resume. Each of the next three
# tests starts real hosts in turn, so they stay apart to run in parallel; a loaded CI runner needs more than 30 s.


@pytest.mark.timeout(60)
@pytest.mark.usefixtures("no_host_left")
def test_a_start_asked_for_paused_is_paused_and_a_restart_keeps_it(monkeypatch) -> None:
    said = []
    monkeypatch.setattr(command, "say", said.append)
    assert control.start(said.append, paused=True) == 0
    assert (said[-1].startswith("OwlBear started, paused until you press Resume"), control.projects()["paused"]) == (
        True, True
    )  # fmt: skip
    assert command.restart() == 0
    assert control.projects()["paused"] is True
    assert control.stop(said.append) == 0


@pytest.mark.timeout(60)
@pytest.mark.usefixtures("no_host_left")
def test_a_start_after_a_crash_is_paused_and_one_after_a_stop_is_not(monkeypatch) -> None:
    said = []
    monkeypatch.setattr(command, "say", said.append)
    assert control.start(said.append) == 0
    os.kill(control.serve.running().pid, signal.SIGKILL)
    while control.serve.running() is not None:
        time.sleep(0.05)
    assert control.start(said.append) == 0
    assert control.projects()["paused"] is True
    assert "(the last run crashed)" in (local_home.root() / control.LOG).read_text()
    assert control.stop(said.append) == 0
    assert "Z stopping: SIGTERM received\n" in (local_home.root() / control.LOG).read_text()  # `owlbear stop`'s signal
    assert (control.start(said.append), control.projects()["paused"]) == (0, False)
    assert control.stop(said.append) == 0


@pytest.mark.timeout(60)
@pytest.mark.usefixtures("no_host_left")
def test_a_restart_keeps_a_running_host_running_unless_asked_for_paused(monkeypatch) -> None:
    said = []
    monkeypatch.setattr(command, "say", said.append)
    assert (control.start(said.append), control.projects()["paused"]) == (0, False)
    assert (command.restart(), control.projects()["paused"]) == (0, False)
    assert (command.restart(paused=True), control.projects()["paused"]) == (0, True)
    assert control.stop(said.append) == 0


def test_a_host_that_fails_leaves_its_crash_mark_and_a_restart_of_an_unanswering_one_is_paused(
    monkeypatch, capsys
) -> None:
    def fail(_self, **_kw):
        raise RuntimeError

    seen, real = [], control.serve.Machine
    monkeypatch.setattr(
        control.serve, "Machine", lambda rec, *, paused: seen.append(paused) or real(rec, paused=paused)
    )
    monkeypatch.setattr(control.serve.Server, "run", fail)
    for _ in range(2):
        with pytest.raises(RuntimeError):
            control.serve.serve(run=True)
    assert (seen, (local_home.root() / "host.json").exists()) == ([False, True], True)
    assert capsys.readouterr().out.count("stopping: the server failed (its error follows)\n") == 2

    started, at = [], "2026-10-10T12:00:00Z"
    up = control.serve.HostRecord(url="http://127.0.0.1:9/", token="t", pid=9, started_at=at, code="")  # noqa: S106
    monkeypatch.setattr(control.serve, "running", lambda: up)
    monkeypatch.setattr(control, "projects", lambda: None)
    monkeypatch.setattr(control, "stop", lambda _say: 0)
    monkeypatch.setattr(control, "start", lambda _say, *, paused: started.append(paused) or 0)
    assert (command.restart(), started) == (0, [True])


def test_a_start_removes_the_retired_decision_index_and_says_each_file_once(monkeypatch, capsys) -> None:
    home, warmed = local_home.root(), []
    home.mkdir(parents=True, exist_ok=True)
    for name in control.serve.RETIRED_INDEX:
        (home / name).write_bytes(b"old")
    monkeypatch.setattr(control.serve.Server, "run", lambda _self, **_kw: None)
    monkeypatch.setattr(control.serve, "warm", warmed.append)
    assert control.serve.serve(run=True) == 0
    first = capsys.readouterr().out
    assert control.serve.serve(run=True) == 0
    assert [n for n in control.serve.RETIRED_INDEX if (home / n).exists()] == []
    removed = [first.count(f"removed the retired decision index file {n}\n") for n in control.serve.RETIRED_INDEX]
    assert removed == [1] * 5
    assert "decision index" not in capsys.readouterr().out
    assert len(warmed) == 2  # once per start, after the projects loaded


def test_stop_never_signals_a_host_that_has_not_named_its_process(monkeypatch) -> None:
    said = []
    starting = control.serve.HostRecord(url="(starting)", token="", pid=0, started_at="2026-10-10T12:00:00Z", code="")
    monkeypatch.setattr(control.serve, "running", lambda: starting)
    monkeypatch.setattr(control, "WAIT", 0.3)
    monkeypatch.setattr(control.os, "kill", lambda *_a: pytest.fail("no signal to process 0's group"))
    assert control.stop(said.append) == 1
    assert "still starting" in said[-1]


def test_a_host_that_ends_at_once_is_reported_not_started(monkeypatch) -> None:
    said = []
    monkeypatch.setattr(control, "argv", lambda **_k: [sys.executable, "-c", "raise SystemExit(3)"])
    assert control.start(said.append) == 1
    assert said[-1] == "OwlBear ended at once (exit 3); see `owlbear logs`"


def test_a_running_host_whose_api_does_not_answer_is_no_success(monkeypatch) -> None:
    said = []
    at = "2026-10-10T12:00:00Z"
    up = control.serve.HostRecord(url="http://127.0.0.1:9/", token="t", pid=9, started_at=at, code="")  # noqa: S106
    monkeypatch.setattr(control.serve, "running", lambda: up)
    monkeypatch.setattr(control, "projects", lambda: None)
    monkeypatch.setattr(control, "WAIT", 0.3)
    monkeypatch.setattr(control.subprocess, "Popen", lambda *_a, **_k: pytest.fail("one host runs already"))
    assert control.start(said.append) == 1
    assert said[-1] == "OwlBear did not answer within 0 s; see `owlbear logs`"


def git(cwd: Path, *args: str) -> None:
    who = ["-c", "user.name=t", "-c", "user.email=t@example.com"]
    subprocess.run(["git", *who, *args], cwd=cwd, check=True, capture_output=True)  # noqa: S603, S607


def flip_channel(other: Path) -> tuple[str | None, str]:
    """Change Global's channel from another clone, on top of what this host's start carried into Global."""
    git(other, "pull", "-q")
    glob = json.loads((other / data_repo.CONFIG).read_text())
    was = glob.setdefault("machine", {}).get("channel")
    glob["machine"]["channel"] = "minor" if was == "major" else "major"
    (other / data_repo.CONFIG).write_text(json.dumps(glob, indent=1))
    git(other, "commit", "-qam", "elsewhere: Global's channel")
    git(other, "push", "-q")
    return was, glob["machine"]["channel"]


def test_the_host_reads_at_start_and_every_hour_and_both_pages_see_it(monkeypatch, tmp_path, shared_repo) -> None:
    """#810: the real ``serve`` reads once at its start and then waits an hour; a Global change from elsewhere that
    the next read finds is shown to the machine's pages and the project's Settings until dismissed."""
    root, remote = shared_repo
    other = tmp_path / "other"
    git(tmp_path, "clone", "-q", str(remote), str(other))
    monkeypatch.setenv(data_repo.VIEW, str(root))
    git(tmp_path, "init", "-q", str(tmp_path / "p"))
    git(tmp_path / "p", "commit", "-q", "--allow-empty", "-m", "i")
    pid = registry.register(tmp_path / "p").id
    waits, go = [], threading.Event()

    def gate(_self, stopping: threading.Event, seconds: float) -> bool:
        """The hour between reads, held until the test lets the next read run."""
        waits.append(seconds)
        while not (go.is_set() or stopping.is_set()):
            stopping.wait(0.05)
        go.clear()
        return stopping.is_set()

    def until(done, what: str) -> None:
        end = time.monotonic() + 30
        while not done():
            assert time.monotonic() < end, what
            time.sleep(0.05)

    checked = []

    def run(self, **_kw) -> None:
        machine = self.machine
        until(lambda: waits, "the host never read at its start")
        first = machine.reads.ledger.load()
        assert (first.read_at is not None, first.notices, waits) == (True, [], [3600])
        was, now = flip_channel(other)
        go.set()
        until(lambda: len(waits) == 2, "the hourly read never ran")
        assert waits == [3600] * 2  # an hour, whatever the constant says
        c = TestClient(app.create(machine), base_url="http://127.0.0.1",
                       headers={"authorization": f"Bearer {machine.record.token}"})  # fmt: skip
        polled = c.get("/api/next/projects").json()["reads"]
        shown = c.get(f"/p/{pid}/api/next/config/read").json()["reads"]
        notices = shown["notices"]
        assert polled["read_at"] == shown["read_at"]  # the page compares them to know a read it has not shown
        assert [(n["id"], n["key"], n["old"], n["new"]) for n in notices] == [
            (polled["notices"][0], "machine.channel", was and json.dumps(was), json.dumps(now))
        ]
        assert c.post("/api/next/settings-read/dismiss", json={"ids": polled["notices"]}).json()["notices"] == []
        assert c.get("/api/next/projects").json()["reads"]["notices"] == []
        assert c.get(f"/p/{pid}/api/next/config/read").json()["reads"]["notices"] == []
        checked.append(True)

    monkeypatch.setattr(settings_read.Reader, "pause", gate)
    monkeypatch.setattr(control.serve.Server, "run", run)
    assert control.serve.serve(run=True) == 0
    assert checked == [True]
    for t in [t for t in threading.enumerate() if t.name == "settings-read"]:
        t.join(5)
        assert not t.is_alive(), "the hourly read outlived its host"
