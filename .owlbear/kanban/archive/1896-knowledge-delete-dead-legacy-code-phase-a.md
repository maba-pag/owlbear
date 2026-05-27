---
id: 1896
title: 'Knowledge: Delete dead legacy code (Phase A)'
status: archived
priority: needed
created: 2026-05-27T16:19:40.136779+02:00
updated: 2026-05-27T17:48:14.847770+02:00
tags:
  - knowledge
  - cleanup
  - layer-4
  - quality
parent:
depends_on:
  - 1881
  - 1882
ac:
  - Listed files deleted from the repository
  - No remaining imports of deleted modules in serve/ or tests/
  - No new test failures caused by the deletion (`import owlbear_knowledge` and 
    `import owlbear_mcp_knowledge` succeed; domain test suite has no regressions
    attributable to deleted files — pre-existing failure 
    `test_mcp_knowledge_lifespan_1888.py::test_list_sources_tool_works_with_new_appcontext_shape`
    excluded from gate)
proof_bundle: skip
blocked: false
block_reason:
claimed_at:
archival_reason: completed
archival_refs: []
---
## Objective
Delete confirmed dead code — files with zero runtime consumers.

## Files to delete
- `serve/mcp-knowledge/src/owlbear_mcp_knowledge/_enrichment.py` (no importers)
- `serve/knowledge/src/owlbear_knowledge/loader.py` (only legacy consumers)
- 9 legacy-only test files:
  - tests/test_manifest_loader_1578.py
  - tests/test_ingest_1656.py
  - tests/test_query_service.py
  - tests/test_browser_fetcher_wiring.py
  - tests/test_qdrant_source_identity.py
  - tests/test_enrichment_schema.py
  - tests/test_schema_bookmark_drop_1583.py
  - tests/test_schema_constraint_enforcement_1586.py
  - tests/test_enrichment_persistence_1557.py

## Verification
- `uv run python -c "import owlbear_knowledge"` passes
- `uv run python -c "import owlbear_mcp_knowledge"` passes
- Full test suite passes

## Research
See .owlbear/research/knowledge-legacy-deletion.md §3.4, §3.5

[[2026-05-27T16:24:27+02:00]]
## Research
Validation pass — existing research doc `.owlbear/research/knowledge-legacy-deletion.md` §3.4–3.5 confirmed current.

**Verified:**
- All 11 target files still exist
- `_enrichment.py` (mcp): zero importers
- `loader.py`: only imported by `test_manifest_loader_1578.py` (also in deletion list)
- 9 test files: self-referential comments only, no external consumers

**Tier:** T1 — autonomous dead-code deletion, no decisions needed.
**Confidence:** 0.92 — straightforward grep-verified deletions with no runtime impact.

[[2026-05-27T16:27:39+02:00]]
## Architecture Review
### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Single concern: delete dead code |
| Interface clarity | PASS | AC specifies exact files, verification commands |
| Dependency correctness | PASS | #1881, #1882 both archived |
| Module layering | PASS | Deletions only — no new imports |
| TDD compliance | PASS | No new code; existing suite is verification |
| KISS/YAGNI | PASS | Minimal deletion scope |
| Premise challenge | PASS | Dead code confirmed by research + grep verification |
| Pattern consistency | PASS | Standard dead-code removal |
| Security surface | PASS | No new boundaries |
| Single domain | PASS | Knowledge domain only |

### Codebase Verification
- `loader.py`: only import is from `test_manifest_loader_1578.py` (co-deleted)
- `_enrichment.py`: zero importers anywhere in workspace
- Neither module's `__init__.py` re-exports from these files
- All 11 target files confirmed present

### Design Diverge
- Skipped: single valid approach (delete files), no alternatives

### Challenge Results
- Challenger: SKIPPED — proof bundle `skip`

### Proof-Bundle Validation
- Planner assignment: (none)
- Final bundle: skip
- Existing proof scope: N/A
- Test-writer: SKIP

### Non-impl Tagging
Added `quality` pass-through tag — deletion task produces no new testable code.

### Verdict: APPROVE
### Action Taken: Advanced to todo. Proof bundle set to `skip`, `quality` tag added for test-writer pass-through.

