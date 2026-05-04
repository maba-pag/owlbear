"""Failing tests for task #1340: revert requires-python to >=3.12 in both pyproject.toml files.

AC1: No Python 3.13+ exclusive syntax found in serve/kanban/ or serve/mcp-kanban/ source.
AC2: requires-python must be ">=3.12" in both serve/kanban/pyproject.toml and
     serve/mcp-kanban/pyproject.toml — if no 3.14-only features are used.
"""

from __future__ import annotations

import re
import tomllib
import pathlib

_KANBAN_PYPROJECT = pathlib.Path("serve/kanban/pyproject.toml")
_MCP_KANBAN_PYPROJECT = pathlib.Path("serve/mcp-kanban/pyproject.toml")

_KANBAN_SRC = pathlib.Path("serve/kanban/src/owlbear_kanban")
_MCP_KANBAN_SRC = pathlib.Path("serve/mcp-kanban/src/owlbear_mcp_kanban")

# Python 3.13+ exclusive feature patterns
_PY313_PLUS_PATTERNS = [
    r"\bTypeIs\b",  # PEP 742 — Python 3.13+ (typing.TypeIs)
]


def _read_requires_python(path: pathlib.Path) -> str:
    with path.open("rb") as f:
        return tomllib.load(f)["project"]["requires-python"]


def _has_313_plus_features(src_dir: pathlib.Path) -> bool:
    """Return True if any .py file in src_dir uses Python 3.13+ exclusive syntax."""
    for py_file in src_dir.rglob("*.py"):
        text = py_file.read_text()
        for pattern in _PY313_PLUS_PATTERNS:
            if re.search(pattern, text):
                return True
    return False


class TestFromAC_RequiresPythonFloor:
    """AC2: Both pyproject.toml files must specify requires-python = '>=3.12'."""

    def test_kanban_requires_python_is_3_12(self) -> None:
        req = _read_requires_python(_KANBAN_PYPROJECT)
        assert req == ">=3.12", (
            f"serve/kanban/pyproject.toml requires-python={req!r}. "
            "No Python 3.14-only features were found in source — must revert to '>=3.12'."
        )

    def test_mcp_kanban_requires_python_is_3_12(self) -> None:
        req = _read_requires_python(_MCP_KANBAN_PYPROJECT)
        assert req == ">=3.12", (
            f"serve/mcp-kanban/pyproject.toml requires-python={req!r}. "
            "No Python 3.14-only features were found in source — must revert to '>=3.12'."
        )

    def test_kanban_does_not_pin_to_3_14(self) -> None:
        req = _read_requires_python(_KANBAN_PYPROJECT)
        assert not re.search(r"3\.14", req), (
            f"serve/kanban/pyproject.toml requires-python={req!r} pins to Python 3.14 "
            "without justification (no 3.14-only features used). Revert to '>=3.12'."
        )

    def test_mcp_kanban_does_not_pin_to_3_14(self) -> None:
        req = _read_requires_python(_MCP_KANBAN_PYPROJECT)
        assert not re.search(r"3\.14", req), (
            f"serve/mcp-kanban/pyproject.toml requires-python={req!r} pins to Python 3.14 "
            "without justification (no 3.14-only features used). Revert to '>=3.12'."
        )


class TestFromAC_NoUnjustifiedVersionBump:
    """AC1+AC2: If no Python 3.13+ features are used, the floor must be <=3.12."""

    def test_kanban_floor_justified_by_source_syntax(self) -> None:
        """requires-python must not exceed the syntax actually used in kanban source."""
        has_313 = _has_313_plus_features(_KANBAN_SRC)
        req = _read_requires_python(_KANBAN_PYPROJECT)
        if not has_313:
            assert req == ">=3.12", (
                f"No Python 3.13+ features found in serve/kanban/src/ but "
                f"requires-python={req!r}. Must revert to '>=3.12'."
            )

    def test_mcp_kanban_floor_justified_by_source_syntax(self) -> None:
        """requires-python must not exceed the syntax actually used in mcp-kanban source."""
        has_313 = _has_313_plus_features(_MCP_KANBAN_SRC)
        req = _read_requires_python(_MCP_KANBAN_PYPROJECT)
        if not has_313:
            assert req == ">=3.12", (
                f"No Python 3.13+ features found in serve/mcp-kanban/src/ but "
                f"requires-python={req!r}. Must revert to '>=3.12'."
            )
