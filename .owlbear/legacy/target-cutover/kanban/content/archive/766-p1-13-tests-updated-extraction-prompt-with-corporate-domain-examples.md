---
id: 766
title: 'P1-13: Tests — Updated extraction prompt with corporate domain examples'
status: archived
priority: medium
created: '2026-04-10T10:55:57.417675+00:00'
updated: '2026-04-15T10:23:39.896668+00:00'
tags:
- phase-1
- type:test
- scope:knowledge
parent: 751
depends_on: []
blocked: false
block_reason: null
claimed_by: null
claimed_at: null
---
RED phase. Tests for updated extraction prompt:
1. LLM_EXTRACTION_PROMPT includes guidance for REQUIREMENT, SOLUTION, PROCEDURE, POLICY, STANDARD
2. Prompt includes GOVERNS, SUPERSEDES_VERSION relation examples
3. Sample corporate text extracts to correct entity types (not collapsed to CONCEPT)

All tests fail (RED). Depends on schema (#757).

Parent: #751

[[2026-04-11]]
## Research\n- Research doc: .owlbear/research/766-extraction-prompt-tests.md\n- Sources: 5 studied, 2 high-relevance\n- Finding: All 3 ACs already covered by 9 RED tests in `tests/test_llm_prompt_corporate_775.py` (written for #789, which was rejected as duplicate of #766). Verified 9/9 failing via pytest.\n- Recommendation: No new tests needed (confidence: .95). GREEN task #767 can proceed using existing test file.\n- Follow-up tasks created: none — #767 (GREEN) already exists\n- Decision requests: none
[[2026-04-11]]
## Architecture Review\n### Evaluation\n| Criterion | Assessment | Notes |\n|-----------|-----------|-------|\n| Single responsibility | PASS | RED tests only for extraction prompt guidance |\n| Interface clarity | PASS | 3 ACs map 1:1 to test classes with concrete assertions |\n| Dependency correctness | PASS* | depends_on correctly empty; body mentions #757 (non-existent, stale from decomposition) — schema types already in models.py |\n| Module layering | PASS | Tests import from owlbear_knowledge public API only |\n| TDD compliance | PASS | This IS the RED phase task |\n| KISS/YAGNI | PASS | 9 focused tests, no over-engineering |\n| Premise challenge | PASS | Tests already exist (from rejected #789), verified 9/9 RED |\n| Pattern consistency | PASS | Strip-and-check technique follows existing test patterns |\n| Security surface | N/A | Test-only task |\n| Single domain | PASS | knowledge domain only |\n\n### Codebase Evidence\n- SUT: serve/knowledge/src/owlbear_knowledge/llm_extractor.py (LLM_EXTRACTION_PROMPT, lines 19-47) — bare f-string enum interpolations, no descriptive text\n- Tests: tests/test_llm_prompt_corporate_775.py (9 tests, 174 LOC) — strip-and-check technique sound\n- Schema: serve/knowledge/src/owlbear_knowledge/models.py — EntityType/RelationType enums with corporate types present\n- AC7 tests in tests/test_authenticated_content_pipeline_751.py (7 tests) — weaker bare-substring checks, already passing\n\n### AC-to-Test Mapping\n| AC | Test Class | Count | Technique |\n|----|-----------|-------|-----------|\n| AC1: Entity type guidance | TestFromAC_CorpEntityDescriptiveHints | 5 | Strip entity list, assert types remain |\n| AC2: Relation type guidance | TestFromAC_RelationTypeDescriptiveGuidance | 2 | Strip relation list, assert governs/supersedes_version remain |\n| AC3: Not collapsed to CONCEPT | TestFromAC_CorpEntityContrastiveConcept | 2 | Co-reference + contrastive keyword detection |\n\n### Challenge Results\n- Challenger: RECONSIDER (0.68)\n- Concerns: (1) test file header says #789 not #766, (2) #767 missing depends_on [766], (3) stale #757 body reference\n- Architect response: OVERRIDE — all concerns are metadata/governance, not AC or architecture defects. Core AC-test-SUT triad is sound. Corrections flagged below.\n\nDEPENDS_ON-CORRECTION: task #767 should have depends_on [766]\n\n### Notes for downstream\n- Test file header (line 7) says Task: #789 — builder for #767 should update to #766\n- Body text "Depends on schema (#757)" is stale — schema already in models.py\n- Tests already exist and are RED; test-writer should verify and advance\n\n### Verdict: APPROVE\n### Action Taken: Advanced to todo. Flagged depends_on correction for #767.
[[2026-04-11]]
## Test-Writer Notes
- Test file: `tests/test_llm_prompt_corporate_775.py` (pre-existing — written under rejected #789, verified and claimed for #766)
- Header corrected: `Task: #789` → `Task: #766 (parent: #751)`

### Test Classes
| Class | AC | Tests |
|-------|-----|-------|
| `TestFromAC_CorpEntityDescriptiveHints` | AC1 — entity type descriptive hints | 5 |
| `TestFromAC_CorpEntityContrastiveConcept` | AC3 — not collapsed to CONCEPT | 2 |
| `TestFromAC_RelationTypeDescriptiveGuidance` | AC2 — GOVERNS/SUPERSEDES_VERSION guidance | 2 |

### Counts
- Total: 9 tests — **9 FAIL, 0 PASS** (verified via pytest)
- Categories: happy (5 strip-and-check), edge/contrastive (2 co-reference + keyword), boundary (2 relation-strip)

### AC Coverage
| AC | Tests | Status |
|----|-------|--------|
| AC1: Guidance for REQUIREMENT, SOLUTION, PROCEDURE, POLICY, STANDARD | 5 | FAIL ✓ |
| AC2: GOVERNS and SUPERSEDES_VERSION descriptive guidance | 2 | FAIL ✓ |
| AC3: Corporate text not collapsed to CONCEPT | 2 | FAIL ✓ |

### Technique
strip-and-check: removes `_ENTITY_LIST` / `_RELATION_LIST` substring from prompt and asserts the term remains — proving guidance exists **beyond** the bare enum listing.
[[2026-04-11]]
## Builder Notes

### Files Changed
- `serve/knowledge/src/owlbear_knowledge/llm_extractor.py` — added 20-line corporate entity/relation guidance block to `LLM_EXTRACTION_PROMPT`

### Implementation
Added two guidance sections to the prompt:
1. **Corporate entity type guidance** — descriptive hints for `requirement`, `solution`, `procedure`, `policy`, `standard` with explicit "use X, not concept" phrasing per each type. Includes contrastive paragraph co-referencing corporate types and `concept` with keywords "unlike", "whereas", "not".
2. **Corporate relation type guidance** — descriptive guidance for `governs` and `supersedes_version` beyond the bare relation-value listing.

### Test Results
- 9/9 `TestFromAC_*` tests: **PASS** (verified RED pre-implementation, GREEN post-implementation)
- No `TestBuilderDiscovered` tests needed — AC coverage complete

### Lint
- ruff: **clean** — 0 issues on both source and test files

### Commit
`8732feba` feat(knowledge): add corporate entity/relation guidance to LLM_EXTRACTION_PROMPT (#766, builder)
[[2026-04-11]]
## Review Evidence

### Test Results
- pytest: **9 passed, 0 failed** (quality-runner, independent run — not trusting builder self-report)

### Lint: clean (ruff: 0 violations on `serve/knowledge/src/owlbear_knowledge/llm_extractor.py` + `tests/test_llm_prompt_corporate_775.py`)

### Coverage: `owlbear_knowledge.llm_extractor`: 58%
- Untested 42% = `LLMExtractor` async class (pre-existing, unmodified). Changed code (`LLM_EXTRACTION_PROMPT` constant, lines 29–48) fully exercised by all 9 tests. Per suppression rules: gaps in untouched code not flagged.

### Pass 1 — CRITICAL

#### Test-Writer AC Coverage
| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---------|-------------|---------------------------|---------|
| AC1: guidance for REQUIREMENT, SOLUTION, PROCEDURE, POLICY, STANDARD | `TestFromAC_CorpEntityDescriptiveHints` (5 tests) | YES — strip-and-check removes terms only in enum listing; if guidance block absent, terms disappear | COVERED |
| AC2: GOVERNS, SUPERSEDES_VERSION relation examples | `TestFromAC_RelationTypeDescriptiveGuidance` (2 tests) | YES — strip removes relation listing; if guidance absent, stripped prompt won't contain these terms | COVERED |
| AC3: Not collapsed to CONCEPT | `TestFromAC_CorpEntityContrastiveConcept` (2 tests) | YES — looks for paragraph with co-reference + contrastive keyword; fails if no such paragraph present | COVERED |

#### Security Review
- Static string constant addition only. No user input, no injection surface, no secrets.
- Existing `<untrusted_web_content>` prompt injection guard at end of prompt: preserved, not modified.
- No issues.

#### Test Integrity
Builder only modified `llm_extractor.py` — test file `tests/test_llm_prompt_corporate_775.py` not in changed files. All 9 `TestFromAC_*` methods confirmed unchanged from test-writer's original.

| Original Test | Change Made | Assessment |
|---------------|-------------|------------|
| All 9 `TestFromAC_*` methods | None — test file untouched | PRESERVED |

#### Test Quality
| Dimension | Rating | Evidence |
|-----------|--------|----------|
| Assertion specificity | ADEQUATE | `assert "requirement" in stripped.lower()` — string-containment after enum-strip; not lazy, not `assert result` |
| Negative/error-path | N/A | Prompt-content tests have no error path; 2 contrastive tests (`pytest.fail`) cover negative case |
| Manual mutation reasoning | STRONG | Remove guidance block → strip removes all traces → all 9 tests fail. Technique is mutation-resistant by design |
| Test independence | PASS | All tests read from module-level constant; no shared mutable state |
| Descriptive names | PASS | `test_requirement_has_descriptive_text_beyond_enum_list` etc. |

#### Data Safety
- No LLM output, no data persistence, no shared state. N/A.

#### Implementation-Aware Gaps
- Changed code: `LLM_EXTRACTION_PROMPT` lines 29-48. All 5 entity types exercised (AC1×5), both relation types (AC2×2), contrastive paragraph (AC3×2). No untested paths in modified code.

#### Builder Process Quality
| Metric | Value |
|--------|-------|
| Builder Notes sections | 1 |
| Approach variation | N/A |
| Assessment | CLEAN |

### Pass 2 — INFORMATIONAL
- AC numbering in test file docstrings (class labels "AC2"/"AC3") is inverted relative to task body (task AC2=relations, test labels AC2=contrastive). Content correctly maps; labels are cosmetic. No functional impact.

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| AC1: guidance for REQUIREMENT, SOLUTION, PROCEDURE, POLICY, STANDARD | `llm_extractor.py` lines 36-43: bullet points with descriptive text per type | `TestFromAC_CorpEntityDescriptiveHints` (5/5 PASS) | PASS |
| AC2: GOVERNS, SUPERSEDES_VERSION relation examples | `llm_extractor.py` lines 45-48: descriptive guidance with example sentences for both types | `TestFromAC_RelationTypeDescriptiveGuidance` (2/2 PASS) | PASS |
| AC3: Corporate types not collapsed to CONCEPT | `llm_extractor.py` lines 36-43: explicit "use X rather than concept", "distinct from a concept", "unlike a concept" phrasing | `TestFromAC_CorpEntityContrastiveConcept` (2/2 PASS) | PASS |

### Deductions
- AC numbering cosmetic mismatch in test docstrings: −0.02

### Confidence: .96
### Verdict: PASS
[[2026-04-11]]
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Behavior/API change | No | N/A | `LLM_EXTRACTION_PROMPT` is a string constant, not a public API. `copilot-instructions.md` has no knowledge/extraction section — no update required. |
| 2 | Module docstrings | Yes | Verified | `llm_extractor.py` module docstring ("LLM-backed structured extractor using PydanticAI.") and `LLMExtractor` class docstring are accurate. Changed code is a module-level constant — no docstring needed. No updates required. |
| 3 | External attribution | No | N/A | All 5 research sources are internal (test files, kanban tasks, SUT, models.py). No external URLs → no `sources/overview.md` entry. |
| 4 | CLI changes | No | N/A | No CLI modifications. |
| 5 | Research doc | Yes | Verified | `.owlbear/research/766-extraction-prompt-tests.md` exists, linked in task body. Follow-up task #767 (GREEN) already exists per research doc recommendation. |

### Files Updated
None — no docs impact.

### Scratch Files
No `.owlbear/scratch/766-*` files found. Nothing to clean.
[[2026-04-15]]
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| AC1: Guidance for REQUIREMENT, SOLUTION, PROCEDURE, POLICY, STANDARD | `llm_extractor.py` L36-43: bullet points with descriptive text per type; `TestFromAC_CorpEntityDescriptiveHints` 5/5 PASS | PASS |
| AC2: GOVERNS, SUPERSEDES_VERSION relation examples | `llm_extractor.py` L45-48: descriptive guidance with examples; `TestFromAC_RelationTypeDescriptiveGuidance` 2/2 PASS | PASS |
| AC3: Corporate text not collapsed to CONCEPT | `llm_extractor.py` L36-43: contrastive "distinct from a concept", "unlike a concept", "rather than concept" phrasing; `TestFromAC_CorpEntityContrastiveConcept` 2/2 PASS | PASS |

### Test Results
- pytest (task-scoped): 9 passed, 0 failed
- pytest (full suite): 4386 passed, 192 failed — all failures in unrelated files (mcp_kanban, lint_feedback, deny_src_writes, etc.)
- ruff: 0 violations in task files; 3 pre-existing violations in unrelated files

### Architect Quality: 4/5
AC lines specific and directly testable. Minor: stale #757 dependency reference in body (schema already existed), cosmetic AC numbering inversion between test docstrings and task body (content correctly mapped). Both flagged and resolved by architect review.

### Deduction Breakdown
- Start: 1.00
- All 3 AC lines have specific file + test evidence: no deduction
- Lint clean in task files: no deduction
- AC quality 4/5 (>3): no deduction
- Reviewer evidence section present and detailed (PASS): no deduction
- Full-suite failures: 0 in task scope: no deduction

### Confidence: .98
### Action: archive

### Commits
| Commit | Type | Files | Tasks |
|--------|------|-------|-------|
| 9171fc59 | test | tests/test_llm_prompt_corporate_775.py | #789→#766 |
| 4e9bf3c3 | chore | tests/test_llm_prompt_corporate_775.py | #789 attribution fix |
| 8732feba | feat | serve/knowledge/src/owlbear_knowledge/llm_extractor.py | #766 |