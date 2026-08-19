from __future__ import annotations

import ast
import json
import re
import subprocess
import sys
import tomllib
from pathlib import Path

import pytest
import yaml

from owlbear_tools.dependency_ci import classify_dependency_change

ROOT = Path(__file__).parents[1]
VERIFY_PATH = ROOT / ".github/workflows/dependency-verification.yml"
MEGALINTER_PATH = ROOT / ".github/workflows/megalinter.yml"
SYNC_PATH = ROOT / ".github/workflows/sync-to-main.yml"
RUNTIME_SCRIPT = ROOT / ".github/scripts/check_node_runtime.py"
PYTHON_RUNTIME_SCRIPT = ROOT / ".github/scripts/check_python_runtime.py"
WORKSPACE_LOCK_SCRIPT = ROOT / ".github/scripts/check_uv_workspace_lock.py"


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


def test_dependency_workflow_runs_without_dependency_label_gate() -> None:
    workflow = _workflow(VERIFY_PATH)
    pull_request = workflow["on"]["pull_request"]

    assert pull_request == {
        "branches": ["dev"],
        "types": ["opened", "reopened", "synchronize"],
    }
    assert "if" not in _job(workflow, "classify")


def test_dependency_verification_is_read_only_and_has_no_renovate_runner() -> None:
    workflow = _workflow(VERIFY_PATH)
    text = VERIFY_PATH.read_text(encoding="utf-8")

    assert workflow["permissions"] == {"actions": "read", "contents": "read"}
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
    proof_python = _job(workflow, "proof-python")
    proof_cockpit = _job(workflow, "proof-cockpit")

    assert "uv sync --locked --all-packages --all-extras --all-groups" in text
    assert 'uv run pytest tests serve -m "not api and not e2e and not browser and not cockpit"' in text
    assert "npm ci" in text
    assert "npm test" in text
    assert "npm run build" in text
    assert "npm run sync:pds" in text
    assert "git apply" not in text
    assert proof_python["if"] == "needs.classify.outputs.python == 'true'"
    assert "needs.classify.outputs.node == 'true'" in proof_cockpit["if"]
    assert "needs.classify.outputs.shared_node_runtime == 'true'" in proof_cockpit["if"]


def test_shared_node_runtime_fans_out_to_all_node_proofs() -> None:
    workflow = _workflow(VERIFY_PATH)

    for job_name in ("proof-cockpit", "proof-root-node", "proof-diagrams"):
        condition = _job(workflow, job_name)["if"]
        assert "needs.classify.outputs.shared_node_runtime == 'true'" in condition

    gate_env = _job(workflow, "gate")["steps"][0]["env"]
    assert (
        gate_env["ROOT_NODE_EXPECTED"]
        == "${{ needs.classify.outputs.root_node == 'true' || needs.classify.outputs.shared_node_runtime == 'true' }}"
    )
    assert (
        gate_env["DIAGRAMS_EXPECTED"]
        == "${{ needs.classify.outputs.diagrams == 'true' || needs.classify.outputs.shared_node_runtime == 'true' }}"
    )


def test_gate_requires_only_current_read_only_proofs() -> None:
    workflow = _workflow(VERIFY_PATH)
    gate = _job(workflow, "gate")

    assert gate["if"] == "always()"
    assert gate["needs"] == [
        "classify",
        "runtime",
        "proof-python",
        "proof-cockpit",
        "proof-root-node",
        "proof-diagrams",
        "compatibility",
    ]
    assert "extraction" not in gate["needs"]
    assert "prepare-fixes" not in gate["needs"]


def test_dependency_workflow_actions_are_pinned() -> None:
    for line in VERIFY_PATH.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped.startswith("uses:"):
            continue
        action = stripped.split("#", maxsplit=1)[0].removeprefix("uses:").strip()
        revision = action.rsplit("@", maxsplit=1)[1]
        assert len(revision) == 40
        assert all(character in "0123456789abcdef" for character in revision)


