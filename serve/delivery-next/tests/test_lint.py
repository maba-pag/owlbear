"""The builder's lint at submit (TD-87): real linters on temporary repositories."""

import asyncio
import contextlib
import os
import signal
import stat
import subprocess
import sys
import threading
import time
from pathlib import Path, PurePosixPath
from types import SimpleNamespace

import pytest

from owlbear_delivery_next import lint, sdk_adapter, tools
from owlbear_delivery_next.models import StepKind
from owlbear_delivery_next.permissions import Policy
from owlbear_delivery_next.results import ACCEPTED, ENDED, Gate
from owlbear_delivery_next.session_result import Run
from owlbear_delivery_next.steps import worktree

RUFF = '[tool.ruff]\nline-length = 100\n\n[tool.ruff.lint]\nselect = ["F"]\n'


def commit(work: Path, files: dict[str, str]) -> None:
    for name, text in files.items():
        (work / name).parent.mkdir(parents=True, exist_ok=True)
        (work / name).write_text(text)
    for args in (("add", "-A"), ("commit", "-qm", "work")):
        subprocess.run(["git", *args], cwd=work, check=True, capture_output=True)  # noqa: S603, S607


def head(work: Path) -> str:
    return worktree.head(work)


def gate(work: Path, since: str, log: list[dict]) -> Gate:
    cfg = sdk_adapter.Session(
        StepKind.BUILD,
        work,
        "s1",
        "m",
        resume=False,
        policy=Policy(work),
        observe=lambda: worktree.observe(work, "main", since),
        checks=(),
    )
    return Gate(cfg, Run("s1"), lambda **e: log.append(e), lambda: None)


def submit(g: Gate, *paths: str) -> tuple[str, bool]:
    return g.call(tools.SUBMIT, {"summary": "Work.", "changed_paths": list(paths), "checks": []})


def tool(folder: Path, name: str, script: str) -> Path:
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / name
    path.write_text(f"#!/bin/sh\n{script}\n")
    path.chmod(path.stat().st_mode | stat.S_IXUSR)
    return path


@pytest.fixture
def real_ruff(monkeypatch) -> None:
    """The package's own ruff, found on PATH; no uv.lock in the temporary repository, so no uv run."""
    monkeypatch.setenv("PATH", f"{Path(sys.executable).parent}:/usr/bin:/bin")


@pytest.mark.usefixtures("real_ruff")
def test_a_lint_error_in_a_changed_file_refuses_the_submit_until_it_is_fixed(change_repo: Path) -> None:
    commit(change_repo, {"pyproject.toml": RUFF, "old.py": "import os\n"})
    since, log = head(change_repo), []
    commit(change_repo, {"new.py": "import sys\nx=1\n"})
    g = gate(change_repo, since, log)
    text, ok = submit(g, "new.py")
    assert not ok
    assert "- lint: ruff check found problems in new.py - fix them, commit, then submit again:\n" in text
    assert "F401" in text
    assert "sys" in text
    assert "`os`" not in text  # old.py is not the task's change
    assert "- lint: ruff format found problems in new.py" in text
    commit(change_repo, {"new.py": "x = 1\n"})
    assert submit(g, "new.py") == (ACCEPTED, True)
    events = [e for e in log if e["event"] == "lint"]
    assert [e["passed"] for e in events] == [False, True]
    assert events[1]["ran"] == [
        {"tool": "ruff check", "files": ["new.py"], "state": "passed"},
        {"tool": "ruff format", "files": ["new.py"], "state": "passed"},
    ]


@pytest.mark.usefixtures("real_ruff")
def test_lint_refusals_never_end_the_step_and_pass_with_lint_unresolved_after_three(change_repo: Path) -> None:
    commit(change_repo, {"pyproject.toml": RUFF})
    since, log = head(change_repo), []
    commit(change_repo, {"new.py": "import sys\n"})
    g = gate(change_repo, since, log)
    assert [submit(g, "new.py")[1] for _ in range(3)] == [False, False, False]
    assert g.run.invalid == 0  # the invalid-submit limit is not spent on lint
    assert submit(g, "new.py") == (ACCEPTED, True)
    assert [e["event"] for e in log if e["event"].startswith("lint-")] == ["lint-unresolved"]


