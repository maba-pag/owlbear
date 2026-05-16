"""Behavioral tests for the deny-non-doc-writes hook.

The current contract is shared between the runtime copy and the seeded copy:

- `.owlbear/scratch/` is always writable
- `.md` and `.excalidraw` files are writable outside scratch
- other file types are denied outside scratch
"""

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
_HOOK_CASES = [
    ("dev", _REPO_ROOT / ".owlbear" / "hooks" / "deny-non-doc-writes.py"),
    ("seed", _REPO_ROOT / "seed" / ".owlbear" / "hooks" / "deny-non-doc-writes.py"),
]


def _load_hook(path: Path, module_name: str) -> types.ModuleType:
    spec = importlib.util.spec_from_file_location(module_name, path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(params=_HOOK_CASES, ids=[case[0] for case in _HOOK_CASES])
def hook_module(request: pytest.FixtureRequest) -> types.ModuleType:
    label, path = request.param
    return _load_hook(path, f"deny_non_doc_writes_{label}")


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


def _write(tool: str, file_path: str) -> dict[str, Any]:
    return {"tool_name": tool, "tool_input": {"filePath": file_path}}


def _is_allowed(result: dict[str, Any]) -> bool:
    return result.get("hookSpecificOutput", {}).get("permissionDecision") != "deny"


def _is_denied(result: dict[str, Any]) -> bool:
    return result.get("hookSpecificOutput", {}).get("permissionDecision") == "deny"


class TestDenyCodeWrites:
    def test_allows_markdown_outside_scratch(self, hook_module: types.ModuleType) -> None:
        result = _invoke(hook_module, _write("create_file", "README.md"))
        assert _is_allowed(result), result

    def test_allows_excalidraw_outside_scratch(self, hook_module: types.ModuleType) -> None:
        result = _invoke(hook_module, _write("create_file", "share/diagrams/flow.excalidraw"))
        assert _is_allowed(result), result

    def test_allows_any_file_type_inside_scratch(self, hook_module: types.ModuleType) -> None:
        result = _invoke(hook_module, _write("create_file", ".owlbear/scratch/notes.tmp"))
        assert _is_allowed(result), result

    def test_allows_scratch_directory_creation(self, hook_module: types.ModuleType) -> None:
        payload = {
            "tool_name": "create_directory",
            "tool_input": {"dirPath": ".owlbear/scratch/research/cache"},
        }
        result = _invoke(hook_module, payload)
        assert _is_allowed(result), result

    def test_denies_python_outside_scratch(self, hook_module: types.ModuleType) -> None:
        result = _invoke(hook_module, _write("create_file", "serve/app.py"))
        assert _is_denied(result), result

    def test_denies_typescript_outside_scratch(self, hook_module: types.ModuleType) -> None:
        result = _invoke(hook_module, _write("create_file", "serve/cockpit/web/src/app.tsx"))
        assert _is_denied(result), result

    def test_denies_directory_creation_outside_scratch(self, hook_module: types.ModuleType) -> None:
        payload = {
            "tool_name": "create_directory",
            "tool_input": {"dirPath": "docs/generated"},
        }
        result = _invoke(hook_module, payload)
        assert _is_denied(result), result

    def test_allows_apply_patch_inside_scratch(self, hook_module: types.ModuleType) -> None:
        payload = {
            "tool_name": "apply_patch",
            "tool_input": {
                "input": "*** Begin Patch\n*** Update File: .owlbear/scratch/notes.txt\n@@\n-old\n+new\n*** End Patch"
            },
        }
        result = _invoke(hook_module, payload)
        assert _is_allowed(result), result

    def test_denies_apply_patch_for_python_file(self, hook_module: types.ModuleType) -> None:
        payload = {
            "tool_name": "apply_patch",
            "tool_input": {
                "input": "*** Begin Patch\n*** Update File: serve/kanban/src/owlbear_kanban/engine.py\n@@\n-old\n+new\n*** End Patch"
            },
        }
        result = _invoke(hook_module, payload)
        assert _is_denied(result), result

    def test_non_write_tool_passes_through(self, hook_module: types.ModuleType) -> None:
        payload = {"tool_name": "read_file", "tool_input": {"filePath": "README.md"}}
        assert _invoke(hook_module, payload) == {}
