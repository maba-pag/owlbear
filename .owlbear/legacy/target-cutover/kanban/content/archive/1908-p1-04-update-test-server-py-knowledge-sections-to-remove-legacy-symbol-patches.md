---
id: 1908
title: 'P1-04: Update test_server.py knowledge sections to remove legacy symbol patches'
status: archived
priority: medium
created: 2026-05-28T00:34:20.763020+02:00
updated: 2026-05-28T04:27:12.143898+02:00
tags:
  - knowledge
  - cleanup
  - test
parent:
depends_on:
  - 1900
ac:
  - test_server.py no longer patches init_db, GraphStore, 
    BgeM3EmbeddingProvider, KnowledgeQueryService, GraphAugmentedRetriever, 
    EntityExtractor, or IntraDocGraphBuilder in owlbear_mcp_knowledge.server
  - test_server.py no longer accesses ctx.query_service, ctx.ingest_pipeline, or
    ctx.structured_extractor (removed AppContext fields)
  - pytest tests/test_server.py -k "not (StatusNamesDictFormBug or 
    FunctionRemoval or OutputSchemaPreserved)" passes (0 failures, 0 errors) — 
    excludes pre-existing mcp-kanban-section failures unrelated to this task
proof_bundle: smoke
blocked: false
block_reason:
claimed_at:
archival_reason: completed
archival_refs: []
---
## Objective
Update the knowledge-related merged sections in `tests/test_server.py` that patch legacy symbols removed by #1900.

## Current State
Two merged knowledge sections patch removed symbols:
1. **Section from test_server_1170.py** (line ~1240): `mock_lifespan_deps` autouse fixture patches `init_db`, `GraphStore`, `QdrantVectorStore`, `BgeM3EmbeddingProvider`, `KnowledgeQueryService`, `GraphAugmentedRetriever`. `TestFromAC_LifespanNoCopilotAuth` accesses `ctx.query_service`, `ctx.ingest_pipeline`, `ctx.structured_extractor`.
2. **Section from test_server_1358.py** (line ~1450): `mock_lifespan_deps_1358` autouse fixture patches the same 6 legacy symbols.

## Direction
- Remove patches for symbols no longer in server.py (`init_db`, `GraphStore`, `BgeM3EmbeddingProvider`, `KnowledgeQueryService`, `GraphAugmentedRetriever`)
- Retain `QdrantVectorStore` patch (still present in v2 lifespan)
- Delete or rewrite tests that assert removed AppContext fields (query_service, ingest_pipeline, structured_extractor)
- Evaluate whether the remaining assertions (copilot_auth removal, API key branch removal, EntityExtractor/IntraDocGraphBuilder extractor=None) are still valid in the v2-only server — delete those superseded by #1900 AC1/AC6

## Scope
- In-scope: the two knowledge-related merged sections in `tests/test_server.py`
- Out-of-scope: the mcp-kanban section at the top of test_server.py, other test files

[[2026-05-28T01:50:49+02:00]]
## Architecture Review
### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | One task: remove dead patches/assertions from two merged sections |
| Interface clarity | PASS | AC names specific symbols and fields to remove |
| Dependency correctness | PASS | #1900 archived (completed) |
| Module layering | PASS | Test file only, no production changes |
| TDD compliance | PASS | Tagged `test` (pass-through); AC3 is self-verifying |
| KISS/YAGNI | PASS | Pure deletion/cleanup, no new abstractions |
| Premise challenge | PASS | Patches target symbols absent from v2 server.py — tests will error without cleanup |
| Pattern consistency | PASS | Standard test cleanup |
| Security surface | PASS | No new system boundaries |
| Single domain | PASS | Knowledge domain only |

