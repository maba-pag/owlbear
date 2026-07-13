---
id: 767
title: 'P1-14: Impl — Updated extraction prompt'
status: archived
priority: medium
created: '2026-04-10T10:56:34.222398+00:00'
updated: '2026-04-15T10:34:09.480281+00:00'
tags:
- phase-1
- scope:knowledge
parent: 751
depends_on: []
blocked: false
block_reason: null
claimed_by: null
claimed_at: null
---
GREEN phase. LLM_EXTRACTION_PROMPT updated with corporate domain examples and guidance for REQUIREMENT, SOLUTION, PROCEDURE, POLICY, STANDARD entity types and GOVERNS, SUPERSEDES_VERSION relations.

All P1-13 (#766) tests pass.

Parent: #751

[[2026-04-11]]
## Research\n- Research doc: N/A — trivial GREEN implementation, findings in task body\n- Sources: 3 studied, 3 high-relevance (all internal: 751-authenticated-content-pipeline.md, extract-entity-extraction-graph-builders.md, brittle-prompt-assertions.md)\n- Recommendation: Add ~15-20 line descriptive/contrastive guidance block to LLM_EXTRACTION_PROMPT in serve/knowledge/src/owlbear_knowledge/llm_extractor.py (confidence: .90)\n- Follow-up tasks created: none (this IS the implementation task)\n- Decision requests: none\n\n### Key Findings\n1. **Implementation approach**: Single path — add classification hints for REQUIREMENT, SOLUTION, PROCEDURE, POLICY, STANDARD with contrastive guidance vs CONCEPT, plus GOVERNS/SUPERSEDES_VERSION relation descriptions to the existing f-string prompt constant\n2. **Tests exist and confirmed RED**: 9 tests in tests/test_llm_prompt_corporate_775.py (from #789, rejected as duplicate of #766). Uses strip-and-check technique — strips enum listing, asserts corporate type names and contrastive language remain. All 9 FAILED confirmed by pytest run.\n3. **#766 is redundant**: Task #766 (P1-13 RED phase, parent #751) covers identical scope to #789 (parent #775). Tests already written in test_llm_prompt_corporate_775.py. Builder should target that file.\n4. **Tier**: T1 (Autonomous) — string constant update, no architecture/security/behavior impact\n5. **Existing AC7 tests in test_authenticated_content_pipeline_751.py (7 tests) already pass** — they check bare substring presence only. Will continue to pass after implementation.
[[2026-04-11]]
## Architecture Review

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Single string constant update to `LLM_EXTRACTION_PROMPT` in one file |
| Interface clarity | PASS | Tests in `tests/test_llm_prompt_corporate_775.py` (9 tests, 3 AC classes) define verifiable acceptance mechanically. Target file and constant explicitly named. |
| Dependency correctness | PASS | `depends_on: []` correct. Enum members (REQUIREMENT, SOLUTION, PROCEDURE, POLICY, STANDARD, GOVERNS, SUPERSEDES_VERSION) already exist in `models.py` from #751 builder commit `2dfae28b`. Test file exists independently. |
| Module layering | PASS | String constant in `llm_extractor.py` — no cross-module impact |
| TDD compliance | PASS | 9 RED tests confirmed in `tests/test_llm_prompt_corporate_775.py`: 5 descriptive hint tests (AC1), 2 contrastive guidance tests (AC2), 2 relation guidance tests (AC3). All strip the enum listing and assert remaining descriptive text. |
| KISS/YAGNI | PASS | ~15-20 line text addition to existing f-string. No new abstractions. |
| Premise challenge | PASS | Multiple sources confirm LLM collapses corporate types to CONCEPT without guidance text (brief data-person voice, 751 research, 775 research F3). |
| Pattern consistency | PASS | Extends existing prompt structure. Same f-string constant pattern. |
| Security surface | PASS | No new system boundaries. Prompt text only. Existing `<untrusted_web_content>` guard unaffected. |
| Single domain | PASS | `scope:knowledge` only |

### Failure Mode Map
Not applicable — string constant update, no runtime failure modes introduced.

### Challenge Results
- Challenger: FALLBACK — challenger subagent not in available agent roster
- Architect response: Proceeded without challenge. High confidence — T1 string constant update with existing RED tests, no architectural risk.

### Codebase Evidence
- `serve/knowledge/src/owlbear_knowledge/llm_extractor.py:19-47` — Current `LLM_EXTRACTION_PROMPT` has dynamic enum interpolation but guidance text only mentions "files, functions, classes, decisions, patterns, and concepts." Corporate types appear in the comma-separated list but with no descriptive or contrastive text.
- `serve/knowledge/src/owlbear_knowledge/models.py:22-28` — EntityType enum already includes REQUIREMENT, SOLUTION, PROCEDURE, POLICY, STANDARD (from #751).
- `serve/knowledge/src/owlbear_knowledge/models.py:38-39` — RelationType enum already includes GOVERNS, SUPERSEDES_VERSION.
- `tests/test_llm_prompt_corporate_775.py` — 9 RED tests: `TestFromAC_CorpEntityDescriptiveHints` (5), `TestFromAC_CorpEntityContrastiveConcept` (2), `TestFromAC_RelationTypeDescriptiveGuidance` (2). Strip-and-check technique validates guidance text exists beyond enum interpolation.

### AC Clarification for Builder
The tests define the AC mechanically:
1. **AC1 (5 tests)**: After stripping the comma-separated `_ENTITY_LIST` from `LLM_EXTRACTION_PROMPT`, each corporate type name ('requirement', 'solution', 'procedure', 'policy', 'standard') must still appear as descriptive guidance text.
2. **AC2 (2 tests)**: After stripping `_ENTITY_LIST`, at least one paragraph must co-reference a corporate entity type and 'concept' with contrastive language (e.g., 'not', 'unlike', 'distinct', 'distinguish', 'rather than').
3. **AC3 (2 tests)**: After stripping the comma-separated `_RELATION_LIST`, 'governs' and 'supersedes_version' must still appear as descriptive guidance text.

**Test file**: `tests/test_llm_prompt_corporate_775.py` — all 9 tests must go GREEN.
**Target file**: `serve/knowledge/src/owlbear_knowledge/llm_extractor.py` — `LLM_EXTRACTION_PROMPT` constant.
**Constraint**: Do not break existing 7 AC7 tests in `tests/test_authenticated_content_pipeline_751.py` (bare substring checks).

### Verdict: APPROVE
### Action Taken: Advanced #767 to todo.
[[2026-04-11]]
## Test-Writer Notes
- Test file: tests/test_llm_prompt_corporate_775.py (pre-existing, written under #789)
- Classes: TestFromAC_CorpEntityDescriptiveHints, TestFromAC_CorpEntityContrastiveConcept, TestFromAC_RelationTypeDescriptiveGuidance
- Tests per category: happy 0, edge 2 (contrastive-coreference), error 0, boundary 7 (strip-and-check for each entity/relation type)
- Total: 9 tests, all FAIL (verified April 11 2026)
- ruff: clean
- AC coverage:
  | AC | Tests | Status |
  |----|-------|--------|
  | AC1: Descriptive hint per corporate entity type | 5 (one per type) | FAIL |
  | AC2: Contrastive coreference with CONCEPT | 2 | FAIL |
  | AC3: Relation guidance for GOVERNS, SUPERSEDES_VERSION | 2 | FAIL |
- No new test file committed — tests already committed as part of #789 rejection resolution; file is present and confirmed RED.
- Builder target: serve/knowledge/src/owlbear_knowledge/llm_extractor.py — LLM_EXTRACTION_PROMPT constant.
[[2026-04-11]]
## Builder Notes

### Files Changed
- `serve/knowledge/src/owlbear_knowledge/llm_extractor.py` — `LLM_EXTRACTION_PROMPT`: added two descriptive guidance blocks (corporate entity classification and corporate relation types) between the relation-type enum listing and the JSON schema instruction.

### Implementation
Single surgical edit: inserted ~18 lines of descriptive text into the existing f-string constant. No new imports, no new abstractions, no other files touched.

### Test Results (evidence)
- `tests/test_llm_prompt_corporate_775.py`: **9/9 PASSED** (was 9/9 FAILED, RED confirmed before implementation)
  - `TestFromAC_CorpEntityDescriptiveHints`: 5/5 PASSED (AC1)
  - `TestFromAC_CorpEntityContrastiveConcept`: 2/2 PASSED (AC2)
  - `TestFromAC_RelationTypeDescriptiveGuidance`: 2/2 PASSED (AC3)
- `tests/test_authenticated_content_pipeline_751.py`: **41/41 PASSED** (no regressions)

### Lint
- ruff check `llm_extractor.py`: **clean**

### Coverage
Not scoped — string constant change, no branching code added.

### AC Satisfaction
| AC | Evidence |
|----|----------|
| AC1: descriptive hint per corporate entity type | Each of requirement/solution/procedure/policy/standard appears as individual descriptive text; survives `_ENTITY_LIST` strip ✓ |
| AC2: contrastive coreference with CONCEPT | Guidance block contains "distinct from a concept", "unlike a concept", "rather than concept" — co-references corporate type + 'concept' + contrastive keyword in one paragraph ✓ |
| AC3: relation guidance for GOVERNS, SUPERSEDES_VERSION | Both appear as named relation guidance beyond the comma-separated relation list ✓ |
[[2026-04-11]]
## Review Evidence

### Tests
- quality-runner executed independently: **50 passed, 0 failed**
  - `tests/test_llm_prompt_corporate_775.py`: 9/9 PASSED (AC1: 5, AC2: 2, AC3: 2)
  - `tests/test_authenticated_content_pipeline_751.py`: 41/41 PASSED (no regressions)
- pytest exit code: 0

### Lint
- `serve/knowledge/src/owlbear_knowledge/llm_extractor.py`: **clean**
- `tests/test_llm_prompt_corporate_775.py`: **clean**
- ruff exit code: 0

### Coverage
- `owlbear_knowledge.llm_extractor`: **58%** overall — pre-existing gap in `LLMExtractor` class methods (async LLM calls, require live model or mock beyond this task scope). Changed string constant is 100% covered by import in all 9 AC tests. Not a new gap.

### AC Compliance

| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| AC1: descriptive hint per corporate entity type | `llm_extractor.py:29-40` — requirement, solution, procedure, policy, standard each have explicit bullet-point guidance surviving `_ENTITY_LIST` strip | `TestFromAC_CorpEntityDescriptiveHints` (5 tests) | PASS |
| AC2: contrastive coreference with CONCEPT | `llm_extractor.py:29-40` — guidance block contains "distinct from a concept", "not a generic concept", "unlike a concept", "rather than concept" — all in one paragraph | `TestFromAC_CorpEntityContrastiveConcept` (2 tests) | PASS |
| AC3: relation guidance for GOVERNS, SUPERSEDES_VERSION | `llm_extractor.py:49-53` — both appear as named relation guidance beyond comma-separated relation list | `TestFromAC_RelationTypeDescriptiveGuidance` (2 tests) | PASS |

### Critical Checks (Pass 1)

**5.0 Test-Writer Audit**: All 3 AC lines mapped to TestFromAC classes. Strip-and-check technique is appropriate — would fail if guidance text were removed. No MISSING or LAX mappings.

**5.1 Security**: Static f-string constant addition. No user input, no injection surface, no new dependencies. `<untrusted_web_content>` guard unaffected. PASS.

**5.2 TestFromAC Integrity**: Read full test file. All 9 assertions are strict substring presence checks after enum-list strip. No weakening patterns detected. Builder notes only `llm_extractor.py` modified. PRESERVED.

**5.3 Test Quality**: Strip-and-check is semantically correct for string constant validation. Assertions would fail if guidance text were deleted or renamed. Test names are descriptive. ADEQUATE.

**5.4 Data Safety**: No runtime state, no persistence, no concurrency. N/A.

**5.5 Implementation Gap Analysis**: Implementation is a string constant. No branches, error paths, or code paths exist to test. N/A.

**5.6 Necessity Check**: N/A — string constant update, no new dependencies.

**5.7 Builder Process**: CLEAN — 1 `## Builder Notes` section, no loop.

### Deductions
None.

### Verdict
Confidence: **.95** → **PASS #767 -> docs**
[[2026-04-11]]
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Behavior/API change | No | N/A | `LLM_EXTRACTION_PROMPT` is an internal string constant — no public API, no interface change. `copilot-instructions.md` has only project-identity and branch sections; LLM prompt behavior is not documented there. No update needed. |
| 2 | Module docstrings | Yes | Verified | `llm_extractor.py`: module docstring ✓, `LLMExtractor` class docstring ✓, `extract()` method docstring ✓. All accurate and consistent with implementation. No edits required. |
| 3 | External attribution | No | N/A | Task body notes all 3 sources as internal (751-authenticated-content-pipeline.md, extract-entity-extraction-graph-builders.md, brittle-prompt-assertions.md). No new row needed in `.owlbear/sources/overview.md`. |
| 4 | CLI changes | No | N/A | No CLI commands added or modified. |
| 5 | Research doc | No | N/A | Task body explicitly states "Research doc: N/A — trivial GREEN implementation, findings in task body." No `.owlbear/research/` file produced. |

### Files Updated
- None

### Scratch Files Cleaned
- None (no `.owlbear/scratch/767-*` files found)
[[2026-04-15]]
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| AC1: Descriptive hint per corporate entity type | `llm_extractor.py:29-40` — 5 types with bullet descriptions; `TestFromAC_CorpEntityDescriptiveHints` 5/5 PASS | PASS |
| AC2: Contrastive coreference with CONCEPT | `llm_extractor.py:29-40` — "distinct from a concept", "not a generic concept", "unlike a concept", "rather than concept"; `TestFromAC_CorpEntityContrastiveConcept` 2/2 PASS | PASS |
| AC3: Relation guidance for GOVERNS, SUPERSEDES_VERSION | `llm_extractor.py:49-53` — both with named guidance; `TestFromAC_RelationTypeDescriptiveGuidance` 2/2 PASS | PASS |

### Test Results
- pytest (task-scoped): 50 passed (9 AC + 41 regression), 0 failed
- pytest (full suite): 4386 passed, 192 failed — all failures pre-existing, unrelated to task scope (kanban server AttributeError ~84, analysis/lint-guard assertions, missing lint-changed.ps1, AppContext signature changes). 3 knowledge_integration failures caused by upstream LLMExtractor refactor (#875), not prompt text.
- ruff: 3 violations, all outside task scope (engine.py E501, test_refresh_sharepoint_879.py RUF002/UP024). Task files clean.

### Architect Quality: 4/5
AC was mechanically testable via strip-and-check technique. Not explicitly listed in original task body but clearly defined through architecture review's "AC Clarification for Builder" section. Minor gap: original task body relied on implicit AC from pre-existing tests rather than stating AC lines explicitly.

### Deduction Breakdown
- AC lines without evidence: 0 (all 3 verified) → no deduction
- Lint violations in scope: 0 → no deduction
- AC quality 4 > 3 → no deduction
- Reviewer evidence: present, detailed, PASS at .95 → no deduction
- Full-suite failures in scope: 0 → no deduction

### Confidence: 1.00
### Action: archive