[[2026-05-27T16:28:15+02:00]]
## Test-Writer Notes
- Proof bundle: skip — no new test writing required.
- Task deletes dead code only; all verification is via the existing test suite (AC: "All tests pass after deletion").
- Passing through to builder.

[[2026-05-27T17:03:37+02:00]]
## Builder Notes
- Implementation: Deleted the exact 11 AC-listed dead files.
  - `serve/mcp-knowledge/src/owlbear_mcp_knowledge/_enrichment.py`
  - `serve/knowledge/src/owlbear_knowledge/loader.py`
  - `tests/test_manifest_loader_1578.py`
  - `tests/test_ingest_1656.py`
  - `tests/test_query_service.py`
  - `tests/test_browser_fetcher_wiring.py`
  - `tests/test_qdrant_source_identity.py`
  - `tests/test_enrichment_schema.py`
  - `tests/test_schema_bookmark_drop_1583.py`
  - `tests/test_schema_constraint_enforcement_1586.py`
  - `tests/test_enrichment_persistence_1557.py`
- Proof-bundle handling: `skip` removed `TestFromAC_*` gate for this task; AC implementation obligations still applied.
- Import/runtime verification:
  - `uv run python -c "import owlbear_knowledge"` passed (exit 0)
  - `uv run python -c "import owlbear_mcp_knowledge"` passed (exit 0)
  - Import-statement scan for deleted modules in `serve/` + `tests/` returned no matches.
- Quality evidence:
  - quality-runner `mode=full` (domain-mapped run) returned substantial unrelated pre-existing failures/timeouts outside this task scope (pytest exit 1; ruff exit 1).
  - quality-runner `mode=scoped` on active knowledge/mcp-knowledge regression set: 396 passed, 1 failed (`tests/test_mcp_knowledge_lifespan_1888.py::test_list_sources_tool_works_with_new_appcontext_shape`), plus pre-existing unrelated ruff violations in untouched files.
- Lint status: not clean globally; only pre-existing violations reported in untouched files.
- Coverage: not used as gate for this deletion-only cleanup task.
- Commit:
  - `eac38b5a` — `chore: delete dead legacy knowledge code (#1896, builder)`
  - Includes only the 11 deletions above.
- Evidence summary:
  - AC1 satisfied: listed files are removed.
  - AC2 satisfied: no remaining import statements for deleted modules in `serve/` or `tests/`.
  - AC3 blocked by repository baseline instability unrelated to this diff; documented with quality-runner output for reviewer visibility.

