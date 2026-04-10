"""Tests for #496: Standardize error handling, return types, and exports across MCP servers.

TDD RED phase — the following tests fail until the builder implements:
- mcp-project project_readme: catch OSError on read_text() and return error: string
- mcp-project project_structure: catch unexpected exceptions from build_tree() and return error: string
- mcp-knowledge __all__: add init_db to the exports list

Regression guards (currently passing) verify the happy path is not broken by the builder
when adding try/except wrappers.
"""

from __future__ import annotations

import owlbear_mcp_knowledge.server as _knowledge_server_module


# ---------------------------------------------------------------------------
# TestFromAC_KnowledgeServerExports
# ---------------------------------------------------------------------------


class TestFromAC_KnowledgeServerExports:
    """AC: Add __all__ to mcp-knowledge server.py listing all public symbols.

    init_db is a public function defined in server.py but currently absent
    from __all__. The builder must add it to complete the exports list.
    """

    def test_init_db_exported(self) -> None:
        """init_db is a public function and must appear in __all__."""
        assert "init_db" in _knowledge_server_module.__all__, (
            f"'init_db' is a public function in server.py but missing from __all__;\n"
            f"current __all__: {sorted(_knowledge_server_module.__all__)}"
        )

    def test_all_symbols_actually_exist_on_module(self) -> None:
        """Every symbol listed in __all__ must exist as a module attribute."""
        for name in _knowledge_server_module.__all__:
            assert hasattr(_knowledge_server_module, name), (
                f"__all__ references '{name}' but it does not exist on the module"
            )
