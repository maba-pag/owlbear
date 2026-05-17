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


def _step_index_by_name(steps: list[dict[str, Any]], name: str) -> int:
    """Return the index of a step by exact display name."""
    for index, step in enumerate(steps):
        if step.get("name") == name:
            return index
    raise AssertionError(f"Expected workflow step named {name!r}.")


def _uses_cockpit_gate(value: object) -> bool:
    """Return true when a workflow expression gates on the Cockpit sync scope."""
    return "SYNC_COCKPIT" in str(value)


class TestCockpitDeliveryGateWorkflow:
    """Workflow must enforce Cockpit frontend quality gates."""

    def test_sync_workflow_runs_cockpit_vitest_before_commit(self) -> None:
        """AC1/AC5: sync-to-main must run cockpit build and Vitest before commit."""
        workflow = _load_sync_workflow()
        steps = _sync_job_steps(workflow)

        commit_index = _step_index_by_name(steps, "Commit")

        build_step = _step_by_name(steps, "Build cockpit SPA")
        assert build_step.get("working-directory") == "serve/cockpit/web", (
            "Build cockpit SPA must run in serve/cockpit/web."
        )
        assert "npm run build" in str(build_step.get("run", "")), (
            "Build cockpit SPA must run `npm run build` for cockpit frontend quality gate."
        )
        build_index = _step_index_by_name(steps, "Build cockpit SPA")
        assert build_index < commit_index, "Build cockpit SPA must run before the consumer branch commit step."

        vitest_steps = [
            (index, step)
            for index, step in enumerate(steps)
            if "npm test" in str(step.get("run", "")) and step.get("working-directory") == "serve/cockpit/web"
        ]
        assert vitest_steps, (
            "sync-to-main must run Vitest (`npm test`) inside serve/cockpit/web before the consumer branch commit."
        )
        assert all(index < commit_index for index, _ in vitest_steps), (
            "All cockpit Vitest steps must run before the consumer branch commit step."
        )

    def test_sync_workflow_runs_cockpit_playwright_e2e_distinct_from_excalidraw(
        self,
    ) -> None:
        """AC1/AC5: workflow needs a cockpit `npm run test:e2e` step, not only Excalidraw Playwright."""
        workflow = _load_sync_workflow()
        steps = _sync_job_steps(workflow)

        commit_index = _step_index_by_name(steps, "Commit")

        cockpit_e2e_steps = [
            (index, step)
            for index, step in enumerate(steps)
            if "npm run test:e2e" in str(step.get("run", "")) and step.get("working-directory") == "serve/cockpit/web"
        ]
        assert cockpit_e2e_steps, (
            "sync-to-main must run cockpit Playwright E2E (`npm run test:e2e`) in "
            "serve/cockpit/web; Excalidraw export Playwright is not a substitute."
        )
        assert all(index < commit_index for index, _ in cockpit_e2e_steps), (
            "All cockpit Playwright E2E steps must run before the consumer branch commit step."
        )

    def test_sync_workflow_disallows_build_gate_bypass_when_sync_cockpit_true(
        self,
    ) -> None:
        """AC3/AC5: cockpit quality gate conditions must not depend on build_cockpit."""
        workflow = _load_sync_workflow()
        steps = _sync_job_steps(workflow)

        explicitly_gated = {
            "Setup Node.js (cockpit)",
            "Build cockpit SPA",
            "Assert SPA bundle exists",
            "Stage built SPA bundle",
        }
        dynamic_cockpit_test_steps = {
            str(step.get("name", ""))
            for step in steps
            if step.get("working-directory") == "serve/cockpit/web"
            and ("npm test" in str(step.get("run", "")) or "npm run test:e2e" in str(step.get("run", "")))
        }
        gated_step_names = sorted(explicitly_gated | dynamic_cockpit_test_steps)

        for name in gated_step_names:
            step = _step_by_name(steps, name)
            if_expr = str(step.get("if", ""))
            assert _uses_cockpit_gate(if_expr), (
                f"{name} must be gated by SYNC_COCKPIT to avoid accidental cross-scope runs."
            )
            assert "build_cockpit" not in if_expr, (
                f"{name} condition must not depend on build_cockpit; this input allows "
                "bypassing cockpit quality gates while sync_cockpit is enabled."
            )

    def test_setup_node_conditions_scope_cockpit_and_diagram_paths(self) -> None:
        """Node setup stays scoped to Cockpit or share-only diagram exports."""
        workflow = _load_sync_workflow()
        steps = _sync_job_steps(workflow)

        cockpit_step = _step_by_name(steps, "Setup Node.js (cockpit)")
        cockpit_if = str(cockpit_step.get("if", ""))
        assert _uses_cockpit_gate(cockpit_if), (
            "Cockpit Node.js setup must be gated by SYNC_COCKPIT so Node.js is "
            "available for cockpit build and test steps."
        )
        assert "build_cockpit" not in cockpit_if, (
            "Cockpit Node.js setup must not reference build_cockpit; "
            "that input is no longer a valid gate for Node.js setup."
        )

        diagrams_step = _step_by_name(steps, "Setup Node.js (diagrams only)")
        diagrams_if = str(diagrams_step.get("if", ""))
        assert "SYNC_SHARE" in diagrams_if, (
            "Diagram-only Node.js setup must preserve the share sync path when cockpit is disabled."
        )
        assert "SYNC_COCKPIT != 'true'" in diagrams_if, (
            "Diagram-only Node.js setup must not duplicate the cockpit Node.js setup path."
        )


