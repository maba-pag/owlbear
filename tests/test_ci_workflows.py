from __future__ import annotations

import importlib.util
import os
import re
import subprocess
import tomllib
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).parents[1]
WORKFLOWS = ROOT / ".github/workflows"
SUITE_WORKFLOWS = (
    "agent-ecosystem.yml",
    "cockpit.yml",
    "python.yml",
    "python-browser.yml",
    "security.yml",
    "static.yml",
    "tooling.yml",
)
REUSING_WORKFLOWS = ("cockpit.yml", "python.yml", "python-browser.yml", "static.yml", "tooling.yml")
SKIPPED_PACKAGE_WORKFLOWS = ("python.yml", "copilot-setup-steps.yml")
PR_ONLY = "${{ github.event_name == 'pull_request' }}"
_SPEC = importlib.util.spec_from_file_location("ci_scope", ROOT / ".github/scripts/ci_scope.py")
ci_scope = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(ci_scope)


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


@pytest.mark.parametrize("name", SUITE_WORKFLOWS)
def test_suites_run_only_when_the_ci_gate_calls_them_and_also_on_drafts(name: str) -> None:
    assert set(_workflow(name)["on"]) == {"workflow_call", "workflow_dispatch"}
    for job_name, job in _jobs(name).items():
        assert "draft" not in str(job.get("if", "")), f"{name}:{job_name}"
        assert "needs" not in job, f"{name}:{job_name} must start without waiting for another job"


def test_the_ci_gate_calls_each_touched_suite_and_passes_only_when_all_of_them_passed() -> None:
    gate = _workflow("ci.yml")
    jobs = gate["jobs"]
    pull_request = gate["on"]["pull_request"]
    called = {name: job for name, job in jobs.items() if "uses" in job}

    assert (pull_request["branches"], "paths" in pull_request) == (["main"], False)
    assert "ready_for_review" in pull_request["types"]
    assert gate["on"]["push"] == {"branches": ["main"]}  # every merge gets its own CI (self-update design section 8)
    assert set(called) == set(ci_scope.SUITES)
    assert {job["uses"] for job in called.values()} == {f"./.github/workflows/{n}" for n in SUITE_WORKFLOWS}
    for name, job in called.items():
        assert job["if"] == f"contains(fromJSON(needs.scope.outputs.suites), '{name}')"
    final = jobs["ci"]
    assert (final["name"], final["if"]) == ("CI", "always()")
    assert set(final["needs"]) == {"scope", *ci_scope.SUITES}
    check = final["steps"][0]["run"]
    assert 'needs["scope"]["result"] != "success"' in check
    assert 'needs[name]["result"] != "success"' in check


@pytest.mark.parametrize(
    ("paths", "touched"),
    [
        (["README.md"], []),
        (["serve/delivery-next/src/owlbear_delivery_next/api.py"], ["python", "python-browser", "static", "security"]),
        (["serve/cockpit/web/src/app.tsx"], ["cockpit", "static", "security"]),
        (["uv.lock"], ["python", "python-browser", "static", "tooling", "security"]),
        ([".github/workflows/ci.yml"], list(ci_scope.SUITES)),
        ([".github/scripts/ci_scope.py"], list(ci_scope.SUITES)),
        (["share/skills/x/SKILL.md"], ["agent-ecosystem"]),
        (["serve/a/b/src/x.txt"], []),
    ],
)
def test_the_scope_follows_github_path_filters(paths: list[str], touched: list[str]) -> None:
    assert ci_scope.suites(paths) == touched


def test_the_scope_reads_changed_paths_unquoted(tmp_path: Path) -> None:
    def git(*args: str) -> str:
        done = subprocess.run(  # noqa: S603 - fixed git argument vector
            ["git", "-c", "user.name=t", "-c", "user.email=t@t", *args],  # noqa: S607
            cwd=tmp_path,
            capture_output=True,
            text=True,
            check=True,
        )
        return done.stdout.strip()

    git("init", "-q")
    git("commit", "-q", "--allow-empty", "-m", "base")
    base = git("rev-parse", "HEAD")
    source = tmp_path / "serve/delivery-next/src/caf\u00e9 x.py"
    source.parent.mkdir(parents=True)
    source.write_text("\n")
    git("add", ".")
    git("commit", "-q", "-m", "head")

    paths = subprocess.run(  # noqa: S603
        ["python3", str(ROOT / ".github/scripts/ci_scope.py"), base, "HEAD"],  # noqa: S607
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=True,
    ).stdout

    assert paths == 'suites=["python", "python-browser", "static", "security"]\n'


