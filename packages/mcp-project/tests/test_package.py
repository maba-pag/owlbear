"""Trivial smoke test — verifies mcp-project package is importable."""

from __future__ import annotations

import owlbear_mcp_project


def test_mcp_project_package_importable() -> None:
    """MCP project package can be imported."""
    assert owlbear_mcp_project.__name__ == "owlbear_mcp_project"
