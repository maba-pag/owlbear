"""Regression checks for the dev-to-main sync manifest."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType

_ROOT = Path(__file__).resolve().parents[1]
_MANIFEST_SCRIPT = _ROOT / ".github/scripts/sync_manifest.py"
_WORKFLOW = _ROOT / ".github/workflows/sync-to-main.yml"


def _load_manifest_module() -> ModuleType:
    spec = importlib.util.spec_from_file_location("sync_manifest", _MANIFEST_SCRIPT)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_declared_sync_paths_exist_on_dev() -> None:
    module = _load_manifest_module()
    manifest = module._load_manifest()  # noqa: SLF001

    for scope, paths in manifest["scopes"].items():
        for relative_path in paths:
            assert (_ROOT / relative_path).exists(), f"{scope} declares missing path: {relative_path}"


def test_all_consumer_paths_exclude_dev_only_surfaces() -> None:
    module = _load_manifest_module()
    consumer_paths = module.paths_for_scope("all")
    excluded_paths = module.consumer_excluded_paths()

    assert ".markdownlint.json" in consumer_paths
    assert ".yamllint.yml" in consumer_paths
    assert ".editorconfig" in consumer_paths
    assert {".github", ".mega-linter.yml"}.issubset(excluded_paths)
    assert all(
        not (path == excluded or path.startswith(f"{excluded}/"))
        for path in consumer_paths
        for excluded in excluded_paths
    )


def test_sync_workflow_consumes_manifest_projections() -> None:
    workflow = _WORKFLOW.read_text(encoding="utf-8")

    assert "sync_manifest.py paths" in workflow
    assert "sync_manifest.py excluded" in workflow
    assert 'serve_paths="serve/README.md ' in workflow
    assert 'echo "COCKPIT_PATHS=$cockpit_paths"' in workflow
    assert "git checkout dev -- $ALL_CONSUMER_PATHS" in workflow
    assert "git checkout dev -- $INFRA_PATHS" in workflow
    assert "for excluded_path in $CONSUMER_EXCLUDED_PATHS" in workflow
