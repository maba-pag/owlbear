"""Behavioral tests for maintained test command wrappers."""

from __future__ import annotations

import fcntl
import json
import sys
import threading
from importlib.metadata import version
from pathlib import Path
from unittest.mock import patch

import pytest

from owlbear_tools import task_scope
from owlbear_tools import testing as testing_module
from owlbear_tools.task_testing import _targets
from owlbear_tools.testing import _commands_for_paths, _require_development_checkout, _workspace_packages
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
_WEB = "serve/delivery-next/src/owlbear_delivery_next/web/"
_TESTS = "serve/delivery-next/tests/"


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


def test_a_delivery_next_change_testmon_cannot_see_runs_the_whole_package() -> None:
    (command,) = _routed("serve/delivery-next/tests/conftest.py", _LOOP)

    assert "serve/delivery-next/tests/test_loop.py" in command
    assert "--testmon" not in command


@pytest.mark.parametrize(
    ("page", "selected"),
    [
        ("pages/changes/forms.mjs", {"test_amendment_page.py", "test_spotter_question_page.py"}),
        ("config.html", {"test_machine_pages.py", "test_config_api.py"}),
    ],
    ids=["pages/changes/forms.mjs-selected0", "config.html-selected2"],
)
def test_a_page_change_runs_the_tests_that_load_pages(page: str, selected: set[str]) -> None:
    (command,) = _routed(_WEB + page)

    assert {_TESTS + name for name in selected} <= set(command)
    assert "tests/test_package_boundary.py" in command
    assert _TESTS + "test_loop.py" not in command


def test_a_page_change_beside_a_source_change_keeps_the_source_scope() -> None:
    (plain, monitored) = _routed(_WEB + "pages/changes/forms.mjs", _LOOP)

    assert _TESTS + "test_amendment_page.py" in plain
    assert _TESTS + "test_dispatch.py" in plain
    assert _TESTS + "test_loop.py" in monitored


@pytest.mark.parametrize(
    ("config", "expected"),
    [
        (
            ".pre-commit-config.yaml",
            (
                "tests/test_linter_formatter_policy.py",
                "serve/tools/tests/test_quality.py",
                "tests/test_dependency_verification_workflow.py",
            ),
        ),
        ("./.editorconfig", ("tests/test_linter_formatter_policy.py",)),
        ("biome.json", ("tests/test_linter_formatter_policy.py",)),
        (
            "package.json",
            ("tests/test_linter_formatter_policy.py", "tests/test_dependency_verification_workflow.py"),
        ),
        ("package-lock.json", ("tests/test_linter_formatter_policy.py",)),
        (".nvmrc", ("tests/test_linter_formatter_policy.py", "tests/test_dependency_verification_workflow.py")),
        (".markdownlint-cli2.jsonc", ("tests/test_linter_formatter_policy.py",)),
        ("renovate.json", ("tests/test_dependency_verification_workflow.py",)),
        (
            ".github/workflows/agent-ecosystem.yml",
            (
                "tests/test_ci_workflows.py",
                "tests/test_linter_formatter_policy.py",
                "tests/test_agent_ecosystem_validation.py",
                "serve/tools/tests/test_quality.py",
            ),
        ),
        (
            ".github/workflows/ci.yml",
            ("tests/test_ci_workflows.py", "tests/test_linter_formatter_policy.py", "tests/test_snyk_findings.py"),
        ),
        (
            ".github/workflows/copilot-setup-steps.yml",
            (
                "tests/test_ci_workflows.py",
                "tests/test_linter_formatter_policy.py",
                "tests/test_dependency_verification_workflow.py",
            ),
        ),
        (".github/workflows/python.yml", ("tests/test_ci_workflows.py", "tests/test_linter_formatter_policy.py")),
        (
            ".github/workflows/python-browser.yml",
            ("tests/test_ci_workflows.py", "tests/test_linter_formatter_policy.py"),
        ),
        (".github/workflows/static.yml", ("tests/test_ci_workflows.py", "tests/test_linter_formatter_policy.py")),
        (
            ".github/workflows/tooling.yml",
            (
                "tests/test_ci_workflows.py",
                "tests/test_linter_formatter_policy.py",
                "tests/test_dependency_verification_workflow.py",
            ),
        ),
        (
            ".github/workflows/security.yml",
            ("tests/test_ci_workflows.py", "tests/test_linter_formatter_policy.py", "tests/test_snyk_findings.py"),
        ),
        (
            ".github/workflows/release.yml",
            ("tests/test_ci_workflows.py", "tests/test_linter_formatter_policy.py", "tests/test_release.py"),
        ),
        (
            ".github/workflows/snyk-ignore.yml",
            ("tests/test_ci_workflows.py", "tests/test_linter_formatter_policy.py", "tests/test_snyk_findings.py"),
        ),
    ],
)
def test_known_root_configs_run_their_consumers(config: str, expected: tuple[str, ...]) -> None:
    (command,) = _routed(config)

    assert set(command[4:]) == {*expected, "tests/test_package_boundary.py"}


