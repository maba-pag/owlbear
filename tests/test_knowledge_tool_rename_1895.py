"""Smoke tests for MCP tool rename task #1895.

Source files under test:
  serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py
  share/agents/knowledge-enricher.agent.md
  share/agents/knowledge-ingestor.agent.md
  serve/mcp-knowledge/README.md
  share/skills/h-knowledge-ops/SKILL.md
  setup/setup-guide.md
  share/skills/w-knowledge-enrichment/SKILL.md
  share/prompts/kb-enrich.prompt.md
  README.md

Rename matrix (old → new):
  search_knowledge          → knowledge_search
  list_sources              → knowledge_sources_list
  get_stats                 → knowledge_stats
  ingest_document           → knowledge_ingest
  knowledge_register_source → knowledge_sources_register
  remove_source             → knowledge_sources_delete
  refresh_source            → knowledge_sources_refresh

AC coverage:
  AC1 — 7 @mcp.tool functions renamed per matrix; __all__ updated to match
  AC2 — Non-tool knowledge_stats helper (L1209) renamed to private or removed
  AC3 — Agent allowlists and prose in knowledge-enricher.agent.md and
         knowledge-ingestor.agent.md use new tool names
  AC4 — No old tool names remain in the specified doc files
"""

from __future__ import annotations

import pathlib
import subprocess
import sys
from typing import ClassVar

from owlbear_mcp_knowledge import server
from owlbear_mcp_knowledge.server import mcp

# ---------------------------------------------------------------------------
# Rename matrix
# ---------------------------------------------------------------------------

_RENAME_MATRIX: dict[str, str] = {
    "search_knowledge": "knowledge_search",
    "list_sources": "knowledge_sources_list",
    "get_stats": "knowledge_stats",
    "ingest_document": "knowledge_ingest",
    "knowledge_register_source": "knowledge_sources_register",
    "remove_source": "knowledge_sources_delete",
    "refresh_source": "knowledge_sources_refresh",
}

_OLD_TOOL_NAMES: set[str] = set(_RENAME_MATRIX.keys())
_NEW_TOOL_NAMES: set[str] = set(_RENAME_MATRIX.values())


def _registered_tool_names() -> set[str]:
    """Return the set of tool names registered in the MCP server."""
    if hasattr(mcp, "_tool_manager"):
        return {
            getattr(t, "name", None)
            for t in mcp._tool_manager.list_tools()  # noqa: SLF001
        }
    return set()


# ---------------------------------------------------------------------------
# AC1 — 7 @mcp.tool functions renamed per matrix; __all__ updated
# ---------------------------------------------------------------------------


class TestFromAC_ToolRenames:
    """AC1: all 7 new tool names appear in __all__; all 7 old names are gone."""

    def test_new_tool_names_in_dunder_all(self) -> None:
        """All 7 target names must be present in server.__all__ after rename."""
        all_names = set(server.__all__)
        missing = _NEW_TOOL_NAMES - all_names
        assert not missing, f"New tool names missing from __all__: {sorted(missing)}"

    def test_old_tool_names_absent_from_dunder_all(self) -> None:
        """Pre-rename tool names must NOT appear in server.__all__."""
        all_names = set(server.__all__)
        still_present = _OLD_TOOL_NAMES & all_names
        assert not still_present, (
            f"Old (pre-rename) tool names still in __all__: {sorted(still_present)}"
        )

    def test_new_tool_names_in_mcp_registry(self) -> None:
        """All 7 new tool names must be present in the live MCP tool registry.

        Distinct from __all__ membership: a broken implementation could export
        new aliases in __all__ while the registry still contains the old names.
        """
        registry = _registered_tool_names()
        missing = _NEW_TOOL_NAMES - registry
        assert not missing, (
            f"New tool names missing from MCP registry: {sorted(missing)}. "
            f"Registry contains: {sorted(t for t in registry if t)}"
        )

    def test_old_tool_names_absent_from_mcp_registry(self) -> None:
        """Pre-rename tool names must NOT appear in the live MCP tool registry.

        Ensures the registry itself was updated, not just __all__ or module-level
        aliases — prevents silent stale-name registrations.
        """
        registry = _registered_tool_names()
        still_present = _OLD_TOOL_NAMES & registry
        assert not still_present, (
            f"Old (pre-rename) tool names still in MCP registry: {sorted(still_present)}"
        )