def test_the_snyk_suite_only_tests_and_gets_its_token_from_the_gate() -> None:
    """TD-319: nothing is written into the Snyk org; a finding fails the run with its file and line in the log."""
    steps = _jobs("security.yml")["snyk"]["steps"]
    runs = _runs({"steps": steps})
    assert "snyk code test" in runs
    assert "snyk test --all-projects" in runs
    assert "--fail-on=upgradable" in runs  # TD-321: a finding without a Snyk fix prints but passes
    assert not any(word in runs for word in ("monitor", "--report", "|| true"))
    assert _workflow("security.yml")["env"]["SNYK_API"] == "https://api.eu.snyk.io"
    assert _jobs("ci.yml")["security"]["secrets"] == {"SNYK_TOKEN": "${{ secrets.SNYK_TOKEN }}"}


def test_every_suite_lists_its_own_workflow_and_no_glob_twice() -> None:
    for name, globs in ci_scope.SUITES.items():
        assert len(globs) == len(set(globs)), name
        assert f".github/workflows/{name}.yml" in globs or ".github/workflows/**" in globs, name


@pytest.mark.parametrize("name", ["ci.yml", *SUITE_WORKFLOWS])
def test_a_pull_request_cancels_its_older_runs_but_a_push_to_main_runs_per_commit_to_the_end(name: str) -> None:
    """A cancelled push run would leave its merge without a passed CI, which holds back every later version."""
    concurrency = _workflow(name)["concurrency"]
    assert concurrency["group"].endswith("-${{ github.event.pull_request.number || github.sha }}")
    assert concurrency["cancel-in-progress"] == PR_ONLY


def test_tooling_scopes_a_push_by_the_merge_against_its_first_parent() -> None:
    """A push has no pull request base; reading it made git exit 128 on main's first push run."""
    step = next(s for s in _jobs("tooling.yml")["verify"]["steps"] if s.get("id") == "scope")
    assert step["env"]["HEAD_SHA"] == "${{ github.event.pull_request.head.sha || github.sha }}"
    assert 'if [[ "$EVENT_NAME" == "push" ]]; then BASE_SHA="$(git rev-parse "$HEAD_SHA^1")"; fi' in step["run"]


def test_a_push_is_scoped_by_the_merge_against_its_first_parent(tmp_path: Path) -> None:
    def git(*args: str) -> str:
        done = subprocess.run(  # noqa: S603 - fixed git argument vector
            ["git", "-c", "user.name=t", "-c", "user.email=t@t", *args],  # noqa: S607
            cwd=tmp_path, capture_output=True, text=True, check=True,
        )  # fmt: skip
        return done.stdout.strip()

    git("init", "-q", "-b", "main")
    (tmp_path / ".github/scripts").mkdir(parents=True)
    (tmp_path / ".github/scripts/ci_scope.py").write_bytes((ROOT / ".github/scripts/ci_scope.py").read_bytes())
    git("add", ".")
    git("commit", "-q", "-m", "base")
    git("switch", "-q", "-c", "work")
    (tmp_path / "share/skills/x").mkdir(parents=True)
    (tmp_path / "share/skills/x/SKILL.md").write_text("x\n")
    git("add", ".")
    git("commit", "-q", "-m", "skill")
    git("switch", "-q", "main")
    git("merge", "-q", "--no-ff", "-m", "merge", "work")
    run = next(s["run"] for s in _jobs("ci.yml")["scope"]["steps"] if s.get("id") == "scope")
    out = tmp_path / "output"
    env = {"PATH": os.environ["PATH"], "EVENT": "push", "BASE_SHA": "", "HEAD_SHA": git("rev-parse", "HEAD"),
           "GITHUB_OUTPUT": str(out)}  # fmt: skip
    subprocess.run(["bash", "-c", run], cwd=tmp_path, env=env, check=True)  # noqa: S603, S607
    assert out.read_text() == 'suites=["agent-ecosystem"]\n'  # the merge's own change, not every suite


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
    assert workflow["concurrency"]["cancel-in-progress"] == PR_ONLY
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
    runs = _runs(_jobs("python-browser.yml")["browser"])

    assert {"serve/browser/**", "serve/browser-mcp/**", "serve/web-content/**"} <= set(
        ci_scope.SUITES["python-browser"]
    )
    assert "uv sync --locked --package owlbear-browser-mcp --group dev" in runs
    assert "uv run --no-sync playwright install --with-deps chromium" in runs
    assert "pytest serve/browser serve/browser-mcp -m browser" in runs


