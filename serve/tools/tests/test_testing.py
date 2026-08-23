"""Behavioral tests for maintained test command wrappers."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

from owlbear_tools.testing import _commands_for_paths, _require_development_checkout
from owlbear_tools.testing import test_e2e_main as run_test_e2e
from owlbear_tools.testing import test_main as run_test

_ROOT = Path(__file__).resolve().parents[3]
_WEB = _ROOT / "serve/cockpit/web"


def test_python_source_routes_to_owning_package_tests() -> None:
    commands = _commands_for_paths(
        ["serve/tools/src/owlbear_tools/commands.py"],
        all_tests=False,
        python_only=False,
        web_only=False,
        coverage=False,
    )

    assert commands == [(["uv", "run", "pytest", "serve/tools/tests"], _ROOT)]


def test_shared_web_content_source_routes_to_owning_package_tests() -> None:
    commands = _commands_for_paths(
        ["serve/web-content/src/owlbear_web_content/extractor.py"],
        all_tests=False,
        python_only=False,
        web_only=False,
        coverage=False,
    )

    assert commands == [(["uv", "run", "pytest", "serve/web-content/tests"], _ROOT)]


def test_shared_web_content_path_executes_owning_package_suite() -> None:
    with (
        patch.object(sys, "argv", ["test", "serve/web-content/src/owlbear_web_content/extractor.py"]),
        patch("owlbear_tools.testing.subprocess.call", return_value=0) as call,
        pytest.raises(SystemExit, match="0"),
    ):
        run_test()

    call.assert_called_once_with(["uv", "run", "pytest", "serve/web-content/tests"], cwd=_ROOT)


def test_frontend_source_routes_to_vitest() -> None:
    commands = _commands_for_paths(
        ["serve/cockpit/web/src/App.tsx"],
        all_tests=False,
        python_only=False,
        web_only=False,
        coverage=False,
    )

    assert commands == [(["npm", "test"], _WEB)]


def test_markdown_outside_shared_roots_needs_no_test_scope() -> None:
    commands = _commands_for_paths(
        ["README.md"],
        all_tests=False,
        python_only=False,
        web_only=False,
        coverage=False,
    )

    assert commands == []


def test_all_runs_python_and_frontend_suites_with_coverage() -> None:
    commands = _commands_for_paths(
        [],
        all_tests=True,
        python_only=False,
        web_only=False,
        coverage=True,
    )

    assert commands == [
        (["uv", "run", "pytest", "tests", "serve", "--cov"], _ROOT),
        (["npm", "test", "--", "--coverage"], _WEB),
    ]


def test_docs_only_paths_exit_without_running_tests(capsys: pytest.CaptureFixture[str]) -> None:
    with (
        patch.object(sys, "argv", ["test", "share/README.md"]),
        patch("owlbear_tools.testing.subprocess.call") as call,
        pytest.raises(SystemExit, match="0"),
    ):
        run_test()

    call.assert_not_called()
    assert "No test scope matched" in capsys.readouterr().out


def test_no_paths_runs_all_suites() -> None:
    with (
        patch.object(sys, "argv", ["test"]),
        patch("owlbear_tools.testing.subprocess.call", side_effect=[0, 0]) as call,
        pytest.raises(SystemExit, match="0"),
    ):
        run_test()

    assert [item.args for item in call.call_args_list] == [
        (["uv", "run", "pytest", "tests", "serve"],),
        (["npm", "test"],),
    ]
    assert [item.kwargs for item in call.call_args_list] == [{"cwd": _ROOT}, {"cwd": _WEB}]


def test_failures_are_aggregated_across_all_suites() -> None:
    with (
        patch.object(sys, "argv", ["test", "--all"]),
        patch("owlbear_tools.testing.subprocess.call", side_effect=[1, 0]) as call,
        pytest.raises(SystemExit, match="1"),
    ):
        run_test()

    assert call.call_count == 2


@pytest.mark.parametrize(
    ("argv", "expected"),
    [
        (["test-e2e"], ["npm", "run", "test:e2e"]),
        (["test-e2e", "--all"], ["npm", "run", "test:e2e:all"]),
        (["test-e2e", "work.spec.ts"], ["npm", "run", "test:e2e", "--", "work.spec.ts"]),
    ],
)
def test_e2e_delegates_to_root_npm_scripts(argv: list[str], expected: list[str]) -> None:
    with (
        patch.object(sys, "argv", argv),
        patch("owlbear_tools.testing.subprocess.call", return_value=0) as call,
        pytest.raises(SystemExit, match="0"),
    ):
        run_test_e2e()

    call.assert_called_once_with(expected, cwd=_ROOT)


def test_commands_reject_consumer_checkouts(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)

    with pytest.raises(RuntimeError, match="development checkout root"):
        _require_development_checkout()