[[2026-05-27T17:09:28+02:00]]
## Review Evidence
- Verdict: FAIL
- Evidence map:
| AC Line | Code Evidence | Test Evidence | Status |
|---|---|---|---|
| Listed files deleted from the repository | Workspace file search returned no matches for the 11 AC-listed paths from `.owlbear/kanban/tasks/1896-knowledge-delete-dead-legacy-code-phase-a.md:24-35`; builder notes enumerate the same 11 deletions at `.owlbear/kanban/tasks/1896-knowledge-delete-dead-legacy-code-phase-a.md:113-125`. | N/A | PASS |
| No remaining imports of deleted modules | Workspace grep for import patterns referencing `owlbear_knowledge.loader`, `.loader`, `owlbear_mcp_knowledge._enrichment`, and `._enrichment` returned no matches in `serve/**`; package exports in `serve/knowledge/src/owlbear_knowledge/__init__.py` and `serve/mcp-knowledge/src/owlbear_mcp_knowledge/__init__.py` do not reference removed modules. | N/A | PASS |
| All tests pass after deletion | AC3 requires full test pass at `.owlbear/kanban/tasks/1896-knowledge-delete-dead-legacy-code-phase-a.md:20`. Builder evidence records one failing active regression in `tests/test_mcp_knowledge_lifespan_1888.py::test_list_sources_tool_works_with_new_appcontext_shape` at `.owlbear/kanban/tasks/1896-knowledge-delete-dead-legacy-code-phase-a.md:133` and states AC3 is blocked at `.owlbear/kanban/tasks/1896-knowledge-delete-dead-legacy-code-phase-a.md:142`. The failing test expects `list_sources` to work with `source_store_v2=None` at `tests/test_mcp_knowledge_lifespan_1888.py:490`, but current `list_sources` explicitly errors when `source_store_v2` is unavailable at `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:904-912`, and the current read-tools contract requires delegation to `source_store_v2.list_sources` at `tests/test_mcp_knowledge_read_tools_1881.py:387-418`. | FAIL |
- Blocking findings:
| # | AC Line | Finding | Evidence | Route |
|---|---|---|---|---|
| 1 | All tests pass after deletion | Builder evidence does not satisfy AC3. The cited failure is outside the deletion surface and reflects a pre-existing or stale proof surface around `list_sources`, so the gate on this deletion task is structurally infeasible in the current baseline. | `.owlbear/kanban/tasks/1896-knowledge-delete-dead-legacy-code-phase-a.md:20`, `.owlbear/kanban/tasks/1896-knowledge-delete-dead-legacy-code-phase-a.md:133`, `.owlbear/kanban/tasks/1896-knowledge-delete-dead-legacy-code-phase-a.md:142`, `tests/test_mcp_knowledge_lifespan_1888.py:490`, `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:904-912`, `tests/test_mcp_knowledge_read_tools_1881.py:387-418` | backlog |

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | architect | Re-scope AC3 so this deletion task is gated by a provable relevant surface, or split the unrelated `list_sources` baseline failure into its own task before re-running review. | `.owlbear/kanban/tasks/1896-knowledge-delete-dead-legacy-code-phase-a.md`, `tests/test_mcp_knowledge_lifespan_1888.py`, `tests/test_mcp_knowledge_read_tools_1881.py`, `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py` | AC3 at `.owlbear/kanban/tasks/1896-knowledge-delete-dead-legacy-code-phase-a.md:20`; builder evidence at `.owlbear/kanban/tasks/1896-knowledge-delete-dead-legacy-code-phase-a.md:133` and `.owlbear/kanban/tasks/1896-knowledge-delete-dead-legacy-code-phase-a.md:142`; failing test at `tests/test_mcp_knowledge_lifespan_1888.py:490`; current tool contract at `tests/test_mcp_knowledge_read_tools_1881.py:387-418` and `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:904-912` |

## Observations
- Proof bundle `skip` correctly waived task-local test authoring, but it did not waive the explicit AC3 full-pass gate in the task.
- No independent quality-runner rerun was needed; the builder's own evidence already showed AC3 unmet, and direct file inspection established that the cited failing regression is outside the deleted surface.
- No safety or security issues were identified on the deletion surface.

[[2026-05-27T17:11:44+02:00]]
## Architecture Review (Re-entry after reviewer rejection)

### Context
Task was rejected from review because AC3 ("All tests pass after deletion") was structurally infeasible — a pre-existing failure in `test_mcp_knowledge_lifespan_1888.py::test_list_sources_tool_works_with_new_appcontext_shape` (unrelated to deleted modules) blocked the global pass gate.

### AC Refinement
- AC3 refined from "All tests pass after deletion" to scoped gate: "No new test failures caused by the deletion (import checks succeed; domain suite has no regressions attributable to deleted files — pre-existing failure excluded from gate)"
- Root cause: Task #1888 wrote a backwards-compat test for `list_sources` with `source_store_v2=None`, but a subsequent task (#1889+) made `source_store_v2` mandatory. That stale test is not attributable to this deletion task.

### Evaluation (unchanged from prior review)
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Single concern: delete dead code |
| Interface clarity | PASS | AC specifies exact files, scoped verification commands |
| Dependency correctness | PASS | #1881, #1882 both archived |
| Module layering | PASS | Deletions only — no new imports |
| TDD compliance | PASS | No new code; existing suite is verification |
| KISS/YAGNI | PASS | Minimal deletion scope |
| Premise challenge | PASS | Dead code confirmed by research + grep verification |
| Pattern consistency | PASS | Standard dead-code removal |
| Security surface | PASS | No new boundaries |
| Single domain | PASS | Knowledge domain only |

### Proof-Bundle Validation
- Planner assignment: skip
- Final bundle: skip
- Test-writer: SKIP

### Non-impl Tagging
`quality` tag present — deletion task produces no new testable code.

### Challenger
Skipped per proof-bundle `skip` gating rule.

### Verdict: APPROVE
AC3 refined to a verifiable, scoped test gate. Builder can now satisfy AC by demonstrating domain-relevant tests pass and the excluded failure is not attributable to the deletion.

