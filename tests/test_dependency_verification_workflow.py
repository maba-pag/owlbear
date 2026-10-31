from __future__ import annotations

import importlib.util
import json
import re
import stat
import subprocess
import sys
import tomllib
from pathlib import Path
from types import ModuleType

import pytest
import yaml

from owlbear_tools.dependency_ci import classify_dependency_change

ROOT = Path(__file__).parents[1]
VERIFY_PATH = ROOT / ".github/workflows/tooling.yml"
AGENT_WORKFLOW_PATH = ROOT / ".github/workflows/agent-ecosystem.yml"
COPILOT_SETUP_PATH = ROOT / ".github/workflows/copilot-setup-steps.yml"
RUNTIME_SCRIPT = ROOT / ".github/scripts/check_node_runtime.py"
UV_VERSION_SCRIPT = ROOT / ".github/scripts/check_uv_version.py"
WORKSPACE_LOCK_SCRIPT = ROOT / ".github/scripts/check_uv_workspace_lock.py"
RUFF_TOOLCHAIN_SCRIPT = ROOT / ".github/scripts/check_ruff_toolchain.py"
_SCOPE_SPEC = importlib.util.spec_from_file_location("ci_scope_dependency_test", ROOT / ".github/scripts/ci_scope.py")
ci_scope = importlib.util.module_from_spec(_SCOPE_SPEC)
_SCOPE_SPEC.loader.exec_module(ci_scope)
COPILOT_UV_SYNC = "uv sync --locked --all-packages --group dev"


def _workflow(path: Path) -> dict[str, object]:
    document = yaml.safe_load(path.read_text(encoding="utf-8"))
    if True in document and "on" not in document:
        document["on"] = document.pop(True)
    return document


def _job(workflow: dict[str, object], name: str) -> dict[str, object]:
    jobs = workflow["jobs"]
    assert isinstance(jobs, dict)
    job = jobs[name]
    assert isinstance(job, dict)
    return job