# ---------------------------------------------------------------------------
# AC2 — Non-tool knowledge_stats helper resolved (collision removed)
# ---------------------------------------------------------------------------


class TestFromAC_KnowledgeStatsCollision:
    """AC2: the old non-tool knowledge_stats helper is private/removed; the new
    knowledge_stats is a registered MCP tool (renamed from get_stats).
    """

    def test_knowledge_stats_is_registered_mcp_tool(self) -> None:
        """knowledge_stats must appear in the MCP tool registry.

        Before the rename, knowledge_stats is a non-tool helper function that
        returns a formatted string (not a tool). After the rename get_stats
        becomes knowledge_stats in the @mcp.tool registry and the old helper
        is privatised or removed.
        """
        tool_names = _registered_tool_names()
        assert "knowledge_stats" in tool_names, (
            "knowledge_stats is not registered as an MCP tool. "
            "The old non-tool helper at L1209 must be renamed/removed and "
            "get_stats must be renamed to knowledge_stats as an @mcp.tool."
        )

    def test_collision_helper_privatised(self) -> None:
        """Collision resolution: the pre-existing non-tool knowledge_stats helper
        must have been privatised as _legacy_graph_stats.

        Unconditional assert — no fallback branch. The builder chose privatisation
        (confirmed at server.py:1209). Any OR-branch logic here would be a
        tautology because knowledge_stats IS in the registry as the renamed MCP
        tool, making a "removed entirely" fallback condition always False.
        """
        assert hasattr(server, "_legacy_graph_stats"), (
            "_legacy_graph_stats does not exist in server module namespace. "
            "The pre-existing non-tool knowledge_stats helper must be privatised "
            "as _legacy_graph_stats to resolve the naming collision."
        )
        assert callable(server._legacy_graph_stats), (  # noqa: SLF001
            "server._legacy_graph_stats exists but is not callable."
        )


# ---------------------------------------------------------------------------
# AC3 — Agent files use new tool names (allowlists + prose)
# ---------------------------------------------------------------------------


class TestFromAC_AgentAllowlists:
    """AC3: neither agent file may reference any pre-rename tool name."""

    _ENRICHER = pathlib.Path("share/agents/knowledge-enricher.agent.md")
    _INGESTOR = pathlib.Path("share/agents/knowledge-ingestor.agent.md")

    def test_enricher_agent_no_old_tool_names(self) -> None:
        """knowledge-enricher.agent.md must not reference any old tool name."""
        content = self._ENRICHER.read_text()
        found = [name for name in _OLD_TOOL_NAMES if name in content]
        assert not found, (
            f"knowledge-enricher.agent.md still references old tool names: {sorted(found)}"
        )

    def test_ingestor_agent_no_old_tool_names(self) -> None:
        """knowledge-ingestor.agent.md must not reference any old tool name."""
        content = self._INGESTOR.read_text()
        found = [name for name in _OLD_TOOL_NAMES if name in content]
        assert not found, (
            f"knowledge-ingestor.agent.md still references old tool names: {sorted(found)}"
        )

    def test_enricher_agent_has_expected_new_tool_names(self) -> None:
        """knowledge-enricher.agent.md must contain the new tool names it references.

        Positive guard: absence-only tests pass even if references are deleted
        entirely. This asserts the expected new names are present in allowlist
        and/or prose so deletion-only regressions fail.
        """
        content = self._ENRICHER.read_text()
        # Enricher uses knowledge_search and knowledge_stats (renamed from
        # search_knowledge and get_stats respectively)
        expected = ["knowledge_search", "knowledge_stats"]
        missing = [name for name in expected if name not in content]
        assert not missing, (
            f"knowledge-enricher.agent.md is missing expected new tool names: {missing}"
        )

    def test_ingestor_agent_has_expected_new_tool_names(self) -> None:
        """knowledge-ingestor.agent.md must contain the new tool names it references.

        Positive guard: absence-only tests pass even if references are deleted
        entirely. This asserts the expected new names are present in allowlist
        and/or prose so deletion-only regressions fail.
        """
        content = self._INGESTOR.read_text()
        # Ingestor uses knowledge_ingest, knowledge_search, knowledge_sources_list,
        # knowledge_sources_refresh, and knowledge_stats
        expected = [
            "knowledge_ingest",
            "knowledge_search",
            "knowledge_sources_list",
            "knowledge_sources_refresh",
            "knowledge_stats",
        ]
        missing = [name for name in expected if name not in content]
        assert not missing, (
            f"knowledge-ingestor.agent.md is missing expected new tool names: {missing}"
        )