@pytest.mark.parametrize(
    ("path", "surface"),
    [
        ("pyproject.toml", "python"),
        ("uv.lock", "python"),
        ("serve/delivery/pyproject.toml", "python"),
        ("serve/cockpit/web/package.json", "node"),
        ("serve/cockpit/web/package-lock.json", "node"),
        ("serve/cockpit/web/.nvmrc", "node"),
        ("package.json", "root_node"),
        ("package-lock.json", "root_node"),
        (".owlbear/scripts/export-diagrams/package.json", "diagrams"),
        (".owlbear/scripts/export-diagrams/package-lock.json", "diagrams"),
        (".pre-commit-config.yaml", "precommit"),
        (".github/workflows/sync-to-main.yml", "workflows"),
        (".github/renovate.json", "renovate"),
        (".mega-linter.yml", "megalinter"),
    ],
)
def test_classifier_maps_every_dependency_surface(path: str, surface: str) -> None:
    scope = classify_dependency_change([path], "")

    assert getattr(scope, surface)
    assert scope.applicable


def test_classifier_derives_runtime_specific_proofs_from_lock_diff() -> None:
    frontend = classify_dependency_change(
        ["serve/cockpit/web/package-lock.json"],
        '+    "node_modules/@porsche-design-system/components-react": {\n',
    )

    assert frontend.node
    assert frontend.pds
    assert frontend.frontend_runtime


def test_classifier_outputs_do_not_include_fix_policy() -> None:
    outputs = classify_dependency_change(["pyproject.toml"], "").github_outputs()

    assert outputs["python"] == "true"
    assert outputs["applicable"] == "true"
    assert outputs["compatibility"] == "false"
    assert "fix_mode" not in outputs


def test_sync_manifest_preserves_workflow_support_paths() -> None:
    manifest = json.loads((ROOT / ".github/sync-manifest.json").read_text(encoding="utf-8"))
    workflow = SYNC_PATH.read_text(encoding="utf-8")

    assert ".github" not in manifest["consumer_excluded_paths"]
    assert {
        ".github/renovate.json",
        ".github/scripts",
        ".github/sync-manifest.json",
        ".github/workflows",
    }.issubset(manifest["scopes"]["infra"])
    assert {
        ".github/copilot-instructions.md",
        ".github/skills",
    }.issubset(manifest["consumer_excluded_paths"])
    assert ".mega-linter.yml" in manifest["consumer_excluded_paths"]
    assert "python3 .github/scripts/sync_manifest.py paths" in workflow
    assert "python3 .github/scripts/sync_manifest.py excluded" in workflow
    assert "for excluded_path in $CONSUMER_EXCLUDED_PATHS" in workflow


def test_sync_delivery_scope_carries_the_github_adapter() -> None:
    manifest = json.loads((ROOT / ".github/sync-manifest.json").read_text(encoding="utf-8"))
    workflow = SYNC_PATH.read_text(encoding="utf-8")

    assert manifest["scopes"]["delivery"] == [
        "serve/delivery",
        "serve/delivery-mcp",
        "serve/delivery-github",
    ]
    assert "delivery_paths=$(manifest_paths delivery)" in workflow
    assert "git rm -rf --quiet $scope_paths" in workflow
    assert "git checkout dev -- $scope_paths" in workflow


def test_node_runtime_checker_accepts_the_checked_in_contract() -> None:
    result = _run_script(
        RUNTIME_SCRIPT,
        "--version-file",
        "serve/cockpit/web/.nvmrc",
        "--engines-file",
        "serve/cockpit/web/package.json",
    )

    assert result.returncode == 0, result.stderr


def test_node_runtime_checker_rejects_a_lower_runtime(tmp_path: Path) -> None:
    version_file = tmp_path / ".nvmrc"
    engines_file = tmp_path / "package.json"
    version_file.write_text("24.15.0\n", encoding="utf-8")
    engines_file.write_text(json.dumps({"engines": {"node": ">=24.16.0"}}), encoding="utf-8")

    result = _run_script(
        RUNTIME_SCRIPT,
        "--version-file",
        str(version_file),
        "--engines-file",
        str(engines_file),
    )

    assert result.returncode != 0
    assert "below" in result.stderr


