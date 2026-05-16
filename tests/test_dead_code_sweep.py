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

import json
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


class TestFromAC_DeadCodeSweep:
    """Integration-level checks: AC2, AC3, AC4, AC9, AC10 of parent task #1296."""

    # ---- AC2: serve/orchestrator absent from doc and skill files ------------

    # ---- AC2 (wide): serve/orchestrator absent from full repo surface --------

    def test_no_serve_orchestrator_repo_wide(self) -> None:
        """No non-excluded, non-test file in the repo may reference 'serve/orchestrator'.

        Wider than the per-file spot checks below — enforces the full AC2 surface.
        tests/ is excluded because test files that assert absence of a string
        necessarily contain that string; import-level boundaries are enforced
        separately by test_package_boundary.py.
        """
        tests_dir = _REPO_ROOT / "tests"
        hits: list[str] = []
        for p in _REPO_ROOT.rglob("*"):
            if not p.is_file():
                continue
            rel = p.relative_to(_REPO_ROOT)
            if any(part in _SCAN_SKIP_DIRS for part in rel.parts):
                continue
            if _is_excluded(p):
                continue
            try:
                rel.relative_to(tests_dir.relative_to(_REPO_ROOT))
            except ValueError:
                pass
            else:
                continue  # skip tests/ directory
            try:
                text = p.read_text(encoding="utf-8")
            except (UnicodeDecodeError, OSError):
                continue
            if "serve/orchestrator" in text:
                hits.append(str(rel))
        assert hits == [], f"Files still reference 'serve/orchestrator': {hits}"

    # ---- AC2 (spot checks): serve/orchestrator absent from doc/skill files --

    def test_no_serve_orchestrator_in_readme(self) -> None:
        """README.md must not reference serve/orchestrator after sweep."""
        text = (_REPO_ROOT / "README.md").read_text(encoding="utf-8")
        assert "serve/orchestrator" not in text

    def test_no_serve_orchestrator_in_share_skills(self) -> None:
        """No *.md file in share/skills/ may reference serve/orchestrator."""
        hits = [
            str(p)
            for p in (_REPO_ROOT / "share" / "skills").rglob("*.md")
            if "serve/orchestrator" in p.read_text(encoding="utf-8")
        ]
        assert hits == [], f"share/skills/ files still reference serve/orchestrator: {hits}"

    def test_no_serve_orchestrator_in_share_prompts(self) -> None:
        """No *.md file in share/prompts/ may reference serve/orchestrator."""
        hits = [
            str(p)
            for p in (_REPO_ROOT / "share" / "prompts").rglob("*.md")
            if "serve/orchestrator" in p.read_text(encoding="utf-8")
        ]
        assert hits == [], f"share/prompts/ files still reference serve/orchestrator: {hits}"

    # ---- AC3: Copilot CLI zero hits in *.md outside excluded paths ----------

    # ---- AC3 (wide): Copilot CLI absent from all *.md files repo-wide ---------

    def test_no_copilot_cli_in_md_files_repo_wide(self) -> None:
        """No *.md file outside excluded dirs may contain 'Copilot CLI'.

        Enforces the full AC3 surface: all Markdown files repo-wide except
        .owlbear/{research,kanban,scratch,briefs,decisions,sources}/ and
        generated/VCS dirs.
        """
        hits = [
            str(p.relative_to(_REPO_ROOT))
            for p in _REPO_ROOT.rglob("*.md")
            if not _is_excluded(p)
            and not any(part in _SCAN_SKIP_DIRS for part in p.relative_to(_REPO_ROOT).parts)
            and "Copilot CLI" in p.read_text(encoding="utf-8")
        ]
        assert hits == [], f"*.md files still contain 'Copilot CLI': {hits}"

    # ---- AC3 (spot checks): Copilot CLI absent from key doc surfaces ----------

    def test_no_copilot_cli_in_readme(self) -> None:
        """README.md must not contain 'Copilot CLI'."""
        text = (_REPO_ROOT / "README.md").read_text(encoding="utf-8")
        assert "Copilot CLI" not in text

    def test_no_copilot_cli_in_github_instructions(self) -> None:
        """.github/copilot-instructions.md must not contain 'Copilot CLI'."""
        path = _REPO_ROOT / ".github" / "copilot-instructions.md"
        assert "Copilot CLI" not in path.read_text(encoding="utf-8")

    def test_no_copilot_cli_in_seed_github_instructions(self) -> None:
        """seed/.github/copilot-instructions.md must not contain 'Copilot CLI'."""
        path = _REPO_ROOT / "seed" / ".github" / "copilot-instructions.md"
        assert "Copilot CLI" not in path.read_text(encoding="utf-8")

    def test_no_copilot_cli_in_share_skills(self) -> None:
        """No *.md file in share/skills/ may contain 'Copilot CLI'."""
        hits = [
            str(p)
            for p in (_REPO_ROOT / "share" / "skills").rglob("*.md")
            if not _is_excluded(p) and "Copilot CLI" in p.read_text(encoding="utf-8")
        ]
        assert hits == [], f"share/skills/ files still contain 'Copilot CLI': {hits}"

    # ---- AC4: agent-client-protocol absent from all *.toml files ------------

    def test_no_acp_protocol_in_toml_files(self) -> None:
        """No *.toml file outside excluded dirs may contain 'agent-client-protocol'."""
        hits = [
            str(p)
            for p in _REPO_ROOT.rglob("*.toml")
            if not _is_excluded(p) and "agent-client-protocol" in p.read_text(encoding="utf-8")
        ]
        assert hits == [], f"*.toml files still reference agent-client-protocol: {hits}"

    # ---- AC9: doc-index regenerated without orchestrator refs ---------------

    def test_doc_index_no_serve_orchestrator(self) -> None:
        """.owlbear/doc-index.md must not reference serve/orchestrator after regen."""
        doc_index = _REPO_ROOT / ".owlbear" / "doc-index.md"
        assert doc_index.exists(), ".owlbear/doc-index.md not found"
        assert "serve/orchestrator" not in doc_index.read_text(encoding="utf-8")

    # ---- AC10: mcp-topology.excalidraw — deleted elements removed -----------

    def test_mcp_topology_no_orchestrator_rect(self) -> None:
        """mcp-topology.excalidraw must not contain the s1_orchestrator_rect element."""
        path = _REPO_ROOT / "share" / "diagrams" / "mcp-topology.excalidraw"
        data = json.loads(path.read_text(encoding="utf-8"))
        ids = {elem.get("id") for elem in data.get("elements", [])}
        assert "s1_orchestrator_rect" not in ids

    def test_mcp_topology_no_orchestrator_text_element(self) -> None:
        """mcp-topology.excalidraw must not contain the s1_orchestrator_text element."""
        path = _REPO_ROOT / "share" / "diagrams" / "mcp-topology.excalidraw"
        data = json.loads(path.read_text(encoding="utf-8"))
        ids = {elem.get("id") for elem in data.get("elements", [])}
        assert "s1_orchestrator_text" not in ids

    def test_mcp_topology_no_acp_arrow(self) -> None:
        """mcp-topology.excalidraw must not contain the s1_acp_arrow element."""
        path = _REPO_ROOT / "share" / "diagrams" / "mcp-topology.excalidraw"
        data = json.loads(path.read_text(encoding="utf-8"))
        ids = {elem.get("id") for elem in data.get("elements", [])}
        assert "s1_acp_arrow" not in ids

    def test_mcp_topology_no_acp_label(self) -> None:
        """mcp-topology.excalidraw must not contain the s1_acp_label element."""
        path = _REPO_ROOT / "share" / "diagrams" / "mcp-topology.excalidraw"
        data = json.loads(path.read_text(encoding="utf-8"))
        ids = {elem.get("id") for elem in data.get("elements", [])}
        assert "s1_acp_label" not in ids

    def test_mcp_topology_no_dangling_binding_refs(self) -> None:
        """Surviving elements in mcp-topology.excalidraw must not reference deleted IDs.

        After deletion of {s1_orchestrator_rect, s1_orchestrator_text, s1_acp_arrow,
        s1_acp_label}, any element NOT in that set must have its boundElements,
        startBinding, endBinding, and containerId cleaned of those IDs.
        """
        path = _REPO_ROOT / "share" / "diagrams" / "mcp-topology.excalidraw"
        data = json.loads(path.read_text(encoding="utf-8"))
        dangling: list[str] = []
        for elem in data.get("elements", []):
            eid = elem.get("id", "")
            if eid in _MCP_DELETED_IDS:
                continue  # skip the elements being deleted themselves
            # boundElements array
            for ref in elem.get("boundElements") or []:
                if ref.get("id") in _MCP_DELETED_IDS:
                    dangling.append(f"element '{eid}' boundElements refs deleted id '{ref.get('id')}'")
            # startBinding / endBinding
            for binding_key in ("startBinding", "endBinding"):
                binding = elem.get(binding_key)
                if isinstance(binding, dict) and binding.get("elementId") in _MCP_DELETED_IDS:
                    dangling.append(f"element '{eid}' {binding_key}.elementId '{binding.get('elementId')}'")
            # containerId
            if elem.get("containerId") in _MCP_DELETED_IDS:
                dangling.append(f"element '{eid}' containerId '{elem.get('containerId')}'")
        assert dangling == [], f"Dangling binding refs found in mcp-topology.excalidraw: {dangling}"

    # ---- AC10: project-overview.excalidraw — no serve/orchestrator text -----

    def test_project_overview_no_serve_orchestrator_text(self) -> None:
        """project-overview.excalidraw must not contain 'serve/orchestrator' in element text."""
        path = _REPO_ROOT / "share" / "diagrams" / "project-overview.excalidraw"
        data = json.loads(path.read_text(encoding="utf-8"))
        hits = [
            elem.get("id", "<unknown>")
            for elem in data.get("elements", [])
            if "serve/orchestrator" in elem.get("text", "") or "serve/orchestrator" in elem.get("originalText", "")
        ]
        assert hits == [], f"project-overview.excalidraw elements still contain 'serve/orchestrator': {hits}"
