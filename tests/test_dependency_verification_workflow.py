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
COCKPIT_VERIFY_PATH = ROOT / ".github/workflows/cockpit-verification.yml"
AGENT_WORKFLOW_PATH = ROOT / ".github/workflows/agent-ecosystem.yml"
MEGALINTER_PATH = ROOT / ".github/workflows/megalinter.yml"
SYNC_PATH = ROOT / ".github/workflows/sync-to-main.yml"
RUNTIME_SCRIPT = ROOT / ".github/scripts/check_node_runtime.py"
UV_VERSION_SCRIPT = ROOT / ".github/scripts/check_uv_version.py"
WORKSPACE_LOCK_SCRIPT = ROOT / ".github/scripts/check_uv_workspace_lock.py"
RUFF_TOOLCHAIN_SCRIPT = ROOT / ".github/scripts/check_ruff_toolchain.py"


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


def _fake_docker(tmp_path: Path, version: str) -> Path:
    executable = tmp_path / "docker"
    executable.write_text(f"#!/bin/sh\nprintf 'ruff {version}\\n'\n", encoding="utf-8")
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

    assert pull_request["branches"] == ["dev"]
    assert pull_request["types"] == ["opened", "reopened", "synchronize", "ready_for_review"]
    assert set(pull_request["paths"]) == {
        ".github/renovate.json",
        ".github/scripts/check_node_runtime.py",
        ".github/scripts/check_ruff_toolchain.py",
        ".github/scripts/check_uv_version.py",
        ".github/scripts/check_uv_workspace_lock.py",
        ".github/workflows/**",
        ".mega-linter.yml",
        ".pre-commit-config.yaml",
        ".python-version",
        ".owlbear/scripts/diagrams/**",
        "share/diagrams/**",
        "package.json",
        "package-lock.json",
        "pyproject.toml",
        "serve/*/pyproject.toml",
        "serve/cockpit/web/.nvmrc",
        "serve/cockpit/web/package.json",
        "serve/cockpit/web/package-lock.json",
        "serve/tools/src/owlbear_tools/dependency_ci.py",
        "serve/tools/src/owlbear_tools/megalinter.py",
        "tests/test_archify_diagrams.py",
        "tests/test_dependency_verification_workflow.py",
        "uv.lock",
    }
    assert _job(workflow, "classify")["if"] == (
        "github.event_name != 'pull_request' || github.event.pull_request.draft == false"
    )
    assert "workflow_dispatch" in workflow["on"]