[[2026-05-27T17:13:10+02:00]]
## Test-Writer Notes
- Retry pass-through: proof_bundle = skip; quality tag present.
- Reviewer Required Follow-up was directed at architect (re-scope AC3 to a verifiable gate) — completed by the Architecture Review (Re-entry) section above.
- No new test writing required. AC3 is now scoped to domain-relevant regressions; existing test suite is the gate.
- Passing through to builder.

[[2026-05-27T17:24:52+02:00]]
## Builder Notes
- Implementation: no new code changes in this retry pass; using existing builder commit `eac38b5a` (`chore: delete dead legacy knowledge code (#1896, builder)`) that removed the 11 AC-listed files.
- Files changed (this pass): none.
- Proof bundle handling: `skip` (no `TestFromAC_*` gate required), AC evidence re-verified after architect AC3 refinement.
- Import/runtime verification:
  - `uv run python -c "import owlbear_knowledge"` passed (exit 0)
  - `uv run python -c "import owlbear_mcp_knowledge"` passed (exit 0)
- AC1 evidence: all 11 target files confirmed absent via workspace file checks (no matches for each listed path).
- AC2 evidence: no remaining references/imports found in `serve/` or `tests/` for deleted modules (`owlbear_knowledge.loader`, `owlbear_mcp_knowledge._enrichment`, related import forms, and dotted references scan).
- Quality evidence (quality-runner, scoped):
  - Tests: 228 passed, 1 failed
  - Failing test: `tests/test_mcp_knowledge_lifespan_1888.py::TestFromAC_ExistingFieldsPreserved::test_list_sources_tool_works_with_new_appcontext_shape`
  - Failure detail: `ToolError: source store v2 not available`
  - Lint: not clean in scoped domain; reported violations are pre-existing and unrelated to task 1896 deletion surface
  - Coverage (informational): `owlbear_knowledge` 45%, `owlbear_mcp_knowledge` 58%
- AC3 decision: satisfied per refined gate — no new failures attributable to deletion; the single failing test is the explicitly excluded pre-existing baseline (`test_mcp_knowledge_lifespan_1888.py::test_list_sources_tool_works_with_new_appcontext_shape`).
- Evidence summary:
  - AC1 PASS
  - AC2 PASS
  - AC3 PASS (scoped + exclusion rule applied)

[[2026-05-27T17:31:37+02:00]]
## Review Evidence
- Verdict: PASS
- PASS confirmation: PASS #1896 -> docs | AC mapped to code and evidence sufficient.
- Evidence map:
| AC Line | Code Evidence | Test Evidence | Status |
|---|---|---|---|
| Listed files deleted from the repository | All 11 AC-listed paths are absent in the workspace, matching the retry builder evidence for the existing deletion commit at `.owlbear/kanban/tasks/1896-knowledge-delete-dead-legacy-code-phase-a.md:219` and `.owlbear/kanban/tasks/1896-knowledge-delete-dead-legacy-code-phase-a.md:225`. | N/A | PASS |
| No remaining imports of deleted modules in serve/ or tests/ | Workspace grep found no surviving references to `owlbear_knowledge.loader` or `owlbear_mcp_knowledge._enrichment` in `serve/**` or `tests/**`; package surfaces inspected at `serve/knowledge/src/owlbear_knowledge/__init__.py:1` and `serve/mcp-knowledge/src/owlbear_mcp_knowledge/__init__.py:1` do not re-export the removed modules. Retry builder evidence is consistent at `.owlbear/kanban/tasks/1896-knowledge-delete-dead-legacy-code-phase-a.md:226`. | N/A | PASS |
| No new test failures caused by the deletion (`import owlbear_knowledge` and `import owlbear_mcp_knowledge` succeed; domain test suite has no regressions attributable to deleted files — pre-existing failure `test_mcp_knowledge_lifespan_1888.py::test_list_sources_tool_works_with_new_appcontext_shape` excluded from gate) | Frontmatter AC3 is the authoritative scoped gate at `.owlbear/kanban/tasks/1896-knowledge-delete-dead-legacy-code-phase-a.md:20`, refined by architecture notes at `.owlbear/kanban/tasks/1896-knowledge-delete-dead-legacy-code-phase-a.md:176` and `.owlbear/kanban/tasks/1896-knowledge-delete-dead-legacy-code-phase-a.md:179`. Retry builder evidence shows `228 passed, 1 failed` with the lone failure explicitly identified and excluded at `.owlbear/kanban/tasks/1896-knowledge-delete-dead-legacy-code-phase-a.md:228`, `.owlbear/kanban/tasks/1896-knowledge-delete-dead-legacy-code-phase-a.md:229`, and `.owlbear/kanban/tasks/1896-knowledge-delete-dead-legacy-code-phase-a.md:233`. Direct inspection confirms that excluded test exercises stale `list_sources` compatibility with `source_store_v2 is None` at `tests/test_mcp_knowledge_lifespan_1888.py:487` and `tests/test_mcp_knowledge_lifespan_1888.py:490`, while the current product contract requires `source_store_v2` delegation at `tests/test_mcp_knowledge_read_tools_1881.py:387`, `tests/test_mcp_knowledge_read_tools_1881.py:390`, `tests/test_mcp_knowledge_read_tools_1881.py:407`, and `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:904`, `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:907`, `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:909`. | Builder quality evidence plus direct code/test inspection show the sole failing test is the explicit pre-existing exclusion and not attributable to the deleted modules. | PASS |
- Safety/security check: PASS. The change surface is file deletion only; no new input handling, auth, storage, path, or external integration behavior was introduced.

