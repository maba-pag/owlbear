from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from owlbear_tools.dependency_ci import FixMode, classify_dependency_change, select_fix_mode


ROOT = Path(__file__).parents[1]
VERIFY_PATH = ROOT / ".github/workflows/dependency-verification.yml"
WRITEBACK_PATH = ROOT / ".github/workflows/dependency-autofix-writeback.yml"
PDS_PATH = ROOT / ".github/workflows/cockpit-pds-assets.yml"


def _workflow(path: Path) -> dict[str, object]:
    return yaml.safe_load(path.read_text())


def _job(workflow: dict[str, object], name: str) -> dict[str, object]:
    jobs = workflow["jobs"]
    assert isinstance(jobs, dict)
    job = jobs[name]
    assert isinstance(job, dict)
    return job


def test_dependency_workflow_is_label_driven_across_target_branches() -> None:
    workflow = _workflow(VERIFY_PATH)
    pull_request = workflow["on"]["pull_request"]

    assert pull_request == {"types": ["opened", "labeled", "synchronize"]}
    assert "branches" not in pull_request
    assert "contains(github.event.pull_request.labels.*.name, 'dependencies')" in _job(workflow, "classify")["if"]


def test_verification_is_read_only_and_writeback_owns_write_permission() -> None:
    verification = _workflow(VERIFY_PATH)
    writeback = _workflow(WRITEBACK_PATH)

    assert verification["permissions"] == {"actions": "read", "contents": "read"}
    assert writeback["permissions"] == {"actions": "read", "contents": "read"}
    assert _job(writeback, "writeback")["permissions"] == {
        "actions": "read",
        "contents": "write",
        "pull-requests": "read",
    }
    assert writeback["on"] == {"workflow_run": {"workflows": ["Dependency verification"], "types": ["completed"]}}
    assert not PDS_PATH.exists()


@pytest.mark.parametrize(
    ("path", "surface"),
    [
        ("pyproject.toml", "python"),
        ("uv.lock", "python"),
        ("serve/delivery/pyproject.toml", "python"),
        ("serve/cockpit/web/package.json", "node"),
        ("serve/cockpit/web/package-lock.json", "node"),
        ("package.json", "root_node"),
        ("package-lock.json", "root_node"),
        (".owlbear/scripts/export-diagrams/package.json", "diagrams"),
        (".owlbear/scripts/export-diagrams/package-lock.json", "diagrams"),
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


def test_classifier_derives_runtime_specific_proofs_from_lock_diff() -> None:
    frontend = classify_dependency_change(
        ["serve/cockpit/web/package-lock.json"],
        '+    "node_modules/@porsche-design-system/components-react": {\n',
    )

    assert frontend.node
    assert frontend.pds
    assert frontend.frontend_runtime


def test_fix_labels_select_one_strongest_mode() -> None:
    assert select_fix_mode(["dependencies"]) is FixMode.NONE
    assert select_fix_mode(["dependencies", "autofix"]) is FixMode.SAFE
    assert select_fix_mode(["dependencies", "autofix", "autofix-unsafe"]) is FixMode.UNSAFE


def test_workflow_runs_native_and_megalinter_fixes_before_writeback() -> None:
    verification = VERIFY_PATH.read_text()
    writeback = WRITEBACK_PATH.read_text()

    assert "uv run lint --all" in verification
    assert "uv run megalint" in verification
    assert verification.index("uv run playwright install chromium --with-deps") < verification.index(
        'uv run pytest tests serve -m "not api and not e2e"'
    )
    assert "Verified fixes are pending writeback" in verification
    assert "github.event.workflow_run.head_repository.full_name == github.repository" in writeback
    assert "git apply --check --binary" in writeback
    assert 'git push origin "HEAD:$HEAD_BRANCH"' in writeback
    assert "pull_request_target" not in verification + writeback


def test_dependency_workflow_actions_are_pinned() -> None:
    for path in (VERIFY_PATH, WRITEBACK_PATH):
        for line in path.read_text().splitlines():
            stripped = line.strip()
            if not stripped.startswith("uses:"):
                continue
            action = stripped.split("#", maxsplit=1)[0].removeprefix("uses:").strip()
            revision = action.rsplit("@", maxsplit=1)[1]
            assert len(revision) == 40
            assert all(character in "0123456789abcdef" for character in revision)


def test_renovate_keeps_dependency_label_and_waits_for_gate() -> None:
    renovate = json.loads((ROOT / ".github/renovate.json").read_text())

    assert "dependencies" in renovate["labels"]
    assert renovate["lockFileMaintenance"]["automerge"] is False
    for rule in renovate["packageRules"]:
        assert rule.get("automerge") is not True