### Codebase Evidence
- `server.py` AppContext (line 367): fields are conn, source_store, query_facade, graph_store_v2, content_store, enrichment_store, source_store_v2, ingest_coordinator, vector_store, refresh_orchestrator. No query_service/ingest_pipeline/structured_extractor.
- `server.py` imports (line 42): QdrantVectorStore still present. init_db, GraphStore, BgeM3EmbeddingProvider, KnowledgeQueryService, GraphAugmentedRetriever, EntityExtractor, IntraDocGraphBuilder are ALL absent.
- `app_lifespan` (line 422): v2-only — no copilot_auth, no API key branch, no LLMExtractor.
- Both autouse fixtures (lines 1242, 1450) patch 6 symbols — 5 are dead.
- Inline patches for EntityExtractor (line 1632) and IntraDocGraphBuilder (line 1654) also target absent symbols.

### Challenge Results
- Challenger: reconsider (confidence 0.64)
- Finding: AC1 omitted EntityExtractor and IntraDocGraphBuilder patches (also dead in server.py)
- Architect response: accepted — refined AC1 to include both symbols. Other challenger concerns (scope vs proof surface, unnumbered AC) dismissed: AC3 is a regression guard covering the whole file, and kanban stores AC as an ordered array (numbering is positional).

### Proof-Bundle Validation
- Planner assignment: smoke
- Final bundle: smoke
- Test-writer: PROCEED

### AC Refinement
Added `EntityExtractor` and `IntraDocGraphBuilder` to AC1 — both are patched in the in-scope sections (lines 1632, 1654) against symbols absent from v2 server.py.

### Verdict: APPROVE
### Action Taken: Refined AC1 to include 2 missing dead symbols, advanced backlog → todo.

[[2026-05-28T02:03:19+02:00]]
## Test-Writer Notes
- Non-implementation task (tagged `test`) — no new RED tests applicable.
- Task is test-file cleanup: remove dead patches and assertions from `tests/test_server.py`. Builder will edit the existing test file directly.
- Passing through to builder.

[[2026-05-28T02:42:48+02:00]]
## Builder Notes
- Implementation: tests/test_server.py
- Updated both merged knowledge fixtures to patch only `owlbear_mcp_knowledge.server.QdrantVectorStore`.
- Removed stale tests that patched removed knowledge symbols or accessed removed AppContext fields.
- Deleted obsolete regression class that patched removed `EntityExtractor`/`IntraDocGraphBuilder` symbols.
- AC1/AC2 verification: no remaining patches for `init_db`, `GraphStore`, `BgeM3EmbeddingProvider`, `KnowledgeQueryService`, `GraphAugmentedRetriever`, `EntityExtractor`, or `IntraDocGraphBuilder`; no remaining accesses to `ctx.query_service`, `ctx.ingest_pipeline`, or `ctx.structured_extractor` in `tests/test_server.py`.
- Quality evidence:
  - quality-runner scoped (`tests/test_server.py`): 57 passed, 9 failed, 0 errors; ruff clean.
  - Direct pytest confirmation (`uv run pytest tests/test_server.py -q`): 57 passed, 9 failed, 0 errors.
  - Remaining failures are in out-of-scope top mcp-kanban section:
    - 7x `TestFromAC_StatusNamesDictFormBug::*` with `TypeError: 'NoneType' object is not callable` at `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py:515`
    - `TestFromAC_FunctionRemoval::test_apply_tool_exclusions_not_in_server_module` assertion at `tests/test_server.py:1097`
    - `TestFromAC_OutputSchemaPreserved::test_patch_params_applies_enum_and_description` `KeyError: 'enum'` at `tests/test_server.py:1176`
- Commit: `1a2c2977`

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | architect | Refine AC3 to an in-scope test selection for the two knowledge merged sections, or explicitly expand #1908 scope to include mcp-kanban section failures. | tests/test_server.py | Full-file run after cleanup is still 57 passed / 9 failed in out-of-scope sections. |
| 2 | architect | If AC3 remains full-file (`pytest tests/test_server.py`), create and sequence prerequisite tasks for the 9 mcp-kanban-section failures before redispatching #1908. | tests/test_server.py; serve/mcp-kanban/src/owlbear_mcp_kanban/server.py | Failing tests listed above; root causes at server.py:515 and tests/test_server.py:1097,1176. |

[[2026-05-28T02:53:03+02:00]]
## Architecture Re-Review (AC3 Refinement)

