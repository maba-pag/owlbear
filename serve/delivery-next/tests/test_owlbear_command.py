import os
import plistlib
import signal
import subprocess
import sys
import time
from pathlib import Path

import pytest

from owlbear_delivery_next.commands import cli
from owlbear_delivery_next.local_system import local_home
from owlbear_delivery_next.machine_host import command, control, install


def test_help_and_completion_load_no_command_module() -> None:
    code = (
        "import sys; from owlbear_delivery_next.machine_host import command; command.app(['--help']); "
        "command.app.generate_completion(shell='zsh'); "
        "print(sorted(m for m in sys.modules if m.startswith('owlbear_delivery_next.')))"
    )
    done = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, check=True)  # noqa: S603
    loaded = done.stdout.strip().splitlines()[-1]
    assert loaded == "['owlbear_delivery_next.machine_host', 'owlbear_delivery_next.machine_host.command']"


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


def test_the_login_item_runs_the_machine_host_with_this_path_and_a_refusal_is_said(monkeypatch, tmp_path) -> None:
    calls, said = [], []
    refuse = [0]

    def launchctl(args, **_kw):
        calls.append(args[1])
        return subprocess.CompletedProcess(args, refuse[0] if args[1] == "bootstrap" else 0, b"", b"denied")

    monkeypatch.setattr(control.subprocess, "run", launchctl)
    shim, node = tmp_path / "copilot-shim", tmp_path / "state" / "fnm_multishells" / "1_2" / "bin"
    monkeypatch.setenv("PATH", os.pathsep.join(["/opt/homebrew/bin", str(shim), str(node), "/usr/bin"]))
    assert (control.saved_path(), control.autostart(said.append, on=True)) == (None, 0)
    item = plistlib.loads(control.plist_path().read_bytes())
    assert (item["ProgramArguments"], control.saved_path()) == (control.argv(), "/opt/homebrew/bin:/usr/bin")
    assert item["ProgramArguments"][-1] == "machine"  # a login start is paused (TD-350)
    assert (item["RunAtLoad"], calls) == (True, ["bootout", "bootstrap"])
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
        f"login item: {name} not on its PATH" for name in ("gh", "copilot")
    ] + ["4 problems found"]


def test_start_runs_one_detached_host_and_stop_ends_it() -> None:
    said = []
    assert control.start(said.append) == 0
    rec = control.serve.running()
    assert said[-1] == f"OwlBear started, running: {rec.url}#token={rec.token}"
    assert control.start(said.append, paused=True) == 0
    assert said[-1].startswith("OwlBear is running")
    listed = control.projects()
    assert listed is not None
    assert listed | {"update": None} == {
        "paused": False, "waiting": 0, "projects": [], "ending": False, "left": [], "update_while_paused": True,
        "update": None, "updated": "", "announce": None,
    }  # fmt: skip
    assert listed["update"]["phase"] == "idle"
    assert control.stop(said.append) == 0
    assert (control.serve.running(), said[-1]) == (None, "OwlBear stopped; running steps finish on their own")
    logged = (local_home.root() / control.LOG).read_text()
    assert ("· running" in logged, "stopped: every project closed" in logged) == (True, True)


@pytest.mark.timeout(120)  # six real hosts start and stop in turn; a loaded CI runner needs more than 30 s
def test_a_start_asked_for_paused_or_after_a_crash_is_paused_and_a_restart_keeps_the_state(monkeypatch) -> None:
    """TD-350: only a login start, a start after a crash and one asked for paused wait for Resume."""
    said = []
    monkeypatch.setattr(command, "say", said.append)
    assert control.start(said.append, paused=True) == 0
    assert (said[-1].startswith("OwlBear started, paused until you press Resume"), control.projects()["paused"]) == (
        True, True
    )  # fmt: skip
    assert command.restart() == 0
    assert control.projects()["paused"] is True
    rec = control.serve.running()
    os.kill(rec.pid, signal.SIGKILL)
    while control.serve.running() is not None:
        time.sleep(0.05)
    assert control.start(said.append) == 0
    assert control.projects()["paused"] is True
    assert "(the last run crashed)" in (local_home.root() / control.LOG).read_text()
    assert control.stop(said.append) == 0
    assert (control.start(said.append), control.projects()["paused"]) == (0, False)
    assert (command.restart(), control.projects()["paused"]) == (0, False)
    assert (command.restart(paused=True), control.projects()["paused"]) == (0, True)
    assert control.stop(said.append) == 0


def test_a_host_that_fails_leaves_its_crash_mark_and_a_restart_of_an_unanswering_one_is_paused(monkeypatch) -> None:
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

    started, at = [], "2026-10-10T12:00:00Z"
    up = control.serve.HostRecord(url="http://127.0.0.1:9/", token="t", pid=9, started_at=at, code="")  # noqa: S106
    monkeypatch.setattr(control.serve, "running", lambda: up)
    monkeypatch.setattr(control, "projects", lambda: None)
    monkeypatch.setattr(control, "stop", lambda _say: 0)
    monkeypatch.setattr(control, "start", lambda _say, *, paused: started.append(paused) or 0)
    assert (command.restart(), started) == (0, [True])


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
