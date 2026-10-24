"""OwlBear's memory, knowledge and browser servers run pinned to their installed version, as the chat server does."""

import json
import os
import shutil
import subprocess
import sys
import sysconfig
from pathlib import Path

import pytest

from owlbear_delivery_next.commands import mcp_launch
from owlbear_delivery_next.local_system import leases, local_home
from owlbear_delivery_next.machine_host import versions

SITE = Path("lib") / f"python{sys.version_info.major}.{sys.version_info.minor}" / "site-packages"
PROBE = {
    "__init__.py": "",
    "__main__.py": (
        "import json, os, sys\n"
        "print(json.dumps({'exe': sys.executable, 'file': __file__, 'cwd': os.getcwd(),"
        " 'said': os.environ.get('SAID')}), flush=True)\n"
        "sys.stdin.readline()  # the test moves the alias and prunes meanwhile\n"
        "from owlbear_memory_mcp import later\n"
        "print(json.dumps({'later': later.__file__}), flush=True)\n"
    ),
    "later.py": "",  # imported only after the update
}


def installed(tag: str) -> Path:
    """An installed version whose interpreter finds its own probe ``owlbear_memory_mcp`` before the real one."""
    venv = local_home.root() / local_home.VERSIONS / tag / ".venv"
    (venv / "bin").mkdir(parents=True)
    base = Path(sys.base_prefix) / "bin" / Path(sys.executable).name
    (venv / "pyvenv.cfg").write_text(f"home = {base.parent}\ninclude-system-site-packages = false\n")
    (venv / "bin" / "python").symlink_to(base.resolve())
    probe = venv / SITE / "owlbear_memory_mcp"
    probe.mkdir(parents=True)
    for name, text in PROBE.items():
        (probe / name).write_text(text)
    dev = sysconfig.get_paths()["purelib"]  # Delivery itself, with its editable packages after the probe
    (venv / SITE / "zz_dev.pth").write_text(f"import site; site.addsitedir({dev!r})\n")
    return venv.parent


def alias(to: Path) -> None:
    runtime = local_home.root() / local_home.RUNTIME
    runtime.unlink(missing_ok=True)
    runtime.symlink_to(to)
    (to / versions.ACTIVATED).touch()


def launched(cwd: Path) -> subprocess.Popen[str]:
    python = local_home.root() / local_home.RUNTIME / ".venv" / "bin" / "python"
    return subprocess.Popen(  # noqa: S603 - the installed interpreter, through the alias as a chat starts it
        [str(python), "-m", "owlbear_delivery_next", "serve", "memory"], cwd=cwd, text=True,
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env={**os.environ, "SAID": "env"},
    )  # fmt: skip


def under(path: str, folder: Path) -> bool:
    """Whether *path* lies in *folder*; a venv's python is a link, so only its folder is resolved."""
    return Path(path).parent.resolve().is_relative_to(folder.resolve())


@pytest.mark.timeout(60)
def test_a_server_keeps_its_version_while_owlbear_updates_and_no_prune_takes_its_code(tmp_path, monkeypatch):
    monkeypatch.setattr(versions, "remove", shutil.rmtree)  # no repository behind these versions
    v1, v2 = installed("v1.0"), installed("v1.1")
    (local_home.root() / local_home.VERSIONS / "v1.2").mkdir()  # a third: v1.0 is old enough to go
    alias(v1)
    work = tmp_path / "work"
    work.mkdir()
    old = launched(work)
    try:
        first = json.loads(old.stdout.readline() or old.stderr.read())
        assert (
            Path(first["exe"]).parent == (v1 / ".venv" / "bin").resolve()
        )  # re-run from its own folder, not the alias
        assert under(first["file"], v1)
        assert (Path(first["cwd"]).resolve(), first["said"]) == (work.resolve(), "env")
        assert leases.held(v1) == [old.pid]
        alias(v2)  # OwlBear updated beneath it
        (v2.parent / "v1.2" / versions.ACTIVATED).touch()
        assert versions.prune() == []  # v1.0 is held; v1.1 runs
        old.stdin.write("go\n")
        old.stdin.flush()
        assert under(json.loads(old.stdout.readline())["later"], v1)  # imported after the update, from its version
        assert old.wait(10) == 0
    finally:
        old.kill()
    assert (leases.held(v1), list((v1 / leases.LEASES).iterdir())) == ([], [])
    assert versions.prune() == ["v1.0"]
    new = launched(work)
    try:
        assert under(json.loads(new.stdout.readline() or new.stderr.read())["exe"], v2)
        new.stdin.write("go\n")
        new.stdin.flush()
        assert new.wait(10) == 0
    finally:
        new.kill()


@pytest.mark.parametrize("argv", [[], ["cache"], ["memory", "extra"]])
def test_only_one_known_server_is_run(argv, capsys):
    assert mcp_launch.main(argv) == 2
    assert capsys.readouterr().err.startswith("usage: python -m owlbear_delivery_next serve {memory,knowledge,browser}")


def test_a_server_this_install_lacks_says_so_and_one_that_fails_to_import_raises(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(mcp_launch.importlib.util, "find_spec", lambda _name: None)
    assert mcp_launch.main(["browser"]) == 2
    assert "owlbear_browser_mcp is not installed in" in capsys.readouterr().err
    monkeypatch.undo()
    broken = tmp_path / "broken_mcp"
    broken.mkdir()
    (broken / "__init__.py").write_text("")
    (broken / "__main__.py").write_text("import no_such_dependency\n")
    monkeypatch.syspath_prepend(str(tmp_path))
    monkeypatch.setitem(mcp_launch.SERVERS, "browser", "broken_mcp")
    with pytest.raises(ModuleNotFoundError, match="no_such_dependency"):
        mcp_launch.main(["browser"])


@pytest.mark.timeout(60)
def test_the_real_memory_server_answers_over_stdio_with_protocol_only_output(tmp_path):
    (tmp_path / ".owlbear").mkdir()  # a workspace: the server reads its folder from the client's working folder
    asked = [
        {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2025-06-18",
         "capabilities": {}, "clientInfo": {"name": "t", "version": "0"}}},
        {"jsonrpc": "2.0", "method": "notifications/initialized"},
        {"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
    ]  # fmt: skip
    server = subprocess.Popen(
        [sys.executable, "-m", "owlbear_delivery_next", "serve", "memory"], cwd=tmp_path, text=True,
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    )  # fmt: skip
    try:
        server.stdin.write("".join(json.dumps(m) + "\n" for m in asked))
        server.stdin.flush()
        frames = [json.loads(server.stdout.readline()) for _ in range(2)]  # each line a frame: nothing else on stdout
        server.stdin.close()  # the client ends it, after its answers
        rest, err = server.communicate(timeout=20)
    finally:
        server.kill()
    assert (server.returncode, [f.get("id") for f in frames], rest) == (0, [1, 2], ""), err
    assert "save_memory" in [t["name"] for t in frames[1]["result"]["tools"]]
