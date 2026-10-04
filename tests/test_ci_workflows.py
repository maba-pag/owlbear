from __future__ import annotations

import re
import tomllib
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).parents[1]
WORKFLOWS = ROOT / ".github/workflows"
PULL_REQUEST_WORKFLOWS = (
    "agent-ecosystem.yml",
    "cockpit.yml",
    "python.yml",
    "python-browser.yml",
    "static.yml",
    "tooling.yml",
)
REUSING_WORKFLOWS = ("cockpit.yml", "python.yml", "python-browser.yml", "static.yml", "tooling.yml")
SKIPPED_PACKAGE_WORKFLOWS = ("python.yml", "copilot-setup-steps.yml")


def _workflow(name: str) -> dict[str, object]:
    document = yaml.safe_load((WORKFLOWS / name).read_text(encoding="utf-8"))
    if True in document and "on" not in document:
        document["on"] = document.pop(True)
    return document


def _jobs(name: str) -> dict[str, dict[str, object]]:
    jobs = _workflow(name)["jobs"]
    assert isinstance(jobs, dict)
    return jobs


def _runs(job: dict[str, object]) -> str:
    return "\n".join(str(step.get("run", "")) for step in job["steps"])


def _skipped_packages(name: str) -> list[str]:
    workflow = _workflow(name)
    env = workflow.get("env") or {}
    if "CI_SKIPPED_PACKAGES" not in env:
        steps = [step for job in _jobs(name).values() for step in job["steps"]]
        env = next(step["env"] for step in steps if "CI_SKIPPED_PACKAGES" in step.get("env", {}))
    return env["CI_SKIPPED_PACKAGES"].split()


def test_replaced_workflows_are_gone() -> None:
    for name in ("source-verification.yml", "dependency-verification.yml", "cockpit-verification.yml"):
        assert not (WORKFLOWS / name).exists()


@pytest.mark.parametrize("name", PULL_REQUEST_WORKFLOWS)
def test_pull_request_workflows_target_dev_and_skip_drafts(name: str) -> None:
    workflow = _workflow(name)
    pull_request = workflow["on"]["pull_request"]

    assert pull_request["branches"] == ["dev"]
    assert len(pull_request["paths"]) == len(set(pull_request["paths"]))
    for job_name, job in _jobs(name).items():
        condition = job["if"]
        assert "github.event.pull_request.draft == false" in condition, f"{name}:{job_name}"
        assert "needs" not in job, f"{name}:{job_name} must start without waiting for another job"


@pytest.mark.parametrize("name", sorted(path.name for path in WORKFLOWS.glob("*.yml")))
def test_workflow_actions_are_pinned_to_full_commits(name: str) -> None:
    for line in (WORKFLOWS / name).read_text(encoding="utf-8").splitlines():
        stripped = line.strip().removeprefix("- ")
        if not stripped.startswith("uses:") or "uses: ./" in stripped:
            continue
        revision = stripped.split("#", maxsplit=1)[0].rsplit("@", maxsplit=1)[1].strip()
        assert re.fullmatch(r"[0-9a-f]{40}", revision), line


@pytest.mark.parametrize("name", REUSING_WORKFLOWS)
def test_proof_jobs_reuse_only_identical_passing_inputs(name: str) -> None:
    workflow = _workflow(name)
    assert workflow["permissions"] == {"contents": "read"}
    assert workflow["concurrency"]["cancel-in-progress"] is True
    for job_name, job in _jobs(name).items():
        steps = job["steps"]
        checkout = steps[0]
        assert checkout["uses"].startswith("actions/checkout@")
        assert checkout["with"]["ref"] == "${{ github.event.pull_request.head.sha || github.sha }}"
        assert checkout["with"]["persist-credentials"] is False
        fingerprint = next(step for step in steps if step.get("id") == "fingerprint")
        assert "git ls-files -s" in fingerprint["run"]
        lookup = next(step for step in steps if step.get("id") == "reuse")
        save = steps[-1]
        assert lookup["uses"].startswith("actions/cache/restore@")
        assert lookup["with"]["lookup-only"] is True
        assert save["uses"].startswith("actions/cache/save@")
        assert save["with"]["key"] == lookup["with"]["key"]
        assert lookup["with"]["key"].startswith("ci-pass-v1-")
        assert "steps.fingerprint.outputs.value" in lookup["with"]["key"]
        work = steps[steps.index(lookup) + 1 : -1]
        for step in work:
            condition = step.get("if", "")
            if step.get("name") in {"Report reused result", "Upload browser diagnostics"}:
                continue
            assert "steps.reuse.outputs.cache-hit != 'true'" in condition, f"{name}:{job_name}:{step.get('name')}"


