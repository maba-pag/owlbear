"""Regression checks for the dev-to-main sync manifest."""

from __future__ import annotations

import importlib.util
import shutil
import subprocess
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
    for group, definition in manifest["scope_groups"].items():
        for relative_path in definition["paths"]:
            assert (_ROOT / relative_path).exists(), f"{group} declares missing path: {relative_path}"
    for relative_path in manifest["consumer_excluded_paths"] + manifest["source_only_paths"]:
        assert (_ROOT / relative_path).exists(), f"boundary declares missing path: {relative_path}"


def test_all_consumer_paths_exclude_dev_only_surfaces() -> None:
    module = _load_manifest_module()
    consumer_paths = module.paths_for_scope("all")
    excluded_paths = module.consumer_excluded_paths()

    assert ".markdownlint.json" in consumer_paths
    assert ".yamllint.yml" in consumer_paths
    assert ".editorconfig" in consumer_paths
    assert ".github/renovate.json" in consumer_paths
    assert ".github/scripts" in consumer_paths
    assert ".github/sync-manifest.json" in consumer_paths
    assert ".github/workflows" in consumer_paths
    assert {"pyproject.toml", "uv.lock"}.issubset(consumer_paths)
    assert "serve/web-content" in consumer_paths
    assert {
        ".github/README-automation.md",
        ".github/copilot-instructions.md",
        ".github/skills",
        ".mega-linter.yml",
        ".owlbear",
        ".pre-commit-config.yaml",
        ".vscode",
        "conftest.py",
        "eslint-json.config.cjs",
        "package-lock.json",
        "package.json",
        "store",
        "tests",
        "serve/cockpit/web",
    }.issubset(excluded_paths)
    assert all(
        not (path == excluded or path.startswith(f"{excluded}/"))
        for path in consumer_paths
        for excluded in excluded_paths
    )


def test_sync_workflow_consumes_manifest_projections() -> None:
    workflow = _WORKFLOW.read_text(encoding="utf-8")

    assert "sync_manifest.py paths" in workflow
    assert "sync_manifest.py group-paths serve" in workflow
    assert "sync_manifest.py scopes serve" in workflow
    assert "sync_manifest.py excluded" in workflow
    assert 'serve_paths="serve/README.md ' not in workflow
    scope_suffix_command = "scope_suffix=$(printf '%s' \"$serve_scope\" | tr '[:lower:]-' '[:upper:]_')"
    assert workflow.count(scope_suffix_command) == 5
    assert "SYNC_WEB_CONTENT: ${{ inputs.sync_web_content }}" in workflow
    assert "WEB_CONTENT_PATHS=$web_content_paths" in workflow
    assert 'scope_env="SYNC_${serve_scope^^}"' not in workflow
    assert 'path_var="${serve_scope^^}_PATHS"' not in workflow
    assert "git rm -rf --quiet $scope_paths" in workflow
    assert "git checkout dev -- $ALL_CONSUMER_PATHS" in workflow
    assert "git checkout dev -- $INFRA_PATHS" in workflow
    assert "for excluded_path in $CONSUMER_EXCLUDED_PATHS" in workflow
    assert "if [ -d serve ]" in workflow
    assert "Install uv for MCP dev-source gate" not in workflow
    assert "Install Chromium for cockpit E2E" not in workflow
    assert "Export Excalidraw diagrams to PNG" not in workflow


def test_tracked_projection_roots_have_one_boundary_owner() -> None:
    module = _load_manifest_module()
    manifest = module._load_manifest()  # noqa: SLF001
    consumer_paths = module.paths_for_scope("all")
    excluded_paths = module.consumer_excluded_paths()
    source_only_paths = module.source_only_paths()

    git_executable = shutil.which("git")
    assert git_executable is not None
    tracked_paths = (
        subprocess.run(  # noqa: S603
            [git_executable, "ls-files", "-z"],
            cwd=_ROOT,
            check=True,
            capture_output=True,
        )
        .stdout.decode()
        .split("\0")
    )
    candidates = {path.split("/", 1)[0] for path in tracked_paths if path}
    candidates.update(
        "/".join(path.split("/")[:2])
        for path in tracked_paths
        if path.startswith("serve/") and len(path.split("/")) > 1
    )

    def is_within(path: str, root: str) -> bool:
        return path == root or path.startswith(f"{root}/")

    for candidate in sorted(candidates):
        in_consumer = any(
            is_within(declared, candidate) or is_within(candidate, declared) for declared in consumer_paths
        )
        is_excluded = any(is_within(candidate, excluded) for excluded in excluded_paths)
        is_source_only = any(is_within(candidate, source_only) for source_only in source_only_paths)
        owners = sum((in_consumer, is_excluded, is_source_only))
        assert owners == 1, f"{candidate} has {owners} sync-boundary owners"

    assert "README.md" in source_only_paths
    assert manifest["scope_groups"]["serve"]["scopes"] == [
        "browser",
        "delivery",
        "knowledge",
        "cockpit",
        "tools",
        "memory",
        "web-content",
    ]


def test_serve_group_projection_contains_shared_docs_and_all_packages() -> None:
    module = _load_manifest_module()

    assert module.scope_names_for_group("serve") == [
        "browser",
        "delivery",
        "knowledge",
        "cockpit",
        "tools",
        "memory",
        "web-content",
    ]
    serve_paths = module.paths_for_group("serve")
    assert serve_paths[0] == "serve/README.md"
    assert {"serve/browser", "serve/delivery-github", "serve/memory-mcp", "serve/web-content"}.issubset(serve_paths)