def test_pull_request_proof_workflows_skip_draft_jobs_and_run_when_ready() -> None:
    expected_types = ["opened", "reopened", "synchronize", "ready_for_review"]
    for path in (AGENT_WORKFLOW_PATH, VERIFY_PATH, COCKPIT_VERIFY_PATH):
        workflow = _workflow(path)
        pull_request = workflow["on"]["pull_request"]
        assert pull_request["types"] == expected_types
        jobs = workflow["jobs"]
        assert isinstance(jobs, dict)
        for job_name, job in jobs.items():
            assert isinstance(job, dict)
            condition = job.get("if")
            assert isinstance(condition, str), f"{path.name}:{job_name} needs a draft guard"
            assert "github.event_name != 'pull_request'" in condition
            assert "github.event.pull_request.draft == false" in condition


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
    resolve = _job(workflow, "resolve_runtimes")
    proof_python = _job(workflow, "proof-python")
    proof_node = _job(workflow, "proof-node")

    assert resolve["outputs"] == {"python_matrix": "${{ steps.runtime.outputs.python_matrix }}"}
    assert "python_upper=\"$(tr -d '\\r\\n' < .python-version)\"" in text
    assert 'python_matrix=["3.12.14","3.13","%s"]' in text
    assert 'python_matrix=["3.12.14","%s"]' in text
    assert proof_python["strategy"] == {
        "fail-fast": False,
        "matrix": {"python": "${{ fromJSON(needs.resolve_runtimes.outputs.python_matrix) }}"},
    }
    assert proof_python["needs"] == ["classify", "resolve_runtimes"]
    assert proof_python["env"] == {"UV_PROJECT_ENVIRONMENT": ".venv-${{ matrix.python }}"}
    assert 'uv sync --locked --python "${{ matrix.python }}" --all-packages --all-extras --all-groups' in text
    assert 'uv run --python "${{ matrix.python }}" pytest tests serve \\' in text
    assert '            -m "not api and not e2e and not browser and not cockpit"' in text
    assert "npm ci --engine-strict" in text
    assert "npm run sync:pds" in text
    assert "git apply" not in text
    assert proof_python["if"] == (
        "(github.event_name != 'pull_request' || github.event.pull_request.draft == false) && "
        "needs.classify.outputs.python == 'true'"
    )
    assert "runtime" not in workflow["jobs"]
    assert "proof-pds" not in workflow["jobs"]
    assert "proof-root-node" not in workflow["jobs"]
    assert "proof-diagrams" not in workflow["jobs"]
    assert "Check Node runtime declaration" in text
    assert "needs.classify.outputs.pds == 'true'" in proof_node["if"]
    assert "needs.classify.outputs.root_node == 'true'" in proof_node["if"]
    assert "needs.classify.outputs.diagrams == 'true'" in proof_node["if"]
    assert "needs.classify.outputs.shared_node_runtime == 'true'" in proof_node["if"]
    archify_steps = [
        step for step in proof_node["steps"] if step.get("name") == "Verify pinned Archify release and static render"
    ]
    assert len(archify_steps) == 1
    archify_step = archify_steps[0]
    assert archify_step["if"] == (
        "needs.classify.outputs.diagrams == 'true' || needs.classify.outputs.shared_node_runtime == 'true'"
    )
    assert archify_step["timeout-minutes"] == 10
    assert archify_step["shell"] == "bash"
    archify_run = archify_step["run"]
    assert "--check" not in archify_run
    assert '"$RUNNER_TEMP/archify-diagrams.tsv"' in archify_run
    assert 'test -s "$RUNNER_TEMP/archify-diagrams.tsv"' in archify_run
    assert 'manifest_sources = {diagram["source"] for diagram in manifest["diagrams"]}' in archify_run
    assert 'Path("share/diagrams").rglob("*.architecture.json")' in archify_run
    assert "Archify manifest source coverage mismatch" in archify_run
    assert "while IFS=$'\\t' read -r source artifact; do" in archify_run
    assert 'done < "$RUNNER_TEMP/archify-diagrams.tsv"' in archify_run
    assert "python3 .owlbear/scripts/diagrams/render.py" in archify_run
    assert "--offline" in archify_run
    assert 'if cmp --silent "$output" "$artifact"; then' in archify_run
    assert "Archify artifact is stale" in archify_run
    assert "Regenerate with:" in archify_run


def test_dependency_workflow_proves_ruff_toolchain_parity() -> None:
    workflow = _workflow(VERIFY_PATH)
    compatibility = _job(workflow, "compatibility")
    text = VERIFY_PATH.read_text(encoding="utf-8")

    assert "ruff_toolchain: ${{ steps.scope.outputs.ruff_toolchain }}" in text
    parity_steps = [step for step in compatibility["steps"] if step.get("name") == "Verify Ruff toolchain parity"]
    assert parity_steps == [
        {
            "name": "Verify Ruff toolchain parity",
            "if": "needs.classify.outputs.ruff_toolchain == 'true'",
            "run": "uv run python .github/scripts/check_ruff_toolchain.py",
        }
    ]


def test_dependency_workflow_uses_semantic_snapshots_and_protects_proof_tooling() -> None:
    workflow = _workflow(VERIFY_PATH)
    classify = _job(workflow, "classify")
    compatibility = _job(workflow, "compatibility")
    text = VERIFY_PATH.read_text(encoding="utf-8")

    assert classify["outputs"]["proof_tooling"] == "${{ steps.proof_tooling.outputs.proof_tooling }}"
    assert 'MERGE_BASE="$(git merge-base "$BASE_SHA" "$HEAD_SHA")"' in text
    assert '--base-ref "$MERGE_BASE"' in text
    assert '--head-ref "$HEAD_SHA"' in text
    assert compatibility["if"] == (
        "(github.event_name != 'pull_request' || github.event.pull_request.draft == false) && "
        "(needs.classify.outputs.compatibility == 'true' || needs.classify.outputs.proof_tooling == 'true')"
    )
    proof_step_name = "Exercise dependency proof tooling"
    steps = compatibility["steps"]
    proof_steps = [step for step in steps if step.get("name") == proof_step_name]
    assert proof_steps == [
        {
            "name": "Exercise dependency proof tooling",
            "if": "needs.classify.outputs.proof_tooling == 'true'",
            "run": (
                "uv run pytest -q tests/test_dependency_verification_workflow.py serve/tools/tests/test_megalinter.py"
            ),
        }
    ]
    assert ".github/workflows/*|" in text
    assert "serve/tools/src/owlbear_tools/megalinter.py|" in text
    assert "tests/test_dependency_verification_workflow.py)" in text


