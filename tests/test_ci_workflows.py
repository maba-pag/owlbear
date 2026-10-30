from __future__ import annotations

import importlib.util
import os
import re
import subprocess
import sys
import tomllib
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).parents[1]
WORKFLOWS = ROOT / ".github/workflows"
SUITE_WORKFLOWS = (
    "agent-ecosystem.yml",
    "python.yml",
    "python-browser.yml",
    "security.yml",
    "static.yml",
    "tooling.yml",
)
REUSING_WORKFLOWS = ("python.yml", "python-browser.yml", "static.yml", "tooling.yml")
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
    for name in ("source-verification.yml", "dependency-verification.yml", "cockpit-verification.yml", "cockpit.yml"):
        assert not (WORKFLOWS / name).exists()


def test_python_checks_out_history_for_immutable_legacy_fixtures() -> None:
    job = _jobs("python.yml")["tests"]
    checkout = next(step for step in job["steps"] if str(step.get("uses", "")).startswith("actions/checkout@"))
    assert checkout["with"]["fetch-depth"] == 0
    assert checkout["with"]["persist-credentials"] is False


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
        (["README.md"], ["static"]),
        (["serve/delivery-next/src/owlbear_delivery_next/api.py"], ["python", "python-browser", "static", "security"]),
        ([".nvmrc"], ["static", "tooling"]),
        (["renovate.json"], ["static", "tooling"]),
        (["uv.lock"], ["python", "python-browser", "static", "tooling"]),
        ([".github/workflows/ci.yml"], list(ci_scope.SUITES)),
        ([".github/scripts/ci_scope.py"], list(ci_scope.SUITES)),
        (["share/skills/x/SKILL.md"], ["static", "agent-ecosystem"]),
        ([".mcp.json"], ["static", "agent-ecosystem"]),
        (["serve/a/b/src/x.txt"], ["static"]),
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
        env={k: v for k, v in os.environ.items() if k not in {"EVENT", "SOURCE_REPOSITORY"}}
        | {"GITHUB_REPOSITORY": ci_scope.HOME},
        capture_output=True,
        text=True,
        check=True,
    ).stdout

    assert paths == 'suites=["python", "python-browser", "static", "security"]\n'


@pytest.mark.parametrize(
    "case",
    [
        ("maba-pag/owlbear", "pull_request", "maba-pag/owlbear", True),
        ("maba-pag/owlbear", "push", "", True),
        ("maba-pag/owlbear", "pull_request", "someone/owlbear", False),  # a fork's pull request into OwlBear
        ("maba-pag/owlbear", "pull_request", "", False),  # its fork deleted
        ("someone/owlbear", "pull_request", "maba-pag/owlbear", False),  # OwlBear's branch into a fork
        ("someone/owlbear", "push", "", False),  # a copy
    ],
)
def test_only_owlbear_s_own_changes_select_the_snyk_suite(
    monkeypatch: pytest.MonkeyPatch, capsys, case: tuple[str, str, str, bool]
) -> None:
    """TD-363: GitHub gives Snyk's token only to OwlBear's own runs of its own changes; others must not wait for it."""
    step = next(s for s in _jobs("ci.yml")["scope"]["steps"] if s.get("id") == "scope")
    assert step["env"]["SOURCE_REPOSITORY"] == "${{ github.event.pull_request.head.repo.full_name }}"
    *values, selected = case
    for name, value in zip(("GITHUB_REPOSITORY", "EVENT", "SOURCE_REPOSITORY"), values, strict=True):
        monkeypatch.setenv(name, value)
    ci_scope.main([])
    assert ("security" in capsys.readouterr().out) is selected


def test_the_snyk_suite_only_tests_code_and_gets_its_token_from_the_gate() -> None:
    """TD-360: nothing is written into the Snyk org. TD-382: only Snyk Code, whose tests are unlimited, runs."""
    steps = _jobs("security.yml")["snyk"]["steps"]
    runs = _runs({"steps": steps})
    assert "snyk code test" in runs
    assert "snyk test" not in runs  # dependencies are Renovate's; manifest tests would spend the private quota
    assert not any(word in runs for word in ("monitor", "--report", "|| true"))
    assert _workflow("security.yml")["env"]["SNYK_API"] == "https://api.eu.snyk.io"
    assert _jobs("ci.yml")["security"]["secrets"] == {"SNYK_TOKEN": "${{ secrets.SNYK_TOKEN }}"}


