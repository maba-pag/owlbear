import os
import plistlib
import subprocess
import sys
from pathlib import Path

import pytest

from owlbear_delivery_next.commands import cli
from owlbear_delivery_next.local_system import local_home
from owlbear_delivery_next.machine_host import command, control, install


def test_help_and_completion_load_no_command_module() -> None:
    code = (
        "import sys; from owlbear_delivery_next.machine_host import command; command.parser(); "
        "print(sorted(m for m in sys.modules if m.startswith('owlbear_delivery_next.')))"
    )
    done = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, check=True)  # noqa: S603
    assert done.stdout.strip() == "['owlbear_delivery_next.machine_host', 'owlbear_delivery_next.machine_host.command']"


def test_project_commands_run_as_owlbear_next_with_the_repo_before_them(monkeypatch) -> None:
    called = []
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
    assert install.install(said.append, pytest.fail, command.parser()) == 1  # not the installed runtime
    monkeypatch.setattr(install, "runtime", lambda: Path(sys.executable).parent.parent)
    monkeypatch.setattr(control, "autostart", lambda _say, *, on: items.append(on) or 0)
    answers = iter([True, False])
    assert install.install(said.append, lambda q: asked.append(q) or next(answers), command.parser()) == 0
    completion = local_home.root() / install.COMPLETION
    assert ("#compdef owlbear" in completion.read_text(), (Path.home() / ".zshrc").exists()) == (True, False)
    assert (install.link_path().readlink(), items, len(asked)) == (Path(sys.executable).parent / "owlbear", [], 2)
    assert install.uninstall(said.append) == 0
    assert (install.link_path().is_symlink(), completion.exists(), items) == (False, False, [False])


def test_the_login_item_runs_the_machine_host_with_this_path_and_a_refusal_is_said(monkeypatch) -> None:
    calls, said = [], []
    refuse = [0]

    def launchctl(args, **_kw):
        calls.append(args[1])
        return subprocess.CompletedProcess(args, refuse[0] if args[1] == "bootstrap" else 0, b"", b"denied")

    monkeypatch.setattr(control.subprocess, "run", launchctl)
    assert control.autostart(said.append, on=True) == 0
    item = plistlib.loads(control.plist_path().read_bytes())
    assert (item["ProgramArguments"], item["EnvironmentVariables"]["PATH"]) == (control.argv(), os.environ["PATH"])
    assert (item["RunAtLoad"], calls) == (True, ["bootout", "bootstrap"])
    refuse[0] = 1
    assert control.autostart(said.append, on=True) == 1
    assert "macOS refused to load it (denied)" in said[-1]
    assert control.autostart(said.append, on=False) == 0
    assert not control.plist_path().exists()


def test_start_runs_one_detached_host_and_stop_ends_it() -> None:
    said = []
    assert control.start(said.append) == 0
    rec = control.serve.running()
    assert said[-1] == f"OwlBear started, paused until you press Resume: {rec.url}#token={rec.token}"
    assert control.start(said.append) == 0
    assert said[-1].startswith("OwlBear is running")
    assert control.projects() == {"paused": True, "waiting": 0, "projects": []}
    assert control.stop(said.append) == 0
    assert (control.serve.running(), said[-1]) == (None, "OwlBear stopped; running steps finish on their own")
    logged = (local_home.root() / control.LOG).read_text()
    assert ("paused until you press Resume" in logged, "stopped: every project closed" in logged) == (True, True)


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
    monkeypatch.setattr(control, "argv", lambda: [sys.executable, "-c", "raise SystemExit(3)"])
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
