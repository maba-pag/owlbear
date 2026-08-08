from __future__ import annotations

import json
import re
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
VERIFY_PATH = ROOT / ".github/workflows/dependency-verification.yml"
WRITEBACK_PATH = ROOT / ".github/workflows/dependency-autofix-writeback.yml"
RENOVATE_PATH = ROOT / ".github/renovate.json"


def _workflow(path: Path) -> tuple[dict[str, object], str]:
    raw = path.read_text(encoding="utf-8")
    return yaml.safe_load(raw), raw


def test_dependency_verification_is_branch_agnostic_and_read_only() -> None:
    workflow, raw = _workflow(VERIFY_PATH)
    pull_request = workflow["on"]["pull_request"]

    assert "branches" not in pull_request
    assert set(pull_request["types"]) == {
        "opened",
        "synchronize",
        "reopened",
        "labeled",
        "unlabeled",
        "ready_for_review",
    }
    assert workflow["permissions"] == {"contents": "read"}
    assert "dependencies" in raw
    assert "renovate" in raw
    assert "autofix" in raw
    assert "unsafe-autofix" in raw
    assert "cannot be combined" in raw
    assert "Fork pull requests are verification-only" in raw
    assert "uv run lint-full --no-fix" in raw


def test_dependency_writeback_never_checks_out_untrusted_code() -> None:
    workflow, raw = _workflow(WRITEBACK_PATH)

    assert workflow["on"]["workflow_run"]["workflows"] == ["Dependency verification"]
    assert workflow["permissions"] == {
        "actions": "read",
        "contents": "write",
        "pull-requests": "read",
    }
    assert "actions/checkout" not in raw
    assert "pulls/${PR_NUMBER}" in raw
    assert "HEAD_SHA" in raw
    assert "headRepository" in raw
    assert "git apply --check" not in raw
    assert "dependency-autofix-updated" in raw
    assert "AUTHORIZATION: basic" in raw


def test_dependency_workflow_actions_are_pinned() -> None:
    uses = []
    for path in (VERIFY_PATH, WRITEBACK_PATH):
        _workflow_data, raw = _workflow(path)
        uses.extend(re.findall(r"^\s*uses:\s*([^\s#]+)", raw, flags=re.MULTILINE))

    assert uses
    assert all(re.fullmatch(r"[^@]+@[0-9a-f]{40}", action) for action in uses)


def test_renovate_rules_preserve_dependency_gate_labels() -> None:
    config = json.loads(RENOVATE_PATH.read_text(encoding="utf-8"))

    assert set(config["labels"]) == {"dependencies", "renovate"}
    pds_rule = next(
        rule for rule in config["packageRules"] if rule["description"].startswith("Review Porsche Design System")
    )
    assert "labels" not in pds_rule
    assert set(pds_rule["addLabels"]) == {"cockpit", "pds"}
    assert config["gitIgnoredAuthors"] == [
        "github-actions[bot] <41898282+github-actions[bot]@users.noreply.github.com>"
    ]
