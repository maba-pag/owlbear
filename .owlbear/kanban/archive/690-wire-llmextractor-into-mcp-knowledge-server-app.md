---
id: 690
title: Wire LLMExtractor into MCP knowledge server app_lifespan
status: archived
priority: medium
created: 2026-04-08T21:06:20.2270499+02:00
updated: 2026-04-09T19:32:05.1098042+02:00
started: 2026-04-09T19:32:05.1098042+02:00
completed: 2026-04-09T19:32:05.1098042+02:00
tags:
    - scope:mcp-knowledge
    - ' type:feature'
    - ' source:research'
parent: 676
depends_on:
    - 699
    - 689
class: standard
---

## Context

Research for #676. The MCP server's `app_lifespan()` creates `EntityExtractor(model)` without injecting a `StructuredExtractor`. After LLMExtractor exists (sibling task), wire it in.

## Acceptance Criteria

- [ ] AC1: `app_lifespan()` creates `LLMExtractor(model)` and passes it as `EntityExtractor(extractor=llm_extractor)`
- [ ] AC2: `owlbear-mcp-knowledge` declares dependency on `owlbear-knowledge[llm]` (optional extras)
- [ ] AC3: Ingest a test document and verify `get_stats` shows entity_count > 0 and edge_count > 0
- [ ] AC4a: `app_lifespan()` creates `GraphAugmentedRetriever(vs, gs, emb)` and passes it as `KnowledgeQueryService(retriever=...)`
- [ ] AC4b: `search_knowledge` response dicts include `entity_type` field (already in `StructuredSearchResult`, currently dropped by the list comprehension)
- [ ] AC5: Graceful degradation — if OWLBEAR_MODEL is unset or LLM unavailable, ingestion succeeds (vector-only fallback)

## Affected Files

- `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py`
- `serve/mcp-knowledge/pyproject.toml`
- `serve/mcp-knowledge/tests/test_ingest_graph_tools.py`

