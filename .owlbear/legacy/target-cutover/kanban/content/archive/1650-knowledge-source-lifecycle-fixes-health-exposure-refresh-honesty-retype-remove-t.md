---
id: 1650
title: Knowledge source lifecycle fixes — health exposure, refresh honesty, 
  retype, remove tool
status: archived
priority: medium
created: 2026-05-18T03:05:20.577820+02:00
updated: 2026-05-18T19:30:54.425606+02:00
tags:
  - knowledge
  - mcp-tools
  - parent
  - quality
parent:
depends_on:
  - 1655
blocked: false
block_reason:
claimed_at:
archival_reason: completed
archival_refs: []
---
## Brief

See `.owlbear/briefs/draft-knowledge-source-lifecycle/brief.md`

## Summary

4 focused fixes to the knowledge source surface:

- **O1:** Expose source health in `list_sources` (5 new fields: `last_refreshed_at`, `last_checked_at`, `last_error`, `enabled`, `fetch_method`)
- **O2:** Fix refresh honesty — two-field timestamp model (`last_checked_at` + `last_refreshed_at`) with conditional update logic
- **O3:** Retype direct-ingest HTTP sources from `AUTHENTICATED_WEB` to `URL_LIST` (gated on handler equivalence)
- **O4:** Add `remove_source` MCP tool with vectors-first abort-on-failure cascade

## Implementation Order

O2 → O1 → O4 → O3

## Key Constraints

- No `config` in `list_sources` (leak risk)
- Raw error strings (no sanitization)
- `remove_source` aborts if Qdrant cleanup fails
- O3 drops if handler equivalence fails

[[2026-05-18T03:11:44+02:00]]
## Planning
### Decomposition: Knowledge source lifecycle fixes
- Tasks created: 5
- Dependency layers: 3
- Phase: P1

### Task List
| ID | Title | Priority | Depends On | Tags | Proof |
|----|-------|----------|------------|------|-------|
| #1651 | P1-01: Refresh honesty — two-field timestamp model | critical | — | scope:knowledge, knowledge | behavioral |
| #1654 | P1-02: Expose source health in list_sources | needed | #1651 | scope:mcp-knowledge, mcp-tools | behavioral |
| #1652 | P1-03: Add remove_source MCP tool with vectors-first abort | needed | — | scope:mcp-knowledge, mcp-tools | behavioral |
| #1653 | P1-04: Verify handler equivalence for URL_LIST retype | important | — | scope:knowledge, research | skip |
| #1655 | Consolidation test: knowledge source lifecycle | needed | #1651, #1654, #1652 | scope:knowledge, scope:mcp-knowledge, consolidation-test | behavioral |

### Dependency Graph
```mermaid
graph TD
  1651[\"#1651 O2: Refresh honesty\"] --> 1654[\"#1654 O1: Health in list_sources\"]
  1651 --> 1655[\"#1655 Consolidation test\"]
  1654 --> 1655
  1652[\"#1652 O4: remove_source tool\"] --> 1655
  1653[\"#1653 O3: Handler equivalence research\"]
  1655 --> 1650[\"#1650 Parent\"]
```

