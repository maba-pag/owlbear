"""Behavioral tests for scratch-aware write guard hooks."""

from __future__ import annotations

import importlib.util
import json
import sys
import types
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

_REPO_ROOT = Path(__file__).parent.parent
_DENY_WRITES_CASES = [
    ("dev", _REPO_ROOT / ".owlbear" / "hooks" / "deny-writes.py"),
    ("seed", _REPO_ROOT / "seed" / ".owlbear" / "hooks" / "deny-writes.py"),
]
_DENY_SRC_CASES = [
    ("dev", _REPO_ROOT / ".owlbear" / "hooks" / "deny-src-writes.py"),
    ("seed", _REPO_ROOT / "seed" / ".owlbear" / "hooks" / "deny-src-writes.py"),
]


def _load_hook(path: Path, module_name: str) -> types.ModuleType:
    spec = importlib.util.spec_from_file_location(module_name, path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _invoke(module: types.ModuleType, payload: dict[str, Any]) -> dict[str, Any]:
    raw = json.dumps(payload).encode()
    mock_stdin = MagicMock()
    mock_stdin.buffer.read.return_value = raw
    captured: list[str] = []

    def _fake_print(*args: object, **_kwargs: object) -> None:
        if args:
            captured.append(str(args[0]))

    with patch.object(sys, "stdin", mock_stdin), patch("builtins.print", _fake_print):
        module.main()

    return json.loads(captured[-1]) if captured else {}


def _is_allowed(result: dict[str, Any]) -> bool:
    return result.get("hookSpecificOutput", {}).get("permissionDecision") != "deny"


def _is_denied(result: dict[str, Any]) -> bool:
    return result.get("hookSpecificOutput", {}).get("permissionDecision") == "deny"


@pytest.fixture(params=_DENY_WRITES_CASES, ids=[case[0] for case in _DENY_WRITES_CASES])
def deny_writes_module(request: pytest.FixtureRequest) -> types.ModuleType:
    label, path = request.param
    return _load_hook(path, f"deny_writes_{label}")


@pytest.fixture(params=_DENY_SRC_CASES, ids=[case[0] for case in _DENY_SRC_CASES])
def deny_src_module(request: pytest.FixtureRequest) -> types.ModuleType:
    label, path = request.param
    return _load_hook(path, f"deny_src_{label}")


class TestDenyWrites:
    def test_allows_scratch_file(self, deny_writes_module: types.ModuleType) -> None:
        payload = {
            "tool_name": "create_file",
            "tool_input": {"filePath": ".owlbear/scratch/report.txt"},
        }
        assert _is_allowed(_invoke(deny_writes_module, payload))

    def test_denies_non_scratch_file(
        self, deny_writes_module: types.ModuleType
    ) -> None:
        payload = {"tool_name": "create_file", "tool_input": {"filePath": "README.md"}}
        assert _is_denied(_invoke(deny_writes_module, payload))

    def test_allows_apply_patch_in_scratch(
        self, deny_writes_module: types.ModuleType
    ) -> None:
        payload = {
            "tool_name": "apply_patch",
            "tool_input": {
                "input": "*** Begin Patch\n*** Update File: .owlbear/scratch/reviewer.md\n@@\n-old\n+new\n*** End Patch"
            },
        }
        assert _is_allowed(_invoke(deny_writes_module, payload))

    def test_denies_apply_patch_outside_scratch(
        self, deny_writes_module: types.ModuleType
    ) -> None:
        payload = {
            "tool_name": "apply_patch",
            "tool_input": {
                "input": "*** Begin Patch\n*** Update File: README.md\n@@\n-old\n+new\n*** End Patch"
            },
        }
        assert _is_denied(_invoke(deny_writes_module, payload))


class TestDenySrcWrites:
    def test_allows_test_file(self, deny_src_module: types.ModuleType) -> None:
        payload = {
            "tool_name": "create_file",
            "tool_input": {"filePath": "tests/test_feature.py"},
        }
        assert _is_allowed(_invoke(deny_src_module, payload))

    def test_allows_scratch_file(self, deny_src_module: types.ModuleType) -> None:
        payload = {
            "tool_name": "create_file",
            "tool_input": {"filePath": ".owlbear/scratch/test-writer-notes.txt"},
        }
        assert _is_allowed(_invoke(deny_src_module, payload))

    def test_denies_source_file(self, deny_src_module: types.ModuleType) -> None:
        payload = {
            "tool_name": "create_file",
            "tool_input": {"filePath": "serve/app.py"},
        }
        assert _is_denied(_invoke(deny_src_module, payload))

    def test_allows_apply_patch_in_tests(
        self, deny_src_module: types.ModuleType
    ) -> None:
        payload = {
            "tool_name": "apply_patch",
            "tool_input": {
                "input": "*** Begin Patch\n*** Update File: tests/test_feature.py\n@@\n-old\n+new\n*** End Patch"
            },
        }
        assert _is_allowed(_invoke(deny_src_module, payload))

    def test_allows_dunder_tests_file(self, deny_src_module: types.ModuleType) -> None:
        payload = {
            "tool_name": "create_file",
            "tool_input": {
                "filePath": "serve/cockpit/web/src/__tests__/useScanPolling.test.ts"
            },
        }
        assert _is_allowed(_invoke(deny_src_module, payload))

    def test_allows_apply_patch_in_dunder_tests(
        self, deny_src_module: types.ModuleType
    ) -> None:
        payload = {
            "tool_name": "apply_patch",
            "tool_input": {
                "input": "*** Begin Patch\n*** Update File: serve/cockpit/web/src/__tests__/hook.test.ts\n@@\n-old\n+new\n*** End Patch"
            },
        }
        assert _is_allowed(_invoke(deny_src_module, payload))

    def test_allows_e2e_file(self, deny_src_module: types.ModuleType) -> None:
        payload = {
            "tool_name": "create_file",
            "tool_input": {
                "filePath": "serve/cockpit/web/e2e/filter-controls.spec.ts"
            },
        }
        assert _is_allowed(_invoke(deny_src_module, payload))

    def test_allows_apply_patch_in_e2e(
        self, deny_src_module: types.ModuleType
    ) -> None:
        payload = {
            "tool_name": "apply_patch",
            "tool_input": {
                "input": "*** Begin Patch\n*** Update File: serve/cockpit/web/e2e/hook.spec.ts\n@@\n-old\n+new\n*** End Patch"
            },
        }
        assert _is_allowed(_invoke(deny_src_module, payload))

    def test_denies_apply_patch_in_source(
        self, deny_src_module: types.ModuleType
    ) -> None:
        payload = {
            "tool_name": "apply_patch",
            "tool_input": {
                "input": "*** Begin Patch\n*** Update File: serve/app.py\n@@\n-old\n+new\n*** End Patch"
            },
        }
        assert _is_denied(_invoke(deny_src_module, payload))
