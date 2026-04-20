"""Failing tests for deny-code-writes hook refactor (#1019).

RED phase — all behavioral tests fail until the hook is refactored from
deny-list to extension allowlist (GREEN: #1021).

Variants under test:
  - owlbear-dev: .owlbear/hooks/deny-code-writes.py
    Allowed extensions: .md, .excalidraw, .py
  - consumer-seed: seed/.owlbear/hooks/deny-code-writes.py
    Allowed extensions: .md, .excalidraw only

AC coverage:
  AC1  owlbear-dev allows .md, .excalidraw, .py; denies all other extensions
  AC2  consumer-seed allows .md, .excalidraw only; denies .py and all others
  AC3  variant divergence: same .py payload → ALLOW (owlbear-dev) vs DENY (seed)
  AC4  edge cases: no-extension files, dotfiles, create_directory denied by both
  AC5  non-write tools (read_file) pass through unaffected — output {}
  AC6  all _extract_paths shapes: filePath, dirPath, replacements[].filePath, files[]
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

# ---------------------------------------------------------------------------
# Helpers — load hook modules by path
# ---------------------------------------------------------------------------

_REPO_ROOT = Path(__file__).parent.parent
_DEV_HOOK_PATH = _REPO_ROOT / ".owlbear" / "hooks" / "deny-code-writes.py"
_SEED_HOOK_PATH = _REPO_ROOT / "seed" / ".owlbear" / "hooks" / "deny-code-writes.py"


def _load_hook(path: Path, module_name: str) -> types.ModuleType:
    spec = importlib.util.spec_from_file_location(module_name, path)
    assert spec is not None, f"Cannot load hook spec from {path}"
    assert spec.loader is not None, f"Hook spec has no loader: {path}"
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def dev_hook() -> types.ModuleType:
    return _load_hook(_DEV_HOOK_PATH, "deny_code_writes_dev")


@pytest.fixture(scope="module")
def seed_hook() -> types.ModuleType:
    return _load_hook(_SEED_HOOK_PATH, "deny_code_writes_seed")


def _invoke(module: types.ModuleType, payload: dict[str, Any]) -> dict[str, Any]:
    """Call module.main() with payload as stdin; return parsed stdout JSON."""
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


def _write(tool: str, file_path: str) -> dict[str, Any]:
    return {"tool_name": tool, "tool_input": {"filePath": file_path}}


# ===========================================================================
# AC1: owlbear-dev hook — extension allowlist (.md, .excalidraw, .py)
# ===========================================================================


class TestFromAC_OwlbearDevHook:
    """AC1: owlbear-dev allows .md, .excalidraw, .py; denies everything else.

    Key: tests use paths currently in denied prefixes (tests/, serve/) for
    ALLOW cases — old code denies them, new allowlist code permits them.
    Tests use paths outside denied prefixes for DENY cases — old code allows
    them, new allowlist code rejects them.
    """

    # --- ALLOW cases (.md, .excalidraw, .py in currently-denied dirs) ---

    def test_allows_md_file_inside_denied_prefix(self, dev_hook: types.ModuleType) -> None:
        """Happy: .md in tests/ must be ALLOW after refactor; current code DENIES tests/."""
        result = _invoke(dev_hook, _write("create_file", "tests/some-doc.md"))
        assert _is_allowed(result), f"expected ALLOW for .md but got: {result}"

    def test_allows_excalidraw_inside_denied_prefix(self, dev_hook: types.ModuleType) -> None:
        """Happy: .excalidraw in serve/ must be ALLOW after refactor; current code DENIES serve/."""
        result = _invoke(dev_hook, _write("create_file", "serve/docs/arch.excalidraw"))
        assert _is_allowed(result), f"expected ALLOW for .excalidraw but got: {result}"

    def test_allows_py_file_inside_denied_prefix(self, dev_hook: types.ModuleType) -> None:
        """Happy: .py in tests/ must be ALLOW in owlbear-dev; current code DENIES tests/."""
        result = _invoke(dev_hook, _write("create_file", "tests/test_new.py"))
        assert _is_allowed(result), f"expected ALLOW for .py (owlbear-dev) but got: {result}"

    # --- DENY cases (disallowed extensions in currently-allowed paths) ---

    def test_denies_ts_extension(self, dev_hook: types.ModuleType) -> None:
        """Error: .ts must be DENY; current code ALLOWS share/docs/ (not in denied prefixes)."""
        result = _invoke(dev_hook, _write("create_file", "share/docs/page.ts"))
        assert _is_denied(result), f"expected DENY for .ts but got: {result}"

    def test_denies_json_extension(self, dev_hook: types.ModuleType) -> None:
        """Error: .json must be DENY; current code ALLOWS share/config/."""
        result = _invoke(dev_hook, _write("create_file", "share/config/settings.json"))
        assert _is_denied(result), f"expected DENY for .json but got: {result}"

    def test_denies_yaml_extension(self, dev_hook: types.ModuleType) -> None:
        """Error: .yaml must be DENY; current code ALLOWS .owlbear/briefs/."""
        result = _invoke(dev_hook, _write("create_file", ".owlbear/briefs/config.yaml"))
        assert _is_denied(result), f"expected DENY for .yaml but got: {result}"

    def test_denies_no_extension_file(self, dev_hook: types.ModuleType) -> None:
        """Edge: file with no extension must be DENY; current code ALLOWS share/docs/."""
        result = _invoke(dev_hook, _write("create_file", "share/docs/Makefile"))
        assert _is_denied(result), f"expected DENY for no-extension file but got: {result}"

    def test_denies_dotfile(self, dev_hook: types.ModuleType) -> None:
        """Edge: dotfile must be DENY; current code ALLOWS share/ paths."""
        result = _invoke(dev_hook, _write("create_file", "share/.env"))
        assert _is_denied(result), f"expected DENY for dotfile but got: {result}"

    def test_denies_create_directory(self, dev_hook: types.ModuleType) -> None:
        """Edge: create_directory has no extension and must be DENY; current code ALLOWS."""
        payload = {"tool_name": "create_directory", "tool_input": {"dirPath": "share/docs/subfolder"}}
        result = _invoke(dev_hook, payload)
        assert _is_denied(result), f"expected DENY for create_directory but got: {result}"


# ===========================================================================
# AC2: consumer-seed hook — strict allowlist (.md, .excalidraw only)
# ===========================================================================


class TestFromAC_ConsumerSeedHook:
    """AC2: consumer-seed allows .md, .excalidraw only; denies .py and all others.

    Same structural rationale: ALLOW cases use denied-prefix paths; DENY
    cases use non-denied paths that the current code would ALLOW.
    """

    # --- ALLOW cases ---

    def test_allows_md_file_inside_denied_prefix(self, seed_hook: types.ModuleType) -> None:
        """Happy: .md in tests/ must be ALLOW after refactor; current code DENIES tests/."""
        result = _invoke(seed_hook, _write("create_file", "tests/some-doc.md"))
        assert _is_allowed(result), f"expected ALLOW for .md but got: {result}"

    def test_allows_excalidraw_inside_denied_prefix(self, seed_hook: types.ModuleType) -> None:
        """Happy: .excalidraw in serve/ must be ALLOW after refactor; current code DENIES serve/."""
        result = _invoke(seed_hook, _write("create_file", "serve/docs/arch.excalidraw"))
        assert _is_allowed(result), f"expected ALLOW for .excalidraw but got: {result}"

    # --- DENY cases ---

    def test_denies_py_extension(self, seed_hook: types.ModuleType) -> None:
        """Error: .py must be DENY in consumer-seed; current code ALLOWS share/docs/."""
        result = _invoke(seed_hook, _write("create_file", "share/docs/helper.py"))
        assert _is_denied(result), f"expected DENY for .py (consumer-seed) but got: {result}"

    def test_denies_ts_extension(self, seed_hook: types.ModuleType) -> None:
        """Error: .ts must be DENY; current code ALLOWS share/docs/."""
        result = _invoke(seed_hook, _write("create_file", "share/docs/page.ts"))
        assert _is_denied(result), f"expected DENY for .ts but got: {result}"

    def test_denies_no_extension_file(self, seed_hook: types.ModuleType) -> None:
        """Edge: no-extension file must be DENY; current code ALLOWS share/docs/."""
        result = _invoke(seed_hook, _write("create_file", "share/docs/Makefile"))
        assert _is_denied(result), f"expected DENY for no-extension file but got: {result}"

    def test_denies_dotfile(self, seed_hook: types.ModuleType) -> None:
        """Edge: dotfile must be DENY; current code ALLOWS share/ paths."""
        result = _invoke(seed_hook, _write("create_file", "share/.gitignore"))
        assert _is_denied(result), f"expected DENY for dotfile but got: {result}"

    def test_denies_create_directory(self, seed_hook: types.ModuleType) -> None:
        """Edge: create_directory has no extension — must be DENY; current code ALLOWS."""
        payload = {"tool_name": "create_directory", "tool_input": {"dirPath": "share/docs/new-folder"}}
        result = _invoke(seed_hook, payload)
        assert _is_denied(result), f"expected DENY for create_directory but got: {result}"


# ===========================================================================
# AC3: variant divergence — same .py payload → opposite outcomes
# ===========================================================================


class TestFromAC_VariantDivergence:
    """AC3: same write payload for a .py file produces ALLOW from owlbear-dev and
    DENY from consumer-seed.
    """

    def test_py_write_diverges_between_variants(
        self, dev_hook: types.ModuleType, seed_hook: types.ModuleType
    ) -> None:
        """Boundary: .py in share/docs/ — dev ALLOW, seed DENY.

        Current code: both ALLOW (share/ not in denied prefixes).
        The seed assertion fails → overall test FAILS with current code.
        """
        payload = _write("create_file", "share/docs/helper.py")
        dev_result = _invoke(dev_hook, payload)
        seed_result = _invoke(seed_hook, payload)

        assert _is_allowed(dev_result), (
            f"owlbear-dev must ALLOW .py extension but got: {dev_result}"
        )
        assert _is_denied(seed_result), (
            f"consumer-seed must DENY .py extension but got: {seed_result}"
        )

    def test_py_write_in_formerly_denied_dir_diverges(
        self, dev_hook: types.ModuleType, seed_hook: types.ModuleType
    ) -> None:
        """Boundary: .py in tests/ — dev ALLOW (extension wins), seed DENY.

        Current code: both DENY (tests/ prefix denied).
        The dev assertion fails → overall test FAILS with current code.
        """
        payload = _write("create_file", "tests/helper.py")
        dev_result = _invoke(dev_hook, payload)
        seed_result = _invoke(seed_hook, payload)

        assert _is_allowed(dev_result), (
            f"owlbear-dev must ALLOW .py in tests/ after refactor but got: {dev_result}"
        )
        assert _is_denied(seed_result), (
            f"consumer-seed must DENY .py (not in allowlist) but got: {seed_result}"
        )


# ===========================================================================
# AC4: edge cases — create_directory and extensionless paths via both hooks
# ===========================================================================


class TestFromAC_EdgeCasesExtensionless:
    """AC4: create_directory and no-extension paths must be denied by both variants."""

    def test_create_directory_denied_by_dev_hook(self, dev_hook: types.ModuleType) -> None:
        """Edge: create_directory to a doc-like path is DENY in owlbear-dev."""
        payload = {"tool_name": "create_directory", "tool_input": {"dirPath": "share/diagrams/new"}}
        result = _invoke(dev_hook, payload)
        assert _is_denied(result), f"expected DENY for create_directory (dev) but got: {result}"

    def test_create_directory_denied_by_seed_hook(self, seed_hook: types.ModuleType) -> None:
        """Edge: create_directory to a doc-like path is DENY in consumer-seed."""
        payload = {"tool_name": "create_directory", "tool_input": {"dirPath": "share/diagrams/new"}}
        result = _invoke(seed_hook, payload)
        assert _is_denied(result), f"expected DENY for create_directory (seed) but got: {result}"

    def test_extensionless_file_denied_by_dev_hook(self, dev_hook: types.ModuleType) -> None:
        """Edge: file without extension in doc path DENY in owlbear-dev."""
        result = _invoke(dev_hook, _write("create_file", "share/docs/LICENSE"))
        assert _is_denied(result), f"expected DENY for extensionless file (dev) but got: {result}"

    def test_extensionless_file_denied_by_seed_hook(self, seed_hook: types.ModuleType) -> None:
        """Edge: file without extension in doc path DENY in consumer-seed."""
        result = _invoke(seed_hook, _write("create_file", "share/docs/LICENSE"))
        assert _is_denied(result), f"expected DENY for extensionless file (seed) but got: {result}"


# ===========================================================================
# AC5: non-write passthrough — preserved behavior
# ===========================================================================


class TestFromAC_NonWritePassthrough:
    """AC5: non-write tools must pass through unaffected — output {}.

    NOTE: These tests verify PRESERVED behavior that exists in both the current
    deny-list code and the refactored allowlist code. They will PASS with
    current code and are included per AC to document the contract and guard
    against regression during the refactor.
    """

    def test_read_file_returns_empty_dict(self, dev_hook: types.ModuleType) -> None:
        """Non-write: read_file is not in _WRITE_TOOLS — must return {}."""
        payload = {"tool_name": "read_file", "tool_input": {"filePath": "serve/app.py"}}
        assert _invoke(dev_hook, payload) == {}

    def test_grep_search_returns_empty_dict(self, dev_hook: types.ModuleType) -> None:
        """Non-write: grep_search is not in _WRITE_TOOLS — must return {}."""
        payload = {"tool_name": "grep_search", "tool_input": {"query": "something"}}
        assert _invoke(dev_hook, payload) == {}

    def test_non_write_passthrough_for_seed_hook(self, seed_hook: types.ModuleType) -> None:
        """Non-write: read_file passes through unaffected in consumer-seed variant too."""
        payload = {"tool_name": "read_file", "tool_input": {"filePath": "serve/app.py"}}
        assert _invoke(seed_hook, payload) == {}


# ===========================================================================
# AC6: _extract_paths input shapes — all four paths into the hook must be
#      exercised; all with a .ts file so current code ALLOWS but new DENIES
# ===========================================================================


class TestFromAC_InputShapes:
    """AC6: all four _extract_paths input shapes produce the expected result.

    Uses dev_hook with .ts extension: current code ALLOWS (share/ not denied),
    new allowlist code DENIES (.ts not in allowed extensions) → all FAIL.
    """

    def test_file_path_shape(self, dev_hook: types.ModuleType) -> None:
        """filePath key: create_file with .ts path must be DENY."""
        result = _invoke(dev_hook, _write("create_file", "share/docs/page.ts"))
        assert _is_denied(result), f"expected DENY via filePath shape but got: {result}"

    def test_dir_path_shape(self, dev_hook: types.ModuleType) -> None:
        """dirPath key: create_directory must be DENY (no extension)."""
        payload = {"tool_name": "create_directory", "tool_input": {"dirPath": "share/docs/new"}}
        result = _invoke(dev_hook, payload)
        assert _is_denied(result), f"expected DENY via dirPath shape but got: {result}"

    def test_replacements_file_path_shape(self, dev_hook: types.ModuleType) -> None:
        """replacements[].filePath: multi_replace with .ts target must be DENY."""
        payload = {
            "tool_name": "multi_replace_string_in_file",
            "tool_input": {
                "replacements": [
                    {"filePath": "share/docs/page.ts", "oldString": "x", "newString": "y"}
                ]
            },
        }
        result = _invoke(dev_hook, payload)
        assert _is_denied(result), f"expected DENY via replacements[].filePath shape but got: {result}"

    def test_files_string_array_shape(self, dev_hook: types.ModuleType) -> None:
        """files[] string: editFiles with .ts string path must be DENY."""
        payload = {
            "tool_name": "editFiles",
            "tool_input": {"files": ["share/docs/page.ts"]},
        }
        result = _invoke(dev_hook, payload)
        assert _is_denied(result), f"expected DENY via files[] string shape but got: {result}"

    def test_files_dict_array_shape(self, dev_hook: types.ModuleType) -> None:
        """files[] dict: editFiles with .ts dict filePath must be DENY."""
        payload = {
            "tool_name": "editFiles",
            "tool_input": {"files": [{"filePath": "share/docs/page.ts"}]},
        }
        result = _invoke(dev_hook, payload)
        assert _is_denied(result), f"expected DENY via files[] dict shape but got: {result}"

    def test_replace_string_in_file_shape(self, dev_hook: types.ModuleType) -> None:
        """replace_string_in_file uses filePath key — .ts target must be DENY."""
        result = _invoke(dev_hook, _write("replace_string_in_file", "share/docs/page.ts"))
        assert _is_denied(result), f"expected DENY via replace_string_in_file shape but got: {result}"
