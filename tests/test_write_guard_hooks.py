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
_DENY_SRC_CASES = [
    ("dev", _REPO_ROOT / ".owlbear" / "hooks" / "deny-src-writes.py"),
]


def _load_hook(path: Path, module_name: str) -> types.ModuleType:
    spec = importlib.util.spec_from_file_location(module_name, path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _invoke(
    module: types.ModuleType,
    payload: dict[str, Any],
    *,
    argv: list[str] | None = None,
) -> dict[str, Any]:
    return _invoke_raw(module, json.dumps(payload).encode(), argv=argv)


def _invoke_raw(
    module: types.ModuleType,
    raw: bytes,
    *,
    argv: list[str] | None = None,
) -> dict[str, Any]:
    mock_stdin = MagicMock()
    mock_stdin.buffer.read.return_value = raw
    captured: list[str] = []

    def _fake_print(*args: object, **_kwargs: object) -> None:
        if args:
            captured.append(str(args[0]))

    with (
        patch.object(sys, "stdin", mock_stdin),
        patch.object(sys, "argv", argv or [str(module.__file__)]),
        patch("builtins.print", _fake_print),
    ):
        module.main()

    return json.loads(captured[-1]) if captured else {}


def _is_allowed(result: dict[str, Any]) -> bool:
    return result.get("hookSpecificOutput", {}).get("permissionDecision") != "deny"


def _is_denied(result: dict[str, Any]) -> bool:
    return result.get("hookSpecificOutput", {}).get("permissionDecision") == "deny"


@pytest.fixture(params=_DENY_SRC_CASES, ids=[case[0] for case in _DENY_SRC_CASES])
def deny_src_module(request: pytest.FixtureRequest) -> types.ModuleType:
    label, path = request.param
    return _load_hook(path, f"deny_src_{label}")


class TestDenySrcWrites:
    @pytest.mark.parametrize("raw", [b"", b"{", b"[]", b"null"])
    def test_malformed_or_non_object_input_fails_open(
        self,
        deny_src_module: types.ModuleType,
        raw: bytes,
    ) -> None:
        assert _invoke_raw(deny_src_module, raw) == {}

    def test_unknown_tool_fails_open(self, deny_src_module: types.ModuleType) -> None:
        payload = {
            "tool_name": "future/write_tool",
            "tool_input": {"filePath": "serve/app.py"},
        }
        assert _is_allowed(_invoke(deny_src_module, payload))

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

    def test_allows_apply_patch_in_tests(self, deny_src_module: types.ModuleType) -> None:
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
            "tool_input": {"filePath": "serve/example/web/src/__tests__/useScanPolling.test.ts"},
        }
        assert _is_allowed(_invoke(deny_src_module, payload))

    def test_allows_colocated_test_file(self, deny_src_module: types.ModuleType) -> None:
        payload = {
            "tool_name": "apply_patch",
            "tool_input": {
                "input": (
                    "*** Begin Patch\n*** Update File: serve/example/web/src/App.wiring.test.tsx\n@@\n"
                    "-old\n+new\n*** End Patch"
                ),
            },
        }
        assert _is_allowed(_invoke(deny_src_module, payload))

    def test_allows_colocated_spec_file(self, deny_src_module: types.ModuleType) -> None:
        payload = {
            "tool_name": "create_file",
            "tool_input": {"filePath": "serve/example/web/src/App.spec.mts"},
        }
        assert _is_allowed(_invoke(deny_src_module, payload))

    def test_allows_apply_patch_in_dunder_tests(self, deny_src_module: types.ModuleType) -> None:
        payload = {
            "tool_name": "apply_patch",
            "tool_input": {
                "input": (
                    "*** Begin Patch\n*** Update File: serve/example/web/src/__tests__/hook.test.ts\n@@\n"
                    "-old\n+new\n*** End Patch"
                ),
            },
        }
        assert _is_allowed(_invoke(deny_src_module, payload))

    def test_allows_e2e_file(self, deny_src_module: types.ModuleType) -> None:
        payload = {
            "tool_name": "create_file",
            "tool_input": {"filePath": "serve/example/web/e2e/filter-controls.spec.ts"},
        }
        assert _is_allowed(_invoke(deny_src_module, payload))

    def test_allows_apply_patch_in_e2e(self, deny_src_module: types.ModuleType) -> None:
        payload = {
            "tool_name": "apply_patch",
            "tool_input": {
                "input": (
                    "*** Begin Patch\n*** Update File: serve/example/web/e2e/hook.spec.ts\n@@\n"
                    "-old\n+new\n*** End Patch"
                ),
            },
        }
        assert _is_allowed(_invoke(deny_src_module, payload))

    def test_denies_apply_patch_in_source(self, deny_src_module: types.ModuleType) -> None:
        payload = {
            "tool_name": "apply_patch",
            "tool_input": {"input": "*** Begin Patch\n*** Update File: serve/app.py\n@@\n-old\n+new\n*** End Patch"},
        }
        assert _is_denied(_invoke(deny_src_module, payload))

    def test_allows_rename_within_test_surface(self, deny_src_module: types.ModuleType) -> None:
        payload = {
            "tool_name": "edit/rename",
            "tool_input": {"oldPath": "tests/test_old.py", "newPath": "tests/test_new.py"},
        }
        assert _is_allowed(_invoke(deny_src_module, payload))

    @pytest.mark.parametrize("path", ["../outside/tests/test_escape.py", "serve/tests/../../app.py"])
    def test_denies_traversal_write(self, deny_src_module: types.ModuleType, path: str) -> None:
        payload = {"tool_name": "create_file", "tool_input": {"filePath": path}}
        assert _is_denied(_invoke(deny_src_module, payload))
