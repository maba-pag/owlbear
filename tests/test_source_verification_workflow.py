from __future__ import annotations

from pathlib import Path

import yaml

ROOT = Path(__file__).parents[1]
WORKFLOW_PATH = ROOT / ".github/workflows/source-verification.yml"


def _workflow() -> dict[str, object]:
    document = yaml.safe_load(WORKFLOW_PATH.read_text(encoding="utf-8"))
    if True in document and "on" not in document:
        document["on"] = document.pop(True)
    return document


def test_source_verification_covers_python_source_and_test_surfaces() -> None:
    workflow = _workflow()
    pull_request = workflow["on"]["pull_request"]

    assert pull_request["branches"] == ["dev"]
    assert pull_request["types"] == ["opened", "reopened", "synchronize", "ready_for_review"]
    assert set(pull_request["paths"]) == {
        ".github/workflows/source-verification.yml",
        ".python-version",
        "conftest.py",
        "pyproject.toml",
        "uv.lock",
        "serve/*/pyproject.toml",
        "serve/*/src/**",
        "serve/*/tests/**",
        "tests/**",
        "setup/**",
        "seed/**",
    }
    assert "workflow_dispatch" in workflow["on"]


def test_source_verification_runs_full_non_e2e_python_tier() -> None:
    job = _workflow()["jobs"]["python"]
    steps = job["steps"]
    runs = [step.get("run", "") for step in steps]
    run_text = "\n".join(runs)

    assert "uv python install" in runs
    assert "uv sync --locked --all-packages --all-extras --all-groups" in runs
    assert "uv run playwright install --with-deps chromium" in runs
    assert 'uv run pytest tests serve -m "not e2e"' in runs
    assert "uv run ruff check ." in run_text
    assert "uv run ruff format --check ." in run_text


def test_source_verification_actions_are_pinned() -> None:
    for line in WORKFLOW_PATH.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped.startswith("uses:"):
            continue
        revision = stripped.split("#", maxsplit=1)[0].rsplit("@", maxsplit=1)[1].strip()
        assert len(revision) == 40
        assert all(character in "0123456789abcdef" for character in revision)