def test_config_and_source_scopes_are_combined() -> None:
    plain, monitored = _routed(".pre-commit-config.yaml", _LOOP)

    assert {
        "tests/test_linter_formatter_policy.py",
        "serve/tools/tests/test_quality.py",
        "tests/test_dependency_verification_workflow.py",
        "tests/test_package_boundary.py",
        _TESTS + "test_dispatch.py",
        _TESTS + "test_layers.py",
        _TESTS + "test_module_rules.py",
    } <= set(plain)
    assert _TESTS + "test_loop.py" in monitored
    assert not set(plain) & {path for path in monitored if path.endswith(".py")}


def test_config_and_page_scopes_are_combined() -> None:
    (command,) = _routed(".editorconfig", _WEB + "pages/metrics/runs.mjs")

    assert "tests/test_linter_formatter_policy.py" in command
    assert _TESTS + "test_assets.py" in command
    assert _TESTS + "test_loop.py" not in command


@pytest.mark.parametrize(
    "config",
    ["pyproject.toml", "uv.lock", ".python-version", "conftest.py", ".yamllint.yml", ".github/workflows/new.yml"],
)
@pytest.mark.parametrize("order", ["first", "last"])
def test_unknown_config_keeps_full_scope(config: str, order: str) -> None:
    paths = [".editorconfig", _LOOP]
    paths.insert(0 if order == "first" else len(paths), config)

    (command,) = _routed(*paths)

    assert command == ["uv", "run", "--locked", "pytest", "tests", "serve"]