def _write_python_runtime_fixture(
    root: Path,
    *,
    pinned: str = "3.14.7",
    bounds: tuple[str, ...] = (">=3.14.6",),
    guard: str = "(3, 14, 6)",
) -> tuple[Path, Path, Path]:
    """Build one standalone Python runtime declaration set for the checker."""
    version_file = root / ".python-version"
    version_file.write_text(f"{pinned}\n", encoding="utf-8")
    members_root = root / "members"
    for index, bound in enumerate(bounds):
        manifest = members_root / f"pkg{index}"
        manifest.mkdir(parents=True)
        (manifest / "pyproject.toml").write_text(
            f'[project]\nname = "pkg{index}"\nversion = "0.1.0"\nrequires-python = "{bound}"\n',
            encoding="utf-8",
        )
    guard_file = root / "guard.py"
    guard_file.write_text(f"_MINIMUM_PYTHON = {guard}\n", encoding="utf-8")
    return version_file, members_root, guard_file


def _run_python_runtime_checker(
    version_file: Path,
    members_root: Path,
    guard_file: Path,
) -> subprocess.CompletedProcess[str]:
    """Run the Python runtime checker against one declaration set."""
    return _run_script(
        PYTHON_RUNTIME_SCRIPT,
        "--version-file",
        str(version_file),
        "--members-root",
        str(members_root),
        "--guard-file",
        str(guard_file),
    )


def test_python_runtime_checker_accepts_the_checked_in_contract() -> None:
    result = _run_script(
        PYTHON_RUNTIME_SCRIPT,
        "--version-file",
        ".python-version",
        "--members-root",
        "serve",
        "--guard-file",
        "setup/init.py",
    )

    assert result.returncode == 0, result.stderr


def test_python_runtime_checker_rejects_a_lower_pinned_runtime(tmp_path: Path) -> None:
    fixture = _write_python_runtime_fixture(tmp_path, pinned="3.13.0")

    result = _run_python_runtime_checker(*fixture)

    assert result.returncode != 0
    assert "below" in result.stderr


def test_python_runtime_checker_rejects_conflicting_member_bounds(tmp_path: Path) -> None:
    fixture = _write_python_runtime_fixture(tmp_path, bounds=(">=3.14.6", ">=3.12.0"))

    result = _run_python_runtime_checker(*fixture)

    assert result.returncode != 0
    assert "conflicting requires-python" in result.stderr


def test_python_runtime_checker_rejects_a_drifted_bootstrap_guard(tmp_path: Path) -> None:
    fixture = _write_python_runtime_fixture(tmp_path, guard="(3, 12, 0)")

    result = _run_python_runtime_checker(*fixture)

    assert result.returncode != 0
    assert "_MINIMUM_PYTHON" in result.stderr


def test_runtime_job_proves_both_node_and_python_declarations() -> None:
    steps = _job(_workflow(VERIFY_PATH), "runtime")["steps"]
    commands = " ".join(str(step.get("run", "")) for step in steps)

    assert ".github/scripts/check_node_runtime.py" in commands
    assert ".github/scripts/check_python_runtime.py" in commands


def test_setup_bootstrap_parses_on_older_interpreters_to_report_the_floor() -> None:
    """The bootstrap entry point runs before a managed runtime exists.

    It must therefore stay parseable by older interpreters, otherwise the guard
    is unreachable and users see a bare SyntaxError instead of the floor.
    """
    init_path = ROOT / "setup" / "init.py"
    source = init_path.read_text(encoding="utf-8")
    pinned = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["tool"]["ruff"][
        "per-file-target-version"
    ]["setup/init.py"]
    feature_version = (int(pinned.removeprefix("py")[0]), int(pinned.removeprefix("py")[1:]))

    ast.parse(source, str(init_path), feature_version=feature_version)
    assert "\n_check_python_version()\n" in source