def test_every_suite_lists_its_own_workflow_and_no_glob_twice() -> None:
    for name, globs in ci_scope.SUITES.items():
        assert len(globs) == len(set(globs)), name
        assert f".github/workflows/{name}.yml" in globs or {".github/workflows/**", "**"} & set(globs), name


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
    assert out.read_text() == 'suites=["static", "agent-ecosystem"]\n'  # the merge's own change, not every suite


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
    assert '-m "not e2e and not model and not browser" -n "${CI_WORKERS:-auto}" --dist worksteal' in runs
    assert job["steps"][[s.get("name") for s in job["steps"]].index("Run test shard")]["env"]["CI_WORKERS"] == (
        "${{ inputs.workers }}"
    )
    assert workflow["on"]["workflow_dispatch"]["inputs"]["workers"]["default"] == ""
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
    assert "uv run --no-sync playwright install chromium" in runs
    assert "--with-deps" not in runs  # apt on the runner stalls; the image has what headless Chromium needs
    assert "pytest serve/browser serve/browser-mcp -m browser" in runs


def test_delivery_next_browser_tests_run_in_their_own_job_with_chromium() -> None:
    job = _jobs("python-browser.yml")["delivery-next-browser"]
    runs = _runs(job)

    assert {"serve/delivery-next/**", "serve/decisions/**", "serve/memory/**"} <= set(ci_scope.SUITES["python-browser"])
    fingerprint = next(s["run"] for s in job["steps"] if s.get("id") == "fingerprint")
    assert "serve/delivery-next serve/decisions serve/memory" in fingerprint
    assert "uv sync --locked --package owlbear-delivery-next --group dev" in runs
    assert "uv run --no-sync playwright install chromium" in runs
    assert "--with-deps" not in runs  # apt on the runner stalls; the image has what headless Chromium needs
    assert "pytest serve/delivery-next -m browser" in runs


@pytest.mark.parametrize(
    ("workflow", "job_name", "step_name"),
    [
        ("python.yml", "tests", "Run test shard"),
        ("python-browser.yml", "delivery-next-browser", "Run browser-marked tests"),
    ],
)
def test_sharded_jobs_load_the_shared_shard_plugin_once_per_matrix_shard(workflow, job_name, step_name) -> None:
    job = _jobs(workflow)[job_name]
    step = next(s for s in job["steps"] if s.get("name") == step_name)
    env = {**(_workflow(workflow).get("env") or {}), **step["env"]}
    shards = job["strategy"]["matrix"]["shard"]
    fingerprint = next(s["run"] for s in job["steps"] if s.get("id") == "fingerprint")

    assert shards == list(range(1, int(env["CI_SHARDS"]) + 1))
    assert job["name"].endswith(f"${{{{ matrix.shard }}}}/{len(shards)}")
    assert job["strategy"]["fail-fast"] is False
    assert env["CI_SHARD_INDEX"] == "${{ matrix.shard }}"
    assert 'cp .github/scripts/ci_shard.py "$plugin_dir/"' in step["run"]
    assert re.search(r'PYTHONPATH="\$plugin_dir" uv run --no-sync pytest [^\n]* -p ci_shard\b', step["run"])
    assert ".github/scripts/ci_shard.py" in ci_scope.SUITES[workflow.removesuffix(".yml")]
    assert ".github/scripts/ci_shard.py" in fingerprint or "git ls-files -s -- . " in fingerprint


def test_the_shard_plugin_runs_every_collected_test_in_exactly_one_shard(tmp_path: Path) -> None:
    (tmp_path / "pytest.ini").write_text("[pytest]\n")
    (tmp_path / "test_x.py").write_text(
        "import pytest\n\n\n@pytest.mark.parametrize('n', range(40))\ndef test_n(n):\n    pass\n"
    )

    def selected(index: int) -> set[str]:
        done = subprocess.run(
            [sys.executable, "-m", "pytest", "--collect-only", "-q", "-p", "no:cacheprovider", "-p", "ci_shard"],
            cwd=tmp_path,
            env=os.environ
            | {"PYTHONPATH": str(ROOT / ".github/scripts"), "CI_SHARD_INDEX": str(index), "CI_SHARDS": "2"},
            capture_output=True,
            text=True,
            check=True,
        )
        return {line for line in done.stdout.splitlines() if "::" in line}

    first, second = selected(1), selected(2)

    assert first
    assert second
    assert not first & second
    assert first | second == {f"test_x.py::test_n[{n}]" for n in range(40)}


@pytest.mark.parametrize("name", REUSING_WORKFLOWS)
def test_each_matrix_shard_keeps_its_own_cached_pass_and_results(name: str) -> None:
    """One shard's cached pass must never let another shard skip its tests, nor its upload replace another's."""
    for job_name, job in _jobs(name).items():
        steps = job["steps"]
        templates = [
            next(s for s in steps if s.get("id") == "reuse")["with"]["key"],
            steps[-1]["with"]["key"],
            *(s["with"]["name"] for s in steps if str(s.get("uses", "")).startswith("actions/upload-artifact@")),
        ]
        for variable, values in ((job.get("strategy") or {}).get("matrix") or {}).items():
            placeholder = f"${{{{ matrix.{variable} }}}}"
            for template in templates:
                rendered = {template.replace(placeholder, str(value)) for value in values}
                assert len(rendered) == len(values), f"{name}:{job_name}: {template}"


