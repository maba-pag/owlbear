---
id: 1528
title: 'P2-01: MCP integration test for start_work guidance passthrough (AC4)'
status: archived
priority: medium
created: 2026-05-13T12:18:01.416962+00:00
updated: 2026-05-13T16:57:01.537988+00:00
tags:
  - phase-2
  - scope:mcp-kanban
  - test
parent: 1525
depends_on:
  - 1527
blocked: false
block_reason:
claimed_at:
archival_reason: completed
archival_refs: []
---
## Summary

Write MCP integration test in `serve/mcp-kanban/tests/` verifying that dep-status guidance from `agent_view.start_work()` passes through the MCP `start_work` tool handler verbatim.

Brief: see parent #1525

## Acceptance Criteria

- AC4: MCP `start_work` tool response contains the exact guidance string returned by `agent_view.start_work()` (exact-value assertion, not substring)

## Scope

- In scope: MCP-layer integration test in `serve/mcp-kanban/tests/` for guidance passthrough
- Out of scope: agent_view unit tests (covered by #1526), consolidation tests

## Context

- MCP handler at `server.py` L520 calls `agent_view().start_work(resolved_id)` and maps result via `_to_single_task_response()`
- Current handler has `collect_guidance("start_work", ...)` fallback when `result.guidance` is empty — dep guidance will be non-empty so this path is skipped for blocked deps

Proof bundle: existing
Existing proof scope: serve/mcp-kanban/tests/test_guidance.py::TestFromAC_GuidanceProofRepair::test_start_work_guidance_sentinel_passthrough, serve/mcp-kanban/tests/test_guidance.py::TestFromAC_GuidanceDiscriminating_1475::test_start_work_agentview_guidance_not_overwritten_by_collect_guidance

## Research
- Research doc: .owlbear/research/mcp-start-work-guidance-passthrough.md
- Sources: 6 studied, 3 high-relevance (all codebase-internal)
- Recommendation: Add one test to `TestFromAC_StartWorkAdapter` in `test_mcp_lifecycle_tools.py` — mock `agent_view.start_work()` to return `SingleTaskResponse` with pre-populated guidance, assert exact-value match (confidence: 0.92)
- Follow-up tasks created: none (task itself advances to backlog for test-writer)
- Decision requests: none

## Challenge Results
- Challenger: FALLBACK — trivial T1 test-structure research, challenger overkill
- Confidence in original: 0.92
- Key finding: guidance passthrough is guaranteed by 3 mechanisms — isinstance pass-through in `_to_single_task_response()`, `if not result.guidance:` guard, and no field transformation between layers

## Architecture Review
### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Single contract assertion: guidance passthrough at MCP boundary |
| Interface clarity | PASS | AC4 specifies exact-value assertion, field is `guidance: list[str]` |
| Dependency correctness | PASS | #1527 archived/completed — dep-status guidance implementation landed |
| Module layering | PASS | Test in `serve/mcp-kanban/tests/`, tests MCP layer only |
| TDD compliance | PASS | This IS the test task; existing proof already satisfies AC |
| KISS/YAGNI | PASS | No new code needed — existing tests cover the contract |
| Premise challenge | PASS (existing coverage) | `test_guidance.py` already contains 2 tests proving AC4 — sentinel passthrough + non-overwrite guard |
| Pattern consistency | PASS | Existing tests follow established MCP guidance test patterns |
| Security surface | PASS | No new system boundaries |
| Single domain | PASS | MCP kanban domain only |

### Challenge Results
- Challenger: reconsider (0.72)
- Key findings: (1) Existing `test_guidance.py` tests at L1278-1293 and L1440-1467 already cover AC4 exactly — sentinel passthrough + non-overwrite assertion; (2) AC says "exact guidance string" but type is `list[str]` — minor terminology gap; (3) Consolidation-test gap: no gap (#1530 exists)
- Architect response: ACCEPTED finding (1) — verified existing coverage satisfies AC4 completely. Proof bundle de-escalated from `behavioral` to `existing`. Finding (2) is cosmetic — "exact guidance string" is testable via list equality. Finding (3) confirmed no gap.

### Proof-Bundle Validation
- Planner assignment: behavioral
- Final bundle: existing (de-escalated — existing test suite already covers AC4 via sentinel passthrough and non-overwrite assertions)
- Existing proof scope: serve/mcp-kanban/tests/test_guidance.py::TestFromAC_GuidanceProofRepair::test_start_work_guidance_sentinel_passthrough, serve/mcp-kanban/tests/test_guidance.py::TestFromAC_GuidanceDiscriminating_1475::test_start_work_agentview_guidance_not_overwritten_by_collect_guidance
- Test-writer: SKIP (bundle `existing`)

### Verdict: APPROVE (REFINE path — proof bundle de-escalated to `existing` with named tests)
### Action Taken: De-escalated proof bundle from `behavioral` to `existing` after discovering live test suite already covers AC4. Named existing proof scope. Advanced to todo.
2026-05-13T16:33:46+00:00
Architecture review complete. Challenger surfaced existing coverage in test_guidance.py that already satisfies AC4 (sentinel passthrough + non-overwrite guard). Proof bundle de-escalated from behavioral to existing. All 10 criteria pass. Advanced to todo.
2026-05-13T16:34:30+00:00
## Test-Writer Notes
- Proof bundle: existing — no new test writing required.
- Existing proof scope (named by architect):
  - `serve/mcp-kanban/tests/test_guidance.py::TestFromAC_GuidanceProofRepair::test_start_work_guidance_sentinel_passthrough`
  - `serve/mcp-kanban/tests/test_guidance.py::TestFromAC_GuidanceDiscriminating_1475::test_start_work_agentview_guidance_not_overwritten_by_collect_guidance`
- AC4 coverage already satisfied: sentinel passthrough + non-overwrite guard assertions cover exact guidance passthrough at MCP boundary.
- Also tagged `test` — dual pass-through signal (Step 1a + Step 1d).
- Passing through to builder.
2026-05-13T16:38:29+00:00
## Builder Notes
- Implementation: no code changes (proof-bundle existing pass-through)
- Tests: 2 existing proof tests passed
  - serve/mcp-kanban/tests/test_guidance.py::TestFromAC_GuidanceProofRepair::test_start_work_guidance_sentinel_passthrough
  - serve/mcp-kanban/tests/test_guidance.py::TestFromAC_GuidanceDiscriminating_1475::test_start_work_agentview_guidance_not_overwritten_by_collect_guidance
- Coverage: not required for existing-proof pass-through
- ruff: clean (serve/mcp-kanban/tests/test_guidance.py)
- Evidence summary: quality-runner scoped run reported pytest=0 with passed=2 failed=none, and ruff clean=true.
- Fixes applied: none required; AC4 already satisfied by named existing tests and verified in this run.
2026-05-13T16:49:15+00:00
## Review Evidence
- Verdict: PASS
- PASS confirmation (one line): PASS #1528 -> docs | AC mapped to code and evidence sufficient.
- AC evidence map:

| AC Line | Code Evidence | Test Evidence | Status |
|---|---|---|---|
| AC4 | `serve/kanban/src/owlbear_kanban/agent_view.py:962-1047` originates the `guidance` list and returns it in `SingleTaskResponse`; `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py:321-322` preserves a `SingleTaskResponse` unchanged in `_to_single_task_response()`, and `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py:577-578` only falls back to `collect_guidance("start_work", ...)` when `result.guidance` is empty. | `serve/mcp-kanban/tests/test_guidance.py:1255` defines a one-element sentinel list, `serve/mcp-kanban/tests/test_guidance.py:1278-1294` asserts `result.guidance == self._SENTINEL` on the direct `AgentView.start_work()` passthrough branch, and `serve/mcp-kanban/tests/test_guidance.py:1412` plus `serve/mcp-kanban/tests/test_guidance.py:1440-1467` assert the same exact equality while `collect_guidance` is patched to `[]`, proving non-overwrite on the fallback path. | PASS |

- Builder evidence sufficiency: `.owlbear/kanban/tasks/1528-p2-01-mcp-integration-test-for-start-work-guidance-passthrough-ac4.md:97-103` records the existing-proof builder run as no code changes, the two named tests passed, and `ruff` clean. That evidence is internally consistent with the inspected source and test assertions.
- Blocking findings: none.

## Observations
- The proof bundle was correctly de-escalated to `existing`: this task needed verification of named MCP-layer proof quality, not new code or new tests.
- Non-blocking wording nit: AC4 says "exact guidance string" while the transport field is `guidance: list[str]`; the current one-element sentinel equality checks are still sufficient because any mutation, overwrite, or extra list entry would fail the assertions.
2026-05-13T16:50:24+00:00
## Docs Gate

**Verdict:** PASS — no docs impact

### Checklist

| Item | Result | Evidence |
|---|---|---|
| README Verification | N/A | No code changes (existing-proof bundle pass-through); zero file mutations → no README drift |
| External Attribution | N/A | Research doc confirms all 3 high-relevance sources are codebase-internal |
| Research Doc | LINKED ✓ | `.owlbear/research/mcp-start-work-guidance-passthrough.md` exists and linked in task body under `## Research` |
| Deletion Detection | N/A | No files deleted |

### Scratch Cleanup
No `1528-*` scratch files found.
2026-05-13T16:57:01+00:00
## Audit
### Regression Detection
- quality-runner mode full: 4603 passed, 212+ failed (pre-existing background), 14 skipped, ruff clean
- Zero code changes (existing-proof pass-through) — failures cannot be attributed to this task
- regression verdict: PASS

### Intent Verification
- scope alignment: PASS (zero files changed, stays within MCP kanban domain)
- purpose match: PASS (existing test coverage for AC4 confirmed by reviewer AC evidence map)
- extraneous scope: none
- boundary check: function-level behavior verification deferred to reviewer

### Architect Quality: 4/5
AC4 is specific and verifiable. Minor terminology gap (string vs list[str]) noted as cosmetic. Architect correctly de-escalated proof bundle from behavioral to existing after challenger surfaced live coverage. Good upstream decision.

### Commit Integrity
- upstream commit presence: PASS (research doc at f2f6fa1a; no builder/test-writer commits needed for zero-change task)
- kanban commit packaging: pending (this commit)

### Deduction Breakdown
- Intent mismatch: none
- Evidence integrity concern: none
- Lint violations: none
- AC quality score 4/5 (above threshold): no deduction
- Missing reviewer evidence: none (detailed AC map present)
- Regression failures: none attributable
Total deductions: 0

### Confidence: 1.00
### Action: archive