@pytest.mark.parametrize(
    ("paths", "coverage"),
    [
        ((_LOOP,), True),
        ((_LOOP, "scripts/new_tool.py"), False),
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


def test_an_unrouted_python_source_falls_back_to_full_python_suite() -> None:
    scope = testing_module._python_scope("scripts/new_tool.py")  # noqa: SLF001

    assert scope is None


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


@pytest.mark.parametrize("options", [[], ["--coverage"]], ids=["plain-and-testmon", "coverage"])
def test_changed_runs_git_scope_and_accepts_explicit_base(options: list[str]) -> None:
    with (
        patch.object(sys, "argv", ["test", "--changed", "--base", "origin/dev", *options]),
        patch("owlbear_tools.testing._changed_paths", return_value=[_LOOP]) as changed_paths,
        patch("owlbear_tools.testing.subprocess.call", return_value=0) as call,
        pytest.raises(SystemExit, match="0"),
    ):
        run_test()

    changed_paths.assert_called_once_with("origin/dev")
    commands = [item.args[0] for item in call.call_args_list]
    assert len(commands) == (1 if options else 2)
    assert commands[0][:4] == ["uv", "run", "--locked", "pytest"]
    assert "tests/test_package_boundary.py" in commands[0]
    assert all(command[-2:] == ["-o", "session_timeout="] for command in commands)
    if options:
        assert "--cov" in commands[0]
        assert "--testmon" not in commands[0]
    else:
        assert commands[1][0] == "env"
        assert "--testmon" in commands[1]
        target = "serve/tools/tests/test_todo.py::test_todo_ignores_binary_files"
        with (
            patch.object(sys, "argv", ["test", "--changed", target, "--task-base", "base", "--target", "target"]),
            patch("owlbear_tools.task_scope.commit", return_value="target"),
            patch("owlbear_tools.task_scope.changed", return_value=[]),
            patch("owlbear_tools.testing.subprocess.call", return_value=0) as task_call,
            pytest.raises(SystemExit, match="0"),
        ):
            run_test()
        task_command = task_call.call_args.args[0]
        assert target in task_command
        assert "tests/test_package_boundary.py" in task_command
        assert "--testmon" not in task_command
        assert task_command[-2:] == ["-o", "session_timeout="]
        page = "serve/delivery-next/src/owlbear_delivery_next/web/metrics.html"
        with (
            patch.object(sys, "argv", ["test", "--changed", target, "--task-base", "base", "--target", "target"]),
            patch("owlbear_tools.task_scope.commit", return_value="target"),
            patch("owlbear_tools.task_scope.changed", return_value=[page]),
            patch("owlbear_tools.test_impact.select", return_value=[target]) as select,
            patch("owlbear_tools.testing.subprocess.call", return_value=0),
            pytest.raises(SystemExit, match="0"),
        ):
            run_test()
        scope = select.call_args.args[4]
        assert select.call_args.args[1] == []
        assert scope.paths == [page]
        assert set(scope.tests) == {target, "tests/test_package_boundary.py"}
        data = "serve/delivery-next/tests/fixtures/ahp/version-negotiation.json"
        with (
            patch.object(sys, "argv", ["test", "--changed", "--task-base", "base", "--target", "target"]),
            patch("owlbear_tools.task_scope.commit", return_value="target"),
            patch("owlbear_tools.task_scope.changed", return_value=[data]),
            patch("owlbear_tools.test_impact.select", return_value=[target]) as select_data,
            patch("owlbear_tools.testing.subprocess.call", return_value=0),
            pytest.raises(SystemExit, match="0"),
        ):
            run_test()
        scope = select_data.call_args.args[4]
        assert scope.paths == [data]
        assert scope.tests == ["tests/test_package_boundary.py"]
        module = target.split("::", 1)[0]
        _, python, _, required = _targets([module], _workspace_packages())
        assert python == [module]
        assert module in required


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

    assert call.call_args.args[0] == ["uv", "run", "--locked", "pytest", "tests", "serve", "-o", "session_timeout="]


def test_failures_are_aggregated_across_all_commands() -> None:
    commands = [(["uv", "run", "pytest", "a"], _ROOT), (["uv", "run", "pytest", "b"], _ROOT)]
    with (
        patch.object(sys, "argv", ["test", "--changed"]),
        patch("owlbear_tools.testing._changed_paths", return_value=[]),
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


def test_dependency_artifacts_cannot_name_tests_outside_the_checkout(tmp_path: Path) -> None:
    from owlbear_tools.test_dependencies import read_evidence  # noqa: PLC0415 - exercise the artifact boundary.

    node = "serve/tools/tests/../../../outside.py::test_escape"
    artifact = tmp_path / "dependencies.json"
    artifact.write_text(
        json.dumps(
            {
                "format": 1,
                "testmon": version("pytest-testmon"),
                "python": f"{sys.version_info.major}.{sys.version_info.minor}",
                "platform": "linux",
                "repo": "maba-pag/owlbear",
                "complete": True,
                "failed": [],
                "inputs": {"serve/tools/tests/test_testing.py": "0" * 64},
                "nodes": [node],
                "completed": [node],
                "skipped": [],
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="Invalid dependency test identity"):
        read_evidence(artifact)
    with pytest.raises(task_scope.ScopeError, match="checkout-relative test module"):
        task_scope.explicit_targets(_ROOT, [node])


def test_page_consumers_keep_real_indirect_http_but_not_dictionary_gets(tmp_path: Path) -> None:
    from owlbear_tools.test_consumers import _Consumers  # noqa: PLC0415

    test, other = "serve/demo/tests/test_web.py", "serve/demo/tests/test_other.py"
    page = "serve/demo/src/demo/web/changes.html"
    texts = {
        "serve/demo/src/demo/project_host/pages.py": "PAGES = (('/', 'Changes', 'changes.html'),)\n",
        page: "<h1>Changes</h1>",
        test: (
            "from starlette.testclient import TestClient\n\n"
            "def opened(client, route):\n    return client.get(route).text\n\n"
            "def test_http(client):\n    return opened(client, '/')\n\n"
            "def test_constructed(route):\n    client = TestClient(None)\n    client.get(route)\n\n"
            "def test_browser(page, route):\n    page.goto(route)\n"
            "def test_link(page, base, project):\n"
            "    page.goto('/elsewhere')\n    page.get_by_role('link').click()\n"
            "    expect(page).to_have_url(f'{base}/?project={project}')\n"
        ),
        other: ("FAILING = {}\n\ndef test_lookup(parent, word):\n    return FAILING.get(word, parent.get(word))\n"),
    }
    for name, text in texts.items():
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
    consumers = _Consumers(tmp_path, set(texts))
    assert consumers.outside_nodes({page}, {test}) == {
        f"{test}::test_http",
        f"{test}::test_constructed",
        f"{test}::test_browser",
        f"{test}::test_link",
    }


def test_observed_changes_keep_platform_callers_and_only_relevant_test_drift(tmp_path: Path) -> None:
    from testmon.process_code import Module  # noqa: PLC0415

    from owlbear_tools.test_consumers import _Consumers  # noqa: PLC0415
    from owlbear_tools.test_dependencies import Evidence, Observation  # noqa: PLC0415
    from owlbear_tools.test_impact import _Selection  # noqa: PLC0415

    source, caller = "serve/demo/src/demo/source.py", "serve/demo/src/demo/caller.py"
    test, guarded, newer, other = (f"serve/demo/tests/test_{name}.py" for name in ("direct", "guard", "new", "other"))
    helper, data = "serve/demo/tests/other_helper.py", "serve/demo/tests/other.json"
    before = Module(source_code="def work():\n    return 1\n")
    texts = {
        source: "def work():\n    return 2\n",
        caller: "import sys\nfrom demo.source import work\n\ndef guarded():\n"
        "    return work() if sys.platform == 'darwin' else 1\n",
        test: "from demo.source import work\n\ndef test_direct():\n    return work()\n",
        guarded: "from demo.caller import guarded\n\ndef test_guard():\n    return guarded()\n",
        newer: "from demo.source import work\n\ndef test_new():\n    return work()\n",
        other: "from other_helper import value\n\ndef test_other():\n    return value()\n",
        helper: "DATA = Path('other.json').read_text()\n\ndef value():\n    return DATA\n",
    }
    for name, text in texts.items():
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
    (tmp_path / data).write_text("{}")
    consumers = _Consumers(tmp_path, set(texts) | {data})
    recorded = dict.fromkeys(set(texts) - {newer, helper}, "same")
    current = dict.fromkeys(set(texts) | {data}, "same") | {other: "changed"}
    evidence = Evidence(
        "map",
        1,
        1,
        "python",
        1,
        4,
        recorded,
        frozenset(),
        (
            Observation(f"{test}::test_direct", source, tuple(before.checksums)),
            Observation(f"{guarded}::test_guard", caller, tuple(Module(source_code=texts[caller]).checksums)),
        ),
    )
    selection = _Selection(tmp_path, [source], consumers, [evidence], current)
    selection.supplements(source, before, Module(source_code=texts[source]))
    selection.reconcile()
    assert f"{guarded}::test_guard" in selection.reasons
    assert newer in selection.reasons
    assert other not in selection.reasons
    selection.add(f"{other}::test_other", "caller-supplied explicit target")
    selection.reconcile()
    assert other in selection.reasons


def test_unobserved_data_uses_named_ci_consumers_without_expanding_their_modules(tmp_path: Path) -> None:
    from testmon.process_code import Module  # noqa: PLC0415 - exercise native footprint identities.

    from owlbear_tools import test_impact  # noqa: PLC0415 - task-only selection machinery.
    from owlbear_tools.test_dependencies import Evidence, Observation  # noqa: PLC0415

    source = "serve/demo/src/demo/tables.py"
    entry = "serve/demo/src/demo/entry.py"
    orphan = "serve/demo/src/demo/deleted_only.py"
    orphan_before = Module(source_code="def only():\n    return 1\n")
    fixture, test, shared, data_helper = (
        "serve/demo/tests/conftest.py",
        "serve/demo/tests/test_consumer.py",
        "serve/demo/tests/test_shared_user.py",
        "serve/demo/tests/shared_reader.py",
    )
    texts = {
        source: "CURRENT = 2\nimport demo.entry as hop\n\ndef forwarding():\n    return hop.load()\n",
        orphan: "def only():\n    return 2\n",
        shared: (
            "from test_consumer import shared_helper\nfrom shared_reader import shared_value\n\n"
            "def test_shared():\n    return shared_helper()\n\n"
            "def test_shared_data():\n    return shared_value()\n"
        ),
        data_helper: ("DATA = Path('fixtures/shared.json').read_text()\n\ndef shared_value():\n    return DATA\n"),
        "serve/demo/src/demo/project_host/pages.py": "PAGES = (('/', 'Changes', 'changes.html'),)\n",
        "serve/demo/src/demo/web/changes.html": (
            '<script type="module" src="/assets/page/changes/main.mjs"></script>'
            '<script type="module" src="/assets/pds/<!-- pds -->/load.mjs"></script>'
        ),
        "serve/demo/src/demo/web/pages/changes/main.mjs": (
            "import {show} from './forms.mjs';\nimport {html} from '/assets/lit-html/3.3.3/lit-html.js';\n"
        ),
        "serve/demo/src/demo/web/pages/changes/forms.mjs": "export function show() {}\n",
        "serve/demo/src/demo/web/pds/load.mjs": "export const load = () => {};\n",
        "serve/demo/src/demo/web/vendor/lit-html/lit-html.js": "export const html = () => {};\n",
        entry: (
            "from demo.tables import CURRENT\nimport demo.tables as loop\n\ndef load():\n    return CURRENT\n"
            "\ndef unrelated():\n    return 3\n\ndef mutual():\n    return loop.forwarding()\n"
        ),
        fixture: (
            "import sys\nimport pytest\nfrom demo.entry import load\n\n"
            "@pytest.fixture\ndef loaded():\n    return load() if sys.platform == 'darwin' else 2\n"
            "@pytest.fixture\ndef marked():\n    return Path('fixtures/marked.json').read_text()\n"
        ),
        test: (
            "import sys\nimport pytest\nimport demo.entry as api\nfrom demo.entry import load, unrelated\n\n"
            "pytestmark = pytest.mark.usefixtures('marked')\n"
            "def test_current():\n    assert load() == 2\n\n"
            "def test_other():\n    assert unrelated() == 3\n\n"
            "@pytest.mark.skipif(sys.platform == 'linux', reason='Mac consumer')\n"
            "def test_platform():\n    assert load() == 2\n\n"
            "def test_fixture(loaded):\n    assert loaded == 2\n"
            "def shared_helper():\n    return load()\n\n"
            "def test_reflective():\n    return getattr(api, 'load')()\n\n"
            "def test_dynamic(name):\n    return getattr(api, name)()\n\n"
            "def test_namespace():\n    return vars(api).values()\n\n"
            "def test_page_source():\n    return Path('web/metrics.html').read_text()\n\n"
            "def test_other_page_source():\n    return Path('web/settings.html').read_text()\n"
            "def opened(page, base):\n    page.goto(f'{base}/?change=c1')\n\n"
            "def test_root_browser(page):\n    opened(page, 'http://localhost')\n"
            "INVENTORY = [p for p in Path('web').rglob('*') if p.suffix == '.mjs']\n\n"
            "def test_inventory():\n    return INVENTORY\n\n"
            "def test_data():\n    return Path('fixtures/input.json').read_text()\n\n"
            "@pytest.fixture(autouse=True)\ndef local_data():\n    return Path('fixtures/local.json').read_text()\n\n"
            "class TestScoped:\n"
            "    @pytest.fixture(autouse=True)\n    def class_data(self):\n"
            "        return Path('fixtures/class.json').read_text()\n"
            "    def test_class(self):\n        assert True\n"
            "def test_computed():\n    return Path(f'chat_contract_{1}.json').read_text()\n\n"
            "def indirect(page, base, path):\n    page.goto(f'{base}{path}#token=t')\n\n"
            "def test_indirect_route(page):\n    indirect(page, 'http://localhost', '/updates/owlbear')\n"
        ),
    }
    for path, text in texts.items():
        target = tmp_path / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text)
    consumers = test_impact._Consumers(tmp_path, set(texts))  # noqa: SLF001
    load = consumers.block_hashes(entry, {"load"})
    unknown = set(Module(source_code=texts[entry]).checksums) - consumers.block_hashes(
        entry, {"load", "unrelated", "mutual"}
    )
    skipped = f"{test}::test_platform"
    evidence = Evidence(
        "map",
        1,
        1,
        "python",
        1,
        4,
        dict.fromkeys(texts, "same"),
        frozenset({skipped}),
        (
            Observation(f"{test}::test_current", entry, tuple(load)),
            Observation(f"{test}::test_other", entry, tuple(unknown)),
            Observation("serve/demo/tests/test_deleted.py::test_only", orphan, tuple(orphan_before.checksums)),
        ),
    )
    selection = test_impact._Selection(tmp_path, [source], consumers, [evidence], dict.fromkeys(texts, "same"))  # noqa: SLF001

    def historical(_root, _head, paths):
        return {path: Module(source_code=texts[path]) for path in paths}

    with patch.object(test_impact, "_revision", side_effect=historical):
        selection.supplements(source, Module(source_code="CURRENT = 1\n"), Module(source_code=texts[source]))
    assert consumers.tests_for({entry}) == {test, shared}
    assert set(selection.reasons) == {
        f"{test}::test_current",
        f"{test}::test_fixture",
        f"{test}::test_reflective",
        f"{test}::test_dynamic",
        f"{test}::test_namespace",
        f"{shared}::test_shared",
        skipped,
    }
    assert any("current platform branch" in reason for reason in selection.reasons[skipped])
    assert any("platform fixture" in reason for reason in selection.reasons[f"{test}::test_fixture"])
    assert consumers.outside_nodes({"serve/demo/src/demo/web/metrics.html"}, {test}) == {f"{test}::test_page_source"}
    assert consumers.outside_nodes({"serve/demo/src/demo/web/pages/changes/forms.mjs"}, {test}) == {
        f"{test}::test_root_browser",
        f"{test}::test_inventory",
        f"{test}::test_indirect_route",
    }
    assert consumers.outside_nodes({"serve/demo/src/demo/web/pds/load.mjs"}, {test}) == {
        f"{test}::test_root_browser",
        f"{test}::test_inventory",
        f"{test}::test_indirect_route",
    }
    assert consumers.outside_nodes({"serve/demo/src/demo/web/vendor/lit-html/lit-html.js"}, {test}) == {
        f"{test}::test_root_browser",
        f"{test}::test_indirect_route",
    }
    selection.current_hashes[test] = "changed"
    selection.add(f"{test}::test_current", "native footprint")
    selection.add(f"{test}::test_other", "caller-supplied explicit target")
    assert test in selection.reasons
    assert f"{test}::test_other" in selection.reasons
    selection.current_hashes[test] = "same"
    selection.add(f"{test}::test_current[removed-state]", "native footprint")
    selection.add(f"{test}::test_other[explicit-state]", "caller-supplied explicit target")
    assert f"{test}::test_current[removed-state]" not in selection.reasons
    assert f"{test}::test_current" in selection.reasons
    assert f"{test}::test_other[explicit-state]" in selection.reasons
    selection.helper("serve/demo/tests/fixtures/input.json")
    assert f"{test}::test_data" in selection.reasons
    all_nodes = consumers.test_nodes({test: set(consumers.definitions[test])})
    assert consumers.outside_nodes({"serve/demo/tests/fixtures/local.json"}, {test}) == all_nodes
    assert consumers.outside_nodes({"serve/demo/tests/fixtures/class.json"}, {test}) == {
        f"{test}::TestScoped::test_class"
    }
    assert consumers.outside_nodes({"serve/demo/tests/fixtures/marked.json"}, {test}) == all_nodes
    assert consumers.outside_nodes({"serve/demo/tests/fixtures/chat_contract_1.json"}, {test}) == {
        f"{test}::test_computed"
    }
    assert consumers.outside_nodes({"serve/demo/tests/fixtures/shared.json"}, {test, shared}) == {
        f"{shared}::test_shared_data"
    }
    with (
        patch.object(test_impact, "_revision", return_value={orphan: orphan_before}),
        pytest.raises(RuntimeError, match="no resolved current consumers"),
    ):
        selection.fingerprints({orphan}, set(), "base")