def test_delivery_next_browser_tests_run_in_their_own_job_with_chromium() -> None:
    job = _jobs("python-browser.yml")["delivery-next-browser"]
    runs = _runs(job)

    assert {"serve/delivery-next/**", "serve/memory/**"} <= set(ci_scope.SUITES["python-browser"])
    assert "serve/delivery-next serve/memory" in next(s["run"] for s in job["steps"] if s.get("id") == "fingerprint")
    assert "uv sync --locked --package owlbear-delivery-next --group dev" in runs
    assert "uv run --no-sync playwright install --with-deps chromium" in runs
    assert "pytest serve/delivery-next -m browser" in runs


def test_cockpit_unit_and_browser_proofs_run_in_parallel() -> None:
    jobs = _jobs("cockpit.yml")
    unit = _runs(jobs["unit"])
    browser = _runs(jobs["browser"])

    assert "**/*.json" not in ci_scope.SUITES["cockpit"]
    assert "serve/cockpit/web/**" in ci_scope.SUITES["cockpit"]
    for command in ("npm test", "npm run typecheck:e2e", "npm run test:biome-pds", "npm run test:sync-pds"):
        assert command in unit
    assert "check_node_runtime.py" in unit
    assert "npx playwright install --with-deps chromium" in browser
    assert "npm run test:e2e:compat" in browser
    assert jobs["browser"]["env"] == {"E2E_COMPAT_BROWSERS": "chromium"}
    upload = next(step for step in jobs["browser"]["steps"] if step.get("name") == "Upload browser diagnostics")
    assert upload["if"] == "failure()"


def test_static_checks_own_repository_lint() -> None:
    runs = _runs(_jobs("static.yml")["lint"])

    assert {"**/*.py", "**/*.json", "**/*.jsonc", "biome.json", "pyproject.toml"} <= set(ci_scope.SUITES["static"])
    assert "uv sync --locked --only-group dev" in runs
    assert "uv run --no-sync ruff check ." in runs
    assert "uv run --no-sync ruff format --check ." in runs
    assert "npm run lint:biome:ci" in runs
    assert "npm run lint:html" in runs


@pytest.mark.parametrize("name", [*SUITE_WORKFLOWS, "copilot-setup-steps.yml"])
def test_uv_setups_use_scoped_caches_and_check_the_runtime_first(name: str) -> None:
    for job in _jobs(name).values():
        steps = job["steps"]
        setups = [index for index, step in enumerate(steps) if "astral-sh/setup-uv@" in str(step.get("uses", ""))]
        if not setups:
            continue
        setup = steps[setups[0]]["with"]
        if name != "copilot-setup-steps.yml" and setup.get("enable-cache") is not False:
            assert setup["cache-suffix"] in {"python-tests", "python-browser", "delivery-next-browser", "dev-tools"}
        check = next(index for index, step in enumerate(steps) if "check_uv_version.py" in str(step.get("run", "")))
        first_uv = next(
            (
                index
                for index, step in enumerate(steps)
                if re.search(r"\buv\s+(?:python|run|sync|lock)", str(step.get("run", "")))
            ),
            len(steps),  # the security suite's uv runs only inside Snyk
        )
        assert setups[0] < check < first_uv