[[2026-04-09]] Thu 05:09
## Research
- Research doc: .owlbear/research/wire-llmextractor-mcp-knowledge.md
- Sources: 7 studied, 5 high-relevance (all codebase)
- Recommendation: Wire LLMExtractor + GraphAugmentedRetriever in app_lifespan, try/except for graceful degradation (confidence: 0.85)
- Key findings:
  1. Wiring is ~15 LOC across 2 files (server.py + pyproject.toml); DI slot is pre-built
  2. AC4 has scope ambiguity: "graph expansion context" needs GraphAugmentedRetriever wiring + entity_type in SearchResult (Option A+B); full expansion text output (Option C) is a separate enhancement
  3. Graceful degradation via try/except around LLMExtractor import handles missing-dep and construction-failure cases; runtime failures handled by LLMExtractor itself (#689 AC5)
  4. METADATA DEFECTS: depends_on should be [699, 689], parent should be 676, tag should be scope:mcp-knowledge — orchestrator must fix before dispatch
- Follow-up tasks created: none (decomposition from #676 covers all work)
- Decision requests: none — T1 autonomous
- Challenge: FALLBACK — challenger agent not available

[[2026-04-09]] Thu 05:30
## Architecture Review

### Metadata Fixes Applied
- `depends_on`: [676] → [699, 689] — #689 creates LLMExtractor, #699 is TDD RED
- `parent`: null → 676
- `tags`: scope:knowledge → scope:mcp-knowledge

### AC Refinement
- AC4 split into AC4a (wire GraphAugmentedRetriever) and AC4b (include entity_type in search response) — original "graph expansion context" was ambiguous per research finding #2

### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | All changes are "activate graph features in MCP server" — one logical unit |
| Interface clarity | PASS (after refine) | AC4 was vague; split into AC4a/AC4b with specific wiring targets |
| Dependency correctness | PASS (after fix) | Fixed depends_on to [699, 689]; #689=LLMExtractor impl, #699=TDD RED tests |
| Module layering | PASS | MCP server → knowledge package (correct direction) |
| TDD compliance | PASS | #699 is TDD RED predecessor |
| KISS/YAGNI | PASS | Wiring existing DI slots; no new abstractions |
| Premise challenge | PASS | EntityExtractor is currently a no-op stub; this task activates it |
| Pattern consistency | PASS | Follows existing app_lifespan DI pattern, try/except graceful degradation |
| Security surface | PASS | No new system boundaries; LLM calls go through existing model infrastructure |
| Single domain | PASS | scope:mcp-knowledge only |

### Failure Mode Map
| Codepath | Failure Mode | Exception | Handled? | User Impact |
|----------|-------------|-----------|----------|-------------|
| LLMExtractor import | pydantic-ai not installed | ImportError | Yes (AC5 try/except → extractor=None) | Vector-only mode |
| LLMExtractor(model) | construction failure | Exception | Yes (AC5 same try block) | Vector-only mode |
| GraphAugmentedRetriever.retrieve | vector store error | Exception | Yes (KnowledgeQueryService wraps in try/except) | Empty results |

### Codebase Evidence
- EntityExtractor DI slot: `serve/knowledge/src/owlbear_knowledge/extractor.py` L66-73 (`extractor: StructuredExtractor | None = None`)
- KnowledgeQueryService retriever slot: `serve/knowledge/src/owlbear_knowledge/query_service.py` L57 (`retriever: GraphAugmentedRetriever | None = None`)
- search_knowledge drops entity_type: `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py` L227 (dict comprehension only includes title/score/snippet)
- GraphAugmentedRetriever: `serve/knowledge/src/owlbear_knowledge/retrieval.py` L36-43 (constructor matches available components vs/gs/emb)

### Challenge Results
- Challenger: FALLBACK — challenger agent not available
- Architect response: Proceeded with high confidence (0.90) — all DI slots pre-built, wiring is mechanical, research corroborates

### Verdict: APPROVE (with refinements applied)
### Action Taken: Fixed metadata defects (depends_on, parent, tags), refined AC4 into AC4a/AC4b with specific wiring targets, advanced to todo

[[2026-04-09]] Thu 15:29
## Test-Writer Notes
- Test file: serve/mcp-knowledge/tests/test_ingest_graph_wiring.py
- Classes: TestFromAC_LLMExtractorWiring, TestFromAC_IngestWithLLMExtractor, TestFromAC_GraphAugmentedRetrieverWiring, TestFromAC_SearchKnowledgeEntityType, TestFromAC_LLMExtractorImportError, TestFromAC_PyprojectDependency, TestFromAC_GracefulDegradation
- Tests per category: happy 4, edge 5, error 4, boundary 2
- Total: 15 tests, all FAIL (AttributeError — LLMExtractor/GraphAugmentedRetriever not in server.py namespace; AssertionError — entity_type missing from search_knowledge response; AssertionError — owlbear-knowledge[llm] not in pyproject.toml)
- ruff: clean

### AC Coverage
| AC | Tests | Class |
|----|-------|-------|
| AC1: LLMExtractor wired into EntityExtractor | 3 | TestFromAC_LLMExtractorWiring |
| AC2: pyproject.toml declares owlbear-knowledge[llm] | 1 | TestFromAC_PyprojectDependency |
| AC3: ingest → get_stats shows entity_count > 0 and edge_count > 0 | 1 | TestFromAC_IngestWithLLMExtractor |
| AC4a: GraphAugmentedRetriever wired into KnowledgeQueryService | 3 | TestFromAC_GraphAugmentedRetrieverWiring |
| AC4b: search_knowledge response dicts include entity_type field | 3 | TestFromAC_SearchKnowledgeEntityType |
| AC5: graceful degradation (ImportError, generic Exception, OWLBEAR_MODEL unset) | 4 | TestFromAC_LLMExtractorImportError + TestFromAC_GracefulDegradation |

### Notes
- File originally created by task #699 (TDD RED predecessor); extended with AC2 + AC5 boundary tests that were missing.
- Commit: 21cd09a

[[2026-04-09]] Thu 16:16
## Builder Notes

### Files Changed (2)
- `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py` — added imports, wired LLMExtractor + GraphAugmentedRetriever in app_lifespan, added entity_type to SearchResult TypedDict and search_knowledge response
- `serve/mcp-knowledge/pyproject.toml` — `owlbear-knowledge` → `owlbear-knowledge[llm]`

### Implementation Summary
- Imported `LLMExtractor` from `owlbear_knowledge.llm_extractor` and `GraphAugmentedRetriever` from `owlbear_knowledge.retrieval` at module level (required for patch() targets in tests)
- In `app_lifespan`: moved `model = os.environ.get(...)` before extractor construction; wrapped `LLMExtractor(model)` + `EntityExtractor(model, extractor=llm_extractor)` in `try/except Exception` block — on any failure falls back to `EntityExtractor(model)` (no-op, vector-only mode)
- Created `GraphAugmentedRetriever(vs, gs, emb)` and passed as `retriever=gar` kwarg to `KnowledgeQueryService`
- Added `entity_type: str | None` field to `SearchResult` TypedDict and `entity_type=r.entity_type` to the search_knowledge dict comprehension
- 1 ruff I001 auto-fixed (import ordering after inserting new imports)

### Test Results
- **15 passed, 0 failed** (serve/mcp-knowledge/tests/test_ingest_graph_wiring.py)
- RED verified before implementation: 15 failures (12 AttributeError, 3 AssertionError/KeyError)
- Coverage: 60% on server.py (all new lines covered; uncovered lines are pre-existing tool handlers outside this task's scope)

### Lint Status
- ruff: **clean** (All checks passed)

### Evidence Summary
- AC1: `LLMExtractor(model)` called, passed as `extractor=` to `EntityExtractor` — 3 tests ✓
- AC2: `pyproject.toml` declares `owlbear-knowledge[llm]` — 1 test ✓
- AC3: ingest → entity_count > 0 and edge_count > 0 via mocked LLMExtractor — 1 test ✓
- AC4a: `GraphAugmentedRetriever(vs, gs, emb)` created and passed as `retriever=` to `KnowledgeQueryService` — 3 tests ✓
- AC4b: `search_knowledge` response dicts include `entity_type` field — 3 tests ✓
- AC5: ImportError and RuntimeError from LLMExtractor → applifespan still yields valid context, EntityExtractor constructed without extractor= — 4 tests ✓

[[2026-04-09]] Thu 16:48
## Review Evidence

### Test Results
- pytest: 15 passed, 0 failed (serve/mcp-knowledge/tests/test_ingest_graph_wiring.py)
- runner-verified; not taken from builder self-report

### Lint
- ruff: clean (0 violations)

### Coverage
- server.py: 60% overall. Builder confirmed all new lines covered; uncovered lines are pre-existing tool handlers outside task scope.

### Builder Process Quality
- 1 Builder Notes section. No retry loop. CLEAN.

### TestFromAC Integrity
- No TestFromAC_* tests were modified or removed by the builder. File is additive-only from the test-writer's commit.

### AC Compliance Table

| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| AC1: app_lifespan creates LLMExtractor(model), passes as EntityExtractor(extractor=...) | server.py diff L164–166: try block constructs `LLMExtractor(model)` and `EntityExtractor(model, extractor=llm_extractor)` | TestFromAC_LLMExtractorWiring (3 tests, all pass) | PASS |
| AC2: owlbear-mcp-knowledge declares owlbear-knowledge[llm] | pyproject.toml diff: `owlbear-knowledge` → `owlbear-knowledge[llm]` | TestFromAC_PyprojectDependency (1 test, passes) | PASS |
| AC3: ingest → entity_count > 0 and edge_count > 0 | server.py wiring connects mocked LLMExtractor returning ExtractionResult(2 entities, 1 edge); get_stats reflects counts | TestFromAC_IngestWithLLMExtractor (1 test, passes) | PASS |
| AC4a: GraphAugmentedRetriever(vs, gs, emb) passed as KnowledgeQueryService(retriever=...) | server.py diff L170–172: `gar = GraphAugmentedRetriever(vs, gs, emb)` + `KnowledgeQueryService(..., retriever=gar)` | TestFromAC_GraphAugmentedRetrieverWiring (3 tests, pass) ⚠️ see FAIL below | PASS (impl correct; test WEAK) |
| AC4b: search_knowledge response dicts include entity_type field | server.py diff L236: `entity_type=r.entity_type` added to dict; TypedDict updated at L49 | TestFromAC_SearchKnowledgeEntityType (3 tests, all pass) | PASS |
| AC5: graceful degradation on LLMExtractor failure | server.py diff L164–168: `except Exception` catches ImportError/RuntimeError → fallback `EntityExtractor(model)` with no extractor= | TestFromAC_LLMExtractorImportError + TestFromAC_GracefulDegradation (4 tests, all pass) | PASS |

### FAIL — Step 5.3 Test Quality: WEAK assertion

**File:** serve/mcp-knowledge/tests/test_ingest_graph_wiring.py

**Location:** `TestFromAC_GraphAugmentedRetrieverWiring.test_graph_augmented_retriever_receives_vs_gs_emb` (approximately lines 262–274)

**Assertion pattern (WEAK):**
```python
args, kwargs = mock_gar_cls.call_args
positional = list(args)
assert mock_vs in positional or kwargs.get("vector_store") is mock_vs
assert mock_gs in positional or kwargs.get("graph_store") is mock_gs
assert mock_emb in positional or kwargs.get("embedding_provider") is mock_emb
```

**Why WEAK — mutation reasoning:**
`GraphAugmentedRetriever.__init__` signature (retrieval.py L44–46): positional order is `(vector_store, graph_store, embedding_provider, *, ...)`. If the implementation were `GraphAugmentedRetriever(gs, vs, emb)` (vs/gs transposed), all three assertions still pass: `mock_vs in positional` is True at index 1, `mock_gs in positional` is True at index 0. The argument ordering — which maps to which component — is never verified.

**Fix (test-writer):**
```python
# Replace the three `in positional` assertions with position-specific verification:
mock_gar_cls.assert_called_once_with(mock_vs, mock_gs, mock_emb)
# or equivalently:
assert args == (mock_vs, mock_gs, mock_emb)
```

### Informational (do not block)

1. **SSRF in pre-existing `_web_read`** — not introduced by this task (not in diff); `_web_read` accepts user-controlled URL with only scheme validation (http/https), no private IP range blocklist. Should be addressed in a separate task.
2. **Doc string AC numbering in test module header** — header maps AC2→task's AC3, AC3a/b→AC4a/b, AC4→AC5. Class names are correct; navigating to classes is unambiguous.
3. **Missing LLMExtractor patch in TestFromAC_GraphAugmentedRetrieverWiring** — all three tests omit `patch("owlbear_mcp_knowledge.server.LLMExtractor")`. In CI without pydantic-ai, the try/except fallback fires silently — tests still pass and still verify GAR construction. Non-hermetic but not a blocker.
4. **Env-var model string assertion (line 104–107)** — uses `list(kwargs.values())` losing key semantics. LAX, but catches absent or wrong model name. No compensating test needed.

### Deductions
- Step 5.3 WEAK assertion in TestFromAC_GraphAugmentedRetrieverWiring: -0.15

### Verdict
confidence: .75 → FAIL #690 → todo

**Action:** reject to todo — test-writer adds position-specific assertion to test_graph_augmented_retriever_receives_vs_gs_emb

[[2026-04-09]] Thu 16:54
## Test-Writer Notes
- Retry: strengthened weak assertion in `TestFromAC_GraphAugmentedRetrieverWiring.test_graph_augmented_retriever_receives_vs_gs_emb`
- Replaced 11-line `in positional` membership checks (which passed even with transposed vs/gs args) with `mock_gar_cls.assert_called_once_with(mock_vs, mock_gs, mock_emb)` — exact positional-order verification per reviewer's direction
- 15 existing tests preserved, all pass (builder already implemented)
- ruff: clean
- Commit: b512053

[[2026-04-09]] Thu 17:02
## Builder Notes (retry)

### Re-verification After Test-Writer Retry
- Test-writer strengthened `test_graph_augmented_retriever_receives_vs_gs_emb` — replaced membership checks with `mock_gar_cls.assert_called_once_with(mock_vs, mock_gs, mock_emb)` (exact positional-order assertion per reviewer direction)
- Implementation unchanged; no new code needed

### Test Results
- **15 passed, 0 failed** (serve/mcp-knowledge/tests/test_ingest_graph_wiring.py)
- Strengthened assertion passes — positional order `(vs, gs, emb)` is correct in server.py impl

### Lint Status
- ruff: **clean** (All checks passed)

[[2026-04-09]] Thu 17:19
## Review Evidence

### Test Results
- pytest: **15 passed, 0 failed** (serve/mcp-knowledge/tests/test_ingest_graph_wiring.py)
- Independently verified via quality-runner — not from builder self-report.

### Lint
- ruff: **clean** (exit 0, 0 violations)

### Coverage
- server.py: 60% overall. All lines added by this task are covered. Uncovered lines are pre-existing tool handlers outside task scope.

### Builder Process Quality
- 2 `## Builder Notes` sections (original + retry). Retry was passthrough — no code change needed, only re-verification. **CLEAN.**

### TestFromAC Integrity
| Original Test | Change Made | Assessment |
|---------------|-------------|------------|
| TestFromAC_GraphAugmentedRetrieverWiring.test_graph_augmented_retriever_receives_vs_gs_emb | Replaced 11-line `in positional` membership checks with `mock_gar_cls.assert_called_once_with(mock_vs, mock_gs, mock_emb)` (per reviewer direction) | **STRENGTHENED** |
| All other TestFromAC_* methods | None | PRESERVED |

### Pass 1 — CRITICAL

#### Step 5.0 — AC-to-Test Coverage
| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---------|-------------|---------------------------|---------|
| AC1: app_lifespan creates LLMExtractor(model), passes as EntityExtractor(extractor=...) | TestFromAC_LLMExtractorWiring (3 tests) | Yes — 2 separate mock checks: `mock_llm_cls.assert_called_once()` and `kwargs["extractor"] is mock_llm_instance` | COVERED |
| AC2: pyproject.toml declares owlbear-knowledge[llm] | TestFromAC_PyprojectDependency (1 test) | Yes — reads file, asserts string presence | COVERED |
| AC3: ingest → entity_count > 0 and edge_count > 0 | TestFromAC_IngestWithLLMExtractor (1 test) | Yes — asserts counts > 0 via mocked LLMExtractor returning ExtractionResult | COVERED |
| AC4a: GraphAugmentedRetriever(vs, gs, emb) passed as KnowledgeQueryService(retriever=...) | TestFromAC_GraphAugmentedRetrieverWiring (3 tests) | Yes — `assert_called_once_with(mock_vs, mock_gs, mock_emb)` catches transposed args; retriever kwarg assertion on KnowledgeQueryService | COVERED (STRENGTHENED per prior cycle) |
| AC4b: search_knowledge response dicts include entity_type field | TestFromAC_SearchKnowledgeEntityType (3 tests) | Yes — asserts key presence, value match, and None case | COVERED |
| AC5: graceful degradation on ImportError / generic Exception | TestFromAC_LLMExtractorImportError + TestFromAC_GracefulDegradation (4 tests) | Yes — tests each Exception type; also tests OWLBEAR_MODEL unset | COVERED |

#### Step 5.1 — Security
- No hardcoded secrets, no injection vectors, no new system boundaries.
- Pre-existing `_web_read` SSRF (noted in prior cycle) not introduced by this task.

#### Step 5.3 — Test Quality
After retry strengthen:
| Dimension | Rating | Evidence |
|-----------|--------|---------|
| Assertion specificity | STRONG | `assert_called_once_with(mock_vs, mock_gs, mock_emb)` catches argument transposition; `kwargs["extractor"] is mock_llm_instance` is identity-level |
| Negative/error paths | STRONG | 4 tests cover ImportError, generic Exception, unset env var |
| Mutation resistance | STRONG | Transposed vs/gs/emb → FAIL; missing extractor= kwarg → FAIL; wrong entity_type value → FAIL |
| Test independence | STRONG | All use pytest fixtures + context managers; no shared mutable state |
| Descriptive names | STRONG | `test_entity_extractor_receives_llm_extractor_as_extractor_kwarg`, etc. |

#### Steps 5.4–5.7 — All clear
- Data safety: no unvalidated LLM output; clean DI
- Gap analysis: all non-trivial code paths have tests
- Necessity: LLM dependency is the purpose of this task, not speculative
- Loop detection: CLEAN (2 sections, retry is passthrough variant)

### AC Compliance Table
| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| AC1: LLMExtractor wired into EntityExtractor | server.py L164–166: `try: llm_extractor = LLMExtractor(model); extractor = EntityExtractor(model, extractor=llm_extractor)` | TestFromAC_LLMExtractorWiring (3) | PASS |
| AC2: pyproject.toml declares owlbear-knowledge[llm] | serve/mcp-knowledge/pyproject.toml: `owlbear-knowledge[llm]` in dependencies | TestFromAC_PyprojectDependency (1) | PASS |
| AC3: ingest → entity_count > 0, edge_count > 0 | Wiring connects mocked LLMExtractor returning 2 entities/1 edge; get_stats returns counts | TestFromAC_IngestWithLLMExtractor (1) | PASS |
| AC4a: GraphAugmentedRetriever(vs, gs, emb) → KnowledgeQueryService(retriever=gar) | server.py L170-172: `gar = GraphAugmentedRetriever(vs, gs, emb)` + `KnowledgeQueryService(..., retriever=gar)` | TestFromAC_GraphAugmentedRetrieverWiring (3) | PASS |
| AC4b: search_knowledge response dicts include entity_type | server.py L236: `entity_type=r.entity_type` in dict comprehension; SearchResult TypedDict updated at L49 | TestFromAC_SearchKnowledgeEntityType (3) | PASS |
| AC5: graceful degradation on LLMExtractor failure | server.py L167-168: `except Exception: extractor = EntityExtractor(model)` | TestFromAC_LLMExtractorImportError + GracefulDegradation (4) | PASS |

### Pass 2 — Informational
1. Pre-existing `_web_read` SSRF (no private IP blocklist) — carry-forward from prior cycle; separate task recommended.
2. Missing `LLMExtractor` patch in AC4a tests — GAR construction tests pass without it; non-hermetic in CI without pydantic-ai but not a blocker.

### Deductions
None. All Pass 1 criteria met. The sole prior-cycle defect (WEAK positional-order assertion) was corrected by the test-writer in the retry with the exact fix prescribed.

### Verdict
confidence: .93 → PASS #690 → docs

[[2026-04-09]] Thu 17:22
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Behavior/API change | Yes | N/A (no doc update) | search_knowledge adds entity_type field; app_lifespan wires LLMExtractor+GAR. copilot-instructions.md read in full (~100 lines) — covers only project identity and branch structure; no MCP tool schemas or knowledge-server behavior documented. No update required. |
| 2 | Module docstrings | Yes | Verified / N/A | server.py modified. SearchResult TypedDict docstring "A single knowledge-base search result." accurate (doesn't enumerate fields). app_lifespan docstring accurate. search_knowledge docstring accurate. No updates needed. |
| 3 | External attribution | No | N/A | Research doc sources table: all 7 sources are internal codebase files. No external repos or articles cited. |
| 4 | CLI changes | No | N/A | MCP server wiring only; no CLI commands added or modified. |
| 5 | Research doc | Yes | Verified | .owlbear/research/wire-llmextractor-mcp-knowledge.md exists; linked in task body (2026-04-09 Thu 05:09 block). Follow-up tasks: none needed per research notes (decomposition from #676 covers all work). |

### Files Updated
None — documentation is accurate as-is.

### Scratch Files
None found matching `.owlbear/scratch/690-*`.

[[2026-04-09]] Thu 19:32
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| AC1: app_lifespan creates LLMExtractor(model), passes as EntityExtractor(extractor=...) | server.py L170-171: `llm_extractor = LLMExtractor(model)` + `EntityExtractor(model, extractor=llm_extractor)` in try block; 3 tests pass (TestFromAC_LLMExtractorWiring) | PASS |
| AC2: pyproject.toml declares owlbear-knowledge[llm] | pyproject.toml L6: `owlbear-knowledge[llm]` in dependencies; 1 test pass (TestFromAC_PyprojectDependency) | PASS |
| AC3: ingest → entity_count > 0 and edge_count > 0 | Wiring connects mocked LLMExtractor; 1 test pass (TestFromAC_IngestWithLLMExtractor) | PASS |
| AC4a: GraphAugmentedRetriever(vs, gs, emb) → KnowledgeQueryService(retriever=gar) | server.py L174-175: `gar = GraphAugmentedRetriever(vs, gs, emb)` + `KnowledgeQueryService(..., retriever=gar)`; 3 tests pass with strengthened positional-order assertion | PASS |
| AC4b: search_knowledge response includes entity_type | server.py L241: `entity_type=r.entity_type` in dict; SearchResult TypedDict has `entity_type: str | None`; 3 tests pass | PASS |
| AC5: graceful degradation | server.py L172-173: `except Exception` falls back to `EntityExtractor(model)` without extractor=; 4 tests pass (ImportError, RuntimeError, unset env var) | PASS |

### Test Results
- pytest (task-scoped): 15 passed, 0 failed
- pytest (full suite): 2915 passed, 129 failed, 3 errors — all failures are pre-existing, none in task scope (verified via git log on failing test files — last change was line-ending normalization)
- ruff: clean (0 violations)

### Commit Integrity
- `9789850` feat: enhance knowledge service with LLMExtractor and GraphAugmentedRetriever (server.py + pyproject.toml)
- `b512053` test: strengthen GAR positional-order assertion (#690, test-writer)
- `21cd09a` test: extend failing tests for LLM wiring (#690, test-writer)

### Architect Quality: 4/5
AC was originally adequate with one ambiguous item (AC4 "graph expansion context"). Architect correctly identified the ambiguity from research findings and split into AC4a/AC4b with specific wiring targets. Metadata defects (depends_on, parent, tags) also corrected during arch review. Solid upstream work.

### Deduction Breakdown
- AC lines with no evidence: 0 (-.00)
- Lint violations: 0 (-.00)
- AC quality score ≤ 3: No (4/5) (-.00)
- Missing reviewer evidence: No — two detailed review cycles (-.00)
- Full-suite failures in task scope: 0 (-.00)

### Confidence: .98
### Action: archive

## Commits
| Commit | Type | Files | Tasks |
|--------|------|-------|-------|
| ba6c12e | chore | kanban activity + task file | #690 |