@pytest.mark.usefixtures("real_ruff")
def test_python_without_a_ruff_configuration_is_not_linted(change_repo: Path) -> None:
    since, log = head(change_repo), []
    commit(change_repo, {"new.py": "import sys\nx=1\n"})
    assert submit(gate(change_repo, since, log), "new.py")[1]
    assert [e for e in log if e["event"] == "lint"] == [
        {"event": "lint", "ran": [], "skipped": ["ruff: no configuration for new.py"], "passed": True}
    ]


def test_a_deleted_or_unlintable_file_runs_no_linter(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(lint, "run", lambda *_: pytest.fail("no linter runs"))
    (tmp_path / "pyproject.toml").write_text(RUFF)
    (tmp_path / "notes.md").write_text("x\n")
    log: list[dict] = []
    assert lint.Lint(lambda **e: log.append(e)).check(tmp_path, ["gone.py", "notes.md"]) == []
    assert log == []


def test_a_broken_linter_is_reported_once_then_skipped(change_repo: Path, tmp_path: Path, monkeypatch) -> None:
    tool(tmp_path / "bin", "ruff", "echo 'ruff: panicked' >&2; exit 2")
    monkeypatch.setenv("PATH", f"{tmp_path / 'bin'}:/usr/bin:/bin")
    commit(change_repo, {"ruff.toml": "line-length = 100\n"})
    since, log = head(change_repo), []
    commit(change_repo, {"new.py": "x = 1\n"})
    g = gate(change_repo, since, log)
    text, ok = submit(g, "new.py")
    assert not ok
    assert "- lint: ruff check could not run (exited 2) on new.py" in text
    assert "ruff: panicked" in text
    assert submit(g, "new.py") == (ACCEPTED, True)
    skipped = [e for e in log if e["event"] == "lint-skipped"]
    assert skipped == [
        {"event": "lint-skipped", "tool": "ruff check", "reason": "exited 2"},
        {"event": "lint-skipped", "tool": "ruff format", "reason": "exited 2"},
    ]


def test_node_linters_run_from_their_configuration_on_its_files(change_repo: Path) -> None:
    web = change_repo / "web"
    tool(web / "node_modules" / ".bin", "biome", 'echo "biome $*"; exit 1')
    tool(change_repo / "node_modules" / ".bin", "eslint", 'echo "eslint $*"; exit 0')
    commit(change_repo, {"web/biome.json": "{}", "eslint.config.js": "export default [];\n", ".gitignore": "node_*\n"})
    since, log = head(change_repo), []
    commit(change_repo, {"web/src/a.ts": "let a = 1\n", "tool.js": "x\n"})
    text, ok = submit(gate(change_repo, since, log), "tool.js", "web/src/a.ts")
    assert not ok
    assert "- lint: biome found problems in web/src/a.ts - fix them, commit, then submit again:\n" in text
    assert "biome check --colors=off --no-errors-on-unmatched src/a.ts" in text
    ran = next(e for e in log if e["event"] == "lint")["ran"]
    assert ran == [
        {"tool": "biome", "files": ["web/src/a.ts"], "state": "failed"},
        {"tool": "eslint", "files": ["tool.js", "web/src/a.ts"], "state": "passed"},
    ]


def test_biome_lints_changed_json_and_css_and_eslint_only_scripts(change_repo: Path) -> None:
    web = change_repo / "web"
    tool(web / "node_modules" / ".bin", "biome", 'echo "biome $*"; exit 0')
    tool(change_repo / "node_modules" / ".bin", "eslint", 'echo "eslint $*"; exit 0')
    commit(change_repo, {"web/biome.json": "{}", "eslint.config.js": "export default [];\n", ".gitignore": "node_*\n"})
    since, log = head(change_repo), []
    commit(change_repo, {"web/app.css": "a {}\n", "web/data.json": "{}\n", "web/a.ts": "x\n", "web/n.md": "x\n"})
    assert submit(gate(change_repo, since, log), "web/a.ts", "web/app.css", "web/data.json", "web/n.md")[1]
    ran = next(e for e in log if e["event"] == "lint")["ran"]
    assert ran == [
        {"tool": "biome", "files": ["web/a.ts", "web/app.css", "web/data.json"], "state": "passed"},
        {"tool": "eslint", "files": ["web/a.ts"], "state": "passed"},
    ]


def outside_binary(root: Path, outside: Path) -> None:
    (root / "web" / "node_modules" / ".bin").mkdir(parents=True)
    (root / "web" / "node_modules" / ".bin" / "biome").symlink_to(tool(outside, "biome", "exit 0"))


def outside_node_modules(root: Path, outside: Path) -> None:
    tool(outside / "nm" / ".bin", "biome", "exit 0")
    (root / "web").mkdir()
    (root / "web" / "node_modules").symlink_to(outside / "nm")


def outside_ancestor(root: Path, outside: Path) -> None:
    tool(outside / "web" / "node_modules" / ".bin", "biome", "exit 0")
    (outside / "web" / "biome.json").write_text("{}")
    (root / "web").symlink_to(outside / "web")


@pytest.mark.parametrize("escape", [outside_binary, outside_node_modules, outside_ancestor])
def test_a_node_linter_resolving_outside_the_repository_is_skipped(tmp_path: Path, escape) -> None:
    root, outside = tmp_path / "repo", tmp_path / "outside"
    root.mkdir()
    escape(root, outside)
    (root / "web" / "biome.json").write_text("{}")
    linters, skipped = lint.plan(root, ["web/a.ts"])
    assert linters == []
    assert skipped == ["biome for web: its executable or folder resolves outside the repository"]


def test_a_node_linter_linked_inside_the_repository_runs_from_its_real_path(tmp_path: Path) -> None:
    real = tool(tmp_path / "web" / "node_modules" / "@biomejs" / "biome" / "bin", "biome", "exit 0")
    (tmp_path / "web" / "node_modules" / ".bin").mkdir()
    (tmp_path / "web" / "node_modules" / ".bin" / "biome").symlink_to("../@biomejs/biome/bin/biome")
    (tmp_path / "web" / "biome.json").write_text("{}")
    linters, skipped = lint.plan(tmp_path, ["web/a.ts"])
    assert (skipped, [x.command[0] for x in linters]) == ([], [str(real.resolve())])


def test_linters_share_one_budget_and_later_ones_are_skipped(tmp_path: Path, monkeypatch) -> None:
    tool(tmp_path / "bin", "ruff", "exit 0")
    tool(tmp_path / "node_modules" / ".bin", "biome", "exit 0")
    monkeypatch.setenv("PATH", str(tmp_path / "bin"))
    (tmp_path / "pyproject.toml").write_text(RUFF)
    (tmp_path / "biome.json").write_text("{}")
    (tmp_path / "a.py").write_text("x = 1\n")
    (tmp_path / "a.ts").write_text("x\n")
    clock, timeouts = [0.0], []

    def fake(_root: Path, _linter: lint.Linter, timeout: float) -> lint.Outcome:
        timeouts.append(timeout)
        clock[0] += 100
        return lint.Outcome("passed")

    monkeypatch.setattr(lint, "monotonic", lambda: clock[0])
    monkeypatch.setattr(lint, "run", fake)
    log: list[dict] = []
    assert lint.Lint(lambda **e: log.append(e)).check(tmp_path, ["a.py", "a.ts"]) == []
    assert timeouts == [120, 80]
    assert log[0]["skipped"] == ["biome: not run, the 180 s lint budget for this submit is spent"]


def test_a_timed_out_linter_is_reported_even_when_a_detached_child_holds_its_output(
    tmp_path: Path, monkeypatch
) -> None:
    pidfile = tmp_path / "child.pid"
    child = f"import os, time; os.setsid(); open('{pidfile}', 'w').write(str(os.getpid())); time.sleep(30)"
    script = tool(
        tmp_path,
        "slow",
        f'"{sys.executable}" -c "{child}" &\nwhile [ ! -s "{pidfile}" ]; do sleep 0.05; done\nsleep 30',
    )
    monkeypatch.setattr(lint, "DRAIN", 0.5)
    started = time.monotonic()
    try:
        out = lint.run(tmp_path, lint.Linter("slow", (str(script),), PurePosixPath(), ()), 1)
    finally:
        with contextlib.suppress(OSError, ValueError):
            os.kill(int(pidfile.read_text()), signal.SIGKILL)
    assert (out.state, out.reason) == ("broken", "timed out")
    assert "still holds it open" in out.output  # the drain was cut short, not ended by EOF
    assert time.monotonic() - started < 10


def test_a_linter_skipped_after_breaking_twice_is_not_run_again(tmp_path: Path, monkeypatch) -> None:
    calls = tmp_path / "calls"
    tool(tmp_path / "bin", "ruff", f'echo "$1" >> "{calls}"; exit 2')
    monkeypatch.setenv("PATH", str(tmp_path / "bin"))
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "ruff.toml").write_text("line-length = 100\n")
    (repo / "a.py").write_text("x = 1\n")
    log: list[dict] = []
    session = lint.Lint(lambda **e: log.append(e))
    assert len(session.check(repo, ["a.py"])) == 2
    assert session.check(repo, ["a.py"]) == []
    assert session.check(repo, ["a.py"]) == []
    assert calls.read_text().split() == ["check", "format"] * 2
    assert log[-1] == {
        "event": "lint",
        "ran": [],
        "skipped": [
            "ruff check: skipped for this session, it broke twice (exited 2)",
            "ruff format: skipped for this session, it broke twice (exited 2)",
        ],
        "passed": True,
    }


