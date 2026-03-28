"""Trivial smoke test — verifies mcp-kanban package is importable."""

from __future__ import annotations

import owlbear_mcp_kanban


def test_mcp_kanban_package_importable() -> None:
    """MCP kanban package can be imported."""
    assert owlbear_mcp_kanban.__name__ == "owlbear_mcp_kanban"
