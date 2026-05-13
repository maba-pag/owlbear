---
id: 1520
title: 'P3-02: Implement MCP server ac/proof_bundle tool parameters'
status: in-progress
priority: needed
created: 2026-05-13T02:29:42.731951+00:00
updated: 2026-05-13T07:56:45.008505+00:00
tags:
  - phase-3
  - scope:mcp-kanban
  - tdd
  - feature
parent: 1514
depends_on:
  - 1519
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
Brief: see parent #1514

## Scope
In scope: Add ac/proof_bundle params to MCP create_task and edit_task tools; verify show_task auto-exposes new fields
Out of scope: Engine internals, migration, skill files

## Acceptance Criteria
- AC1: MCP `create_task` tool accepts `ac: list[str] | None` and `proof_bundle: str | None` params and passes them to engine `create_task()` when non-None
- AC2: MCP `edit_task` tool accepts `ac: list[str] | None`, `add_ac: list[str] | None`, `remove_ac: list[str] | None`, and `proof_bundle: str | None` params and maps them to engine `edit_task()` kwargs when non-None
- AC3: MCP `show_task` response includes `ac` (list[str]) and `proof_bundle` (str|None) fields from `TaskFull` model

Proof bundle: existing
Existing proof scope: tests/test_mcp_ac_params_1519.py
2026-05-13T07:56:07+00:00
## Architecture Review

### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Adds ac/proof_bundle params to MCP create_task and edit_task tools — one responsibility |
| Interface clarity | PASS | AC refined with explicit nullable types (`list[str] | None`, `str | None`) and forwarding semantics ("when non-None") per parent #1514 arch review note |
| Dependency correctness | PASS | #1519 archived/completed; #1518 (engine) archived/completed |
| Module layering | PASS | MCP server → AgentView → engine — standard downward dependency |
| TDD compliance | PASS | TDD partner #1519 provides 17 tests covering all 3 AC lines; de-escalated to `existing` |
| KISS/YAGNI | PASS | Pure passthrough — no new abstractions |
| Premise challenge | PASS | Required by parent AC6 ("MCP tools expose both fields") |
| Pattern consistency | PASS | Follows existing add_tag/remove_tag non-None forwarding pattern in server.py |
| Security surface | PASS | No new external boundaries; MCP tools are agent-internal |
| Single domain | PASS | scope:mcp-kanban only |

### AC Assessment
| AC Line | Assessment | Action |
|---------|-----------|--------|
| AC1 | Refined: added explicit types (`list[str] | None`, `str | None`), forwarding clause ("when non-None") | Types from parent #1514 arch review applied |
| AC2 | Refined: added explicit types for all 4 params; `add_ac: list[str] | None` (not `str` as Brief incorrectly specified) | Aligned with existing `add_tag: list[str]` pattern and #1519 arch review |
| AC3 | No change needed | ShowTaskResponse inherits from TaskFull → TaskSummary chain |

### Architecture Notes
- **Implementation already exists:** #1519's builder (commit 016f548e) implemented all server.py changes during GREEN phase. AC1-AC3 are already satisfied by committed code. This task's pipeline pass is a verification pass.
- **Existing test coverage:** `tests/test_mcp_ac_params_1519.py` has 17 tests covering handler signatures (inspect.signature), forwarding behavior (mock AgentView), and response model fields — all 3 AC lines are fully covered.
- **Schema model drift (observation):** `CreateTaskParams` and `EditTaskParams` in `serve/mcp-kanban/src/owlbear_mcp_kanban/models.py` lack `ac`/`proof_bundle` fields. These Pydantic models are NOT used at runtime (FastMCP derives tool schema from function signatures), but they serve as documented contracts with exact-field-set tests in `test_mcp_models.py`. The consolidation test (#1524) should verify schema model parity with handler signatures if this drift is not addressed here.

### Proof-Bundle Validation
- Planner assignment: behavioral
- Final bundle: existing (de-escalated — implementation and tests already complete from #1519's full pipeline pass)
- Existing proof scope: tests/test_mcp_ac_params_1519.py
- Test-writer: SKIP

### Design Diverge
- Trigger: skipped — single clear approach, implementation already committed

### Challenge Results
- Challenger: SKIPPED — proof bundle `existing`

### Verdict: APPROVE
### Action Taken: Refined AC2 with explicit types per parent arch review note. De-escalated proof bundle from `behavioral` to `existing` (17 tests in test_mcp_ac_params_1519.py already cover all AC). Advanced #1520 → todo.
2026-05-13T07:56:45+00:00
## Test-Writer Notes
- Proof bundle: existing — no new test writing required.
- Existing proof scope: tests/test_mcp_ac_params_1519.py (17 tests covering all 3 AC lines)
- AC coverage: AC1 (create_task ac/proof_bundle params), AC2 (edit_task ac/add_ac/remove_ac/proof_bundle params), AC3 (show_task response includes ac/proof_bundle fields) — all verified by #1519 tests.
- Passing through to builder.