def test_an_ending_during_lint_is_not_held_up_and_the_result_is_not_accepted(change_repo: Path) -> None:
    commit(change_repo, {"pyproject.toml": RUFF})
    since, log = head(change_repo), []
    commit(change_repo, {"new.py": "x = 1\n"})
    g = gate(change_repo, since, log)
    linting, release, answer = threading.Event(), threading.Event(), []
    g.lint.check = lambda *_: linting.set() or (release.wait(10) and [])
    builder = threading.Thread(target=lambda: answer.append(submit(g, "new.py")))
    builder.start()
    try:
        assert linting.wait(5)
        deadline = threading.Thread(target=g.finish, args=("deadline", None, "step deadline"))
        deadline.start()
        deadline.join(2)
        assert not deadline.is_alive()
    finally:
        release.set()
        builder.join(5)
    assert answer == [(ENDED, False)]
    assert (g.run.ending, g.run.payload, g.run.head) == ("deadline", None, None)


def test_the_sdk_submit_runs_off_the_event_loop(tmp_path: Path) -> None:
    cfg = sdk_adapter.Session(
        StepKind.BUILD, tmp_path, "s1", "m", resume=False, policy=Policy(tmp_path), observe=tools.Worktree, checks=()
    )
    st = sdk_adapter._Step(cfg, SimpleNamespace(call_soon_threadsafe=lambda *_: None))  # noqa: SLF001
    ran: list[int] = []
    st.gate.call = lambda *_: ran.append(threading.get_ident()) or ("Rejected.", False)
    handler = next(t.handler for t in st.tools() if t.name == tools.SUBMIT.name)
    result = asyncio.run(handler(SimpleNamespace(arguments={})))
    assert (result.text_result_for_llm, result.result_type) == ("Rejected.", "failure")
    assert ran[0] != threading.get_ident()


def test_ruff_runs_through_uv_when_the_repository_locks_it(tmp_path: Path, monkeypatch) -> None:
    uv = tool(tmp_path / "bin", "uv", "exit 0")
    monkeypatch.setenv("PATH", str(tmp_path / "bin"))
    (tmp_path / "pyproject.toml").write_text(RUFF)
    (tmp_path / "uv.lock").write_text('[[package]]\nname = "ruff"\nversion = "0.16.5"\n')
    linters, skipped = lint.plan(tmp_path, ["a.py"])
    assert skipped == []
    assert [x.command[:6] for x in linters] == [(str(uv), "run", "--locked", "--offline", "--quiet", "ruff")] * 2