def test_python_tests_are_sharded_without_the_model_stack() -> None:
    workflow = _workflow("python.yml")
    job = _jobs("python.yml")["tests"]
    shards = job["strategy"]["matrix"]["shard"]
    runs = _runs(job)

    assert shards == list(range(1, int(workflow["env"]["CI_SHARDS"]) + 1))
    assert job["name"] == f"Python tests ${{{{ matrix.shard }}}}/{len(shards)}"
    assert job["strategy"]["fail-fast"] is False
    assert 'uv sync --locked --all-packages --all-groups "${skipped[@]}"' in runs
    assert '-m "not e2e and not model and not browser" --dist worksteal' in runs
    assert "zlib.crc32(item.nodeid.encode()) % total == index" in runs
    assert "playwright install" not in runs
    assert "ruff" not in runs


def test_skipped_packages_cover_the_locked_gpu_stack_and_stay_aligned() -> None:
    lock = tomllib.loads((ROOT / "uv.lock").read_text(encoding="utf-8"))
    locked = {package["name"] for package in lock["package"]}
    gpu = {name for name in locked if name.startswith(("nvidia-", "cuda-")) or name in {"torch", "triton"}}
    lists = {name: _skipped_packages(name) for name in SKIPPED_PACKAGE_WORKFLOWS}

    assert len({tuple(values) for values in lists.values()}) == 1
    skipped = set(next(iter(lists.values())))
    assert gpu <= skipped
    assert {"flagembedding", "transformers"} <= skipped


def test_python_browser_tests_run_alone_with_chromium() -> None:
    workflow = _workflow("python-browser.yml")
    runs = _runs(_jobs("python-browser.yml")["browser"])

    assert {"serve/browser/**", "serve/browser-mcp/**", "serve/web-content/**"} <= set(
        workflow["on"]["pull_request"]["paths"]
    )
    assert "uv sync --locked --package owlbear-browser-mcp --group dev" in runs
    assert "uv run --no-sync playwright install --with-deps chromium" in runs
    assert "pytest serve/browser serve/browser-mcp -m browser" in runs


def test_cockpit_unit_and_browser_proofs_run_in_parallel() -> None:
    workflow = _workflow("cockpit.yml")
    jobs = _jobs("cockpit.yml")
    unit = _runs(jobs["unit"])
    browser = _runs(jobs["browser"])

    assert "**/*.json" not in workflow["on"]["pull_request"]["paths"]
    assert "serve/cockpit/web/**" in workflow["on"]["pull_request"]["paths"]
    for command in ("npm test", "npm run typecheck:e2e", "npm run test:biome-pds", "npm run test:sync-pds"):
        assert command in unit
    assert "check_node_runtime.py" in unit
    assert "npx playwright install --with-deps chromium" in browser
    assert "npm run test:e2e:compat" in browser
    assert jobs["browser"]["env"] == {"E2E_COMPAT_BROWSERS": "chromium"}
    upload = next(step for step in jobs["browser"]["steps"] if step.get("name") == "Upload browser diagnostics")
    assert upload["if"] == "failure()"


def test_static_checks_own_repository_lint() -> None:
    workflow = _workflow("static.yml")
    runs = _runs(_jobs("static.yml")["lint"])

    assert {"**/*.py", "**/*.json", "**/*.jsonc", "biome.json", "pyproject.toml"} <= set(
        workflow["on"]["pull_request"]["paths"]
    )
    assert "uv sync --locked --only-group dev" in runs
    assert "uv run --no-sync ruff check ." in runs
    assert "uv run --no-sync ruff format --check ." in runs
    assert "npm run lint:biome:ci" in runs
    assert "npm run lint:html" in runs


@pytest.mark.parametrize("name", [*PULL_REQUEST_WORKFLOWS, "copilot-setup-steps.yml"])
def test_uv_setups_use_scoped_caches_and_check_the_runtime_first(name: str) -> None:
    for job in _jobs(name).values():
        steps = job["steps"]
        setups = [index for index, step in enumerate(steps) if "astral-sh/setup-uv@" in str(step.get("uses", ""))]
        if not setups:
            continue
        setup = steps[setups[0]]["with"]
        if name != "copilot-setup-steps.yml":
            assert setup["cache-suffix"] in {"python-tests", "python-browser", "dev-tools"}
        check = next(index for index, step in enumerate(steps) if "check_uv_version.py" in str(step.get("run", "")))
        first_uv = next(
            index
            for index, step in enumerate(steps)
            if re.search(r"\buv\s+(?:python|run|sync|lock)", str(step.get("run", "")))
        )
        assert setups[0] < check < first_uv
