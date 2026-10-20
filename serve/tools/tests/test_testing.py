"""Behavioral tests for maintained test command wrappers."""

from __future__ import annotations

import fcntl
import sys
import threading
from pathlib import Path
from unittest.mock import patch

import pytest

from owlbear_tools import testing as testing_module
from owlbear_tools.testing import _commands_for_paths, _require_development_checkout
from owlbear_tools.testing import test_main as run_test

_ROOT = Path(__file__).resolve().parents[3]


def test_python_source_routes_to_owning_package_tests() -> None:
    commands = _commands_for_paths(
        ["serve/tools/src/owlbear_tools/commands.py"],
        all_tests=False,
        coverage=False,
    )

    command = commands[0][0]
    assert command[:4] == ["uv", "run", "--locked", "pytest"]
    assert any(path.startswith("serve/tools/tests/test_") for path in command)
    assert "tests/test_package_boundary.py" in command


def test_package_test_support_file_routes_to_package_test_modules() -> None:
    scope = testing_module._python_scope("serve/delivery-next/tests/conftest.py")  # noqa: SLF001

    assert scope
    assert all(Path(path).name.startswith("test_") and path.endswith(".py") for path in scope)
    assert "serve/delivery-next/tests/test_config.py" in scope


def test_package_test_module_routes_to_itself() -> None:
    scope = testing_module._python_scope("serve/tools/tests/test_testing.py")  # noqa: SLF001

    assert scope == ["serve/tools/tests/test_testing.py"]


_LOOP = "serve/delivery-next/src/owlbear_delivery_next/change_flow/loop.py"
_PAGE = "serve/delivery-next/src/owlbear_delivery_next/web/config.html"


def _routed(*paths: str, coverage: bool = False) -> list[list[str]]:
    commands = _commands_for_paths(list(paths), all_tests=False, coverage=coverage)
    return [command for command, _cwd in commands]


def test_delivery_next_source_runs_testmon_beside_the_tests_it_cannot_see() -> None:
    (plain, monitored) = _routed(_LOOP)

    assert "serve/delivery-next/tests/test_dispatch.py" in plain  # runs the package in a child process
    assert {"serve/delivery-next/tests/test_layers.py", "serve/delivery-next/tests/test_module_rules.py"} <= set(plain)
    assert "tests/test_package_boundary.py" in plain
    assert "serve/delivery-next/tests/test_loop.py" not in plain
    assert monitored[:3] == [
        "env",
        "COVERAGE_CORE=ctrace",
        "TESTMON_DATAFILE=.owlbear/scratch/testmon-delivery-next.db",
    ]
    assert monitored[-2:] == ["--testmon", "--testmon-forceselect"]
    assert "serve/delivery-next/tests/test_loop.py" in monitored
    assert not set(plain) & {path for path in monitored if path.endswith(".py")}


@pytest.mark.parametrize(
    "paths",
    [(_PAGE,), (_PAGE, _LOOP), ("serve/delivery-next/tests/conftest.py", _LOOP)],
    ids=["page", "page-and-source", "fixture-and-source"],
)
def test_a_delivery_next_change_testmon_cannot_see_runs_the_whole_package(paths: tuple[str, ...]) -> None:
    (command,) = _routed(*paths)

    assert "serve/delivery-next/tests/test_loop.py" in command
    assert "--testmon" not in command


@pytest.mark.parametrize(
    ("paths", "coverage"),
    [
        ((_LOOP,), True),
        ((_LOOP, "setup/init.py"), False),
        (("serve/delivery-next/src/owlbear_delivery_next/gone.py",), False),
    ],
    ids=["coverage", "unknown-path", "deleted-source"],
)
def test_coverage_unknown_paths_and_deleted_sources_keep_the_old_scope(
    paths: tuple[str, ...],
    coverage: bool,  # noqa: FBT001 - a parametrized case
) -> None:
    (command,) = _routed(*paths, coverage=coverage)

    assert "--testmon" not in command
    assert "serve/delivery-next/tests/test_loop.py" in command or command[4:6] == ["tests", "serve"]