## Observations
- The task body `## Verification` prose still says `Full test suite passes` at `.owlbear/kanban/tasks/1896-knowledge-delete-dead-legacy-code-phase-a.md:52`, while frontmatter AC3 is now the authoritative scoped gate. This is non-blocking because the frontmatter AC governs review, but aligning the prose later would reduce audit ambiguity.
- I could not independently run git diff/status contamination checks in this session because terminal/git execution is unavailable; the review relied on the builder’s file list plus direct workspace inspection of the deletion and reference surfaces.

[[2026-05-27T17:35:05+02:00]]
## Docs Gate

### Checklist

**Item 1: README Verification**
- `serve/knowledge/README.md`: no stale references to `loader.py` or `_enrichment.py` — clean.
- `serve/mcp-knowledge/README.md`: `store_enrichment`/`get_next_batch` tool names remain valid; no reference to deleted `_enrichment.py` module — clean.
- `README.md` line 109: FOUND task-caused drift — stale `uv run python -m owlbear_knowledge.loader` CLI command referenced deleted module. Fixed: replaced with MCP-tools guidance pointing to `serve/mcp-knowledge/README.md`. Commit: `e2933edc`.

**Item 2: External Attribution**
N/A — dead-code deletion; no external sources used.

**Item 3: Research Doc**
Task body links `.owlbear/research/knowledge-legacy-deletion.md` §3.4–3.5. Research doc exists, is current, and accurately describes the deletion scope.

**Item 4: Deletion Detection**
One stale operational doc reference found and fixed (`README.md`). Remaining grep matches are in archival research docs and the task body — both out of scope for the docs gate.

### Files Updated
- `README.md` — removed stale `## Knowledge Base` CLI command; replaced with MCP-tools description.

### Scratch Cleanup
No `1896-*` scratch files found — nothing to clean.

[[2026-05-27T17:48:14+02:00]]
## Audit
### Regression Detection
- quality-runner mode full (domains: serve/knowledge, serve/mcp-knowledge): 95 passed, 0 failed, lint clean
- regression verdict: PASS

### Intent Verification
- scope alignment: PASS (all changes within knowledge domain; 11 dead-file deletions + 1 README fix)
- purpose match: PASS (dead code removal matches stated objective)
- extraneous scope: none
- boundary check: function-level behavior verification deferred to reviewer

### Architect Quality: 4/5
AC lines specific (exact file list, scoped verification commands). Initial AC3 over-breadth ("Full test suite passes") required one retry cycle; architect corrected cleanly with proper scoped gate. Minor gap filled without significant builder improvisation.

### Commit Integrity
- upstream commit presence: PASS (builder eac38b5a, doc-writer e2933edc)
- kanban commit packaging: pending (this step)

### Deduction Breakdown
No deductions applied.

### Confidence: 1.00
### Action: archive