### Issue
AC3 originally required `pytest tests/test_server.py passes (0 failures, 0 errors)` — a full-file gate. Builder demonstrated AC1/AC2 complete (commit `1a2c2977`) but 9 pre-existing failures in the out-of-scope mcp-kanban section block AC3.

This violates w-arch-review Step 2 criterion 5: "Before defining must-pass durable-suite gates in AC, run a suite-health pre-check and explicitly scope out known pre-existing failures unrelated to the current task."

### AC3 Refinement
Old: `pytest tests/test_server.py passes (0 failures, 0 errors)`
New: `pytest tests/test_server.py -k "not (StatusNamesDictFormBug or FunctionRemoval or OutputSchemaPreserved)" passes (0 failures, 0 errors)` — excludes 9 pre-existing mcp-kanban-section failures unrelated to this task.

### Rationale
- Task scope explicitly states "Out-of-scope: the mcp-kanban section at the top of test_server.py"
- All 9 failures are in mcp-kanban test classes (`TestFromAC_StatusNamesDictFormBug`, `TestFromAC_FunctionRemoval`, `TestFromAC_OutputSchemaPreserved`)
- Builder evidence confirms 57 passed / 0 knowledge-section failures after cleanup
- Separate tasks should address the mcp-kanban test rot

### Verdict: APPROVE (AC3 refinement)
### Action Taken: Scoped AC3 to exclude pre-existing out-of-scope failures, re-advanced backlog → todo.

[[2026-05-28T03:18:44+02:00]]
## Test-Writer Notes
- Non-implementation task (tagged `test`) — second pass-through after AC3 refinement.
- AC verification (live, pre-advance):
  - AC1: `grep` for all 7 dead symbols in `tests/test_server.py` → 0 matches ✓
  - AC2: `grep` for removed AppContext fields → 0 matches ✓
  - AC3: `pytest tests/test_server.py -k "not (StatusNamesDictFormBug or FunctionRemoval or OutputSchemaPreserved)"` → 56 passed, 0 failures, 0 errors ✓
- Builder's commit `1a2c2977` satisfies all refined ACs. Builder can advance directly to review.

[[2026-05-28T03:50:27+02:00]]
## Builder Notes
- Mode: non-implementation pass-through (per latest Test-Writer Notes for tagged `test` cleanup task).
- Code changes this pass: none.
- Existing implementation retained from prior builder commit: `1a2c2977` (`tests/test_server.py`).
- AC1 verification: `rg -n "init_db|GraphStore|BgeM3EmbeddingProvider|KnowledgeQueryService|GraphAugmentedRetriever|EntityExtractor|IntraDocGraphBuilder" tests/test_server.py` -> no matches.
- AC2 verification: `rg -n "ctx\.query_service|ctx\.ingest_pipeline|ctx\.structured_extractor" tests/test_server.py` -> no matches.
- AC3 verification (quality-runner, scoped): `pytest tests/test_server.py -k "not (StatusNamesDictFormBug or FunctionRemoval or OutputSchemaPreserved)"` -> 56 passed, 0 failed, 0 errors.
- Lint (quality-runner): ruff clean (`clean: true`, `ruff: 0`).
- Coverage report from scoped proof: 36% overall (non-gating for this smoke/non-implementation pass-through).

[[2026-05-28T04:01:04+02:00]]
## Review Evidence
- Verdict: PASS
- PASS confirmation: PASS #1908 to docs | AC mapped to code and evidence sufficient.
- AC evidence map:

