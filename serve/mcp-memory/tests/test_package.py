"""Smoke test — verifies mcp-memory package is importable.

AC7: `import owlbear_mcp_memory` succeeds.
"""

from __future__ import annotations

import owlbear_mcp_memory


def test_mcp_memory_package_importable() -> None:
    """AC7: mcp-memory package can be imported."""
    assert owlbear_mcp_memory.__name__ == "owlbear_mcp_memory"