def test_uv_runtime_check_precedes_uv_commands() -> None:
    for path in (VERIFY_PATH, AGENT_WORKFLOW_PATH):
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


def test_ruff_toolchain_proof_accepts_equal_versions(tmp_path: Path) -> None:
    result = _run_script(
        RUFF_TOOLCHAIN_SCRIPT,
        "--ruff-executable",
        str(_fake_ruff(tmp_path, "0.16.2")),
        "--docker-executable",
        str(_fake_docker(tmp_path, "0.16.2")),
    )

    assert result.returncode == 0, result.stderr
    assert "aligned at 0.16.2" in result.stdout


def test_ruff_toolchain_proof_rejects_bundled_version_drift(tmp_path: Path) -> None:
    result = _run_script(
        RUFF_TOOLCHAIN_SCRIPT,
        "--ruff-executable",
        str(_fake_ruff(tmp_path, "0.16.2")),
        "--docker-executable",
        str(_fake_docker(tmp_path, "0.16.1")),
    )

    assert result.returncode != 0
    assert "MegaLinter bundled Ruff=0.16.1" in result.stderr


def test_shared_node_runtime_uses_one_node_proof() -> None:
    workflow = _workflow(VERIFY_PATH)

    condition = _job(workflow, "proof-node")["if"]
    assert "needs.classify.outputs.shared_node_runtime == 'true'" in condition
    assert "needs.classify.outputs.root_node == 'true'" in condition
    assert "needs.classify.outputs.diagrams == 'true'" in condition

    gate_env = _job(workflow, "gate")["steps"][0]["env"]
    assert gate_env["NODE_EXPECTED"] == (
        "${{ needs.classify.outputs.pds == 'true' || "
        "needs.classify.outputs.root_node == 'true' || "
        "needs.classify.outputs.diagrams == 'true' || "
        "needs.classify.outputs.shared_node_runtime == 'true' }}"
    )


def test_gate_requires_only_current_read_only_proofs() -> None:
    workflow = _workflow(VERIFY_PATH)
    gate = _job(workflow, "gate")

    assert gate["if"] == (
        "always() && (github.event_name != 'pull_request' || github.event.pull_request.draft == false)"
    )
    assert gate["needs"] == [
        "classify",
        "resolve_runtimes",
        "proof-python",
        "proof-node",
        "compatibility",
    ]
    assert "extraction" not in gate["needs"]
    assert "prepare-fixes" not in gate["needs"]

    gate_env = gate["steps"][0]["env"]
    assert gate_env["COMPATIBILITY_EXPECTED"] == (
        "${{ needs.classify.outputs.compatibility == 'true' || needs.classify.outputs.proof_tooling == 'true' }}"
    )


def test_dependency_workflow_actions_are_pinned() -> None:
    for line in VERIFY_PATH.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped.startswith("uses:"):
            continue
        action = stripped.split("#", maxsplit=1)[0].removeprefix("uses:").strip()
        revision = action.rsplit("@", maxsplit=1)[1]
        assert len(revision) == 40
        assert all(character in "0123456789abcdef" for character in revision)


def test_renovate_archify_match_spans_version_and_digest() -> None:
    config = json.loads((ROOT / ".github/renovate.json").read_text(encoding="utf-8"))
    managers = config["customManagers"]
    archify = next(manager for manager in managers if manager.get("depNameTemplate") == "tt-a1i/archify")
    patterns = archify["matchStrings"]
    assert "matchStringsStrategy" not in archify
    assert len(patterns) == 1

    lock = (ROOT / ".owlbear/scripts/diagrams/archify.lock.json").read_text(encoding="utf-8")
    assert "(?<currentValue>v[\\d.]+)" in patterns[0]
    assert "(?<currentDigest>[a-f0-9]{64})" in patterns[0]
    replacement_span = lock[lock.index('"version"') : lock.index('"sha256"') + len('"sha256"')]
    lock_document = json.loads(lock)
    assert re.fullmatch(r"v\d+\.\d+\.\d+", lock_document["version"])
    assert f'"version": "{lock_document["version"]}"' in replacement_span
    assert '"sha256"' in replacement_span
    assert lock_document["sha256"] in lock


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
        (".owlbear/scripts/diagrams/archify.lock.json", "diagrams"),
        (".owlbear/scripts/diagrams/sync.py", "diagrams"),
        (".owlbear/scripts/diagrams/render.py", "diagrams"),
        ("share/diagrams/manifest.json", "diagrams"),
        ("share/diagrams/mcp-topology.architecture.json", "diagrams"),
        ("share/diagrams/mcp-topology.svg", "diagrams"),
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


