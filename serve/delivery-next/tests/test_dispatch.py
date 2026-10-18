"""TD-173: every Delivery process starts through one lazy dispatcher, ``python -m owlbear_delivery_next <command>``."""

import subprocess
import sys
from pathlib import Path

import pytest

from owlbear_delivery_next.commands import dispatch, setup


def started(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(  # noqa: S603 - this interpreter and the package
        [sys.executable, "-m", "owlbear_delivery_next", *args], capture_output=True, text=True, check=False
    )


@pytest.mark.parametrize(
    ("args", "prog"),
    [
        (["--help"], "usage: owlbear-next"),
        (["run", "--help"], "usage: python -m owlbear_delivery_next run"),
        (["mcp", "--help"], "usage: python -m owlbear_delivery_next mcp"),
        (["step-mcp", "--help"], "usage: python -m owlbear_delivery_next step-mcp"),
    ],
)
def test_each_process_starts_through_the_dispatcher(args, prog) -> None:
    done = started(*args)
    assert (done.returncode, done.stdout.startswith(prog)) == (0, True), done.stderr


def test_the_dispatcher_loads_only_the_command_it_runs(monkeypatch) -> None:
    code = (
        "import sys; from owlbear_delivery_next.commands import dispatch; "
        "print(sorted(m for m in sys.modules if m.startswith('owlbear_delivery_next.')))"
    )
    done = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, check=True)  # noqa: S603
    assert done.stdout.strip() == "['owlbear_delivery_next.commands', 'owlbear_delivery_next.commands.dispatch']"
    called = []
    monkeypatch.setattr(dispatch, "import_module", lambda name: type("M", (), {"main": lambda rest: called.append(
        (name, rest)) or 3}))  # fmt: skip
    assert dispatch.main(["run", "c1", "--repo", "/r"]) == 3
    assert dispatch.main(["--repo", "/r", "status"]) == 3
    assert dispatch.main(["machine"]) == 3
    assert called == [
        ("owlbear_delivery_next.commands.runner", ["c1", "--repo", "/r"]),
        ("owlbear_delivery_next.commands.cli", ["--repo", "/r", "status"]),
        ("owlbear_delivery_next.machine_host.serve", []),
    ]


def test_the_chat_server_names_only_the_dispatcher() -> None:
    server = setup.with_server({}, "/py", Path("/r"))["mcpServers"][setup.SERVER]
    assert (server["command"], server["args"]) == ("/py", ["-m", "owlbear_delivery_next", "mcp", "--repo", "/r"])