class TestCockpitPackagingShape:
    """Workflow packaging must keep dist and remove the source web tree."""

    def test_sync_workflow_asserts_cockpit_dist_index_and_stages_dist_tree(
        self,
    ) -> None:
        """AC2/AC4: dist index is verified and the dist tree is staged for sync."""
        workflow = _load_sync_workflow()
        steps = _sync_job_steps(workflow)

        build_index = _step_index_by_name(steps, "Build cockpit SPA")
        assert_index = _step_index_by_name(steps, "Assert SPA bundle exists")
        assert build_index < assert_index, "Assert SPA bundle exists must run after Build cockpit SPA."

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
        assert _uses_cockpit_gate(run_script), "Prune of serve/cockpit/web must stay scoped to SYNC_COCKPIT=true runs."


class TestCockpitDeliveryGateOrdering:
    """Cockpit quality-gate steps must run before pruning frontend sources."""

    def test_vitest_step_runs_before_prune_step(self) -> None:
        """Vitest runs before the consumer sync prunes serve/cockpit/web."""
        workflow = _load_sync_workflow()
        steps = _sync_job_steps(workflow)

        prune_index = _step_index_by_name(steps, "Prune dev-only files from consumer tree")

        vitest_steps = [
            (index, step)
            for index, step in enumerate(steps)
            if "npm test" in str(step.get("run", "")) and step.get("working-directory") == "serve/cockpit/web"
        ]
        assert vitest_steps, "sync-to-main must include a Vitest step (`npm test` in serve/cockpit/web)."
        assert all(index < prune_index for index, _ in vitest_steps), (
            "Vitest step must run before 'Prune dev-only files from consumer tree' "
            "because the prune step removes serve/cockpit/web."
        )

    def test_playwright_chromium_install_precedes_cockpit_e2e(self) -> None:
        """Chromium is installed before Cockpit E2E runs."""
        workflow = _load_sync_workflow()
        steps = _sync_job_steps(workflow)

        cockpit_e2e_steps = [
            (index, step)
            for index, step in enumerate(steps)
            if "npm run test:e2e" in str(step.get("run", "")) and step.get("working-directory") == "serve/cockpit/web"
        ]
        assert cockpit_e2e_steps, (
            "sync-to-main must include a cockpit Playwright E2E step (`npm run test:e2e` in serve/cockpit/web)."
        )

        e2e_index = cockpit_e2e_steps[0][0]
        run_text = " ".join(str(step.get("run", "")) for index, step in enumerate(steps) if index <= e2e_index)
        assert "playwright install" in run_text, (
            "A `playwright install chromium` (or equivalent) command must appear "
            "at or before the cockpit E2E step so Chromium is available in CI."
        )

    def test_playwright_e2e_runs_before_prune_step(self) -> None:
        """Cockpit Playwright E2E runs before frontend source pruning."""
        workflow = _load_sync_workflow()
        steps = _sync_job_steps(workflow)

        prune_index = _step_index_by_name(steps, "Prune dev-only files from consumer tree")

        cockpit_e2e_steps = [
            (index, step)
            for index, step in enumerate(steps)
            if "npm run test:e2e" in str(step.get("run", "")) and step.get("working-directory") == "serve/cockpit/web"
        ]
        assert cockpit_e2e_steps, (
            "sync-to-main must include a cockpit Playwright E2E step (`npm run test:e2e` in serve/cockpit/web)."
        )
        assert all(index < prune_index for index, _ in cockpit_e2e_steps), (
            "Cockpit Playwright E2E must run before 'Prune dev-only files from consumer tree' "
            "because the prune step removes serve/cockpit/web."
        )

    def test_vitest_step_runs_after_build_step(self) -> None:
        """Vitest runs after the Cockpit SPA build."""
        workflow = _load_sync_workflow()
        steps = _sync_job_steps(workflow)

        build_index = _step_index_by_name(steps, "Build cockpit SPA")

        vitest_steps = [
            (index, step)
            for index, step in enumerate(steps)
            if "npm test" in str(step.get("run", "")) and step.get("working-directory") == "serve/cockpit/web"
        ]
        assert vitest_steps, "sync-to-main must include a Vitest step (`npm test` in serve/cockpit/web)."
        assert all(index > build_index for index, _ in vitest_steps), (
            "Vitest step must run after 'Build cockpit SPA' so tests run against "
            "the current build output, not a stale or missing dist."
        )
