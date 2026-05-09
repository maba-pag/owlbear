---
id: 1316
title: Knowledge Engine Activation
status: backlog
priority: critical
created: 2026-05-04T05:44:46.924003+00:00
updated: 2026-05-09T11:15:24.168322+00:00
tags:
- parent
- knowledge
- mcp
- activation
parent:
depends_on: []
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

## Closeout — Knowledge Engine Activation

Parent container for the Knowledge Engine Activation feature. All implementation work was decomposed into 20 subtasks across 5 dependency layers.

### Acceptance Criteria

- [ ] All 20 child tasks (#1317–#1335, #1358) are archived with status `done` (td:0)
- [ ] No active (non-archived) tasks exist with `parent: 1316` on the board (td:0)

### Child Inventory (Reconciled)

| ID | Title | Phase | Status |
|----|-------|-------|--------|
| #1317 | P0-01: Tests — MCP startup | L0 | archived |
| #1318 | P0-02: MCP startup fix | L0 | archived |
| #1319 | P0-03: Tests — Qdrant persistence + source identity | L0 | archived |
| #1320 | P0-04: Qdrant persistence + source identity fix | L0 | archived |
| #1321 | P0-05: Tests — Content guard wiring | L0 | archived |
| #1322 | P0-06: Content guard wiring | L0 | archived |
| #1323 | P1-07: Tests — Enrichment schema | L1 | archived |
| #1324 | P1-08: Enrichment schema additions | L1 | archived |
| #1325 | P1-09: Tests — Browser + RefreshOrchestrator | L1 | archived |
| #1326 | P1-10: Browser + RefreshOrchestrator fix | L1 | archived |
| #1327 | P2-11: Tests — Phase 1 enrichment tools | L2 | archived |
| #1328 | P2-12: Phase 1 enrichment tools | L2 | archived |
| #1329 | P2-13: Tests — Phase 2 + stats tools | L2 | archived |
| #1330 | P2-14: Phase 2 + stats tools | L2 | archived |
| #1331 | P3-15: Tests — Search provenance contract | L3 | archived |
| #1332 | P3-16: Search provenance contract | L3 | archived |
| #1333 | P3-17: Agent definitions + prompts | L3 | archived |
| #1334 | P4-18: Tests — Tool surface validation | L4 | archived |
| #1335 | P4-19: Tool surface cleanup + scope stubs | L4 | archived |
| #1358 | Remove legacy API key branch from mcp-knowledge server.py | Follow-up | archived |

### Brief Reference

See `.owlbear/briefs/draft-knowledge-activation/brief.md` for the full approved Brief.

### Outcomes (from Brief)

- O1: MCP server starts cleanly
- O2: Ingest pipeline works (local files, public URLs, authenticated pages)
- O3: Browser detection with user validation
- O4: Enrichment via VS Code agent workers (Phase 1 + Phase 2)
- O5: Graph-augmented retrieval with provenance
- O6: Persistent local DB (Qdrant + SQLite)
- O7: 8 active MCP tools, 4 deferred scope stubs
- O8: Per-source enrichment flag
- O9: Content injection guard at ingest

[[2026-05-09]]
## Architecture Review

### Verdict: APPROVE

Reviewer follow-up items addressed:
1. **Closeout AC rewrite** — replaced stale implementation brief body with 2 explicit closeout AC lines, both td:0, anchored to live child completion (20 archived children, 0 active).
2. **Child inventory reconciled** — full child table now includes follow-up child #1358 alongside planned #1317–#1335 (20 total).

### AC Assessment
| AC Line | Assessment | Action |
|---------|-----------|--------|
| All 20 child tasks archived with status done (td:0) | Verified: grep `parent: 1316` in archive returns exactly 20 matches (#1317–#1335 + #1358) | None |
| No active tasks with parent: 1316 on board (td:0) | Verified: grep `parent: 1316` in tasks/ returns 0 matches (only self-references in own body) | None |

### Architecture Notes
- Parent container only — no source code, no interfaces, no implementation surface.
- All 9 Brief outcomes (O1–O9) were delivered across the 20 subtasks.
- Test-writer: SKIP (all td:0, mechanical closeout verification only)

### Challenge Results
- Challenger: SKIPPED — all AC lines td:0 per Step 2.1
[[2026-05-09]]
## Test-Writer Notes
- All AC lines are (td:0) — test-writer skipped.
- Passing through to builder.
[[2026-05-09]]
## Builder Notes
- Non-implementation task — no code changes required.
- AC evidence verification:
  - `parent: 1316` matches in `.owlbear/kanban/archive/`: 20 child tasks found (#1317–#1335, #1358).
  - `parent: 1316` matches in `.owlbear/kanban/tasks/`: 0 active child tasks found.
- Child IDs verified: 1317, 1318, 1319, 1320, 1321, 1322, 1323, 1324, 1325, 1326, 1327, 1328, 1329, 1330, 1331, 1332, 1333, 1334, 1335, 1358.
- No source or test files were modified in this builder pass.
- Passing through to review.
[[2026-05-09]]
## Review Evidence
### Test Results
- Skipped. Task 1316 is td:0 on both AC lines and has no source or task-scoped test artifacts. Per reviewer td:0 handling, quality-runner was not dispatched; review used direct board/file evidence.

### Lint Results
- Skipped. No code or test files are in scope for this closeout task.

### Coverage
- Skipped. No executable implementation scope in this parent closeout task.

### Scope Check
- No builder commit hash or code/test file changes were provided because this is a non-implementation closeout task.
- Dirty-tree contamination is not applicable to the AC under review; the evidence source is kanban board state plus archive semantics.
- Prior review count: 0 `## Review Evidence` sections found in task 1316 before this review. This is the first review failure, so loop-breaker escalation does not apply.

### AC Compliance
| AC Line | Evidence | Status |
|---|---|---|
| All 20 child tasks (#1317–#1335, #1358) are archived with status `done` (td:0) | PASS on archival presence: grep `^parent: 1316$` in `.owlbear/kanban/archive/**` returned exactly 20 matches, including 1317–1335 and 1358. FAIL on status contract: sampled archived child records show `status: archived`, not `status: done` (e.g. `.owlbear/kanban/archive/1317-p0-01-tests-mcp-startup-copilot-auth-removal-clean-server-start.md:1-20`, `.owlbear/kanban/archive/1322-p0-06-content-injection-guard-wiring-at-ingest-pipeline.md:1-20`, `.owlbear/kanban/archive/1334-p4-18-tests-tool-surface-validation-8-active-inactive-removed-stubs-registered.md:1-20`, `.owlbear/kanban/archive/1358-remove-legacy-api-key-branch-from-mcp-knowledge-server-py.md:1-20`). Current kanban engine explicitly rewrites archived tasks to `record.status = "archived"` in `serve/kanban/src/owlbear_kanban/engine.py:1238-1273`. Read-path test also asserts archived task status is `archived` in `serve/kanban/tests/test_engine_reads_1069.py:377-390`. Archival flow requires moving through terminal `done` before archiving with `archival_reason="completed"`, but the archived record itself is still `archived` (`tests/test_mcp_kanban_1450.py:151-159`, `serve/kanban/src/owlbear_kanban/topology.py:31-47`). | FAIL |
| No active (non-archived) tasks exist with `parent: 1316` on the board (td:0) | grep `^parent: 1316$` in `.owlbear/kanban/tasks/**` returned no matches. Active task file `.owlbear/kanban/tasks/1316-knowledge-engine-activation.md` contains only self-body references; no active child task files remain. | PASS |

### Findings
1. AC1 is not satisfied as written. The board proves all 20 child tasks are archived, but archived task files do not and should not retain `status: done`; current engine semantics convert archived records to `status: archived`.
2. The Architecture Review and Builder Notes both treated archival presence as sufficient and did not verify the explicit `status done` clause against the live archive contract.

### Deductions
- 0.30: AC1 is objectively false under current engine behavior.
- 0.05: Upstream review/build notes accepted the stale AC wording without checking archive-status semantics.

### Verdict
- FAIL -> backlog
- Confidence: 0.95

### Action
- Route to backlog. This is an AC/contract defect in the closeout task, not a builder implementation miss and not a missing-test issue.
- Rewrite AC1 to match the actual archive semantics, for example: "All 20 child tasks (#1317–#1335, #1358) are present in `.owlbear/kanban/archive/` and archived with `archival_reason=completed` where appropriate," or otherwise add a verifiable artifact for the pre-archive `done` state.

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | architect | Rewrite AC1 on task 1316 to match current kanban archive semantics, or define a different verifiable closeout contract for child completion state | .owlbear/kanban/tasks/1316-knowledge-engine-activation.md | Archived child files carry `status: archived`; engine archive path forces `record.status = "archived"` in `serve/kanban/src/owlbear_kanban/engine.py:1238-1273`; read-path test expects archived status in `serve/kanban/tests/test_engine_reads_1069.py:377-390` |
| 2 | architect | Update the Architecture Review note on task 1316 so the AC assessment no longer claims archival presence alone proves `status done` | .owlbear/kanban/tasks/1316-knowledge-engine-activation.md | Current Architecture Review table claims AC1 verified by parent grep only, but that does not prove the explicit status clause |