def test_classifier_derives_pds_asset_proof_from_lock_diff() -> None:
    frontend = classify_dependency_change(
        ["serve/cockpit/web/package-lock.json"],
        '+    "node_modules/@porsche-design-system/components-react": {\n',
    )

    assert frontend.node
    assert frontend.pds
    assert "frontend_runtime" not in frontend.github_outputs()


def test_unrelated_precommit_changes_use_compatibility_proof_without_python_suite() -> None:
    scope = classify_dependency_change([".pre-commit-config.yaml"], "")

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
        (
            ".mega-linter.yml",
            "MEGALINTER_FLAVOR: cupcake\nMEGALINTER_VERSION: v10.0.0\nENABLE_LINTERS: []\n",
            "MEGALINTER_FLAVOR: cupcake\nMEGALINTER_VERSION: v10.1.0\nENABLE_LINTERS: []\n",
            True,
        ),
        (
            ".mega-linter.yml",
            "MEGALINTER_FLAVOR: cupcake\nMEGALINTER_VERSION: v10.0.0\nENABLE_LINTERS: []\n",
            "MEGALINTER_FLAVOR: cupcake\nMEGALINTER_VERSION: v10.0.0\nENABLE_LINTERS: [PYTHON_RUFF]\n",
            False,
        ),
        (
            ".github/workflows/megalinter.yml",
            "      uses: oxsecurity/megalinter/flavors/cupcake@oldsha  # v10.0.0\n",
            "      uses: oxsecurity/megalinter/flavors/cupcake@newsha  # v10.0.0\n",
            True,
        ),
        (
            ".github/workflows/megalinter.yml",
            "      uses: oxsecurity/megalinter/flavors/cupcake@sha  # v10.0.0\n      timeout-minutes: 15\n",
            "      uses: oxsecurity/megalinter/flavors/cupcake@sha  # v10.0.0\n      timeout-minutes: 20\n",
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
        "",
        before_files={path: before},
        after_files={path: after},
    )

    assert scope.ruff_toolchain is ruff_toolchain
    assert scope.compatibility is (
        ruff_toolchain or path in {".pre-commit-config.yaml", ".mega-linter.yml", ".github/workflows/megalinter.yml"}
    )


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


def test_node_runtime_checker_accepts_the_expected_installed_runtime(tmp_path: Path) -> None:
    node = _fake_node(tmp_path, "24.16.0")
    version_file = tmp_path / ".nvmrc"
    engines_file = tmp_path / "package.json"
    version_file.write_text("24.19.0\n", encoding="utf-8")
    engines_file.write_text(json.dumps({"engines": {"node": ">=24.16.0"}}), encoding="utf-8")

    result = _run_script(
        RUNTIME_SCRIPT,
        "--version-file",
        str(version_file),
        "--engines-file",
        str(engines_file),
        "--expected-version",
        "24.16.0",
        "--node-executable",
        str(node),
    )

    assert result.returncode == 0, result.stderr


def test_node_runtime_checker_rejects_an_unexpected_installed_runtime(tmp_path: Path) -> None:
    node = _fake_node(tmp_path, "24.15.0")
    version_file = tmp_path / ".nvmrc"
    engines_file = tmp_path / "package.json"
    version_file.write_text("24.19.0\n", encoding="utf-8")
    engines_file.write_text(json.dumps({"engines": {"node": ">=24.16.0"}}), encoding="utf-8")

    result = _run_script(
        RUNTIME_SCRIPT,
        "--version-file",
        str(version_file),
        "--engines-file",
        str(engines_file),
        "--expected-version",
        "24.16.0",
        "--node-executable",
        str(node),
    )

    assert result.returncode != 0
    assert "does not match" in result.stderr


