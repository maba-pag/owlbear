# Extraction Prompt Tests — Already Implemented

> **Owning task:** #766 — P1-13: Tests — Updated extraction prompt with corporate domain examples
> **Date:** 2026-04-11  **Status:** Complete

## 1. Context and Question

Task #766 requires RED-phase tests for three acceptance criteria:
1. `LLM_EXTRACTION_PROMPT` includes guidance for REQUIREMENT, SOLUTION, PROCEDURE, POLICY, STANDARD
2. Prompt includes GOVERNS, SUPERSEDES_VERSION relation examples
3. Sample corporate text extracts to correct entity types (not collapsed to CONCEPT)

Question: Do these tests already exist, and are they correctly RED?

## 2. Sources Studied

| Source | Type | Relevance |
|--------|------|-----------|
| `tests/test_llm_prompt_corporate_775.py` (9 tests, 175 LOC) | Internal — test file | .95 |
| `serve/knowledge/src/owlbear_knowledge/llm_extractor.py` (LLM_EXTRACTION_PROMPT) | Internal — SUT | .95 |
| `serve/knowledge/src/owlbear_knowledge/models.py` (EntityType, RelationType enums) | Internal — deps | .90 |
| Task #789 body (arch review: REJECTED as duplicate of #766) | Internal — kanban | .85 |
| `tests/test_authenticated_content_pipeline_751.py` (AC7 tests) | Internal — weaker coverage | .60 |

## 3. Analysis — Coverage Matrix

| #766 AC | Existing Tests | Class | Count | Status |
|---------|---------------|-------|-------|--------|
| AC1: Entity type guidance | `TestFromAC_CorpEntityDescriptiveHints` | Strips enum list, asserts types still appear | 5 | RED ✅ |
| AC2: Relation type guidance | `TestFromAC_RelationTypeDescriptiveGuidance` | Strips relation list, asserts governs/supersedes_version still appear | 2 | RED ✅ |
| AC3: Not collapsed to CONCEPT | `TestFromAC_CorpEntityContrastiveConcept` | Asserts co-reference + contrastive language between corporate types and CONCEPT | 2 | RED ✅ |

**Total:** 9 tests, 9 failing (RED), 0 passing. Verified via `uv run pytest tests/test_llm_prompt_corporate_775.py`.

### Duplicate Chain

- #766 (parent #751) and #789 (parent #775) are identical scope from parallel decomposition trees.
- #789 was architecturally rejected as "already implemented" — its test file covers #766's AC.
- File header says `Task: #789` but the canonical owning task is #766.

### Technique Validation

The strip-and-check technique is correct: `LLM_EXTRACTION_PROMPT` builds entity/relation lists via f-string interpolation of enum values. After stripping the comma-separated list, corporate type names vanish — confirming the prompt has no descriptive text beyond bare listings. The GREEN phase (#767) must add that descriptive text.

## 4. Recommendation

**No new tests needed.** (confidence: .95)

All 3 ACs are fully covered by existing RED tests in `test_llm_prompt_corporate_775.py`. The file header attribution (`#789` → `#766`) is a cosmetic cleanup for the GREEN task (#767) to handle.

Challenge: SKIPPED — already-implemented finding, no recommendation to challenge.

## 5. Follow-up Tasks

- #767 (GREEN, already exists): Implement prompt changes to make all 9 tests pass.
- Re-attribution of test file header is a minor cleanup for #767.