def test_copilot_setup_steps_provision_the_pinned_python_runtime() -> None:
    workflow = _workflow(ROOT / ".github/workflows/copilot-setup-steps.yml")
    job = _job(workflow, "copilot-setup-steps")
    commands = " ".join(str(step.get("run", "")) for step in job["steps"])
    actions = [str(step["uses"]) for step in job["steps"] if "uses" in step]

    assert "uv python install" in commands
    assert any(action.startswith("astral-sh/setup-uv@") for action in actions)
    assert all("@" in action and len(action.split("@")[1]) == 40 for action in actions)


def test_uv_workspace_lock_regeneration_tracks_member_changes() -> None:
    result = _run_script(WORKSPACE_LOCK_SCRIPT)

    assert result.returncode == 0, result.stderr


def test_megalinter_native_and_action_versions_stay_aligned() -> None:
    config = (ROOT / ".mega-linter.yml").read_text(encoding="utf-8")
    workflow = MEGALINTER_PATH.read_text(encoding="utf-8")
    flavor_match = re.search(r"^MEGALINTER_FLAVOR:\s*(?P<flavor>[a-z0-9-]+)", config, re.MULTILINE)
    config_match = re.search(r"^MEGALINTER_VERSION:\s*v(?P<version>[0-9]+\.[0-9]+\.[0-9]+)", config, re.MULTILINE)
    action_match = re.search(
        r"uses:\s*oxsecurity/megalinter/flavors/(?P<flavor>[a-z0-9-]+)@[^\s]+\s+#\s*v(?P<version>[0-9]+\.[0-9]+\.[0-9]+)",
        workflow,
    )

    assert flavor_match is not None
    assert config_match is not None
    assert action_match is not None
    assert flavor_match.group("flavor") == action_match.group("flavor")
    assert config_match.group("version") == action_match.group("version")


def test_renovate_policy_keeps_maturity_and_lockfile_controls() -> None:
    renovate = json.loads((ROOT / ".github/renovate.json").read_text(encoding="utf-8"))

    assert "dependencies" in renovate["labels"]
    assert "security:minimumReleaseAgeNpm" in renovate["extends"]
    assert "security:minimumReleaseAgePypi" in renovate["extends"]
    assert renovate["lockFileMaintenance"]["automerge"] is False
    assert renovate["vulnerabilityAlerts"]["minimumReleaseAge"] == "6 hours"
    assert any(
        rule.get("minimumReleaseAge") == "24 hours" and rule.get("matchDatasources") == ["docker"]
        for rule in renovate["packageRules"]
    )
    assert any(
        rule.get("minimumReleaseAge") == "72 hours" and rule.get("matchUpdateTypes") == ["major"]
        for rule in renovate["packageRules"]
    )
    assert all("Renovate CLI" not in manager.get("description", "") for manager in renovate["customManagers"])


def test_ruff_declarations_and_renovate_updates_stay_coupled() -> None:
    renovate = json.loads((ROOT / ".github/renovate.json").read_text(encoding="utf-8"))
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    precommit = (ROOT / ".pre-commit-config.yaml").read_text(encoding="utf-8")
    dependency_match = re.search(r'"ruff==(?P<version>[0-9]+\.[0-9]+\.[0-9]+)"', pyproject)
    hook_match = re.search(
        r"repo: https://github\.com/astral-sh/ruff-pre-commit\s+rev: v(?P<version>[0-9]+\.[0-9]+\.[0-9]+)",
        precommit,
    )
    rule = next(rule for rule in renovate["packageRules"] if rule.get("groupName") == "Ruff toolchain")

    assert dependency_match is not None
    assert hook_match is not None
    assert dependency_match.group("version") == hook_match.group("version")
    assert rule["matchManagers"] == ["pep621", "pre-commit"]
    assert rule["matchPackageNames"] == ["ruff", "astral-sh/ruff-pre-commit"]