def test_testmon_runs_sharing_a_data_file_wait_for_each_other(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(testing_module, "_REPOSITORY_ROOT", tmp_path)
    lock = tmp_path / "t.db.lock"
    held = lock.open("a")
    fcntl.flock(held, fcntl.LOCK_EX)  # another run of this checkout
    waiting, blocked = threading.Event(), []

    def call(*_args: object, **kwargs: object) -> int:
        with lock.open("a") as third:  # a third run while this one's command runs
            try:
                fcntl.flock(third, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                blocked.append(kwargs["pass_fds"])
        return 0

    def said(*args: object, **_kwargs: object) -> None:
        if "Waiting" in str(args[0]):
            waiting.set()

    with patch("builtins.print", side_effect=said), patch("owlbear_tools.testing.subprocess.call", side_effect=call):
        command = (["env", "TESTMON_DATAFILE=t.db", "uv"], tmp_path)
        run = threading.Thread(target=testing_module._run_commands, args=([command],))  # noqa: SLF001
        run.start()
        assert waiting.wait(5)
        assert blocked == []  # nothing ran while the other run held the lock
        held.close()
        run.join(5)

    assert len(blocked) == 1  # held while the command ran
    assert len(blocked[0]) == 1  # and handed to its process tree


def test_knowledge_source_routes_importing_root_and_invariant_tests() -> None:
    scope = testing_module._python_scope("serve/knowledge/src/owlbear_knowledge/query.py")  # noqa: SLF001

    assert scope is not None
    assert "tests/test_query_facade.py" in scope
    assert "tests/test_query_facade_search.py" in scope
    assert "tests/test_ingest_coordinator_delete.py" in scope
    assert "tests/test_source_fetcher.py" in scope
    assert "tests/test_package_boundary.py" in scope


def test_memory_source_routes_confirmation_cycle() -> None:
    scope = testing_module._python_scope("serve/memory/src/owlbear_memory/engine.py")  # noqa: SLF001

    assert scope is not None
    assert "tests/test_confirmation_cycle.py" in scope


def test_setup_source_falls_back_to_full_python_suite() -> None:
    scope = testing_module._python_scope("setup/init.py")  # noqa: SLF001

    assert scope is None


def test_hook_source_routes_guard_tests() -> None:
    scope = testing_module._python_scope(".owlbear/hooks/deny-src-writes.py")  # noqa: SLF001

    assert scope == ["tests/test_write_guard_hooks.py"]


def test_deleted_test_path_falls_back_to_full_python_suite() -> None:
    commands = _commands_for_paths(["tests/test_deleted.py"], all_tests=False, coverage=False)

    assert commands == [(["uv", "run", "--locked", "pytest", "tests", "serve"], _ROOT)]


def test_markdown_outside_shared_roots_needs_no_test_scope() -> None:
    commands = _commands_for_paths(["README.md"], all_tests=False, coverage=False)

    assert commands == []


def test_all_runs_the_python_suite_with_coverage() -> None:
    commands = _commands_for_paths([], all_tests=True, coverage=True)

    assert commands == [(["uv", "run", "--locked", "pytest", "tests", "serve", "--cov"], _ROOT)]


def test_docs_only_paths_exit_without_running_tests(capsys: pytest.CaptureFixture[str]) -> None:
    with (
        patch.object(sys, "argv", ["test", "share/README.md"]),
        patch("owlbear_tools.testing.subprocess.call") as call,
        pytest.raises(SystemExit, match="0"),
    ):
        run_test()

    call.assert_not_called()
    assert "No test scope matched" in capsys.readouterr().out


def test_no_paths_runs_the_full_suite() -> None:
    with (
        patch.object(sys, "argv", ["test"]),
        patch("owlbear_tools.testing.subprocess.call", return_value=0) as call,
        pytest.raises(SystemExit, match="0"),
    ):
        run_test()

    call.assert_called_once_with(["uv", "run", "--locked", "pytest", "tests", "serve"], cwd=_ROOT)


def test_changed_runs_git_scope_and_accepts_explicit_base() -> None:
    with (
        patch.object(sys, "argv", ["test", "--changed", "--base", "origin/dev"]),
        patch(
            "owlbear_tools.testing._changed_paths", return_value=["serve/tools/src/owlbear_tools/commands.py"]
        ) as changed_paths,
        patch("owlbear_tools.testing.subprocess.call", return_value=0) as call,
        pytest.raises(SystemExit, match="0"),
    ):
        run_test()

    changed_paths.assert_called_once_with("origin/dev")
    command = call.call_args.args[0]
    assert command[:4] == ["uv", "run", "--locked", "pytest"]
    assert "tests/test_package_boundary.py" in command


def test_changed_scope_falls_back_to_full_suite_when_git_scope_is_unavailable() -> None:
    with (
        patch.object(sys, "argv", ["test", "--changed"]),
        patch(
            "owlbear_tools.testing._changed_paths",
            side_effect=testing_module._ChangedScopeError("missing upstream"),  # noqa: SLF001
        ),
        patch("owlbear_tools.testing.subprocess.call", return_value=0) as call,
        pytest.raises(SystemExit, match="0"),
    ):
        run_test()

    assert call.call_args.args[0] == ["uv", "run", "--locked", "pytest", "tests", "serve"]


def test_failures_are_aggregated_across_all_commands() -> None:
    commands = [(["uv", "run", "pytest", "a"], _ROOT), (["uv", "run", "pytest", "b"], _ROOT)]
    with (
        patch.object(sys, "argv", ["test", "--all"]),
        patch("owlbear_tools.testing._commands_for_paths", return_value=commands),
        patch("owlbear_tools.testing.subprocess.call", side_effect=[1, 0]) as call,
        pytest.raises(SystemExit, match="1"),
    ):
        run_test()

    assert call.call_count == 2


def test_commands_reject_consumer_checkouts(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)

    with pytest.raises(RuntimeError, match="development checkout root"):
        _require_development_checkout()
