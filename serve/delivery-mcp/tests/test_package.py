"""Trivial smoke test — verifies delivery-mcp package is importable."""

from __future__ import annotations

import owlbear_delivery_mcp


def test_delivery_mcp_package_importable() -> None:
    """MCP delivery package can be imported."""
    assert owlbear_delivery_mcp.__name__ == "owlbear_delivery_mcp"
