from __future__ import annotations

import importlib.util
import json
import re
import shutil
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
VERIFY_PATH = ROOT / ".github/workflows/dependency-verification.yml"
COCKPIT_VERIFY_PATH = ROOT / ".github/workflows/cockpit-verification.yml"
AGENT_WORKFLOW_PATH = ROOT / ".github/workflows/agent-ecosystem.yml"
SOURCE_VERIFY_PATH = ROOT / ".github/workflows/source-verification.yml"
COPILOT_SETUP_PATH = ROOT / ".github/workflows/copilot-setup-steps.yml"
MEGALINTER_PATH = ROOT / ".github/workflows/megalinter.yml"
SYNC_PATH = ROOT / ".github/workflows/sync-to-main.yml"
RUNTIME_SCRIPT = ROOT / ".github/scripts/check_node_runtime.py"
UV_VERSION_SCRIPT = ROOT / ".github/scripts/check_uv_version.py"
WORKSPACE_LOCK_SCRIPT = ROOT / ".github/scripts/check_uv_workspace_lock.py"
RUFF_TOOLCHAIN_SCRIPT = ROOT / ".github/scripts/check_ruff_toolchain.py"


@pytest.fixture
def toolchain_sync_module():
    spec = importlib.util.spec_from_file_location(
        "sync_megalinter_toolchain_test", ROOT / ".github/scripts/sync_megalinter_toolchain.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _toolchain_fixture(root, module, *, ruff="0.16.2", biome="2.5.11"):
    files = {
        module.MANIFEST: f'[dependency-groups]\ndev = ["ruff=={ruff}"]\n',
        module.PRE_COMMIT: f"repos:\n  - repo: https://github.com/astral-sh/ruff-pre-commit\n    rev: v{ruff}\n",
        module.BIOME_CONFIG: json.dumps({"$schema": f"https://biomejs.dev/schemas/{biome}/schema.json"}),
        module.NPM_MANIFEST: json.dumps({"devDependencies": {"@biomejs/biome": biome}}),
        "uv.lock": f'[[package]]\nname = "ruff"\nversion = "{ruff}"\n',
        module.NPM_LOCK: json.dumps(
            {
                "packages": {
                    "": {"devDependencies": {"@biomejs/biome": biome}},
                    "node_modules/@biomejs/biome": {"version": biome},
                }
            }
        ),
        module.MEGALINTER_CONFIG: "MEGALINTER_FLAVOR: cupcake\nMEGALINTER_VERSION: v10.1.0\n",
        module.MEGALINTER_WORKFLOW: f"uses: oxsecurity/megalinter/flavors/cupcake@{'a' * 40}  # v10.1.0\n",
    }
    for path, text in files.items():
        target = root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")


def test_toolchain_sync_uses_bundled_release_and_is_idempotent(tmp_path, toolchain_sync_module, monkeypatch):
    module = toolchain_sync_module
    _toolchain_fixture(tmp_path, module)
    commands = []

    def resolve(root, command):
        commands.append(command)
        if command[0] == "git":
            return "present"
        if command[0] == "uv":
            (tmp_path / "uv.lock").write_text('[[package]]\nname = "ruff"\nversion = "0.16.4"\n')
        else:
            lock = root / "package-lock.json"
            lock.write_text(lock.read_text().replace("2.5.11", "2.5.12"))
        return ""

    monkeypatch.setattr(module, "_run", resolve)
    versions = {"ruff": "0.16.4", "ruff-format": "0.16.4", "biome": "2.5.12"}
    module.synchronize(tmp_path, versions)
    module.synchronize(tmp_path, versions)
    assert "ruff==0.16.4" in (tmp_path / module.MANIFEST).read_text()
    assert "rev: v0.16.4" in (tmp_path / module.PRE_COMMIT).read_text()
    assert "/2.5.12/schema.json" in (tmp_path / module.BIOME_CONFIG).read_text()
    assert len(commands) == 3
    assert commands[0][-1] == "refs/tags/v0.16.4"
    assert "--no-build" in commands[1]
    assert "--ignore-scripts" in commands[2]


def test_toolchain_check_reports_drift_without_writing(tmp_path, toolchain_sync_module):
    module = toolchain_sync_module
    _toolchain_fixture(tmp_path, module)
    before = {path: (tmp_path / path).read_bytes() for path in module.OUTPUT_PATHS}
    with pytest.raises(ValueError, match="MegaLinter toolchain drift"):
        module.synchronize(tmp_path, {"ruff": "0.16.4", "ruff-format": "0.16.4", "biome": "2.5.11"}, check=True)
    assert before == {path: (tmp_path / path).read_bytes() for path in module.OUTPUT_PATHS}


def test_toolchain_sync_rejects_unavailable_hook_before_writing(tmp_path, toolchain_sync_module, monkeypatch):
    module = toolchain_sync_module
    _toolchain_fixture(tmp_path, module)
    before = {path: (tmp_path / path).read_bytes() for path in module.OUTPUT_PATHS}

    def missing(_root, command):
        raise subprocess.CalledProcessError(2, command)

    monkeypatch.setattr(module, "_run", missing)
    with pytest.raises(subprocess.CalledProcessError):
        module.synchronize(tmp_path, {"ruff": "0.16.4", "ruff-format": "0.16.4", "biome": "2.5.11"})
    assert before == {path: (tmp_path / path).read_bytes() for path in module.OUTPUT_PATHS}


@pytest.mark.parametrize("current", ["0.16.5", "0.16.4"])
def test_toolchain_sync_repairs_downgrade_and_lock_only_drift(tmp_path, toolchain_sync_module, monkeypatch, current):
    module = toolchain_sync_module
    _toolchain_fixture(tmp_path, module, ruff=current)
    lock = tmp_path / "uv.lock"
    lock.write_text('[[package]]\nname = "ruff"\nversion = "0.16.5"\n')

    def resolve(_root, command):
        if command[0] == "uv":
            lock.write_text('[[package]]\nname = "ruff"\nversion = "0.16.4"\n')
        return ""

    monkeypatch.setattr(module, "_run", resolve)
    module.synchronize(tmp_path, {"ruff": "0.16.4", "ruff-format": "0.16.4", "biome": "2.5.11"})
    assert "ruff==0.16.4" in (tmp_path / module.MANIFEST).read_text()
    assert tomllib.loads(lock.read_text())["package"][0]["version"] == "0.16.4"


@pytest.mark.parametrize(
    "metadata", [None, {}, {"ruff": "latest"}, {"ruff": "0.16.4", "ruff-format": "0.16.5", "biome": "2.5.11"}]
)
def test_toolchain_sync_rejects_invalid_metadata_before_writes(tmp_path, toolchain_sync_module, metadata):
    module = toolchain_sync_module
    _toolchain_fixture(tmp_path, module)
    before = (tmp_path / module.MANIFEST).read_bytes()
    with pytest.raises(ValueError, match="MegaLinter"):
        module.synchronize(tmp_path, metadata)
    assert (tmp_path / module.MANIFEST).read_bytes() == before


def test_toolchain_metadata_follows_candidate_tag(tmp_path, toolchain_sync_module, monkeypatch):
    module = toolchain_sync_module
    _toolchain_fixture(tmp_path, module)
    commands = []
    metadata = {"ruff": "0.16.4", "ruff-format": "0.16.4", "biome": "2.5.11"}
    monkeypatch.setattr(module, "_run", lambda _root, command: commands.append(command) or json.dumps(metadata))
    assert module.load_versions(tmp_path) == metadata
    assert (
        commands[0][-1]
        == "https://raw.githubusercontent.com/oxsecurity/megalinter/v10.1.0/.automation/generated/linter-versions.json"
    )


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
    pull_request = workflow["on"]["pull_request"]

    assert pull_request["branches"] == ["dev"]
    assert pull_request["types"] == ["opened", "reopened", "synchronize", "ready_for_review"]
    assert set(pull_request["paths"]) == {
        ".github/renovate.json",
        ".github/scripts/check_ruff_toolchain.py",
        ".github/scripts/check_uv_workspace_lock.py",
        ".github/scripts/sync_megalinter_toolchain.py",
        ".github/workflows/**",
        ".mega-linter.yml",
        ".pre-commit-config.yaml",
        ".python-version",
        ".owlbear/scripts/diagrams/**",
        "share/diagrams/**",
        "biome.json",
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
        "(github.event_name != 'pull_request' || github.event.pull_request.draft == false) && "
        "(github.event_name != 'workflow_dispatch' || inputs.cache_probe == 'none')"
    )
    assert "workflow_dispatch" in workflow["on"]


def test_pull_request_proof_workflows_skip_draft_jobs_and_run_when_ready() -> None:
    expected_types = ["opened", "reopened", "synchronize", "ready_for_review"]
    for path in (AGENT_WORKFLOW_PATH, VERIFY_PATH, COCKPIT_VERIFY_PATH, SOURCE_VERIFY_PATH):
        workflow = _workflow(path)
        pull_request = workflow["on"]["pull_request"]
        assert pull_request["types"] == expected_types
        jobs = workflow["jobs"]
        assert isinstance(jobs, dict)
        for job_name, job in jobs.items():
            assert isinstance(job, dict)
            condition = job.get("if")
            assert isinstance(condition, str), f"{path.name}:{job_name} needs a draft guard"
            if path == VERIFY_PATH and job_name in {"cache-probe-uv", "cache-probe-precommit"}:
                assert condition.startswith("github.event_name == 'workflow_dispatch' && ")
                continue
            assert "github.event_name != 'pull_request'" in condition
            assert "github.event.pull_request.draft == false" in condition


def test_agent_workflow_delegates_python_workspace_paths() -> None:
    workflow = _workflow(AGENT_WORKFLOW_PATH)
    paths = set(workflow["on"]["pull_request"]["paths"])

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
    assert 'uv sync --locked --python "${MATRIX_PYTHON}" --all-packages --all-extras --all-groups' in text
    assert 'uv run --python "${MATRIX_PYTHON}" pytest tests serve \\' in text
    assert '            -m "not api and not e2e and not browser and not cockpit and not model"' in text
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


def test_dependency_workflow_avoids_duplicate_pr_python_proof() -> None:
    workflow = _workflow(VERIFY_PATH)
    proof_python = _job(workflow, "proof-python")
    python_steps = {step["name"]: step for step in proof_python["steps"]}

    assert python_steps["Prove workspace lock regeneration"]["if"] == "matrix.python == '3.12.14'"
    for step_name in ("Compile Python sources", "Check Python sources", "Run Python behavior tests"):
        assert python_steps[step_name]["if"] == (
            "github.event_name == 'workflow_dispatch' || matrix.python == '3.12.14'"
        )


def test_dependency_workflow_proves_ruff_toolchain_parity() -> None:
    workflow = _workflow(VERIFY_PATH)
    compatibility = _job(workflow, "compatibility")
    text = VERIFY_PATH.read_text(encoding="utf-8")

    assert "ruff_toolchain: ${{ steps.scope.outputs.ruff_toolchain }}" in text
    assert "uv sync --locked --group dev" in text
    parity_steps = [step for step in compatibility["steps"] if step.get("name") == "Verify Ruff toolchain parity"]
    assert parity_steps == [
        {
            "name": "Verify Ruff toolchain parity",
            "if": "needs.classify.outputs.ruff_toolchain == 'true'",
            "run": "uv run python .github/scripts/check_ruff_toolchain.py",
        }
    ]


def test_dependency_workflow_does_not_download_megalinter_image() -> None:
    workflow = _workflow(VERIFY_PATH)
    compatibility = _job(workflow, "compatibility")
    text = VERIFY_PATH.read_text(encoding="utf-8")

    megalinter_steps = [
        step for step in compatibility["steps"] if step.get("name") == "Exercise updated MegaLinter image"
    ]
    assert megalinter_steps == []
    assert "megalint --no-fix" not in text


def test_source_verification_keeps_ruff_only_updates_lightweight() -> None:
    workflow = _workflow(SOURCE_VERIFY_PATH)
    classify = _job(workflow, "classify")
    python = _job(workflow, "python")
    steps = {step["name"]: step for step in python["steps"]}
    text = SOURCE_VERIFY_PATH.read_text(encoding="utf-8")

    assert classify["outputs"] == {"python": "${{ steps.scope.outputs.python }}"}
    assert python["needs"] == "classify"
    assert steps["Install locked Python workspace"]["if"] == "needs.classify.outputs.python == 'true'"
    assert steps["Install locked Python tooling"]["if"] == "needs.classify.outputs.python != 'true'"
    assert steps["Install locked Python tooling"]["run"] == "uv sync --locked --group dev"
    assert steps["Install Chromium for browser-marked tests"]["if"] == "needs.classify.outputs.python == 'true'"
    assert steps["Compile Python sources"]["if"] == "needs.classify.outputs.python == 'true'"
    assert steps["Run Python behavior tests"]["if"] == "needs.classify.outputs.python == 'true'"
    assert "dependency_ci.py" in text
    assert "git diff --name-only -z" in text


def test_dependency_workflow_uses_semantic_snapshots_and_protects_proof_tooling() -> None:
    workflow = _workflow(VERIFY_PATH)
    classify = _job(workflow, "classify")
    compatibility = _job(workflow, "compatibility")
    text = VERIFY_PATH.read_text(encoding="utf-8")

    assert classify["outputs"]["proof_tooling"] == "${{ steps.proof_tooling.outputs.proof_tooling }}"
    assert classify["outputs"]["workspace_lock_tooling"] == (
        "${{ steps.proof_tooling.outputs.workspace_lock_tooling }}"
    )
    assert 'MERGE_BASE="$(git merge-base "$BASE_SHA" "$HEAD_SHA")"' in text
    assert '--base-ref "$MERGE_BASE"' in text
    assert '--head-ref "$HEAD_SHA"' in text
    assert compatibility["if"] == (
        "(github.event_name != 'pull_request' || github.event.pull_request.draft == false) && "
        "(needs.classify.outputs.compatibility == 'true' || "
        "needs.classify.outputs.proof_tooling == 'true' || "
        "needs.classify.outputs.workspace_lock_tooling == 'true')"
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
    workspace_lock_steps = [step for step in steps if step.get("name") == "Exercise workspace lock proof"]
    assert workspace_lock_steps == [
        {
            "name": "Exercise workspace lock proof",
            "if": "needs.classify.outputs.workspace_lock_tooling == 'true'",
            "run": "uv run python .github/scripts/check_uv_workspace_lock.py",
        }
    ]
    assert ".github/scripts/check_uv_workspace_lock.py)" in text
    assert ".github/workflows/*|" in text
    assert "serve/tools/src/owlbear_tools/megalinter.py|" in text
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
    assert "uv sync --locked --all-packages --group dev" in runs
    assert "npm ci --engine-strict --no-audit --no-fund" in runs
    install_commands = {
        "uv python install",
        "uv sync --locked --all-packages --group dev",
        "npm ci --engine-strict --no-audit --no-fund",
    }
    for step in steps:
        if step.get("working-directory") == "serve/cockpit/web" or step.get("uses", "").startswith(
            "actions/setup-node@"
        ):
            assert step["if"] == "hashFiles('serve/cockpit/web/package-lock.json') != ''"
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
        "uv sync --locked --all-packages --group dev",
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
    assert node_setup["with"]["node-version-file"] == "serve/cockpit/web/.nvmrc"
    assert "node-version" not in node_setup["with"]
    assert not any("python-version" in step.get("with", {}) for step in steps)
    for line in COPILOT_SETUP_PATH.read_text().splitlines():
        if "uses:" in line:
            assert re.search(r"@[0-9a-f]{40}\s+# v[0-9]+\.[0-9]+\.[0-9]+$", line)


def test_uv_runtime_check_precedes_uv_commands() -> None:
    for path in (VERIFY_PATH, AGENT_WORKFLOW_PATH, COPILOT_SETUP_PATH):
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


def test_ruff_toolchain_proof_accepts_aligned_repository_versions(
    tmp_path: Path,
    ruff_toolchain_module: ModuleType,
) -> None:
    version = _workspace_ruff_version()
    ruff_toolchain_module.check_ruff_toolchain(
        ROOT,
        ruff_executable=str(_fake_ruff(tmp_path, version)),
        megalinter_versions_loader=lambda _: {"ruff": version},
    )


def test_megalinter_metadata_url_uses_requested_version(ruff_toolchain_module: ModuleType) -> None:
    urls: list[str] = []

    metadata_version = ruff_toolchain_module._read_megalinter_declared_ruff_version(  # noqa: SLF001
        "v9.9.9",
        json_loader=lambda url: urls.append(url) or {"ruff": "0.16.5"},
    )
    assert metadata_version == "0.16.5"
    assert urls == [
        ("https://raw.githubusercontent.com/oxsecurity/megalinter/v9.9.9/.automation/generated/linter-versions.json")
    ]


def test_ruff_toolchain_proof_rejects_installed_version_drift(
    tmp_path: Path,
    ruff_toolchain_module: ModuleType,
) -> None:
    with pytest.raises(ValueError, match=r"installed Ruff=0\.16\.1"):
        ruff_toolchain_module.check_ruff_toolchain(
            ROOT,
            ruff_executable=str(_fake_ruff(tmp_path, "0.16.1")),
            megalinter_versions_loader=lambda _: {"ruff": _workspace_ruff_version()},
        )


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
        "always() && (github.event_name != 'pull_request' || github.event.pull_request.draft == false) && "
        "(github.event_name != 'workflow_dispatch' || inputs.cache_probe == 'none')"
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
        "${{ needs.classify.outputs.compatibility == 'true' || "
        "needs.classify.outputs.proof_tooling == 'true' || "
        "needs.classify.outputs.workspace_lock_tooling == 'true' }}"
    )


def test_cache_probes_are_opt_in_and_isolated_from_required_proofs() -> None:
    workflow = _workflow(VERIFY_PATH)
    probe_input = workflow["on"]["workflow_dispatch"]["inputs"]["cache_probe"]
    assert probe_input["default"] == "none"
    assert probe_input["options"] == ["none", "uv", "precommit"]
    assert "inputs.cache_probe || 'none'" in workflow["concurrency"]["group"]
    for job_name in ("classify", "resolve_runtimes", "gate"):
        assert (
            "github.event_name != 'workflow_dispatch' || inputs.cache_probe == 'none'"
            in (_job(workflow, job_name)["if"])
        )
    assert not set(_job(workflow, "gate")["needs"]) & {"cache-probe-uv", "cache-probe-precommit"}
    for job_name, mode in (("cache-probe-uv", "uv"), ("cache-probe-precommit", "precommit")):
        probe = _job(workflow, job_name)
        assert probe["if"] == f"github.event_name == 'workflow_dispatch' && inputs.cache_probe == '{mode}'"
        assert probe["runs-on"] == "ubuntu-24.04"
        assert not probe["strategy"]["fail-fast"]
        assert "needs" not in probe
        for step in probe["steps"]:
            assert not any(command in step.get("run", "") for command in ("pytest", "uv run lint", "megalint"))

    uv_probe = _job(workflow, "cache-probe-uv")
    assert uv_probe["strategy"]["matrix"] == {
        "policy": ["current", "pruned", "disabled"],
        "python": ["3.12.14", "pinned"],
    }
    uv_cache = next(step["with"] for step in uv_probe["steps"] if step.get("id") == "uv")
    assert uv_cache["enable-cache"] == "${{ matrix.policy != 'disabled' }}"
    assert uv_cache["prune-cache"] == "${{ matrix.policy == 'pruned' }}"
    assert uv_cache["cache-local-path"] == "${{ runner.temp }}/uv-cache-probe-${{ matrix.policy }}"
    assert uv_cache["cache-suffix"] == "probe-${{ github.run_id }}-${{ matrix.policy }}"
    precommit_probe = _job(workflow, "cache-probe-precommit")
    hooks = next(step for step in precommit_probe["steps"] if step.get("id") == "hooks")
    assert hooks["if"] == "matrix.policy == 'cached'"
    assert hooks["with"]["path"] == "${{ env.PRE_COMMIT_HOME }}"
    assert "precommit-probe-${{ github.run_id }}" in hooks["with"]["key"]
    assert "steps.python.outputs.identity" in hooks["with"]["key"]
    assert ".pre-commit-config.yaml" in hooks["with"]["key"]
    assert "restore-keys" not in hooks["with"]
    assert "github.run_attempt" not in uv_cache["cache-suffix"] + hooks["with"]["key"]


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
        ("serve/web-content/pyproject.toml", "python"),
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


@pytest.mark.parametrize(
    "path",
    [
        ".github/workflows/source-verification.yml",
        "serve/delivery/src/owlbear_delivery/example.py",
        "tests/test_example.py",
    ],
)
def test_classifier_marks_source_paths_for_python_behavior_proof(path: str) -> None:
    scope = classify_dependency_change([path], "")

    assert scope.python


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
        "",
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
        "",
        before_files={"pyproject.toml": before},
        after_files={"pyproject.toml": after},
    )

    assert scope.python
    assert not scope.ruff_toolchain


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
    assert manifest["scopes"]["web-content"] == ["serve/web-content"]
    assert {
        ".github/copilot-instructions.md",
        ".github/skills",
    }.issubset(manifest["consumer_excluded_paths"])
    assert ".mega-linter.yml" in manifest["consumer_excluded_paths"]
    assert "python3 .github/scripts/sync_manifest.py paths" in workflow
    assert "python3 .github/scripts/sync_manifest.py excluded" in workflow
    assert "for excluded_path in $CONSUMER_EXCLUDED_PATHS" in workflow
    assert "sync_web_content:" in workflow


