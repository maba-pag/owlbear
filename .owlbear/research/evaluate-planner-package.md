# Evaluate and Clean Up Orchestrator planner/ Package

> **Owning task:** #624 — Evaluate and clean up orchestrator planner/ package
> **Date:** 2026-04-05 **Status:** Complete

## 1. Context and Question

Task #624 determines whether `serve/orchestrator/src/owlbear/planner/` can be removed now that `pick_tasks` MCP tool (#621) replicates its gate/selector logic in `serve/mcp-kanban/`. The AC specifies: if pick_tasks fully replaces the Python code, remove it; if loop.py still imports directly, keep and document.

## 2. Sources Studied

| # | Source | Rel. | What taken |
|---|--------|:----:|------------|
| S1 | `serve/mcp-kanban/.../server.py` L510-580 | .95 | pick_tasks impl: _check_pick_gates, sort, cap — full gate+selector replica |
| S2 | `serve/orchestrator/.../loop.py` L17-18, L383-385 | .95 | Direct `read_board`, `select_tasks` imports — active in-process usage |
| S3 | `serve/orchestrator/.../cli.py` L15-16, L54-91 | .95 | Same imports — CLI dispatch entry point |
| S4 | `serve/orchestrator/.../waves.py` L12 | .90 | `DispatchEntry` model import from planner |
| S5 | `serve/orchestrator/.../planner/` (all 5 files) | .90 | Package contents: board.py, gates.py, models.py, selector.py, __init__.py |
| S6 | `.owlbear/research/migrate-dispatcher-to-pick-tasks.md` §3.3 | .95 | Prior analysis: "planner/ CANNOT be removed" — same conclusion |
| S7 | 8 test files importing from planner | .85 | test_planner_board, test_planner_gates, test_planner_gates_selector, test_cli, etc. |
| S8 | #619 parent task body (arch review + research) | .90 | Pre-determined: "keep planner/, dual-path comment" |

## 3. Analysis

### 3.1 pick_tasks Coverage of planner/ Logic

| planner/ module | Function | pick_tasks equivalent | Coverage |
|----------------|----------|----------------------|----------|
| gates.py | check_atomicity | _PICK_AND_PATTERN regex | Complete |
| gates.py | check_tdd | status == "in-progress" + body check | Complete |
| gates.py | check_clarity | _PICK_CLARITY_STATUSES + _PICK_AC_PATTERN | Complete |
| gates.py | check_gates (composite) | _check_pick_gates | Complete |
| selector.py | PRIORITY_RANK | _PICK_PRIORITY_RANK (identical values) | Complete |
| selector.py | STATUS_RANK | _PICK_STATUS_RANK (identical values) | Complete |
| selector.py | select_tasks sort+cap | pick_tasks sort+cap (limit param) | Complete |
| selector.py | STATUS_AGENT_MAP | NOT migrated (orchestrator responsibility) | By design |
| selector.py | DECOMP routing | NOT migrated (orchestrator show_task post-filter) | By design |
| board.py | read_board | _run_kanban with same CLI flags | Complete |
| models.py | Task, DispatchEntry, etc. | Not needed — pick_tasks uses raw dicts | By design |

**pick_tasks fully replaces gate+selector+board logic for the MCP path.** Agent mapping and DECOMP routing intentionally stay in the orchestrator layer.

### 3.2 Active Consumers of planner/ Package

| Consumer | File | Imports | Purpose |
|----------|------|---------|---------|
| loop.py | orchestrator/loop.py L17-18, L383-385 | read_board, select_tasks | Headless ACP dispatch loop |
| cli.py | cli.py L15-16, L54-91 | read_board, select_tasks | CLI dispatch trigger |
| waves.py | orchestrator/waves.py L12 | DispatchEntry | Wave assembly data model |
| 8 test files | tests/test_planner_*.py, test_cli.py, etc. | Various planner imports | Unit + integration tests |

**All consumers are in the headless orchestrator path** (ACP mode), not the VS Code agent path. These imports are load-bearing — removal would break the headless loop and 20+ tests.

### 3.3 Dual-Path Architecture

| Path | Consumer | Task selection | planner/ dep |
|------|----------|---------------|-------------|
| Agent mode | orchestrator.agent.md (VS Code) | pick_tasks MCP tool | None |
| Headless mode | loop.py / cli.py (ACP) | planner.select_tasks() in-process | Required |

Both paths coexist. The MCP tool serves agents; the in-process code serves the ACP loop.

## 4. Recommendation (.95 confidence)

**Keep planner/ package. Add dual-path documentation comment.** This follows the "If kept" AC path.

Rationale:
- loop.py, cli.py, waves.py all have active imports — removal breaks the headless loop
- 8+ test files import from planner — removal breaks the test suite
- #619 research (§3.3) reached the same conclusion
- #619 arch review explicitly states: "planner/ package CANNOT be removed"

Implementation scope (for builder when #624 reaches in-progress):
- Add docstring/comment in `planner/__init__.py` explaining dual-path with link to #619
- No file removals, no import changes, no dead code cleanup

Challenge: SKIP — answer pre-determined by #619 research and arch review; no decision to challenge.

Tier: **T1 (Autonomous)** — no new capability, no architecture change, documenting existing design.

## 5. Follow-up Tasks

None needed. The implementation (adding dual-path comment) is #624's own AC. Parent task #619 body already documents the decision. No additional follow-up tasks required.
