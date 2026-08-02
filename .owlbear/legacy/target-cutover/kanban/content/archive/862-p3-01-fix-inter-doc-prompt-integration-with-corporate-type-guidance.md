---
id: 862
title: 'P3-01: Fix inter-doc prompt integration with corporate type guidance'
status: archived
priority: medium
created: '2026-04-13T19:16:55.084666+00:00'
updated: '2026-04-15T19:55:50.811552+00:00'
tags:
- phase-3
- scope:knowledge
- deferred
parent: 772
depends_on: []
blocked: false
block_reason: null
claimed_by: null
claimed_at: null
---
## Context

InterDocGraphBuilder's `INTER_DOC_PROMPT` is defined but never used (dead code). The `_build_inter_prompt()` function sends only entity names — no types, descriptions, or corporate-type relationship guidance. The LLM lacks context to infer GOVERNS or SUPERSEDES_VERSION relationships.

See: .owlbear/research/772-interdocgraphbuilder-corporate-types.md (Gaps G1, G2, G7)

## Acceptance Criteria

- [ ] `INTER_DOC_PROMPT` is used as system prompt for inter-doc extraction (or replaced with a dedicated extractor)
- [ ] `_build_inter_prompt()` includes entity types and descriptions alongside names
- [ ] Corporate-type relationship guidance added to inter-doc prompt (GOVERNS: policy/standard → procedure; SUPERSEDES_VERSION: same entity across versions)
- [ ] Existing inter-doc tests still pass; new tests cover corporate type guidance in prompt

## Affected Files

- `serve/knowledge/src/owlbear_knowledge/inter_doc_graph_builder.py`

## Dependency

Deferred until Phase 1 entity model is proven via real corporate ingestion.

[[2026-04-13]]

## Research

- Research doc: .owlbear/research/862-inter-doc-prompt-integration.md
- Sources: 6 studied (all codebase-internal), 4 high-relevance
- Recommendation: Approach A — configurable `system_prompt` param in LLMExtractor (confidence: .85). 2-line change to `llm_extractor.py`, ~20 LOC in `inter_doc_graph_builder.py`, 4–6 new tests. No protocol change. DI pattern preserved.
- Follow-up tasks created: none — #862 AC already covers the full scope
- Decision requests: none (T1 — correctness fix for dead code + impoverished prompt)

[[2026-04-14]]

## Architecture Review

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | One concern: fix dead prompt + enrich context for inter-doc extraction |
| Interface clarity | PASS/FLAG | AC1 says "INTER_DOC_PROMPT is used as system prompt" — ambiguous in DI context. Builder receives extractor via DI, doesn't control system prompt. See builder guidance below for how to interpret AC1 as testable. |
| Dependency correctness | PASS | No deps needed; self-contained within owlbear_knowledge |
| Module layering | PASS | Changes within owlbear_knowledge package only. No cross-package violations. |
| TDD compliance | PASS | Will go through RED/GREEN pipeline |
| KISS/YAGNI | PASS | ~2 LOC in llm_extractor.py + ~20 LOC in inter_doc_graph_builder.py + 4-6 tests |
| Premise challenge | PASS | Verified: INTER_DOC_PROMPT defined at L31 but never referenced. _build_inter_prompt at L60 sends only bare names. Both are real defects. |
| Pattern consistency | PASS | Follows existing DI pattern. LLMExtractor already uses system_prompt internally; making it a constructor param is natural. Same {relation_types} format pattern as LLM_EXTRACTION_PROMPT. |
| Security surface | PASS | No new system boundaries. Prompt changes are internal to the knowledge package. |
| Single domain | PASS | scope:knowledge only |

### Affected Files Correction

Task body lists only `inter_doc_graph_builder.py`. Research doc explicitly identifies a 2-line change to `llm_extractor.py` (adding optional `system_prompt` parameter). Builder must also touch:

- `serve/knowledge/src/owlbear_knowledge/llm_extractor.py` — add `system_prompt: str = LLM_EXTRACTION_PROMPT` constructor parameter

### Builder Guidance for AC1

AC1 says: "INTER_DOC_PROMPT is used as system prompt for inter-doc extraction (or replaced with a dedicated extractor)"