# ---------------------------------------------------------------------------
# AC4 — No old tool names remain in specified doc files
# ---------------------------------------------------------------------------


class TestFromAC_DocRefs:
    """AC4: the 6 specified doc files must not reference any pre-rename tool name."""

    _DOC_FILES: ClassVar[list[pathlib.Path]] = [
        pathlib.Path("serve/mcp-knowledge/README.md"),
        pathlib.Path("share/skills/h-knowledge-ops/SKILL.md"),
        pathlib.Path("setup/setup-guide.md"),
        pathlib.Path("share/skills/w-knowledge-enrichment/SKILL.md"),
        pathlib.Path("share/prompts/kb-enrich.prompt.md"),
        pathlib.Path("README.md"),
    ]

    def test_doc_files_contain_no_old_tool_names(self) -> None:
        """All 6 doc files must be free of pre-rename tool names."""
        violations: list[str] = []
        for doc_path in self._DOC_FILES:
            if not doc_path.exists():
                continue
            content = doc_path.read_text()
            for old_name in _OLD_TOOL_NAMES:
                if old_name in content:
                    violations.append(f"{doc_path}: {old_name!r}")
        assert not violations, (
            "Old tool names found in doc files:\n"
            + "\n".join(f"  {v}" for v in violations)
        )


# ---------------------------------------------------------------------------
# AC5 — All durable test suites updated to use new import names
# ---------------------------------------------------------------------------


class TestFromAC_DurableSuiteImports:
    """AC5: pytest collection succeeds on all 6 durable test files that import
    renamed MCP tool symbols from owlbear_mcp_knowledge.server.
    """

    _AFFECTED_SUITES: ClassVar[list[str]] = [
        "tests/test_search_provenance.py",
        "tests/test_register_source_1890.py",
        "tests/test_remove_source_1889.py",
        "tests/test_ingest_document_coordinator_1893.py",
        "tests/test_mcp_knowledge_read_tools_1881.py",
        "tests/test_mcp_knowledge_lifespan_1888.py",
        "tests/test_persistence_source_wiring.py",
    ]

    def test_all_affected_suites_collect_without_error(self) -> None:
        """pytest collection must succeed on all 6 durable test files.

        Before the builder updates stale imports in those files, collection fails
        with ImportError because the pre-rename symbols no longer exist in
        owlbear_mcp_knowledge.server. After the builder fixes the imports,
        collection succeeds.
        """
        workspace_root = pathlib.Path(__file__).parent.parent
        result = subprocess.run(  # noqa: S603
            [
                sys.executable,
                "-m",
                "pytest",
                "--collect-only",
                "--no-header",
                "-q",
                *self._AFFECTED_SUITES,
            ],
            capture_output=True,
            text=True,
            cwd=workspace_root,
        )
        assert result.returncode == 0, (
            "pytest collection failed on one or more durable test suites.\n"
            "These suites still import pre-rename MCP tool symbols that no longer "
            "exist in owlbear_mcp_knowledge.server.\n"
            f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
        )