def test_shared_web_content_dependency_edges_are_declared() -> None:
    browser = tomllib.loads((ROOT / "serve/browser/pyproject.toml").read_text(encoding="utf-8"))
    knowledge = tomllib.loads((ROOT / "serve/knowledge/pyproject.toml").read_text(encoding="utf-8"))
    root = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))

    assert "owlbear-web-content" in browser["project"]["dependencies"]
    assert "owlbear-web-content" in knowledge["project"]["optional-dependencies"]["intake"]
    assert "owlbear-web-content" in knowledge["project"]["optional-dependencies"]["full"]
    assert "serve/web-content/src" in root["tool"]["ruff"]["src"]


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
        "**/*.json",
        "**/*.jsonc",
        "**/.editorconfig",
        "**/.gitignore",
        ".mega-linter.yml",
        ".pre-commit-config.yaml",
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

    assert re.search(r"trace:\s*['\"]retain-on-failure['\"]", config)
    assert re.search(r"outputFolder:\s*['\"]playwright-report['\"]", config)

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
        rule.get("minimumReleaseAge") == "24 hours"
        and rule.get("matchDatasources") == ["github-tags"]
        and rule.get("matchPackageNames") == ["oxsecurity/megalinter"]
        for rule in renovate["packageRules"]
    )
    assert any(
        rule.get("minimumReleaseAge") == "72 hours" and rule.get("matchUpdateTypes") == ["major"]
        for rule in renovate["packageRules"]
    )
    assert all("Renovate CLI" not in manager.get("description", "") for manager in renovate["customManagers"])


