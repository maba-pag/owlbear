"""Prove dev-code MCP runtime before main sync (#1347).

(a) Why editor-runtime MCP success via '../owlbear' does not prove dev-source readiness:
    The dev workspace MCP config launches MCP servers with ``uv --project ../owlbear``,
    pointing at the sibling *consumer* checkout. That path is stale relative to dev and
    does not exercise current dev source. A successful MCP tool call in the editor only
    proves the consumer overlay works — not that the dev code is sync-ready.

(b) Seed-placeholder MCP config and dev-code validation are separate concerns:
    ``seed/.vscode/mcp.json`` ships a placeholder config for new consumer checkouts.
    It has nothing to do with validating dev source. These tests run against dev source
    directly and must never parse or depend on any ``.vscode/mcp.json`` file at runtime.

(c) Updating EXPECTED_TOOLS is required when the deployment contract changes:
    ``EXPECTED_TOOLS`` in this file is the authoritative deployment-contract snapshot.
    When a tool is intentionally added or removed, update EXPECTED_TOOLS in the same
    commit that modifies the tool registration in server.py. A drift between the two
    constitutes a broken contract and will fail this test.

AC1 (td:2): app_lifespan starts against isolated temp board fixture; yields AppContext.
AC2 (td:1): owlbear_mcp_kanban.__file__ resolves under the repo working tree.
AC3 (td:1): Live tool registry (post-lifespan, no exclusions) == EXPECTED_TOOLS exactly.
AC4 (td:1): end_work published parameter schema includes all 5 outcome values.
AC5-AC7: td:0 — no executable tests.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

import owlbear_mcp_kanban
from owlbear_mcp_kanban.server import AppContext, app_lifespan, mcp

# ---------------------------------------------------------------------------
# Deployment-contract snapshot
# UPDATE THIS SET (and server.py) together when tools are added or removed.
# ---------------------------------------------------------------------------

EXPECTED_TOOLS: frozenset[str] = frozenset(
    {
        "list_tasks",
        "show_task",
        "create_task",
        "create_dr",
        "resolve_drs",
        "move_task",
        "edit_task",
        "start_work",
        "end_work",
        "pick_tasks",
    }
)

EXPECTED_OUTCOMES: frozenset[str] = frozenset(
    {"success", "fail", "reject", "block", "release"}
)

# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

_CONFIG_YAML = """\
version: 10
board:
  name: TestBoard
tasks_dir: tasks
statuses:
- name: research
- name: backlog
- name: todo
- name: in-progress
- name: review
- name: docs
- name: done
priorities:
- someday
- nice-to-have
- important
- needed
- critical
defaults:
  status: research
  priority: important
claim_timeout: 1h
next_id: 1
archive_dir: archive
activity_log: false
agent_map:
  research: researcher
  backlog: architect
  todo: test-writer
  in-progress: builder
  review: reviewer
  docs: doc-writer
  done: auditor