def test_cockpit_workflow_proves_node_floor_and_browser_engines() -> None:
    workflow = _workflow(COCKPIT_VERIFY_PATH)
    resolve = _job(workflow, "resolve_runtimes")
    proof = _job(workflow, "proof")
    browser = _job(workflow, "browser_compatibility")
    gate = _job(workflow, "gate")
    text = COCKPIT_VERIFY_PATH.read_text(encoding="utf-8")
    package = json.loads((ROOT / "serve/cockpit/web/package.json").read_text(encoding="utf-8"))

    assert workflow["on"]["pull_request"]["paths"] == [
        "serve/cockpit/web/**",
        "serve/cockpit/README.md",
        ".github/scripts/check_node_runtime.py",
        ".github/workflows/cockpit-verification.yml",
    ]
    assert proof["strategy"] == {
        "fail-fast": False,
        "matrix": {"node": "${{ fromJSON(needs.resolve_runtimes.outputs.node_matrix) }}"},
    }
    assert resolve["outputs"] == {"node_matrix": "${{ steps.runtime.outputs.node_matrix }}"}
    assert proof["needs"] == "resolve_runtimes"
    assert "node_upper=\"$(tr -d '\\r\\n' < serve/cockpit/web/.nvmrc)\"" in text
    assert "npm ci --engine-strict" in text
    assert "npm run build" in text
    assert browser["needs"] == "proof"
    assert browser["if"] == (
        "(github.event_name != 'pull_request' || github.event.pull_request.draft == false) && "
        "needs.proof.result == 'success'"
    )
    assert gate["name"] == "Verify Cockpit"
    assert gate["needs"] == ["resolve_runtimes", "proof", "browser_compatibility"]
    assert gate["if"] == (
        "always() && (github.event_name != 'pull_request' || github.event.pull_request.draft == false)"
    )
    assert "workflow_dispatch:" in text
    assert "ref: ${{ github.event.pull_request.head.sha || github.sha }}" in text
    assert browser["env"] == {
        "E2E_COMPAT_BROWSERS": (
            "${{ github.event_name == 'workflow_dispatch' && 'chromium firefox webkit' || 'chromium' }}"
        )
    }
    assert 'npx playwright install --with-deps "$E2E_COMPAT_BROWSERS"' in text
    assert "npm run test:e2e:compat" in text
    assert package["scripts"]["test:e2e:compat:all"] == (
        "cross-env E2E_COMPAT_BROWSERS=chromium,firefox,webkit node scripts/run-e2e-compat.mjs"
    )


def test_cockpit_compatibility_retains_failure_diagnostics() -> None:
    config = (ROOT / "serve/cockpit/web/playwright.compat.config.ts").read_text(encoding="utf-8")
    workflow = _workflow(COCKPIT_VERIFY_PATH)
    browser = _job(workflow, "browser_compatibility")

    assert "trace: 'retain-on-failure'" in config
    assert "outputFolder: 'playwright-report'" in config

    upload_steps = [step for step in browser["steps"] if step.get("name") == "Upload browser compatibility diagnostics"]
    assert upload_steps == [
        {
            "name": "Upload browser compatibility diagnostics",
            "if": "always()",
            "uses": "actions/upload-artifact@043fb46d1a93c77aae656e7c1c64a875d1fc6a0a",
            "with": {
                "name": "cockpit-browser-compatibility-diagnostics",
                "path": "serve/cockpit/web/test-results\nserve/cockpit/web/playwright-report\n",
                "if-no-files-found": "ignore",
                "retention-days": 15,
            },
        }
    ]


def test_cockpit_workflow_actions_are_pinned() -> None:
    for line in COCKPIT_VERIFY_PATH.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped.startswith("uses:"):
            continue
        action = stripped.split("#", maxsplit=1)[0].removeprefix("uses:").strip()
        revision = action.rsplit("@", maxsplit=1)[1]
        assert len(revision) == 40
        assert all(character in "0123456789abcdef" for character in revision)


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
    rule = next(rule for rule in renovate["packageRules"] if rule.get("groupName") == "Ruff and MegaLinter toolchain")
    generic_group_index = next(
        index
        for index, candidate in enumerate(renovate["packageRules"])
        if candidate.get("description") == "Group routine version updates by ecosystem on Friday"
    )
    integrity_group_index = next(
        index
        for index, candidate in enumerate(renovate["packageRules"])
        if candidate.get("description") == "Group integrity updates by ecosystem on Friday"
    )
    toolchain_index = renovate["packageRules"].index(rule)

    assert dependency_match is not None
    assert hook_match is not None
    assert dependency_match.group("version") == hook_match.group("version")
    assert generic_group_index < toolchain_index
    assert integrity_group_index < toolchain_index
    assert rule["matchManagers"] == ["pep621", "pre-commit", "custom.regex", "github-actions"]
    assert rule["matchDatasources"] == ["pypi", "github-tags", "docker"]
    assert rule["matchPackageNames"] == [
        "ruff",
        "astral-sh/ruff-pre-commit",
        "ghcr.io/oxsecurity/megalinter",
        "ghcr.io/oxsecurity/megalinter-cupcake",
        "oxsecurity/megalinter",
    ]