def test_renovate_derives_linter_updates_from_megalinter() -> None:
    renovate = json.loads((ROOT / ".github/renovate.json").read_text(encoding="utf-8"))
    for package in ("ruff", "astral-sh/ruff-pre-commit", "@biomejs/biome"):
        rules = [rule for rule in renovate["packageRules"] if package in rule.get("matchPackageNames", [])]
        assert rules[-1]["enabled"] is False
        assert all("allowedVersions" not in rule for rule in rules)
    rules = [rule for rule in renovate["packageRules"] if "oxsecurity/megalinter" in rule.get("matchPackageNames", [])]
    assert rules[-1]["groupName"] == "MegaLinter toolchain"
    assert all(rule.get("enabled", True) and "minimumGroupSize" not in rule for rule in rules)


def _git_fixture(root, *arguments):
    executable = shutil.which("git")
    assert executable is not None
    return subprocess.run(  # noqa: S603
        [executable, "-c", "core.hooksPath=/dev/null", "-c", "commit.gpgsign=false", *arguments],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _commit_fixture(root):
    _git_fixture(root, "add", ".")
    _git_fixture(root, "-c", "user.name=Fixture", "-c", "user.email=fixture@example.com", "commit", "-m", "fixture")
    return _git_fixture(root, "rev-parse", "HEAD")


@pytest.mark.parametrize("attack", ["unexpected-file", "npm-script", "symlink"])
def test_toolchain_candidate_rejects_unsafe_pr_changes(tmp_path, toolchain_sync_module, attack):
    module = toolchain_sync_module
    _toolchain_fixture(tmp_path, module)
    _git_fixture(tmp_path, "init")
    base = _commit_fixture(tmp_path)
    if attack == "unexpected-file":
        (tmp_path / "malicious.py").write_text("print('untrusted')\n")
    elif attack == "npm-script":
        manifest = tmp_path / module.NPM_MANIFEST
        document = json.loads(manifest.read_text())
        document["scripts"] = {"postinstall": "untrusted"}
        manifest.write_text(json.dumps(document))
    else:
        target = tmp_path / module.MANIFEST
        target.unlink()
        target.symlink_to("uv.lock")
    _commit_fixture(tmp_path)
    with pytest.raises(ValueError, match=r"Unexpected change|Non-version edits|symlink"):
        module.validate_candidate(tmp_path, base)


def test_toolchain_candidate_accepts_version_changes_and_discards_pr_locks(tmp_path, toolchain_sync_module):
    module = toolchain_sync_module
    _toolchain_fixture(tmp_path, module)
    _git_fixture(tmp_path, "init")
    base = _commit_fixture(tmp_path)
    for path in (module.MEGALINTER_CONFIG, module.MEGALINTER_WORKFLOW):
        target = tmp_path / path
        target.write_text(target.read_text().replace("v10.1.0", "v10.2.0"))
    lock = tmp_path / "uv.lock"
    original = lock.read_text()
    lock.write_text("untrusted lockfile contents")
    _commit_fixture(tmp_path)
    module.validate_candidate(tmp_path, base)
    assert lock.read_text() == original
    assert "v10.2.0" in (tmp_path / module.MEGALINTER_CONFIG).read_text()


def test_toolchain_writer_preserves_trust_and_publication_boundaries():
    workflow = _workflow(ROOT / ".github/workflows/sync-megalinter-toolchain.yml")
    job = _job(workflow, "sync")
    assert "github.event.pull_request.user.login == 'renovate[bot]'" in job["if"]
    assert "github.event.pull_request.head.repo.full_name == github.repository" in job["if"]
    steps = {step["name"]: step for step in job["steps"]}
    checkout = steps["Checkout trusted base code"]
    assert checkout["with"]["ref"] == "${{ github.event.pull_request.base.sha }}"
    assert checkout["with"]["persist-credentials"] is False
    sync = steps["Validate candidate and synchronize exact versions"]
    assert '--base-ref "$BASE_SHA"' in sync["run"]
    publish = steps["Publish alignment commit on unchanged PR head"]
    assert "secrets.PAT" in publish["env"]["GH_TOKEN"]
    assert '--force-with-lease="refs/heads/$HEAD_BRANCH:$HEAD_SHA"' in publish["run"]
    assert "core.hooksPath=/dev/null" in publish["run"]
    assert "41898282+github-actions[bot]@users.noreply.github.com" in publish["run"]