In the DI context, this means:

1. `LLMExtractor.__init__` accepts `system_prompt: str = LLM_EXTRACTION_PROMPT` — backward-compatible, single production call site in `server.py:194` uses default
2. `INTER_DOC_PROMPT` content is updated to be ready for use (corporate guidance, {relation_types} placeholder)
3. Test verifies: `LLMExtractor(model="test", system_prompt=INTER_DOC_PROMPT.format(relation_types=...))` creates a working extractor

The actual wiring (caller creates LLMExtractor with INTER_DOC_PROMPT and passes to InterDocGraphBuilder) is #864's scope. This task enables it.

### Codebase Evidence

- `INTER_DOC_PROMPT`: `inter_doc_graph_builder.py:31-52` — defined, never imported/called
- `_build_inter_prompt()`: `inter_doc_graph_builder.py:60-62` — `f"({a.name}, {b.name})"` only
- `LLMExtractor.__init__`: `llm_extractor.py:82-86` — hardcodes `system_prompt=LLM_EXTRACTION_PROMPT`
- `Entity` model: `models.py:88-97` — has `entity_type` (EntityType) and `description` (str, default="")
- Production LLMExtractor calls: only `server.py:194` — backward-compatible with optional param
- Production InterDocGraphBuilder calls: none — no call site exists yet (#864 wiring)
- Existing tests: 20+ in test_inter_doc_graph_builder.py, none verify prompt content

### Challenge Results

- Challenger: FALLBACK — no challenger agent in available roster
- Architect response: Proceeded; high confidence from codebase evidence. Backward-compatible change, no protocol violation, follows established DI pattern.

### Verdict: APPROVE

### Action Taken: Advanced #862 to todo. Flagged missing affected file (llm_extractor.py) and clarified AC1 interpretation for builder

[[2026-04-14]]

## Premise Invalidated

pydantic-ai dependency and LLMExtractor class removed from the project (2026-04-14). Research recommendation (configurable `system_prompt` in LLMExtractor) is no longer viable. When Phase 3 is picked up, this task needs re-scoping — either wire INTER_DOC_PROMPT directly into EntityExtractor, or implement a new lightweight extraction callable without pydantic-ai. Architecture review and research notes above are stale.

[[2026-04-15]]

## Test-Writer Notes

- Test file: tests/test_inter_doc_graph_builder_862.py
- Classes: TestFromAC_InterDocPromptIntegration
- Tests per category: happy 9, edge 1, error 0, boundary 0, backward-compat 1
- Total: 11 tests, all FAIL
- ruff: clean

### AC Coverage

| AC | Tests |
|----|-------|
| AC1: LLMExtractor accepts optional `system_prompt` param | `test_llm_extractor_accepts_system_prompt_kwarg` (TypeError), `test_llm_extractor_default_system_prompt_is_llm_extraction_prompt` (AttributeError), `test_llm_extractor_custom_system_prompt_sent_as_system_message` (TypeError) |
| AC2: `_build_inter_prompt()` includes entity types + descriptions | `test_build_inter_prompt_includes_entity_type_in_extractor_call`, `test_build_inter_prompt_includes_entity_description_in_extractor_call`, `test_build_inter_prompt_includes_types_for_both_entities_in_pair`, `test_build_inter_prompt_empty_description_does_not_omit_entity_type` |
| AC3: Corporate-type guidance in INTER_DOC_PROMPT | `test_inter_doc_prompt_has_governs_guidance_prose`, `test_inter_doc_prompt_governs_guidance_references_policy_or_standard`, `test_inter_doc_prompt_has_supersedes_version_guidance_prose`, `test_inter_doc_prompt_supersedes_version_guidance_references_versions` |
| AC4: New tests cover corporate guidance | All AC3 tests above |

### Fail Evidence (pytest -v output)

- AC1: `TypeError: LLMExtractor.__init__() got an unexpected keyword argument 'system_prompt'`; `AttributeError: 'LLMExtractor' object has no attribute '_system_prompt'`
- AC2: `AssertionError: assert 'policy' in 'scope: test\nEntity pairs: (Risk Policy, Risk Policy)'`
- AC3: `AssertionError: INTER_DOC_PROMPT must contain governs guidance prose, not just rely on {relation_types} placeholder`

### Premise Invalidation Note

The 2026-04-14 "Premise Invalidated" note is stale — `LLMExtractor` remains in the codebase using the `openai` SDK (not pydantic-ai). The arch-review approach (add `system_prompt` param to `LLMExtractor`) is viable.
[[2026-04-15]]

## Builder Notes

### Files Changed

- `serve/knowledge/src/owlbear_knowledge/llm_extractor.py` — added `system_prompt: str = LLM_EXTRACTION_PROMPT` constructor param, stored as `self._system_prompt`, used in `extract()` system message
- `serve/knowledge/src/owlbear_knowledge/inter_doc_graph_builder.py` — enriched `INTER_DOC_PROMPT` with governs/supersedes_version corporate guidance prose; `_build_inter_prompt()` now emits entity_type.value and description for each entity in every pair

### Test Results

- **Task tests**: 11/11 passed (TestFromAC_InterDocPromptIntegration)
- **Regression (existing inter-doc tests)**: 23/23 passed (test_inter_doc_graph_builder.py)
- **Total**: 34 passed, 0 failed

### Coverage

- `inter_doc_graph_builder.py`: 95% (missing lines 191, 193, 219, 233, 241, 246 — pre-existing vector-similarity path gaps)
- `llm_extractor.py`: 89% (missing lines 95–96 — pre-existing `except/else` error-handling path; my additions fully covered)

### Lint

- ruff: clean on both changed files and test file

### Evidence Summary

- RED verified first: all 11 tests failed before any implementation
- AC1: `LLMExtractor(model="m", api_key="k", system_prompt="...")` accepted; `extractor._system_prompt` stores param; custom prompt flows into `messages[0]["content"]`
- AC2: `_build_inter_prompt()` now emits `entity_type.value` and `description` per entity; entity types and descriptions appear in extractor.extract() call arg
- AC3: `INTER_DOC_PROMPT` contains governs guidance prose referencing policy/standard; supersedes_version guidance referencing versions
- AC4: All existing 23 inter-doc tests still pass; 4 new AC3 tests cover corporate guidance prose in INTER_DOC_PROMPT

### Premise Invalidated Note

The 2026-04-14 "Premise Invalidated" entry in task body was stale — `LLMExtractor` remains in the codebase using the openai SDK (not pydantic-ai). The arch-review approach was viable and applied without modification.
[[2026-04-15]]

## Review Evidence

### Test Results

- pytest: 34 passed, 0 failed (11 TestFromAC_InterDocPromptIntegration + 23 regression tests/test_inter_doc_graph_builder.py)

### Lint: clean (ruff: 0 violations on both changed files and test file)

### Coverage: unavailable — Windows pytest-cov KeyboardInterrupt during SSL init (environment issue, not code issue). Builder self-reports: inter_doc_graph_builder.py 95%, llm_extractor.py 89%. Missing lines are pre-existing (lines 95–96: except/else error path in extract(), predating this task). Per suppressions: "coverage gaps in untouched code" suppressed

### Pass 1 — CRITICAL

#### Test-Writer AC Coverage

| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---------|-------------|---------------------------|---------|
| AC1: constructor accepts system_prompt kwarg | test_llm_extractor_accepts_system_prompt_kwarg | No — `assert extractor is not None` (lazy) | LAX |
| AC1: default is LLM_EXTRACTION_PROMPT | test_llm_extractor_default_system_prompt_is_llm_extraction_prompt | Yes — asserts `extractor._system_prompt == LLM_EXTRACTION_PROMPT` | COVERED |
| AC1: custom prompt flows to API call | test_llm_extractor_custom_system_prompt_sent_as_system_message | Yes — full mock, asserts `system_msg["content"] == custom_prompt` | COVERED |
| AC2: entity types in prompt | test_build_inter_prompt_includes_entity_type_in_extractor_call | Yes — asserts EntityType.POLICY.value and PROCEDURE.value in prompt | COVERED |
| AC2: descriptions in prompt | test_build_inter_prompt_includes_entity_description_in_extractor_call | Yes — asserts verbatim description strings in prompt | COVERED |
| AC2: both entities typed | test_build_inter_prompt_includes_types_for_both_entities_in_pair | Yes — asserts both EntityType values present | COVERED |
| AC2: empty description keeps type | test_build_inter_prompt_empty_description_does_not_omit_entity_type | Yes — description="" still emits entity_type | COVERED |
| AC3: governs prose | test_inter_doc_prompt_has_governs_guidance_prose | Yes — asserts "governs" in INTER_DOC_PROMPT.lower() | COVERED |
| AC3: governs → policy/standard | test_inter_doc_prompt_governs_guidance_references_policy_or_standard | Yes — asserts "policy" or "standard" in prompt | COVERED |
| AC3: supersedes_version prose | test_inter_doc_prompt_has_supersedes_version_guidance_prose | Yes — asserts "supersedes_version" or "supersedes" in prompt | COVERED |
| AC3: versioning context | test_inter_doc_prompt_supersedes_version_guidance_references_versions | Yes — asserts "version" in prompt | COVERED |
| AC4: existing tests pass | 23 tests in test_inter_doc_graph_builder.py | Yes — all passed | COVERED |

LAX note: `test_llm_extractor_accepts_system_prompt_kwarg` has a lazy `assert extractor is not None` — compensated by two stronger AC1 tests that verify `_system_prompt` storage and API message injection. No auto-FAIL (compensating COVERED tests exist).

#### Security Review

- Hardcoded secrets: None
- Prompt injection: Entity name/description interpolated into prompt (inter_doc_graph_builder.py:109–114) — LOW risk; entity data comes from internal Pydantic-validated graph store, not raw user input. No new user-controlled paths.
- New dependencies: None
- No issues requiring FAIL

#### Test Integrity

| Original Test | Change Made | Assessment |
|---------------|-------------|------------|
| TestFromAC_InterDocPromptIntegration (all 11) | None — test file absent from git changed-files list | PRESERVED |

#### Test Quality

| Dimension | Rating | Evidence |
|-----------|--------|----------|
| Assertion specificity | ADEQUATE | 10/11 tests have specific, targeted assertions; 1 lazy `assert extractor is not None` compensated by 2 strong tests for same AC1 |
| Negative/error-path coverage | N/A | No new error paths introduced; _build_inter_prompt is non-throwing string construction |
| Mutation resistance | STRONG | Removing entity_type.value or description from_build_inter_prompt fails tests 4–7; removing governs/supersedes text from INTER_DOC_PROMPT fails tests 8–11; changing system_prompt default fails test 2; removing `_system_prompt` usage in extract() fails test 3 |
| Test independence | STRONG | All tests use local fixture functions; no shared mutable state |
| Test names | STRONG | All names descriptive and action-oriented |

#### Data Safety

- No LLM output persisted unsanitized (structured output via response_format=ExtractionResult)
- No race conditions or shared mutable state
- No issues

#### Implementation-Aware Gaps

- All new code paths in `_build_inter_prompt()` covered: empty-description branch (test 7), type-per-entity (tests 4/5/6), description inclusion (test 5)
- `LLMExtractor.__init__` system_prompt param: all branches covered (default: test 2, custom: test 3)
- `self._system_prompt` usage in extract(): covered by test 3 (full API mock)
- No significant untested paths found

#### Builder Process Quality

| Metric | Value |
|--------|-------|
| Builder Notes sections | 1 |
| Approach variation | N/A (single attempt) |
| Assessment | CLEAN |

### Pass 2 — INFORMATIONAL

- `test_llm_extractor_accepts_system_prompt_kwarg`: minor improvement opportunity — changing to `assert extractor._system_prompt == "custom system"` would eliminate the LAX without removing any existing coverage. Not blocking.

### AC Compliance

| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| AC1: INTER_DOC_PROMPT usable as system_prompt | llm_extractor.py:69–77 — `system_prompt: str = LLM_EXTRACTION_PROMPT` param; :76 `self._system_prompt = system_prompt`; :84 used in system message | test_llm_extractor_custom_system_prompt_sent_as_system_message | PASS |
| AC2: _build_inter_prompt includes types + descriptions | inter_doc_graph_builder.py:88–101 — `a.entity_type.value`, `b.entity_type.value`, conditional `a.description`, `b.description` in f-string | tests 4–7 | PASS |
| AC3: Corporate guidance in INTER_DOC_PROMPT | inter_doc_graph_builder.py:48–55 — "governs: Use when a policy or standard…"; "supersedes_version: Use when a document or standard supersedes a prior version…" | tests 8–11 | PASS |
| AC4: Existing tests pass + new tests cover guidance | 23 regression tests pass; 4 new AC3 tests verify literal prose in INTER_DOC_PROMPT | test_inter_doc_graph_builder.py (all), tests 8–11 | PASS |

### Confidence: .94

### Verdict: PASS

[[2026-04-15]]

## Docs Gate

### Checklist

| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Behavior/API change | Yes | N/A | `LLMExtractor.__init__` gained `system_prompt` param; `copilot-instructions.md` documents project branches only — no knowledge API entries. No update needed. |
| 2 | Module docstrings | Yes | Updated | `llm_extractor.py` class docstring updated to document `system_prompt` param and its use with `INTER_DOC_PROMPT`. `inter_doc_graph_builder.py` module docstring accurately reflects current behavior (no change needed). |
| 3 | External attribution | No | N/A | Research doc lists 6 sources — all codebase-internal. No external attribution required. |
| 4 | CLI changes | No | N/A | No CLI commands added or modified. |
| 5 | Research doc | Yes | Verified | `.owlbear/research/862-inter-doc-prompt-integration.md` exists and is linked from task body. |

### Files Updated

- `serve/knowledge/src/owlbear_knowledge/llm_extractor.py` — class docstring updated for `system_prompt` param
- `serve/knowledge/src/owlbear_knowledge/inter_doc_graph_builder.py` — committed (builder's uncommitted implementation; no doc change needed)

### Builder Commit Note

Builder's implementation was uncommitted in the working tree (no commit between test-writer `fa56f46e` and HEAD). Staged and committed both files together as `7513e9c6` with attribution to builder + doc-writer.

### Scratch Files

No `.owlbear/scratch/862-*` files found. Nothing to clean.
[[2026-04-15]]

## Audit

### AC Verification

| AC Line | Evidence | Status |
|---------|----------|--------|
| AC1: INTER_DOC_PROMPT usable as system_prompt | llm_extractor.py:79-83 — `system_prompt: str = LLM_EXTRACTION_PROMPT` param, stored as `self._system_prompt`, used at :92 in system message. Commit 7513e9c6. | PASS |
| AC2: _build_inter_prompt includes types+descriptions | inter_doc_graph_builder.py:95-101 — `a.entity_type.value`, `b.entity_type.value`, conditional descriptions in f-string. Commit 7513e9c6. | PASS |
| AC3: Corporate guidance in INTER_DOC_PROMPT | inter_doc_graph_builder.py:48-55 — governs prose ("policy or standard"), supersedes_version prose ("prior version"). Commit 7513e9c6. | PASS |
| AC4: Existing tests pass + new tests cover guidance | 23 regression pass, 11 new pass (34 total, 0 failed). Commits fa56f46e (tests), 7513e9c6 (impl). | PASS |

### Test Results

- pytest (task scope): 34 passed, 0 failed
- pytest (full suite): 4326 passed, 192 failed — all pre-existing, none in task scope (failures span kanban, lint hooks, bookmarks, etc.)
- ruff: 1 E501 in kanban engine.py:471 — not in task scope; task files clean

### Architect Quality: 4/5

AC was specific and testable. Missing affected file (llm_extractor.py) caught and corrected during arch review. Builder guidance for AC1 DI interpretation was excellent. Minor gap only.

### Deduction Breakdown

- AC lines with no evidence: 0 (4/4 PASS) → 0
- Lint violations in scope: 0 → 0
- AC quality ≤ 3: no (4/5) → 0
- Missing reviewer section: no (present, detailed, PASS at .94) → 0
- Full-suite failures in task scope: 0 → 0

### Confidence: 1.00

### Action: archive