agent_types: {}
agent_compatibility: {}
non_impl_tags: []
archival_reasons: [completed, deprecated, dropped, duplicate, wontfix]
status_predicates: {}
"""


def _make_board(base_dir: Path) -> Path:
    """Create a minimal valid kanban board under *base_dir* and return its path."""
    kanban_dir = base_dir / "board"
    kanban_dir.mkdir(parents=True, exist_ok=True)
    (kanban_dir / "config.yml").write_text(_CONFIG_YAML, encoding="utf-8")
    (kanban_dir / "tasks").mkdir(exist_ok=True)
    (kanban_dir / "archive").mkdir(exist_ok=True)
    return kanban_dir


def _server_mock() -> MagicMock:
    """Minimal FastMCP mock — only ``remove_tool`` is called by _apply_tool_exclusions."""
    server = MagicMock()
    server.remove_tool.side_effect = Exception("no tool")
    return server


def _find_repo_root() -> Path:
    """Walk up from this test file until a pyproject.toml sentinel is found."""
    current = Path(__file__).resolve().parent
    for _ in range(10):
        if (current / "pyproject.toml").exists():
            return current
        parent = current.parent
        if parent == current:
            break
        current = parent
    raise RuntimeError(
        f"Could not locate repo root from {Path(__file__).resolve()!r}. "
        "Expected a pyproject.toml file in an ancestor directory."
    )


# ---------------------------------------------------------------------------
# AC1 — lifespan startup against isolated temp board
# ---------------------------------------------------------------------------


class TestFromAC_LifespanStartup:
    """AC1: app_lifespan starts against an isolated temp board and yields AppContext."""

    @pytest.mark.asyncio
    async def test_lifespan_yields_app_context_with_temp_board(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """AC1: lifespan starts successfully with a valid temp board and yields AppContext."""
        board = _make_board(tmp_path)
        monkeypatch.setenv("KANBAN_DIR", str(board))
        monkeypatch.delenv("KANBAN_TOOLS_EXCLUDE", raising=False)

        async with app_lifespan(_server_mock()) as ctx:
            assert isinstance(ctx, AppContext), (
                f"app_lifespan must yield AppContext, got {type(ctx).__name__!r}"
            )

    @pytest.mark.asyncio
    async def test_app_context_exposes_engine_and_resolved_kanban_dir(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """AC1: AppContext carries a KanbanEngine and an absolute kanban_dir pointing to the board."""
        from owlbear_kanban import KanbanEngine

        board = _make_board(tmp_path)
        monkeypatch.setenv("KANBAN_DIR", str(board))
        monkeypatch.delenv("KANBAN_TOOLS_EXCLUDE", raising=False)

        async with app_lifespan(_server_mock()) as ctx:
            assert isinstance(ctx.engine, KanbanEngine), (
                f"AppContext.engine must be a KanbanEngine, got {type(ctx.engine).__name__!r}"
            )
            assert ctx.kanban_dir == board.resolve(), (
                f"AppContext.kanban_dir must equal {board.resolve()!r}, "
                f"got {ctx.kanban_dir!r}"
            )


# ---------------------------------------------------------------------------
# AC2 — module source origin
# ---------------------------------------------------------------------------


class TestFromAC_ModuleSourceOrigin:
    """AC2: owlbear_mcp_kanban.__file__ resolves under the dev repo working tree."""

    def test_module_file_resolves_under_repo_working_tree(self) -> None:
        """AC2: Imported module must live under the dev repo tree, not a consumer checkout.

        Uses this test file's own __file__ parent chain to derive the repo root —
        no hardcoded paths. Fails when the module was loaded from a sibling consumer
        checkout (``../owlbear``) or a non-dev installation.
        """
        repo_root = _find_repo_root()
        module_path = Path(owlbear_mcp_kanban.__file__).resolve()
        assert module_path.is_relative_to(repo_root), (
            f"owlbear_mcp_kanban resolves to {module_path!r}, which is NOT under "
            f"the repo root {repo_root!r}. "
            "This indicates the module was loaded from a sibling consumer checkout "
            "('../owlbear') or a non-dev installation instead of the dev source tree."
        )


# ---------------------------------------------------------------------------
# AC3 — tool registry contract
# ---------------------------------------------------------------------------


class TestFromAC_ToolRegistryContract:
    """AC3: Live registry (post-lifespan, no exclusions) matches EXPECTED_TOOLS exactly."""

    @pytest.mark.asyncio
    async def test_live_registry_contains_exactly_nine_tools(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """AC3: After lifespan with KANBAN_TOOLS_EXCLUDE unset, tool set == EXPECTED_TOOLS.

        Runs app_lifespan (not just module import) because _apply_tool_exclusions
        executes at lifespan time. With no exclusions, the full deployment contract
        must be intact. Introspects mcp._tool_manager._tools — the established pattern
        in test_tool_annotations_494.py, test_mcp_create_dr_1182.py, etc.
        """
        board = _make_board(tmp_path)
        monkeypatch.setenv("KANBAN_DIR", str(board))
        monkeypatch.delenv("KANBAN_TOOLS_EXCLUDE", raising=False)

        # _server_mock() is used to avoid permanently mutating the mcp singleton;
        # with no exclusions _apply_tool_exclusions is a no-op regardless.
        async with app_lifespan(_server_mock()):
            registered = frozenset(
                t.name
                for t in mcp._tool_manager._tools.values()  # noqa: SLF001
            )

        assert registered == EXPECTED_TOOLS, (
            f"Tool registry mismatch after lifespan. "
            f"Missing from registry: {EXPECTED_TOOLS - registered!r}. "
            f"Unexpected in registry: {registered - EXPECTED_TOOLS!r}. "
            "Update EXPECTED_TOOLS in this file when tools are intentionally "
            "added or removed from server.py."
        )


# ---------------------------------------------------------------------------
# AC4 — end_work outcome schema
# ---------------------------------------------------------------------------


class TestFromAC_EndWorkOutcomeSchema:
    """AC4: end_work published parameter schema (post-_patch_params) includes all 5 outcomes."""

    def test_end_work_published_outcome_schema_includes_all_five_values(self) -> None:
        """AC4: mcp._tool_manager._tools['end_work'].parameters exposes all 5 outcome values.

        Checks the published MCP schema — what MCP clients receive — NOT the Python
        function signature. _patch_params mutates the schema at module scope; this test
        runs after import so post-mutation state is captured. The schema may encode
        allowed values as ``enum`` or ``anyOf`` branches; both forms are accepted.
        """
        tool = next(
            (t for t in mcp._tool_manager._tools.values() if t.name == "end_work"),  # noqa: SLF001
            None,
        )
        assert tool is not None, "end_work must be registered in the MCP tool registry"

        outcome_prop = tool.parameters.get("properties", {}).get("outcome", {})

        # Collect string literals from the schema subtree (enum or anyOf/const forms).
        actual_values: set[str] = set()
        if "enum" in outcome_prop:
            actual_values.update(v for v in outcome_prop["enum"] if isinstance(v, str))
        if "anyOf" in outcome_prop:
            for branch in outcome_prop["anyOf"]:
                if "const" in branch and isinstance(branch["const"], str):
                    actual_values.add(branch["const"])
                if "enum" in branch:
                    actual_values.update(
                        v for v in branch["enum"] if isinstance(v, str)
                    )

        assert actual_values >= EXPECTED_OUTCOMES, (
            f"end_work outcome schema is missing values: "
            f"{EXPECTED_OUTCOMES - actual_values!r}. "
            f"Found values: {actual_values!r}. "
            f"Raw 'outcome' property schema: {outcome_prop!r}"
        )
