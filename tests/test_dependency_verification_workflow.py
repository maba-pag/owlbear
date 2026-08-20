from __future__ import annotations

import json
import re
import stat
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

from owlbear_tools.dependency_ci import classify_dependency_change

ROOT = Path(__file__).parents[1]
VERIFY_PATH = ROOT / ".github/workflows/dependency-verification.yml"
AGENT_WORKFLOW_PATH = ROOT / ".github/workflows/agent-ecosystem.yml"
KNOWLEDGE_WORKFLOW_PATH = ROOT / ".github/workflows/knowledge-source-contracts.yml"
MEGALINTER_PATH = ROOT / ".github/workflows/megalinter.yml"
SYNC_PATH = ROOT / ".github/workflows/sync-to-main.yml"
RUNTIME_SCRIPT = ROOT / ".github/scripts/check_node_runtime.py"
UV_VERSION_SCRIPT = ROOT / ".github/scripts/check_uv_version.py"
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


def _fake_uv(tmp_path: Path, version: str) -> Path:
    executable = tmp_path / "uv"
    executable.write_text(f"#!/bin/sh\nprintf 'uv {version}\\n'\n", encoding="utf-8")
    executable.chmod(executable.stat().st_mode | stat.S_IXUSR)
    return executable


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

    assert proof_python["strategy"] == {
        "fail-fast": False,
        "matrix": {"python": ["3.12.14", "3.13.15", "3.14.7"]},
    }
    assert proof_python["env"] == {"UV_PROJECT_ENVIRONMENT": ".venv-${{ matrix.python }}"}
    assert 'uv sync --locked --python "${{ matrix.python }}" --all-packages --all-extras --all-groups' in text
    assert 'uv run --python "${{ matrix.python }}" pytest tests serve \\' in text
    assert '            -m "not api and not e2e and not browser and not cockpit"' in text
    assert "npm ci" in text
    assert "npm test" in text
    assert "npm run build" in text
    assert "npm run sync:pds" in text
    assert "git apply" not in text
    assert proof_python["if"] == "needs.classify.outputs.python == 'true'"
    assert "needs.classify.outputs.node == 'true'" in proof_cockpit["if"]
    assert "needs.classify.outputs.shared_node_runtime == 'true'" in proof_cockpit["if"]


def test_uv_runtime_check_precedes_uv_commands() -> None:
    for path in (VERIFY_PATH, AGENT_WORKFLOW_PATH, KNOWLEDGE_WORKFLOW_PATH):
        workflow = _workflow(path)
        jobs = workflow["jobs"]
        assert isinstance(jobs, dict)
        for job in jobs.values():
            assert isinstance(job, dict)
            steps = job.get("steps", [])
            if not isinstance(steps, list):
                continue
            setup_indices = [
                index for index, step in enumerate(steps) if "astral-sh/setup-uv@" in str(step.get("uses", ""))
            ]
            if not setup_indices:
                continue
            setup_index = setup_indices[0]
            check_index = next(
                index for index, step in enumerate(steps) if "check_uv_version.py" in str(step.get("run", ""))
            )
            first_uv_command = next(
                index
                for index, step in enumerate(steps)
                if re.search(r"\buv\s+(?:python|run|sync|lock)", str(step.get("run", "")))
            )
            assert setup_index < check_index < first_uv_command


def test_uv_runtime_checker_accepts_the_declared_boundary(tmp_path: Path) -> None:
    result = _run_uv_version_check(_fake_uv(tmp_path, "0.11.0"))

    assert result.returncode == 0


def test_uv_runtime_checker_rejects_an_older_executable(tmp_path: Path) -> None:
    result = _run_uv_version_check(_fake_uv(tmp_path, "0.10.9"))

    assert result.returncode != 0
    assert "below" in result.stderr


def _playwright_install_steps(workflow: dict[str, object]) -> list[dict[str, object]]:
    jobs = workflow["jobs"]
    assert isinstance(jobs, dict)
    steps = []
    for job in jobs.values():
        steps.extend(step for step in job.get("steps", []) if "playwright install" in str(step.get("run", "")))
    return steps


def test_playwright_browser_install_never_provisions_system_packages() -> None:
    """`--with-deps` shells out to apt, which stalls the runner when a mirror is
    unreachable. The runner image already ships Chromium's shared libraries."""
    steps = _playwright_install_steps(_workflow(VERIFY_PATH))

    assert steps
    for step in steps:
        assert "--with-deps" not in str(step["run"])


def test_browser_install_steps_cannot_burn_a_whole_job_timeout() -> None:
    steps = _playwright_install_steps(_workflow(VERIFY_PATH))

    assert steps
    for step in steps:
        timeout = step.get("timeout-minutes")
        assert timeout is not None
        assert 0 < timeout <= 10


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