def _run_script(script: Path, *arguments: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(  # noqa: S603
        [sys.executable, str(script), *arguments],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


@pytest.fixture
def ruff_toolchain_module() -> ModuleType:
    spec = importlib.util.spec_from_file_location("check_ruff_toolchain_test", RUFF_TOOLCHAIN_SCRIPT)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _fake_uv(tmp_path: Path, version: str) -> Path:
    executable = tmp_path / "uv"
    executable.write_text(f"#!/bin/sh\nprintf 'uv {version}\\n'\n", encoding="utf-8")
    executable.chmod(executable.stat().st_mode | stat.S_IXUSR)
    return executable


def _fake_node(tmp_path: Path, version: str) -> Path:
    executable = tmp_path / "node"
    executable.write_text(f"#!/bin/sh\nprintf 'v{version}\\n'\n", encoding="utf-8")
    executable.chmod(executable.stat().st_mode | stat.S_IXUSR)
    return executable


def _fake_ruff(tmp_path: Path, version: str) -> Path:
    executable = tmp_path / "ruff"
    executable.write_text(f"#!/bin/sh\nprintf 'ruff {version}\\n'\n", encoding="utf-8")
    executable.chmod(executable.stat().st_mode | stat.S_IXUSR)
    return executable


def _workspace_ruff_version() -> str:
    document = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    groups = document["dependency-groups"]
    requirements = [requirement for dependencies in groups.values() for requirement in dependencies]
    match = next(
        match
        for requirement in requirements
        if (match := re.fullmatch(r"ruff==(?P<version>[0-9]+\.[0-9]+\.[0-9]+)", requirement)) is not None
    )
    return match.group("version")


def _run_uv_version_check(executable: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(  # noqa: S603
        [sys.executable, str(UV_VERSION_SCRIPT), "--uv-executable", str(executable)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


def test_dependency_workflow_runs_without_dependency_label_gate() -> None:
    workflow = _workflow(VERIFY_PATH)

    assert set(workflow["on"]) == {"workflow_call", "workflow_dispatch"}
    assert set(ci_scope.SUITES["tooling"]) == {
        "renovate.json",
        ".github/scripts/**",
        ".github/workflows/**",
        ".pre-commit-config.yaml",
        ".python-version",
        ".nvmrc",
        "biome.json",
        "package.json",
        "package-lock.json",
        "pyproject.toml",
        "serve/*/pyproject.toml",
        "serve/tools/src/owlbear_tools/dependency_ci.py",
        "tests/test_dependency_verification_workflow.py",
        "uv.lock",
    }
    assert set(workflow["jobs"]) == {"verify"}


def test_agent_workflow_delegates_python_workspace_paths() -> None:
    paths = set(ci_scope.SUITES["agent-ecosystem"])

    assert (
        not {
            ".python-version",
            "conftest.py",
            "pyproject.toml",
            "uv.lock",
        }
        & paths
    )


def test_dependency_verification_is_read_only_and_has_no_renovate_runner() -> None:
    workflow = _workflow(VERIFY_PATH)
    text = VERIFY_PATH.read_text(encoding="utf-8")

    assert workflow["permissions"] == {"contents": "read"}
    for forbidden in (
        "contents: write",
        "RENOVATE_PACKAGE",
        "renovate --platform",
        "verify_renovate_extraction.py",
        "check_renovate_custom_manager.py",
        "prepare-fixes",
        "autofix",
        "upload-artifact",
        "download-artifact",
        "workflow_run",
        "pull_request_target",
        "git push",
        "--labels-json",
    ):
        assert forbidden not in text


def test_dependency_proofs_install_committed_state_and_run_behavior_checks() -> None:
    workflow = _workflow(VERIFY_PATH)
    text = VERIFY_PATH.read_text(encoding="utf-8")
    verify = _job(workflow, "verify")

    assert "pytest tests serve" not in text
    assert "--all-extras" not in text
    assert "git apply" not in text
    assert "Check Node runtime declaration" in text
    node_setup = next(step for step in verify["steps"] if step.get("name") == "Setup Node.js")
    assert node_setup["with"]["node-version-file"] == ".nvmrc"
    for surface in ("shared_node_runtime", "root_node"):
        assert f"steps.scope.outputs.{surface} == 'true'" in node_setup["if"]
    assert "diagrams" not in node_setup["if"]
    assert "Archify" not in text


def test_dependency_workflow_proves_lock_regeneration_without_python_suite() -> None:
    steps = {step["name"]: step for step in _job(_workflow(VERIFY_PATH), "verify")["steps"]}

    lock = steps["Prove workspace lock regeneration"]
    assert "steps.scope.outputs.python == 'true'" in lock["if"]
    assert "steps.proof_tooling.outputs.workspace_lock_tooling == 'true'" in lock["if"]
    assert lock["run"] == "uv run python .github/scripts/check_uv_workspace_lock.py"
    assert not any("pytest tests" in str(step.get("run", "")) for step in steps.values())


def test_dependency_workflow_proves_ruff_toolchain_parity() -> None:
    verify = _job(_workflow(VERIFY_PATH), "verify")
    text = VERIFY_PATH.read_text(encoding="utf-8")

    assert "uv sync --locked --group dev" in text
    parity_steps = [step for step in verify["steps"] if step.get("name") == "Verify Ruff toolchain parity"]
    assert parity_steps == [
        {
            "name": "Verify Ruff toolchain parity",
            "if": "steps.reuse.outputs.cache-hit != 'true' && steps.scope.outputs.ruff_toolchain == 'true'",
            "run": "uv run python .github/scripts/check_ruff_toolchain.py",
        }
    ]


def test_dependency_workflow_uses_semantic_snapshots_and_protects_proof_tooling() -> None:
    verify = _job(_workflow(VERIFY_PATH), "verify")
    text = VERIFY_PATH.read_text(encoding="utf-8")
    steps = {step["name"]: step for step in verify["steps"]}

    assert 'MERGE_BASE="$(git merge-base "$BASE_SHA" "$HEAD_SHA")"' in text
    assert '--base-ref "$MERGE_BASE"' in text
    assert '--head-ref "$HEAD_SHA"' in text
    assert steps["Exercise dependency proof tooling"] == {
        "name": "Exercise dependency proof tooling",
        "if": "steps.reuse.outputs.cache-hit != 'true' && steps.proof_tooling.outputs.proof_tooling == 'true'",
        "run": "uv run pytest -q tests/test_dependency_verification_workflow.py",
    }
    assert ".github/scripts/check_uv_workspace_lock.py)" in text
    assert ".github/workflows/*|" in text
    assert "tests/test_dependency_verification_workflow.py)" in text


def test_copilot_setup_keeps_task_checkout_and_bounds_installation() -> None:
    workflow = _workflow(COPILOT_SETUP_PATH)
    assert set(workflow["on"]) == {"workflow_dispatch"}
    assert set(workflow["jobs"]) == {"copilot-setup-steps"}
    job = _job(workflow, "copilot-setup-steps")
    assert set(job) <= {"steps", "permissions", "runs-on", "services", "snapshot", "timeout-minutes"}
    assert job["timeout-minutes"] == 59
    assert job["permissions"] == {"contents": "read"}
    steps = job["steps"]
    checkout = next(step for step in steps if step.get("uses", "").startswith("actions/checkout@"))
    assert "ref" not in checkout.get("with", {})
    assert checkout["with"]["persist-credentials"] is False
    runs = [step["run"] for step in steps if "run" in step]
    assert "uv python install" in runs
    assert COPILOT_UV_SYNC in runs
    assert "npm ci --engine-strict --no-audit --no-fund" in runs
    install_commands = {
        "uv python install",
        COPILOT_UV_SYNC,
        "npm ci --engine-strict --no-audit --no-fund",
    }
    for step in steps:
        if step.get("run") in install_commands:
            assert 0 < step["timeout-minutes"] <= 8
    assert not re.search(r"\b(pytest|megalint|quality|docker|playwright)\b", "\n".join(runs))
    assert {step["uses"].split("@")[0] for step in steps if "uses" in step} == {
        "actions/checkout",
        "astral-sh/setup-uv",
        "actions/setup-node",
    }


def test_copilot_setup_installs_after_toolchains_before_reporting() -> None:
    steps = _job(_workflow(COPILOT_SETUP_PATH), "copilot-setup-steps")["steps"]
    install_commands = {
        COPILOT_UV_SYNC,
        "npm ci --engine-strict --no-audit --no-fund",
    }
    install_indices = [index for index, step in enumerate(steps) if step.get("run") in install_commands]
    assert len(install_indices) == 2
    assert {steps[index]["run"] for index in install_indices} == install_commands
    for index in install_indices:
        step = steps[index]
        assert not step.get("continue-on-error", False)
        assert not step.get("background", False)
    preceding = steps[: install_indices[0]]
    assert any(step.get("uses", "").startswith("astral-sh/setup-uv@") for step in preceding)
    assert any(step.get("uses", "").startswith("actions/setup-node@") for step in preceding)
    assert any(step.get("run") == "uv python install" for step in preceding)
    assert any("check_node_runtime.py" in step.get("run", "") for step in preceding)
    assert not any(re.search(r"\buv\s+(?:run|sync)\b|\bnpm\s+ci\b", step.get("run", "")) for step in preceding)
    assert all(not step.get("continue-on-error", False) for step in preceding)
    following = steps[install_indices[-1] + 1 :]
    assert len(following) == 1
    assert "uv run --locked --no-sync python --version" in following[0]["run"]


def test_copilot_setup_uses_renovate_managed_version_sources() -> None:
    steps = _job(_workflow(COPILOT_SETUP_PATH), "copilot-setup-steps")["steps"]
    uv_setup = next(step for step in steps if step.get("uses", "").startswith("astral-sh/setup-uv@"))
    required = tomllib.loads((ROOT / "pyproject.toml").read_text())["tool"]["uv"]["required-version"]
    assert required.startswith(">=")
    assert tuple(map(int, uv_setup["with"]["version"].split("."))) >= tuple(map(int, required[2:].split(".")))
    node_setup = next(step for step in steps if step.get("uses", "").startswith("actions/setup-node@"))
    assert node_setup["with"]["node-version-file"] == ".nvmrc"
    assert "node-version" not in node_setup["with"]
    assert not any("python-version" in step.get("with", {}) for step in steps)
    for line in COPILOT_SETUP_PATH.read_text().splitlines():
        if "uses:" in line:
            assert re.search(r"@[0-9a-f]{40}\s+# v[0-9]+\.[0-9]+\.[0-9]+$", line)


def test_uv_runtime_checker_accepts_the_declared_boundary(tmp_path: Path) -> None:
    result = _run_uv_version_check(_fake_uv(tmp_path, "0.11.0"))

    assert result.returncode == 0


def test_uv_runtime_checker_rejects_an_older_executable(tmp_path: Path) -> None:
    result = _run_uv_version_check(_fake_uv(tmp_path, "0.10.9"))

    assert result.returncode != 0
    assert "below" in result.stderr


def test_ruff_toolchain_proof_accepts_aligned_repository_versions(
    tmp_path: Path,
    ruff_toolchain_module: ModuleType,
) -> None:
    version = _workspace_ruff_version()
    ruff_toolchain_module.check_ruff_toolchain(ROOT, ruff_executable=str(_fake_ruff(tmp_path, version)))


def test_ruff_toolchain_proof_rejects_installed_version_drift(
    tmp_path: Path,
    ruff_toolchain_module: ModuleType,
) -> None:
    with pytest.raises(ValueError, match=r"installed Ruff=0\.16\.1"):
        ruff_toolchain_module.check_ruff_toolchain(ROOT, ruff_executable=str(_fake_ruff(tmp_path, "0.16.1")))


@pytest.mark.parametrize(
    ("path", "surface"),
    [
        ("pyproject.toml", "python"),
        ("uv.lock", "python"),
        ("serve/delivery-next/pyproject.toml", "python"),
        ("serve/web-content/pyproject.toml", "python"),
        (".nvmrc", "shared_node_runtime"),
        ("package.json", "root_node"),
        ("package-lock.json", "root_node"),
        (".pre-commit-config.yaml", "precommit"),
        (".github/workflows/python.yml", "workflows"),
        ("renovate.json", "renovate"),
    ],
)
def test_classifier_maps_every_dependency_surface(path: str, surface: str) -> None:
    scope = classify_dependency_change([path])

    assert getattr(scope, surface)
    assert scope.applicable


@pytest.mark.parametrize(
    "path",
    [
        "conftest.py",
        "serve/delivery-next/src/owlbear_delivery_next/example.py",
        "tests/test_example.py",
    ],
)
def test_classifier_marks_source_paths_for_python_behavior_proof(path: str) -> None:
    scope = classify_dependency_change([path])

    assert scope.python


def test_unrelated_precommit_changes_use_compatibility_proof_without_python_suite() -> None:
    scope = classify_dependency_change([".pre-commit-config.yaml"])

    assert scope.precommit
    assert scope.compatibility
    assert not scope.python
    assert not scope.ruff_toolchain


@pytest.mark.parametrize(
    ("path", "before", "after", "ruff_toolchain"),
    [
        (
            "pyproject.toml",
            '[project]\ndependencies = ["ruff==0.16.2"]\n',
            '[project]\ndependencies = ["ruff==0.16.3"]\n',
            True,
        ),
        (
            "pyproject.toml",
            '[project]\ndependencies = ["ruff==0.16.2", "pytest==9.0.3"]\n',
            '[project]\ndependencies = ["ruff==0.16.2", "pytest==9.0.4"]\n',
            False,
        ),
        (
            "uv.lock",
            '[[package]]\nname = "ruff"\nversion = "0.16.2"\n',
            '[[package]]\nname = "ruff"\nversion = "0.16.3"\n',
            True,
        ),
        (
            "uv.lock",
            '[[package]]\nname = "ruff"\nversion = "0.16.2"\n\n[[package]]\nname = "pytest"\nversion = "9.0.3"\n',
            '[[package]]\nname = "ruff"\nversion = "0.16.2"\n\n[[package]]\nname = "pytest"\nversion = "9.0.4"\n',
            False,
        ),
        (
            ".pre-commit-config.yaml",
            "- repo: https://github.com/astral-sh/ruff-pre-commit\n  rev: v0.16.2\n  hooks: []\n",
            "- repo: https://github.com/astral-sh/ruff-pre-commit\n  rev: v0.16.3\n  hooks: []\n",
            True,
        ),
        (
            ".pre-commit-config.yaml",
            (
                "- repo: https://github.com/astral-sh/ruff-pre-commit\n"
                "  rev: v0.16.2\n"
                "  hooks: []\n"
                "- repo: https://github.com/rhysd/actionlint\n"
                "  rev: v1.7.12\n"
            ),
            (
                "- repo: https://github.com/astral-sh/ruff-pre-commit\n"
                "  rev: v0.16.2\n"
                "  hooks: []\n"
                "- repo: https://github.com/rhysd/actionlint\n"
                "  rev: v1.7.13\n"
            ),
            False,
        ),
    ],
)
def test_ruff_toolchain_classification_uses_relevant_snapshot_values(
    path: str,
    before: str,
    after: str,
    *,
    ruff_toolchain: bool,
) -> None:
    scope = classify_dependency_change(
        [path],
        before_files={path: before},
        after_files={path: after},
    )

    assert scope.ruff_toolchain is ruff_toolchain
    assert scope.compatibility is (ruff_toolchain or path == ".pre-commit-config.yaml")


@pytest.mark.parametrize(
    ("path", "before", "after"),
    [
        (
            "pyproject.toml",
            '[dependency-groups]\ndev = ["ruff==0.16.2"]\n',
            '[dependency-groups]\ndev = ["ruff==0.16.5"]\n',
        ),
        (
            "uv.lock",
            '[[package]]\nname = "ruff"\nversion = "0.16.2"\n',
            '[[package]]\nname = "ruff"\nversion = "0.16.5"\n',
        ),
    ],
)
def test_ruff_only_root_manifest_changes_skip_python_behavior_proof(
    path: str,
    before: str,
    after: str,
) -> None:
    scope = classify_dependency_change(
        [path],
        before_files={path: before},
        after_files={path: after},
    )

    assert scope.ruff_toolchain
    assert not scope.python
    assert scope.compatibility


def test_non_ruff_root_manifest_changes_keep_python_behavior_proof() -> None:
    before = '[dependency-groups]\ndev = ["ruff==0.16.2", "pytest==9.0.3"]\n'
    after = '[dependency-groups]\ndev = ["ruff==0.16.2", "pytest==9.0.4"]\n'

    scope = classify_dependency_change(
        ["pyproject.toml"],
        before_files={"pyproject.toml": before},
        after_files={"pyproject.toml": after},
    )

    assert scope.python
    assert not scope.ruff_toolchain


def test_classifier_outputs_do_not_include_fix_policy() -> None:
    outputs = classify_dependency_change(["pyproject.toml"]).github_outputs()

    assert outputs["python"] == "true"
    assert outputs["applicable"] == "true"
    assert outputs["compatibility"] == "false"
    assert "fix_mode" not in outputs


def test_shared_web_content_dependency_edges_are_declared() -> None:
    browser = tomllib.loads((ROOT / "serve/browser/pyproject.toml").read_text(encoding="utf-8"))
    knowledge = tomllib.loads((ROOT / "serve/knowledge/pyproject.toml").read_text(encoding="utf-8"))
    root = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))

    assert "owlbear-web-content" in browser["project"]["dependencies"]
    assert "owlbear-web-content" in knowledge["project"]["optional-dependencies"]["intake"]
    assert "owlbear-web-content" in knowledge["project"]["optional-dependencies"]["full"]
    assert "serve/web-content/src" in root["tool"]["ruff"]["src"]


def test_node_runtime_checker_accepts_the_checked_in_contract() -> None:
    result = _run_script(
        RUNTIME_SCRIPT,
        "--version-file",
        ".nvmrc",
        "--engines-file",
        "package.json",
    )

    assert result.returncode == 0, result.stderr


def test_node_runtime_checker_accepts_an_aligned_pin_and_floor(tmp_path: Path) -> None:
    version_file = tmp_path / ".nvmrc"
    engines_file = tmp_path / "package.json"
    version_file.write_text("24.21.0\n", encoding="utf-8")
    engines_file.write_text(json.dumps({"engines": {"node": ">=24.21.0"}}), encoding="utf-8")

    result = _run_script(
        RUNTIME_SCRIPT,
        "--version-file",
        str(version_file),
        "--engines-file",
        str(engines_file),
    )

    assert result.returncode == 0, result.stderr


def test_node_runtime_checker_rejects_a_raised_pin_with_a_stale_floor(tmp_path: Path) -> None:
    version_file = tmp_path / ".nvmrc"
    engines_file = tmp_path / "package.json"
    version_file.write_text("25.0.0\n", encoding="utf-8")
    engines_file.write_text(json.dumps({"engines": {"node": ">=24.21.0"}}), encoding="utf-8")

    result = _run_script(
        RUNTIME_SCRIPT,
        "--version-file",
        str(version_file),
        "--engines-file",
        str(engines_file),
    )

    assert result.returncode != 0
    assert "does not match" in result.stderr


def test_node_runtime_checker_rejects_a_lower_runtime(tmp_path: Path) -> None:
    version_file = tmp_path / ".nvmrc"
    engines_file = tmp_path / "package.json"
    version_file.write_text("24.20.0\n", encoding="utf-8")
    engines_file.write_text(json.dumps({"engines": {"node": ">=24.21.0"}}), encoding="utf-8")

    result = _run_script(
        RUNTIME_SCRIPT,
        "--version-file",
        str(version_file),
        "--engines-file",
        str(engines_file),
    )

    assert result.returncode != 0
    assert "does not match" in result.stderr


def test_node_runtime_checker_accepts_the_expected_installed_runtime(tmp_path: Path) -> None:
    node = _fake_node(tmp_path, "24.21.0")
    version_file = tmp_path / ".nvmrc"
    engines_file = tmp_path / "package.json"
    version_file.write_text("24.21.0\n", encoding="utf-8")
    engines_file.write_text(json.dumps({"engines": {"node": ">=24.21.0"}}), encoding="utf-8")

    result = _run_script(
        RUNTIME_SCRIPT,
        "--version-file",
        str(version_file),
        "--engines-file",
        str(engines_file),
        "--expected-version",
        "24.21.0",
        "--node-executable",
        str(node),
    )

    assert result.returncode == 0, result.stderr


def test_node_runtime_checker_rejects_an_unexpected_installed_runtime(tmp_path: Path) -> None:
    node = _fake_node(tmp_path, "24.20.0")
    version_file = tmp_path / ".nvmrc"
    engines_file = tmp_path / "package.json"
    version_file.write_text("24.21.0\n", encoding="utf-8")
    engines_file.write_text(json.dumps({"engines": {"node": ">=24.21.0"}}), encoding="utf-8")

    result = _run_script(
        RUNTIME_SCRIPT,
        "--version-file",
        str(version_file),
        "--engines-file",
        str(engines_file),
        "--expected-version",
        "24.21.0",
        "--node-executable",
        str(node),
    )

    assert result.returncode != 0
    assert "does not match" in result.stderr


def test_uv_workspace_lock_regeneration_tracks_member_changes() -> None:
    result = _run_script(WORKSPACE_LOCK_SCRIPT)

    assert result.returncode == 0, result.stderr


def test_renovate_policy_keeps_maturity_and_lockfile_controls() -> None:
    renovate = json.loads((ROOT / "renovate.json").read_text(encoding="utf-8"))

    assert "dependencies" in renovate["labels"]
    assert renovate["extends"][0] == "config:best-practices"  # it brings security:minimumReleaseAgeNpm
    assert "security:minimumReleaseAgePypi" in renovate["extends"]
    assert renovate["lockFileMaintenance"]["automerge"] is False
    assert renovate["vulnerabilityAlerts"]["minimumReleaseAge"] == "6 hours"
    assert "schedule" not in renovate["vulnerabilityAlerts"]  # Renovate ignores schedules for security fixes
    assert any(
        rule.get("minimumReleaseAge") == "24 hours" and rule.get("matchDatasources") == ["docker"]
        for rule in renovate["packageRules"]
    )
    assert any(
        rule.get("minimumReleaseAge") == "72 hours" and rule.get("matchUpdateTypes") == ["major"]
        for rule in renovate["packageRules"]
    )
    assert all("Renovate CLI" not in manager.get("description", "") for manager in renovate.get("customManagers", []))


def test_renovate_updates_the_lint_toolchain_in_one_pull_request() -> None:
    """Ruff's pin and every hook move together, majors in their own Sunday PR, so the Ruff parity holds (TD-409)."""
    renovate = json.loads((ROOT / "renovate.json").read_text(encoding="utf-8"))
    rules = renovate["packageRules"]
    lint = [rule for rule in rules if rule.get("groupName") == "lint toolchain"]
    weekly = [rule.get("groupName") for rule in rules].index("{{datasource}} minor/patch updates")
    majors = [rule.get("matchUpdateTypes") for rule in rules].index(["major"])

    assert "customManagers:biomeVersions" in renovate["extends"]
    assert [rule.get("matchManagers") for rule in lint] == [["pre-commit"], None]
    assert lint[1]["matchPackageNames"] == ["ruff", "@biomejs/biome"]
    assert all("matchUpdateTypes" not in rule for rule in lint)
    assert all(weekly < rules.index(rule) < majors for rule in lint)
    assert all(rule.get("enabled", True) for rule in rules)
