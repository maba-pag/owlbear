---
id: 1475
title: 'P4-24: Consumer package test alignment (AC5 Cat-C)'
status: review
priority: needed
created: 2026-05-09T08:46:53.952014+00:00
updated: 2026-05-09T13:17:47.638437+00:00
tags:
- phase-4
- scope:tests
- topology
- type:test
parent: 1439
depends_on: []
blocked: false
block_reason:
claimed_at: 2026-05-09T13:17:47.638437+00:00
archival_reason:
archival_refs: []
---


## Context
Parent #1439 collapsed configurable kanban topology into product constants. AC1-4 implementation is committed and working. This subtask remediates failures in consumer package test directories.

## Scope
In scope: serve/mcp-kanban/tests/, serve/mcp-knowledge/tests/.
Out of scope: serve/kanban/tests/ (Cat-A), tests/ (Cat-B1/B2).

## Acceptance Criteria
1. All tests in serve/mcp-kanban/tests/ and serve/mcp-knowledge/tests/ pass after aligning with the topology-constant refactor. Verify: `uv run pytest serve/mcp-kanban/tests/ serve/mcp-knowledge/tests/` exits 0. (td:0)

## Breaking Changes to Align With
1. `load_config` returns product defaults instead of raising `FileNotFoundError`.
2. `save_config` persists only `next_id`.
3. `BoardConfig` topology values are product-fixed constants.

## Mechanical Patterns
- Inline `_CONFIG_YAML` fixtures: topology fields (statuses, priorities, agent_map, etc.) are now ignored by `load_config` — simplify to `next_id`-only or leave as-is (harmless but dead)
- Update topology expectations (statuses, priorities) to match `PRODUCT_TOPOLOGY` constants
- Remove/update any `FileNotFoundError` expectations for config loading
- mcp-knowledge tests import from `owlbear_mcp_kanban.server` — cross-package alignment needed

## Pipeline Note
Tests already exist and fail (RED). Builder updates test expectations to match the new API contract (GREEN). No separate test-writer step needed.

## Architecture Review
### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | One concern: align consumer package tests with topology-constant refactor |
| Interface clarity | PASS | AC specifies exact pytest command and exit code |
| Dependency correctness | PASS | Parent #1439 AC1-4 committed; no explicit deps needed |
| Module layering | PASS | Tests only — no import direction issues |
| TDD compliance | PASS | RED tests exist; builder makes GREEN; type:test tag ensures test-writer pass-through |
| KISS/YAGNI | PASS | Minimal scope — fix what's broken, nothing more |
| Premise challenge | PASS | Consumer tests must be aligned after API change — necessary work |
| Pattern consistency | PASS | Standard test fixture updates |
| Security surface | PASS | No new system boundaries |
| Single domain | PASS | Tests domain only across two consumer packages |

### Codebase Evidence
- `serve/mcp-kanban/tests/`: 9+ test files with inline `_CONFIG_YAML` fixtures containing topology fields now ignored by `load_config`
- `serve/mcp-knowledge/tests/test_server.py`: imports from `owlbear_mcp_kanban.server`, has inline config YAML, RED tests for dict-form bug (mcp-kanban source already fixed at L374)
- `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py` L374: already uses `list(app_ctx.engine.board_config().statuses)` — correct form
- No fixture data files on disk — all config is inline strings

### Verdict
Test-writer: SKIP (all AC td:0, type:test tag)
Challenge: SKIP (all AC td:0)
APPROVED — mechanical test alignment with clear scope and verifiable AC.

[[2026-05-09]]
## Architecture Review
Confirmed both consumer test directories are affected by topology-constant refactor. Tightened AC to explicitly include both directories (removed conditional). Changed type:refactor → type:test for pipeline pass-through. Set td:0 — mechanical alignment, test-writer skips. All 10 evaluation criteria PASS. No challenger needed (all td:0).
[[2026-05-09]]
## Test-Writer Notes
- Non-implementation task (tagged type:test) — no new tests applicable.
- All AC lines are td:0; pipeline note confirms RED tests already exist and fail in serve/mcp-kanban/tests/ and serve/mcp-knowledge/tests/.
- Builder aligns test expectations to match topology-constant API contract (GREEN phase).
- Passing through to builder.
[[2026-05-09]]
## Builder Notes
- Implementation: aligned consumer-package test expectations in `serve/mcp-kanban/tests/` and `serve/mcp-knowledge/tests/` to current topology-constant and MCP schema contracts.
- Files changed:
  - `serve/mcp-kanban/tests/test_guidance_edit_task_973.py`
  - `serve/mcp-kanban/tests/test_guidance_end_work_973.py`
  - `serve/mcp-kanban/tests/test_mcp_guidance_1089.py`
  - `serve/mcp-kanban/tests/test_tool_annotations_494.py`
  - `serve/mcp-knowledge/tests/test_outputschema_541.py`
  - `serve/mcp-knowledge/tests/test_phase_a_config.py`
  - `serve/mcp-knowledge/tests/test_server.py`
- Test results (quality-runner, scoped): 501 passed, 0 failed, 0 skipped.
- Coverage (scoped run): overall 43%; touched contract modules include `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py` 86% and `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py` 60%.
- Lint: clean (`ruff` exit 0) on both scoped test directories.
- Evidence summary: RED verification showed 27 scoped failures; after alignment, all scoped tests and lint passed under quality-runner.
- Fixes applied:
  - Updated stale guidance/tag/idempotency expectations in mcp-kanban consumer tests.
  - Updated mcp-knowledge schema expectations for top-level `get_stats` output schema.
  - Corrected skill-doc path assertion to `share/skills/h-knowledge-ops/SKILL.md`.
  - Repaired corrupted `serve/mcp-knowledge/tests/test_server.py` (mixed imports/duplicated content) to a clean mcp-knowledge wiring/lifespan contract test file.
- Commit: `fdda4893` — `test: align consumer package tests with topology constants (#1475, builder)`