| AC Line | Code Evidence | Test Evidence | Status |
|---|---|---|---|
| 1 | `tests/test_server.py:1232` and `tests/test_server.py:1335` are the only remaining `owlbear_mcp_knowledge.server.*` patches, both `QdrantVectorStore`; scoped searches for `init_db`, `GraphStore`, `BgeM3EmbeddingProvider`, `KnowledgeQueryService`, `GraphAugmentedRetriever`, `EntityExtractor`, and `IntraDocGraphBuilder` returned no matches in `tests/test_server.py`; latest builder verification recorded this exact `rg -n` proof in task body line 151. | Structural proof is appropriate for this cleanup AC: the forbidden-symbol search would fail on any remaining stale patch/import reference. | PASS |
| 2 | Scoped search for `ctx.query_service`, `ctx.ingest_pipeline`, and `ctx.structured_extractor` returned no matches in `tests/test_server.py`; latest builder verification recorded this exact `rg -n` proof in task body line 152. | Structural proof is appropriate for this cleanup AC: any surviving removed-field access would be caught by the scoped search. | PASS |
| 3 | The excluded failure classes are confined to the out-of-scope mcp-kanban section at `tests/test_server.py:686`, `tests/test_server.py:1088`, and `tests/test_server.py:1134`; the in-scope knowledge section starts at `tests/test_server.py:1230` and contains the retained knowledge tests at `tests/test_server.py:1242`, `tests/test_server.py:1345`, `tests/test_server.py:1372`, `tests/test_server.py:1407`, and `tests/test_server.py:1433`. | Builder quality evidence is sufficient for a `smoke` bundle: task body line 153 records `pytest tests/test_server.py -k "not (StatusNamesDictFormBug or FunctionRemoval or OutputSchemaPreserved)"` with `56 passed, 0 failed, 0 errors`, and line 154 records `ruff clean`. | PASS |
- Checklist verdict:
  - AC to code: PASS
  - Test to AC: PASS
  - Proof sufficiency: PASS
  - Safety and security: PASS (test-only cleanup; no new input, auth, storage, or integration surface introduced)

## Observations
- No blocking findings.
- This task is a `smoke` / non-implementation cleanup pass, so challenger and code-reader escalation was not required by the review contract.
- Coverage remained non-gating for this task and does not undermine the AC-specific proof above.

[[2026-05-28T04:11:01+02:00]]
## Docs Gate

### Checklist

| Item | Result | Evidence |
|------|--------|----------|
| README Verification | N/A | Changed file is `tests/test_server.py` (root-level test, not `serve/{pkg}/src/**` or `serve/{pkg}/tests/**`). No production code changed. `serve/mcp-knowledge/README.md` documents public tool interface only — no reference to removed symbols. `serve/knowledge/README.md` references these symbols as part of the still-existing library API (unaffected by this task). |
| External Attribution | N/A | Pure test cleanup; no external sources used. |
| Research Doc | N/A | No research artifact for this task. |
| Deletion Detection | N/A | Test fixtures/classes removed from `tests/test_server.py`; none documented in any README. No orphaned references. |

### Files Updated
None — no docs impact.

### Scratch Cleanup
No `.owlbear/scratch/1908-*` files found.

[[2026-05-28T04:27:12+02:00]]
## Audit
### Regression Detection
- AC3 scoped command (pytest tests/test_server.py -k exclusion): 56 passed, 0 failed
- Full file: 57 passed, 9 failed (all in out-of-scope mcp-kanban section, pre-existing)
- Ruff: clean on tests/test_server.py
- Lint violations in serve/knowledge/ are from #1909/#1910, not this task
- Regression verdict: PASS

### Intent Verification
- Scope alignment: PASS (single file tests/test_server.py, 217 deletions of dead patches in knowledge sections)
- Purpose match: PASS (removal of legacy symbol patches matches stated objective)
- Extraneous scope: none
- Boundary check: function-level behavior verification deferred to reviewer

### Architect Quality: 4/5
AC lines are specific (named symbols, named fields, exact pytest command). AC3 required mid-pipeline refinement after builder surfaced pre-existing failures, but architect responded promptly. Challenger caught 2 missing dead symbols and architect incorporated them.

### Commit Integrity
- Upstream commit presence: PASS (1a2c2977, 1 file, 8 insertions / 217 deletions)
- Commit message format: PASS (test: clean legacy knowledge patches in test_server (#1908, builder))
- No uncommitted deliverables

### Deduction Breakdown
No deductions applied.

### Confidence: 1.00
### Action: archive
