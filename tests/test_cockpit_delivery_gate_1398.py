from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

_REPO_ROOT = Path(__file__).resolve().parents[1]
_WORKFLOW_PATH = _REPO_ROOT / ".github" / "workflows" / "sync-to-main.yml"


def _load_sync_workflow() -> dict[str, Any]:
    """Load the sync-to-main workflow YAML as a plain mapping."""
    data = yaml.safe_load(_WORKFLOW_PATH.read_text(encoding="utf-8"))
    assert isinstance(data, dict), "sync-to-main.yml must parse as a mapping."
    return data


def _sync_job_steps(workflow: dict[str, Any]) -> list[dict[str, Any]]:
    """Return the step list for the sync job with dict-only entries."""
    jobs = workflow.get("jobs")
    assert isinstance(jobs, dict), "Workflow must define jobs."
    sync_job = jobs.get("sync")
    assert isinstance(sync_job, dict), "Workflow must define jobs.sync."
    steps = sync_job.get("steps")
    assert isinstance(steps, list), "jobs.sync.steps must be a list."
    return [step for step in steps if isinstance(step, dict)]


def _step_by_name(steps: list[dict[str, Any]], name: str) -> dict[str, Any]:
    """Find a workflow step by exact display name."""
    for step in steps:
        if step.get("name") == name:
            return step
    raise AssertionError(f"Expected workflow step named {name!r}.")


class TestFromAC_CockpitDeliveryGateWorkflow:
    """AC1/AC2/AC3/AC5: workflow must enforce cockpit frontend quality gates."""

    def test_sync_workflow_runs_cockpit_vitest_before_commit(self) -> None:
        """AC1/AC5: sync-to-main must run `npm test` in `serve/cockpit/web`."""
        workflow = _load_sync_workflow()
        steps = _sync_job_steps(workflow)
        vitest_steps = [
            step
            for step in steps
            if "npm test" in str(step.get("run", ""))
            and step.get("working-directory") == "serve/cockpit/web"
        ]
        assert vitest_steps, (
            "sync-to-main must run Vitest (`npm test`) inside serve/cockpit/web "
            "before the consumer branch commit."
        )

    def test_sync_workflow_runs_cockpit_playwright_e2e_distinct_from_excalidraw(self) -> None:
        """AC1/AC5: workflow needs a cockpit `npm run test:e2e` step, not only Excalidraw Playwright."""
        workflow = _load_sync_workflow()
        steps = _sync_job_steps(workflow)

        cockpit_e2e_steps = [
            step
            for step in steps
            if "npm run test:e2e" in str(step.get("run", ""))
            and step.get("working-directory") == "serve/cockpit/web"
        ]
        assert cockpit_e2e_steps, (
            "sync-to-main must run cockpit Playwright E2E (`npm run test:e2e`) in "
            "serve/cockpit/web; Excalidraw export Playwright is not a substitute."
        )

    def test_sync_workflow_disallows_build_gate_bypass_when_sync_cockpit_true(self) -> None:
        """AC3/AC5: cockpit gate conditions must not depend on a bypass input."""
        workflow = _load_sync_workflow()
        steps = _sync_job_steps(workflow)

        gated_step_names = [
            "Build cockpit SPA",
            "Assert SPA bundle exists",
            "Stage built SPA bundle",
        ]
        for name in gated_step_names:
            step = _step_by_name(steps, name)
            if_expr = str(step.get("if", ""))
            assert "inputs.sync_cockpit" in if_expr, (
                f"{name} must be gated by sync_cockpit to avoid accidental cross-scope runs."
            )
            assert "build_cockpit" not in if_expr, (
                f"{name} condition must not depend on build_cockpit; this input allows "
                "bypassing cockpit quality gates while sync_cockpit is enabled."
            )


class TestFromAC_CockpitPackagingShape:
    """AC2/AC4: workflow packaging must keep dist and remove source web tree."""

    def test_sync_workflow_asserts_cockpit_dist_index_and_stages_dist_tree(self) -> None:
        """AC2/AC4: dist index is verified and the dist tree is staged for sync."""
        workflow = _load_sync_workflow()
        steps = _sync_job_steps(workflow)

        assert_step = _step_by_name(steps, "Assert SPA bundle exists")
        assert "serve/cockpit/dist/index.html" in str(assert_step.get("run", "")), (
            "Bundle assertion step must verify serve/cockpit/dist/index.html exists."
        )

        stage_step = _step_by_name(steps, "Stage built SPA bundle")
        assert "git add -f serve/cockpit/dist/" in str(stage_step.get("run", "")), (
            "Workflow must stage serve/cockpit/dist/ for consumer sync."
        )

    def test_sync_workflow_prunes_cockpit_web_tree_for_consumer_shape(self) -> None:
        """AC4: consumer sync removes `serve/cockpit/web` when cockpit scope is enabled."""
        workflow = _load_sync_workflow()
        steps = _sync_job_steps(workflow)

        prune_step = _step_by_name(steps, "Prune dev-only files from consumer tree")
        run_script = str(prune_step.get("run", ""))
        assert "git rm -rf serve/cockpit/web" in run_script, (
            "Prune step must remove serve/cockpit/web so consumers rely on prebuilt dist/."
        )
        assert "inputs.sync_cockpit" in run_script, (
            "Prune of serve/cockpit/web must stay scoped to sync_cockpit=true runs."
        )
