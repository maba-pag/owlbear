from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

_REPO_ROOT = Path(__file__).resolve().parents[1]
_WORKFLOW_PATH = _REPO_ROOT / ".github" / "workflows" / "sync-to-main.yml"


def _load_sync_workflow() -> dict[str, Any]:
    data = yaml.safe_load(_WORKFLOW_PATH.read_text(encoding="utf-8"))
    assert isinstance(data, dict), "sync-to-main.yml must parse as a mapping."
    return data


def _sync_job_steps(workflow: dict[str, Any]) -> list[dict[str, Any]]:
    jobs = workflow.get("jobs")
    assert isinstance(jobs, dict), "Workflow must define jobs."
    sync_job = jobs.get("sync")
    assert isinstance(sync_job, dict), "Workflow must define jobs.sync."
    steps = sync_job.get("steps")
    assert isinstance(steps, list), "jobs.sync.steps must be a list."
    return [step for step in steps if isinstance(step, dict)]


def _step_index_by_name(steps: list[dict[str, Any]], name: str) -> int:
    for index, step in enumerate(steps):
        if step.get("name") == name:
            return index
    raise AssertionError(f"Expected workflow step named {name!r}.")


class TestFromAC_CockpitDeliveryGateOrdering:
    """AC1/AC2: cockpit quality-gate steps must run before the prune step."""

    def test_vitest_step_runs_before_prune_step(self) -> None:
        """AC1: Vitest (`npm test`) must run before 'Prune dev-only files' removes serve/cockpit/web."""
        workflow = _load_sync_workflow()
        steps = _sync_job_steps(workflow)

        prune_index = _step_index_by_name(steps, "Prune dev-only files from consumer tree")

        vitest_steps = [
            (index, step)
            for index, step in enumerate(steps)
            if "npm test" in str(step.get("run", ""))
            and step.get("working-directory") == "serve/cockpit/web"
        ]
        assert vitest_steps, (
            "sync-to-main must include a Vitest step (`npm test` in serve/cockpit/web)."
        )
        assert all(index < prune_index for index, _ in vitest_steps), (
            "Vitest step must run before 'Prune dev-only files from consumer tree' "
            "because the prune step removes serve/cockpit/web."
        )

    def test_playwright_chromium_install_precedes_cockpit_e2e(self) -> None:
        """AC2: a `playwright install chromium` command must appear before cockpit E2E runs."""
        workflow = _load_sync_workflow()
        steps = _sync_job_steps(workflow)

        cockpit_e2e_steps = [
            (index, step)
            for index, step in enumerate(steps)
            if "npm run test:e2e" in str(step.get("run", ""))
            and step.get("working-directory") == "serve/cockpit/web"
        ]
        assert cockpit_e2e_steps, (
            "sync-to-main must include a cockpit Playwright E2E step "
            "(`npm run test:e2e` in serve/cockpit/web)."
        )

        e2e_index = cockpit_e2e_steps[0][0]
        # Collect all run text from steps at or before the first E2E step
        run_text = " ".join(
            str(step.get("run", ""))
            for _, step in enumerate(steps)
            if _ <= e2e_index
        )
        assert "playwright install" in run_text, (
            "A `playwright install chromium` (or equivalent) command must appear "
            "at or before the cockpit E2E step so Chromium is available in CI."
        )

    def test_playwright_e2e_runs_before_prune_step(self) -> None:
        """AC2: cockpit Playwright E2E must run before 'Prune dev-only files' removes serve/cockpit/web."""
        workflow = _load_sync_workflow()
        steps = _sync_job_steps(workflow)

        prune_index = _step_index_by_name(steps, "Prune dev-only files from consumer tree")

        cockpit_e2e_steps = [
            (index, step)
            for index, step in enumerate(steps)
            if "npm run test:e2e" in str(step.get("run", ""))
            and step.get("working-directory") == "serve/cockpit/web"
        ]
        assert cockpit_e2e_steps, (
            "sync-to-main must include a cockpit Playwright E2E step "
            "(`npm run test:e2e` in serve/cockpit/web)."
        )
        assert all(index < prune_index for index, _ in cockpit_e2e_steps), (
            "Cockpit Playwright E2E must run before 'Prune dev-only files from consumer tree' "
            "because the prune step removes serve/cockpit/web."
        )

    def test_vitest_step_runs_after_build_step(self) -> None:
        """AC1: Vitest must run after 'Build cockpit SPA' so it tests the freshly built output."""
        workflow = _load_sync_workflow()
        steps = _sync_job_steps(workflow)

        build_index = _step_index_by_name(steps, "Build cockpit SPA")

        vitest_steps = [
            (index, step)
            for index, step in enumerate(steps)
            if "npm test" in str(step.get("run", ""))
            and step.get("working-directory") == "serve/cockpit/web"
        ]
        assert vitest_steps, (
            "sync-to-main must include a Vitest step (`npm test` in serve/cockpit/web)."
        )
        assert all(index > build_index for index, _ in vitest_steps), (
            "Vitest step must run after 'Build cockpit SPA' so tests run against "
            "the current build output, not a stale or missing dist."
        )
