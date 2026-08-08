from __future__ import annotations

import json
from pathlib import Path

import yaml

from owlbear_tools.dependency_ci import classify_dependency_change


ROOT = Path(__file__).parents[1]
WORKFLOW_PATH = ROOT / ".github/workflows/dependency-verification.yml"
WRITEBACK_PATH = ROOT / ".github/workflows/dependency-autofix-writeback.yml"


def _workflow() -> dict[str, object]:
    return yaml.safe_load(WORKFLOW_PATH.read_text())


def _job(workflow: dict[str, object], name: str) -> dict[str, object]:
    jobs = workflow["jobs"]
    assert isinstance(jobs, dict)
    job = jobs[name]
    assert isinstance(job, dict)
    return job


def test_dependency_verification_is_read_only_and_head_bound() -> None:
    workflow = _workflow()

    assert workflow["permissions"] == {"contents": "read"}
    assert "repository_dispatch" not in workflow["on"]
    assert not WRITEBACK_PATH.exists()

    workflow_text = WORKFLOW_PATH.read_text()
    assert "github.event.pull_request.head.sha" in workflow_text
    assert "persist-credentials: false" in workflow_text
    assert "contents: write" not in workflow_text


def test_dependency_gate_always_aggregates_each_proof() -> None:
    gate = _job(_workflow(), "gate")

    assert gate["name"] == "Verify dependency update"
    assert gate["if"] == "always()"
    assert gate["needs"] == [
        "classify",
        "proof-python",
        "proof-node",
        "compatibility",
        "repair-pds",
    ]


def test_dependency_repair_is_pds_only_and_artifact_only() -> None:
    workflow_text = WORKFLOW_PATH.read_text()

    assert "needs.classify.outputs.pds == 'true'" in workflow_text
    assert "serve/cockpit/web/public/porsche-design-system/*" in workflow_text
    assert "actions/upload-artifact@" in workflow_text
    assert "retention-days: 1" in workflow_text
    assert "git push" not in workflow_text
    assert "pull-requests: write" not in workflow_text


def test_dependency_workflow_actions_are_pinned() -> None:
    for line in WORKFLOW_PATH.read_text().splitlines():
        stripped = line.strip()
        if not stripped.startswith("uses:"):
            continue
        action = stripped.split("#", maxsplit=1)[0].strip().removeprefix("uses:").strip()
        assert "@" in action
        revision = action.rsplit("@", maxsplit=1)[1]
        assert len(revision) == 40
        assert all(character in "0123456789abcdef" for character in revision)


def test_classifier_derives_python_and_frontend_runtime_from_lockfiles() -> None:
    python_scope = classify_dependency_change(
        ["uv.lock"],
        '+name = "ruff"\n+version = "0.15.0"\n',
    )
    frontend_scope = classify_dependency_change(
        ["serve/cockpit/web/package-lock.json"],
        '+        "react": "19.3.0"\n',
    )

    assert python_scope.python
    assert python_scope.python_tooling
    assert frontend_scope.node
    assert frontend_scope.frontend_runtime


def test_classifier_derives_compatibility_and_pds_surfaces() -> None:
    compatibility_scope = classify_dependency_change(
        [".github/workflows/dependency-verification.yml", ".github/renovate.json"],
        "",
    )
    pds_scope = classify_dependency_change(
        ["serve/cockpit/web/package-lock.json"],
        '+    "node_modules/@porsche-design-system/components-react": {\n',
    )

    assert compatibility_scope.workflows
    assert compatibility_scope.renovate
    assert compatibility_scope.compatibility
    assert pds_scope.node
    assert pds_scope.pds
    assert pds_scope.frontend_runtime


def test_renovate_automerge_waits_for_required_gate_configuration() -> None:
    renovate = json.loads((ROOT / ".github/renovate.json").read_text())

    assert renovate["lockFileMaintenance"]["automerge"] is False
    for rule in renovate["packageRules"]:
        assert rule.get("automerge") is not True
