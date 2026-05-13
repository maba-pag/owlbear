---
id: 1529
title: 'P2-02: implement MCP start_work guidance passthrough (AC4)'
status: archived
priority: needed
created: 2026-05-13T12:18:10.756634+00:00
updated: 2026-05-13T17:26:02.538903+00:00
tags:
  - phase-2
  - scope:mcp-kanban
  - feature
parent: 1525
depends_on:
  - 1528
blocked: false
block_reason:
claimed_at:
archival_reason: completed
archival_refs: []
---
## Summary

Ensure MCP `start_work` tool handler passes dep-status guidance through verbatim. Verify existing handler logic already satisfies this — if `_to_single_task_response()` preserves guidance, no code change is needed; if not, fix the mapping.

Brief: see parent #1525

## Acceptance Criteria

- AC4: When `agent_view.start_work()` returns a `SingleTaskResponse` with non-empty `guidance`, the MCP `start_work` handler returns the same list (value equality) — `collect_guidance()` fallback must not overwrite it

## Scope

- In scope: MCP handler at `server.py` — verify/fix guidance passthrough in `_to_single_task_response()` and `collect_guidance` fallback logic
- Out of scope: agent_view implementation (covered by #1527), unit tests

## Context

- `collect_guidance("start_work", None, result)` only fires when `result.guidance` is falsy — dep guidance will be non-empty for blocked tasks, so the fallback is skipped
- `_to_single_task_response()` must preserve the guidance list from the `SingleTaskResponse`

Proof bundle: existing
Existing proof scope: serve/mcp-kanban/tests/test_guidance.py::TestFromAC_GuidanceProofRepair::test_start_work_guidance_sentinel_passthrough, serve/mcp-kanban/tests/test_guidance.py::TestFromAC_GuidanceDiscriminating_1475::test_start_work_agentview_guidance_not_overwritten_by_collect_guidance

## Research
- Research doc: .owlbear/research/mcp-start-work-guidance-impl.md
- Sources: 6 studied, 4 high-relevance (all codebase-internal)
- Recommendation: No code change needed — current implementation already satisfies AC4 via 3 preservation mechanisms (isinstance pass-through, falsy-guard on fallback, no field transformation) (confidence: 0.95)
- Follow-up tasks created: none (verify-only outcome)
- Decision requests: none

## Challenge Results
- Challenger: FALLBACK — trivial T1 verify-only research
- Confidence in original: 0.95
- Key finding: `_to_single_task_response()` returns `SingleTaskResponse` as-is; `if not result.guidance:` guard prevents fallback overwrite; 2 existing tests already prove AC4
- Researcher response: N/A (no challenge needed)
2026-05-13T17:11:04+00:00
## Architecture Review

### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Single contract: MCP guidance passthrough |
| Interface clarity | PASS | AC4 refined to specify condition (non-empty), check (value equality), failure mode (fallback overwrite) |
| Dependency correctness | PASS | #1528 archived/completed — dep satisfied |
| Module layering | PASS | Scope limited to MCP handler at `server.py` |
| TDD compliance | PASS | #1528 was the test task and is archived/done |
| KISS/YAGNI | PASS | Research confirms no code change needed; verify-only |
| Premise challenge | PASS | Task exists as implementation counterpart to #1528; builder verifies existing behavior |
| Pattern consistency | PASS | Follows MCP server pattern: isinstance pass-through, falsy-guard fallback |
| Security surface | PASS | No new system boundaries |
| Single domain | PASS | MCP kanban domain only |

### Challenge Results
- Challenger: reconsider (0.68)
- Key findings: (1) AC4 "exact" wording imprecise — lacks condition/semantics; (2) empty-guidance fallback path not covered by cited tests; (3) research "no field transformation" claim overstated; (4) proof bundle not yet updated in task
- Architect response: (1) ACCEPTED — AC4 rewritten with explicit condition (non-empty guidance), check semantics (value equality), and failure mode (fallback overwrite); (2) REBUTTED — empty path is by-design additive fallback, not a violation; dep-guidance is always non-empty; (3) PARTIALLY ACCEPTED — cosmetic; (4) ACCEPTED — bundle de-escalated in this review

### Proof-Bundle Validation
- Planner assignment: behavioral
- Final bundle: existing (de-escalated — existing test suite covers AC4 via sentinel passthrough + non-overwrite guard; identical reasoning to sibling #1528)
- Existing proof scope: serve/mcp-kanban/tests/test_guidance.py::TestFromAC_GuidanceProofRepair::test_start_work_guidance_sentinel_passthrough, serve/mcp-kanban/tests/test_guidance.py::TestFromAC_GuidanceDiscriminating_1475::test_start_work_agentview_guidance_not_overwritten_by_collect_guidance
- Test-writer: SKIP (bundle `existing`)

### Verdict: APPROVE (REFINE path — AC tightened + bundle de-escalated, then advanced)
### Action Taken: Refined AC4 from vague "exact guidance list without mutation or loss" to precise testable condition. De-escalated proof bundle from behavioral to existing with named proof scope. Advanced to todo.
2026-05-13T17:11:38+00:00
## Test-Writer Notes
- Proof bundle: existing — no new test writing required.
- Existing proof scope: `serve/mcp-kanban/tests/test_guidance.py::TestFromAC_GuidanceProofRepair::test_start_work_guidance_sentinel_passthrough`, `serve/mcp-kanban/tests/test_guidance.py::TestFromAC_GuidanceDiscriminating_1475::test_start_work_agentview_guidance_not_overwritten_by_collect_guidance`
- Passing through to builder.
2026-05-13T17:12:45+00:00
## Builder Notes
- Implementation: no code changes required
- Verification scope: existing proof bundle for AC4 passthrough behavior
- Tests: 2 existing proof tests passed
  - serve/mcp-kanban/tests/test_guidance.py::TestFromAC_GuidanceProofRepair::test_start_work_guidance_sentinel_passthrough
  - serve/mcp-kanban/tests/test_guidance.py::TestFromAC_GuidanceDiscriminating_1475::test_start_work_agentview_guidance_not_overwritten_by_collect_guidance
- ruff: clean (serve/mcp-kanban/src/, serve/mcp-kanban/tests/test_guidance.py)
- Evidence summary:
  - `_to_single_task_response()` preserves `SingleTaskResponse` records without field rewrite.
  - `start_work` guidance fallback is guarded by `if not result.guidance`, so non-empty guidance from `agent_view.start_work()` is not overwritten.
  - Existing proof bundle confirms sentinel passthrough and non-overwrite semantics required by AC4.
2026-05-13T17:20:26+00:00
## Review Evidence
- Verdict: PASS
- PASS confirmation: PASS #1529 to docs | AC mapped to code and evidence sufficient.
- Builder evidence reviewed first: existing-bundle evidence is sufficient for this task. Builder reported the two named proof tests passed and ruff was clean for serve/mcp-kanban/src/ and serve/mcp-kanban/tests/test_guidance.py; direct source/test inspection found no contradiction.
- Blocking findings: none.

| AC Line | Code Evidence | Test Evidence | Status |
|---|---|---|---|
| AC4: When `agent_view.start_work()` returns a `SingleTaskResponse` with non-empty `guidance`, the MCP `start_work` handler returns the same list (value equality) and `collect_guidance()` fallback does not overwrite it | `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py:319` returns `SingleTaskResponse` inputs as-is; `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py:559` and `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py:577` only call `collect_guidance("start_work", None, result)` when `result.guidance` is falsy; `serve/kanban/src/owlbear_kanban/agent_view.py:54` and `serve/kanban/src/owlbear_kanban/agent_view.py:962` show `AgentView.start_work()` builds and returns a `SingleTaskResponse` carrying guidance | `serve/mcp-kanban/tests/test_guidance.py::TestFromAC_GuidanceProofRepair::test_start_work_guidance_sentinel_passthrough` proves the returned guidance equals the AgentView sentinel list; `serve/mcp-kanban/tests/test_guidance.py::TestFromAC_GuidanceDiscriminating_1475::test_start_work_agentview_guidance_not_overwritten_by_collect_guidance` patches `collect_guidance` to `[]` and still requires the original AgentView sentinel guidance to survive | PASS |

- Proof sufficiency: The named tests are falsifiable and cover both preservation mechanisms required by AC4: passthrough on the `SingleTaskResponse` branch and non-overwrite when fallback produces `[]`.
- Safety and security: PASS. This AC does not add a new input-handling, storage, auth, shell, SQL, or path surface.

## Observations
- The builder summary slightly over-generalizes `_to_single_task_response()` as a universal no-rewrite guarantee. The AC passes for the narrower reason that `AgentView.start_work()` already returns `SingleTaskResponse`, so the passthrough branch at `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py:319` is the operative path.
- No builder commit hash was recorded, so review scope was reconstructed from Builder Notes, proof scope, and direct inspection of the current source/test files.
- Editor diagnostics were clean for the reviewed source and test files.
2026-05-13T17:21:30+00:00
## Docs Gate

**Verdict: PASS — no docs impact**

| Item | Result | Evidence |
|------|--------|----------|
| README Verification | N/A | Verify-only task — no code changes; no convention-mapped README target triggered |
| External Attribution | N/A | All sources codebase-internal (per task body: "4 high-relevance (all codebase-internal)") |
| Research Doc | VERIFIED | `.owlbear/research/mcp-start-work-guidance-impl.md` exists and linked in task body |
| Deletion Detection | N/A | No files deleted |

Scratch cleanup: no `1529-*` scratch files found.
2026-05-13T17:26:02+00:00
## Audit
### Regression Detection
- quality-runner mode full: 4607 passed, 20 failed (all pre-existing — cockpit_view FileNotFoundError, ideation_diagram assertion, server StatusNamesDictFormBug TypeError, engine_accessor_migration assertions), 14 skipped, clean lint
- task proof tests (test_start_work_guidance_sentinel_passthrough, test_start_work_agentview_guidance_not_overwritten_by_collect_guidance): both PASSED
- regression verdict: PASS (zero code changes; all failures pre-existing and in unrelated domains)

### Intent Verification
- scope alignment: PASS (verify-only task — no source changes, research doc and task file in correct MCP kanban domain)
- purpose match: PASS (research confirmed existing implementation satisfies AC4 via isinstance pass-through, falsy-guard fallback, and no field transformation; 2 existing proof tests validate)
- extraneous scope: none
- boundary check: function-level behavior verification deferred to reviewer

### Architect Quality: 4/5
AC4 was originally vague ("exact guidance list without mutation or loss"). Architect refined to precise testable condition with explicit semantics (non-empty condition, value equality check, fallback overwrite failure mode). Proof bundle correctly de-escalated from behavioral to existing with named scope. Challenger findings addressed properly. Minor deduction: original AC required refinement, but architect handled it well.

### Commit Integrity
- upstream commit presence: PASS (ceeeb964 — researcher docs commit; no builder commit expected for verify-only task with zero code changes)
- kanban commit packaging: pending (this audit cycle)

### Deduction Breakdown
No deductions applied.

### Confidence: 1.00
### Action: archive