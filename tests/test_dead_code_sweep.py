"""Failing tests for task #1296: Dead code sweep — remove Copilot CLI/ACP orchestrator
and owlbear-project.json infrastructure (integration-level checks).

These tests cover the parent-level AC items not tested by test_core_removal.py.
They verify the doc/skill reference cleanup (#1298) and diagram cleanup (#1299) scopes.

All tests must FAIL on the current codebase; they pass once all child tasks are done.

AC coverage:
  AC2  — test_no_serve_orchestrator_in_readme, test_no_serve_orchestrator_in_share_skills,
          test_no_serve_orchestrator_in_share_prompts
  AC3  — test_no_copilot_cli_in_readme, test_no_copilot_cli_in_github_instructions,
          test_no_copilot_cli_in_seed_github_instructions, test_no_copilot_cli_in_share_skills
  AC4  — test_no_acp_protocol_in_toml_files
  AC9  — test_doc_index_no_serve_orchestrator
  AC10 — test_mcp_topology_no_orchestrator_rect, test_mcp_topology_no_orchestrator_text_element,
          test_mcp_topology_no_acp_arrow, test_mcp_topology_no_acp_label,
          test_mcp_topology_no_dangling_binding_refs,
          test_project_overview_no_serve_orchestrator_text
"""

from __future__ import annotations

from pathlib import Path

_REPO_ROOT = Path(__file__).parent.parent

# IDs of elements being deleted from mcp-topology.excalidraw per #1299 scope.
_MCP_DELETED_IDS: frozenset[str] = frozenset(
    {"s1_orchestrator_rect", "s1_orchestrator_text", "s1_acp_arrow", "s1_acp_label"}
)

# Directories excluded from "Copilot CLI" / "serve/orchestrator" grep checks per AC.
# AC3 (refined by arch-review retry): .owlbear/decisions and .owlbear/sources added —
# historical architecture decisions and bibliographic source entries are intentionally preserved.
_EXCLUDED_DIRS = frozenset(
    {
        _REPO_ROOT / ".owlbear" / "research",
        _REPO_ROOT / ".owlbear" / "kanban",
        _REPO_ROOT / ".owlbear" / "scratch",
        _REPO_ROOT / ".owlbear" / "briefs",
        _REPO_ROOT / ".owlbear" / "decisions",
        _REPO_ROOT / ".owlbear" / "sources",
    }
)

# Directories to skip in repo-wide file scans (generated / VCS / vendored).
_SCAN_SKIP_DIRS: frozenset[str] = frozenset(
    {".git", ".venv", "node_modules", "__pycache__", "dist", "build", ".pytest_cache"}
)


def _is_excluded(path: Path) -> bool:
    """Return True if *path* lives inside any of the excluded dirs."""
    for excl in _EXCLUDED_DIRS:
        try:
            path.relative_to(excl)
        except ValueError:
            pass
        else:
            return True
    return False