### Notes
- O2 (#1651) is critical path — O1 depends on it for `last_checked_at` field
- O4 (#1652) can develop in parallel with O2/O1
- O3 research (#1653) is independent; creates conditional follow-up impl task if handler equivalence holds
- Consolidation test (#1655) moved to backlog and gates parent completion

[[2026-05-18T18:49:46+02:00]]
## Architecture Review
### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Parent coordination task — single purpose: track subtask completion |
| Interface clarity | PASS | No interface — pure tracking |
| Dependency correctness | PASS | Depends on #1655 (consolidation test); #1655 archived/completed |
| Module layering | PASS | N/A — no code |
| TDD compliance | PASS | N/A — parent task produces no code |
| KISS/YAGNI | PASS | Minimal coordination wrapper |
| Premise challenge | PASS | Parent exists to track 4-outcome feature; all subtasks delivered |
| Pattern consistency | PASS | Standard parent-with-subtasks pattern |
| Security surface | PASS | No system boundaries |
| Single domain | PASS | Knowledge domain coordination |

### Subtask Status
- #1651 (O2 Refresh honesty): archived/completed
- #1654 (O1 Health exposure): archived/completed
- #1652 (O4 remove_source): archived/completed
- #1653 (O3 Handler equivalence research): archived/completed
- #1655 (Consolidation test): archived/completed

### Proof-Bundle Validation
- Planner assignment: none (parent task)
- Final bundle: skip
- Existing proof scope: N/A
- Test-writer: SKIP

### Challenge Results
- Challenger: SKIPPED — proof bundle `skip`

### Design Diverge
- Trigger: skipped — parent coordination task with no design decisions

### Non-impl tagging
Added `quality` pass-through tag for test-writer pass-through.

### Verdict: APPROVE
### Action Taken: Advanced parent task to todo. All 5 subtasks archived/completed; dependency #1655 satisfied.

[[2026-05-18T18:51:35+02:00]]
## Test-Writer Notes
- Non-implementation task (tagged `quality`, parent coordination) — no tests applicable.
- AC is empty; architect explicitly added `quality` tag for test-writer pass-through.
- All subtasks (#1651, #1652, #1653, #1654, #1655) archived/completed; consolidation tests delivered via #1655.
- Passing through to builder.

[[2026-05-18T18:59:03+02:00]]
## Builder Notes
- Classification: Non-implementation parent coordination task (quality pass-through)
- Trigger used: Test-Writer Notes explicitly state "Non-implementation task" and pass-through to builder
- Implementation: No code changes required or applied
- Tests: Not applicable for parent pass-through at builder stage (evidence carried by completed subtasks and consolidation task #1655)
- Coverage: Not applicable (no touched modules)
- ruff: Not applicable (no code edits)
- Evidence summary: Subtasks #1651, #1652, #1653, #1654 and consolidation #1655 are completed/archived; parent task is coordination closure only

[[2026-05-18T19:03:56+02:00]]
## Review Evidence
- Verdict: PASS
- PASS confirmation: PASS #1650 -> docs | Parent coordination scope verified; all child tasks archived/completed.
- Builder evidence reviewed first: builder correctly treated this as a non-implementation parent closure, but its summary omitted late-added child #1656, so review verified the authoritative archived child set directly before verdict.
- Task frontmatter AC is empty; review scope is therefore the parent coordination contract expressed in the task summary and planning notes.

| Scope Item | Evidence | Status |
|---|---|---|
| Parent scope includes O3 retype gated on handler equivalence and allows a conditional implementation follow-up | `.owlbear/kanban/tasks/1650-knowledge-source-lifecycle-fixes-health-exposure-refresh-honesty-retype-remove-t.md:33`; `.owlbear/kanban/tasks/1650-knowledge-source-lifecycle-fixes-health-exposure-refresh-honesty-retype-remove-t.md:77` | PASS |
| O1/O2/O4 child delivery | `.owlbear/kanban/archive/1651-p1-01-refresh-honesty-two-field-timestamp-model.md:4`; `.owlbear/kanban/archive/1651-p1-01-refresh-honesty-two-field-timestamp-model.md:11`; `.owlbear/kanban/archive/1651-p1-01-refresh-honesty-two-field-timestamp-model.md:35`; `.owlbear/kanban/archive/1652-p1-03-add-remove-source-mcp-tool-with-vectors-first-abort.md:4`; `.owlbear/kanban/archive/1652-p1-03-add-remove-source-mcp-tool-with-vectors-first-abort.md:11`; `.owlbear/kanban/archive/1652-p1-03-add-remove-source-mcp-tool-with-vectors-first-abort.md:37`; `.owlbear/kanban/archive/1654-p1-02-expose-source-health-in-list-sources.md:4`; `.owlbear/kanban/archive/1654-p1-02-expose-source-health-in-list-sources.md:11`; `.owlbear/kanban/archive/1654-p1-02-expose-source-health-in-list-sources.md:40` | PASS |
| O3 research gate completed | `.owlbear/kanban/archive/1653-p1-04-verify-handler-equivalence-for-url-list-retype.md:4`; `.owlbear/kanban/archive/1653-p1-04-verify-handler-equivalence-for-url-list-retype.md:11`; `.owlbear/kanban/archive/1653-p1-04-verify-handler-equivalence-for-url-list-retype.md:28` | PASS |
| O3 implementation follow-up completed under the same parent | `.owlbear/kanban/archive/1656-retype-direct-source-config-from-authenticated-web-to-url-list-for-new-http-sour.md:5`; `.owlbear/kanban/archive/1656-retype-direct-source-config-from-authenticated-web-to-url-list-for-new-http-sour.md:12`; `.owlbear/kanban/archive/1656-retype-direct-source-config-from-authenticated-web-to-url-list-for-new-http-sour.md:35` | PASS |
| Consolidation gate completed | `.owlbear/kanban/archive/1655-consolidation-test-knowledge-source-lifecycle.md:4`; `.owlbear/kanban/archive/1655-consolidation-test-knowledge-source-lifecycle.md:12`; `.owlbear/kanban/archive/1655-consolidation-test-knowledge-source-lifecycle.md:38` | PASS |

## Observations
- Non-blocking: the original parent planning table still lists only five tasks, and the builder summary repeats that incomplete set at `.owlbear/kanban/tasks/1650-knowledge-source-lifecycle-fixes-health-exposure-refresh-honesty-retype-remove-t.md:136`. Review therefore had to verify the authoritative archived child set directly to include late-added implementation child #1656.
- No parent-level code changed in this task; the review was a coordination-closure verification rather than an implementation or test-proof audit.

[[2026-05-18T19:07:57+02:00]]
## Docs Gate

**Verdict: PASS**

### Convention Mapping
Parent coordination task — no code changed directly in #1650. Code changes were in subtasks #1651, #1652, #1654, #1655, #1656, which each completed their own docs gates. Mapped targets: `serve/knowledge/README.md` and `serve/mcp-knowledge/README.md`.

### Checklist

| Item | Result | Evidence |
|------|--------|----------|
| 1. README Verification | PASS | Full reads of both READMEs performed. `serve/mcp-knowledge/README.md`: `remove_source` row present (added by #1652 docs gate, commit c07f22ce); `list_sources` description accurate (#1654 docs gate confirmed no field enumeration — response shape expansion does not cause drift); all 9 tools accurate. `serve/knowledge/README.md`: `KnowledgeSourceStore` in module groups unchanged. Layer 1 grep: no stale `AUTHENTICATED_WEB` refs in READMEs (type still exists in codebase, retype was internal to `ingest.py`). Layer 2 editorial: both READMEs coherent and unaffected. |
| 2. External Attribution | N/A — no external sources at parent level | Subtask attribution handled per-subtask in each docs gate. |
| 3. Research Doc | N/A — no research artifact for parent task | Task body references `.owlbear/briefs/` (brief, not research doc). No parent-level research doc created. |
| 4. Deletion Detection | N/A — no deletions | No source files deleted at parent level; subtask docs gates confirmed no orphaned references. |

### Files Updated
None — all subtask docs gates handled their respective README updates inline.

### Scratch Cleanup
No `.owlbear/scratch/1650-*` files found — nothing to clean.

[[2026-05-18T19:30:54+02:00]]
## Audit

### Regression Detection
Quality-runner full report: 4901 passed, 20 failed, lint clean. All 20 failures are background debt unrelated to #1650:
- 7 FileNotFoundError for deleted task-scoped test files (orphaned references from old tasks)
- 2 AttributeError for `_move_with_collision_suffix` (kanban decisions module, unrelated domain)
- 1 KeyError in cockpit view test (unrelated domain)
- 4 sqlite3.IntegrityError in graph_store_counts setup (pre-existing schema drift)
- 3 knowledge embedding/vector tests (infrastructure-dependent, pre-existing)
- 1 edge relation validation test (pre-existing)
- 1 vitest timeout (cockpit PDS build compat, unrelated)
- 1 Python version floor meta-test (unrelated)

Parent task #1650 made zero code changes — all implementation was in subtasks (#1651, #1652, #1653, #1654, #1655, #1656), each individually audited and archived. No regression attributable to this task.

### Intent Verification
- Purpose: coordinate 4 knowledge source lifecycle fixes (O1–O4)
- All 6 subtasks archived with `archival_reason: completed`
- Domain stayed within `serve/knowledge/` and `serve/mcp-knowledge/`
- No extraneous scope
- Late-added #1656 (O3 implementation follow-up after #1653 research) appropriately handled under same parent

### Architect Quality
Score: 4/5
- Clean decomposition into 5 tasks (later 6) with correct dependency ordering
- O3 correctly gated on research (#1653) before implementation (#1656)
- Consolidation test (#1655) correctly gates parent completion
- Minor gap: original planning table lists 5 tasks; late-added #1656 not reflected in table (reviewer caught this)
- Parent AC empty — appropriate for coordination tasks (real AC lived in subtasks)

### Commit Integrity
- No builder commit at parent level (correct — no code changes)
- All subtask commits verified in git log (serve/knowledge/, serve/mcp-knowledge/)
- Kanban archival commit for #1655 present: `2c4e00a4`

### Deductions
None.

### Confidence: 1.00
### Action: ARCHIVE
