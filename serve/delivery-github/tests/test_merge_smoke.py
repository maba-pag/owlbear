"""N05 3.3: one exact-head merge on a disposable GitHub repository, approved through Cockpit's HTTP route.

Runs only when ``OWLBEAR_MERGE_SMOKE_REPO=<owner>/<name>`` names a disposable repository the authenticated
``gh`` user may push to and merge in. It pushes ``main`` and one Change branch there, opens one pull request
and merges it. Nothing else is mutated; deleting the repository afterwards is the user's step.
"""

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import time
from pathlib import Path
from types import ModuleType

import pytest
from fastapi.testclient import TestClient

from owlbear_cockpit.routes.target_work import assemble_target_app
from owlbear_delivery.change_workspace import ChangeWorkspaceManager, PortfolioCoordinator
from owlbear_delivery.delivery_application_loader import load_delivery_application
from owlbear_delivery.design_package import DesignPackageStore
from owlbear_delivery_github import GitHubCliPublicationProvider

REPOSITORY = os.environ.get("OWLBEAR_MERGE_SMOKE_REPO", "")
CHANGE_ID = "merge-smoke"
pytestmark = [
    pytest.mark.api,
    pytest.mark.timeout(600),
    pytest.mark.skipif(not REPOSITORY, reason="OWLBEAR_MERGE_SMOKE_REPO names no disposable repository"),
]
# The assembled Work E2E seed owns the public-owner lifecycle that brings a Change to its merge offer.
_SEED = Path(__file__).resolve().parents[2] / "cockpit/web/e2e/support/seed-work-portfolio-delivery.py"


def _seed() -> ModuleType:
    spec = importlib.util.spec_from_file_location("seed_work_portfolio_delivery", _SEED)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _git(repository: Path, *arguments: str) -> str:
    return subprocess.run(  # noqa: S603 - fixed executable and test-owned arguments.
        ("git", "-C", str(repository), *arguments),  # noqa: S607
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _gh(endpoint: str) -> dict[str, object]:
    completed = subprocess.run(  # noqa: S603 - fixed read-only gh call.
        ("gh", "api", endpoint),  # noqa: S607
        check=True,
        capture_output=True,
        text=True,
    )
    return json.loads(completed.stdout)


def _base_repository(workspace: Path) -> str:
    workspace.mkdir()
    _git(workspace, "init", "-b", "main")
    _git(workspace, "config", "user.name", "OwlBear merge smoke")
    _git(workspace, "config", "user.email", "merge-smoke@example.invalid")
    _git(workspace, "config", "credential.helper", "!gh auth git-credential")
    (workspace / "product.txt").write_text("baseline\n", encoding="utf-8")
    _git(workspace, "add", "product.txt")
    _git(workspace, "commit", "-m", "baseline")
    _git(workspace, "remote", "add", "origin", f"https://github.com/{REPOSITORY}.git")
    _git(workspace, "push", "origin", "main")
    _git(workspace, "fetch", "origin")
    return _git(workspace, "rev-parse", "HEAD")


def test_cockpit_approval_merges_the_exact_head_and_delivery_completes_once(tmp_path: Path) -> None:
    seed = _seed()
    workspace = tmp_path / "workspace"
    base = _base_repository(workspace)
    runtime_root = workspace / ".owlbear/delivery/runtime"
    seed._write_host_config(workspace)  # noqa: SLF001
    manager = ChangeWorkspaceManager(
        workspace, workspace / ".owlbear/delivery/worktrees", PortfolioCoordinator(runtime_root), "main"
    )
    store = DesignPackageStore(workspace / ".owlbear/delivery/packages", workspace)
    seed._write_publishable_change(runtime_root, store, manager, CHANGE_ID, title="Merge smoke", base=base)  # noqa: SLF001
    config = seed._write_config(workspace, REPOSITORY)  # noqa: SLF001
    application = load_delivery_application(
        config, workspace_root=workspace, publication_provider=GitHubCliPublicationProvider()
    )
    seed._publish_ready(application, CHANGE_ID)  # noqa: SLF001
    offer_id = seed._merge_offer(application, CHANGE_ID)  # noqa: SLF001
    offer = application.get_change(CHANGE_ID).readiness.merge_offer
    statuses: list[tuple[str, int, object]] = []

    with TestClient(assemble_target_app(application)) as client:
        approved = client.post(
            f"/api/changes/{CHANGE_ID}/approve-merge",
            json={"offer_id": offer_id, "submission_id": "merge-smoke-1"},
        )
        statuses.append(("approve-merge", approved.status_code, approved.json().get("state")))
        completion_id = approved.json().get("completion_id")
        for _ in range(40):
            if completion_id is not None:
                break
            time.sleep(3)
            observed = client.post(f"/api/changes/{CHANGE_ID}/acceptance/observe")
            body = observed.json()
            statuses.append(("acceptance/observe", observed.status_code, body.get("code", body.get("completion_id"))))
            if observed.status_code == 200:
                completion_id = body["completion_id"]
        repeated = client.post(f"/api/changes/{CHANGE_ID}/acceptance/observe")

    pull = _gh(f"repos/{REPOSITORY}/pulls/{offer.number}")
    merge_commit = repeated.json().get("accepted_merge_commit")
    parents = [parent["sha"] for parent in _gh(f"repos/{REPOSITORY}/commits/{merge_commit}")["parents"]]
    print(  # noqa: T201 - the run's evidence for the N05-C pull request.
        json.dumps(
            {
                "repository": REPOSITORY,
                "pull_request": offer.number,
                "approved_head": offer.head_sha,
                "target_head": offer.target_head,
                "statuses": statuses,
                "completion_id": completion_id,
                "merge_commit": merge_commit,
                "merge_commit_parents": parents,
                "github_merged": pull["merged"],
            },
            indent=2,
        )
    )
    assert approved.status_code == 200, statuses
    assert completion_id is not None, statuses
    assert (repeated.status_code, repeated.json()["completion_id"]) == (200, completion_id)
    assert pull["merged"] is True
    assert parents == [offer.target_head, offer.head_sha]