@pytest.mark.parametrize(
    ("workflow", "job", "step"),
    [
        ("python.yml", "tests", "Run test shard"),
        ("python-browser.yml", "browser", "Run browser-marked tests"),
        ("python-browser.yml", "delivery-next-browser", "Run browser-marked tests"),
    ],
)
def test_tests_run_with_bare_repositories_named_explicitly_as_in_agent_shells(workflow, job, step) -> None:
    env = next(s for s in _jobs(workflow)[job]["steps"] if s.get("name") == step)["env"]

    assert {k: str(v) for k, v in env.items() if k.startswith("GIT_CONFIG_")} == {
        "GIT_CONFIG_COUNT": "1",
        "GIT_CONFIG_KEY_0": "safe.bareRepository",
        "GIT_CONFIG_VALUE_0": "explicit",
    }


@pytest.mark.parametrize(
    ("workflow", "job", "step"),
    [
        ("python.yml", "tests", "Run test shard"),
        ("python-browser.yml", "browser", "Run browser-marked tests"),
        ("python-browser.yml", "delivery-next-browser", "Run browser-marked tests"),
    ],
)
def test_test_jobs_rerun_only_open_flaky_issues_and_upload_results_even_on_failure(workflow, job, step) -> None:
    steps = _jobs(workflow)[job]["steps"]
    names = [s.get("name") for s in steps]
    lookup, tests, upload = (steps[names.index(n)] for n in ("Find open flaky issues", step, "Upload test results"))

    assert names.index("Find open flaky issues") < names.index(step) < names.index("Upload test results")
    assert lookup["run"] == "python3 .github/scripts/flaky_issues.py"
    assert lookup["env"] == {"GH_TOKEN": "${{ github.token }}"}
    assert "GH_TOKEN" not in tests["env"]
    assert tests["env"]["OWLBEAR_FLAKY_REPORT"] == "${{ runner.temp }}/test-results/flaky.json"
    assert '--junitxml="$RUNNER_TEMP/test-results/junit.xml"' in tests["run"]
    assert upload["uses"].startswith("actions/upload-artifact@")
    assert upload["if"].startswith("${{ !cancelled() && ")
    assert upload["with"]["path"] == "${{ runner.temp }}/test-results/"
    assert upload["with"]["name"].endswith("-attempt-${{ github.run_attempt }}")


def test_static_runs_the_workspace_lint_on_every_change() -> None:
    """CI runs what `uv run lint` and `uv run format` run locally; EditorConfig reads every text file (TD-409)."""
    runs = _runs(_jobs("static.yml")["lint"])

    assert ci_scope.SUITES["static"] == ("**",)
    assert "uv sync --locked --package owlbear-tools --group dev" in runs
    assert "uv run --no-sync lint --no-fix" in runs
    assert "uv run --no-sync format --no-fix" in runs
    assert "npm ci --engine-strict --no-audit --no-fund" in runs
    setup = next(s for s in _jobs("static.yml")["lint"]["steps"] if "astral-sh/setup-uv@" in str(s.get("uses", "")))
    assert setup["with"]["cache-suffix"] == "static"  # lint installs only owlbear-tools; dev-tools' cache is ~2.9 GB


@pytest.mark.parametrize("name", [*SUITE_WORKFLOWS, "copilot-setup-steps.yml"])
def test_uv_setups_use_scoped_caches_and_check_the_runtime_first(name: str) -> None:
    for job in _jobs(name).values():
        steps = job["steps"]
        setups = [index for index, step in enumerate(steps) if "astral-sh/setup-uv@" in str(step.get("uses", ""))]
        if not setups:
            continue
        setup = steps[setups[0]]["with"]
        if name != "copilot-setup-steps.yml" and setup.get("enable-cache") is not False:
            assert setup["cache-suffix"] in {
                "python-tests",
                "python-browser",
                "delivery-next-browser",
                "dev-tools",
                "static",
            }
        check = next(index for index, step in enumerate(steps) if "check_uv_version.py" in str(step.get("run", "")))
        first_uv = next(
            (
                index
                for index, step in enumerate(steps)
                if re.search(r"\buv\s+(?:python|run|sync|lock)", str(step.get("run", "")))
            ),
            len(steps),
        )
        assert setups[0] < check < first_uv
