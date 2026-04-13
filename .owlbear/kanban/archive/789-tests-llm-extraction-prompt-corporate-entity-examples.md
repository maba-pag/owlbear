---
id: 789
title: Tests — LLM extraction prompt corporate entity examples
status: done
priority: needed
created: '2026-04-10T12:31:33.658191+00:00'
updated: '2026-04-12T03:05:42.495973+00:00'
tags:
- phase-1
- scope:knowledge
- type:test
parent: 775
depends_on:
- 784
blocked: false
block_reason: null
claimed_by: null
claimed_at: null
---
## Acceptance Criteria

- Tests assert `LLM_EXTRACTION_PROMPT` contains example text for REQUIREMENT, SOLUTION, PROCEDURE, POLICY, STANDARD
- Tests assert prompt distinguishes corporate entity types from CONCEPT (prevents LLM collapse per F3)
- Tests verify GOVERNS and SUPERSEDES_VERSION appear in relation type guidance
- File: `tests/test_llm_prompt_corporate_775.py`

## Context
- WS-B: Pipeline Quality
- Scope item 9 from #775
- See research F3: entity/relation/prompt must ship atomically — depends on entity types being defined first

[[2026-04-11]]
## Architecture Review

### Verdict: REJECT — Already Implemented

### AC Assessment

| AC Line | Assessment | Action |
|---------|-----------|--------|
| Tests assert `LLM_EXTRACTION_PROMPT` contains example text for REQUIREMENT, SOLUTION, PROCEDURE, POLICY, STANDARD | **ALREADY EXISTS** — `tests/test_llm_prompt_corporate_775.py` class `TestFromAC_CorpEntityDescriptiveHints` (5 tests, all correctly RED) | Reject — tests already written |
| Tests assert prompt distinguishes corporate entity types from CONCEPT | **ALREADY EXISTS** — class `TestFromAC_CorpEntityContrastiveConcept` (2 tests, correctly RED) | Reject — tests already written |
| Tests verify GOVERNS and SUPERSEDES_VERSION appear in relation type guidance | **ALREADY EXISTS** — class `TestFromAC_RelationTypeDescriptiveGuidance` (2 tests, correctly RED) | Reject — tests already written |
| File: `tests/test_llm_prompt_corporate_775.py` | **EXISTS** — 175 lines, 9 tests, all RED | Reject — file already present |

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Premise challenge | **FAIL** | All AC deliverables already exist. Test file `test_llm_prompt_corporate_775.py` contains 9 RED tests covering every AC line. Confirmed via pytest: 9 failed, 0 passed. |
| Dependency correctness | **FAIL** | Dependency #784 is in `research` (rejected as already-implemented). Semantically satisfied (models.py has the types) but kanban-status unresolved. |
| Single responsibility | N/A | Moot — nothing to build |
| TDD compliance | N/A | This IS the test task; tests exist |

### Architecture Notes

- `tests/test_llm_prompt_corporate_775.py` exists with complete RED tests:
  - `TestFromAC_CorpEntityDescriptiveHints` (5 tests): strips enum list, asserts corporate type names still appear as descriptive guidance
  - `TestFromAC_CorpEntityContrastiveConcept` (2 tests): asserts co-reference of corporate types with CONCEPT and contrastive language
  - `TestFromAC_RelationTypeDescriptiveGuidance` (2 tests): strips relation list, asserts governs/supersedes_version appear as descriptive guidance
- Duplicate of #766 (parent #751) which covers identical scope
- Parent #775 no longer exists on the board
- Existing tests in `test_authenticated_content_pipeline_751.py` class `TestFromAC_AuthenticatedContentExtractionPrompt` provide weaker coverage (bare string presence, no strip-and-check technique)
- A corresponding GREEN task (#767) also exists in research

### Challenge Results
- Challenger: SKIPPED (REJECT verdict — challenge not required)

### Action Taken
Rejected to research. Test file already exists with 9 correctly RED tests covering all AC lines. Stale decomposition artifact from defunct parent #775. Duplicate of #766.
[[2026-04-11]]
## Research

### Verification Summary

Independent verification confirms the architecture review's REJECT verdict. Task #789 is a stale decomposition artifact — all AC lines are already covered by canonical task #766 (parent #751).

| AC Line | Evidence | Status |
|---------|----------|--------|
| Tests assert LLM_EXTRACTION_PROMPT contains examples for REQUIREMENT, SOLUTION, PROCEDURE, POLICY, STANDARD | `tests/test_llm_prompt_corporate_775.py` class `TestFromAC_CorpEntityDescriptiveHints` (5 tests) | Already exists |
| Tests assert prompt distinguishes corporate types from CONCEPT | class `TestFromAC_CorpEntityContrastiveConcept` (2 tests) | Already exists |
| Tests verify GOVERNS/SUPERSEDES_VERSION in relation guidance | class `TestFromAC_RelationTypeDescriptiveGuidance` (2 tests) | Already exists |
| File: `tests/test_llm_prompt_corporate_775.py` | 175 lines, 9 tests, confirmed 9/9 RED via pytest | Already exists |

### Duplicate Analysis

| Task | Parent | Status | Scope |
|------|--------|--------|-------|
| **#789** (this) | #775 (archived) | research (stale) | LLM prompt corporate entity test RED |
| **#766** (canonical) | #751 | in-progress | Identical scope — same 9 tests, same file |
| **#767** (GREEN) | #751 | in-progress | Implementation task for the prompt changes |
| **#784** (dep) | #775 (archived) | todo | Stale — enum types already in models.py |

### Classification

T1 — Autonomous closure. Stale decomposition artifact from archived parent #775. Scope fully satisfied by #766 (RED tests) and #767 (GREEN implementation), both from active parent #751.

- Research doc: N/A — trivial duplicate verification
- Sources: 4 internal (test file, #766, #767, #784)
- Recommendation: Archive as stale duplicate (confidence: .95)
- Follow-up tasks created: none — #766/#767 fully cover this scope
- Decision requests: none
- Challenge: SKIPPED — closure of verified-duplicate, not a design choice
[[2026-04-11]]
[[2026-04-11]]
## Architecture Review (2nd pass)

### Verdict: APPROVE — Pre-satisfied duplicate, advance for closure

### AC Assessment

| AC Line | Assessment | Action |
|---------|-----------|--------|
| Tests assert `LLM_EXTRACTION_PROMPT` contains example text for REQUIREMENT, SOLUTION, PROCEDURE, POLICY, STANDARD | **SATISFIED** — `tests/test_llm_prompt_corporate_775.py` class `TestFromAC_CorpEntityDescriptiveHints` (5 tests, all GREEN under #766) | Pass-through |
| Tests assert prompt distinguishes corporate entity types from CONCEPT | **SATISFIED** — class `TestFromAC_CorpEntityContrastiveConcept` (2 tests, GREEN) | Pass-through |
| Tests verify GOVERNS and SUPERSEDES_VERSION appear in relation type guidance | **SATISFIED** — class `TestFromAC_RelationTypeDescriptiveGuidance` (2 tests, GREEN) | Pass-through |
| File: `tests/test_llm_prompt_corporate_775.py` | **EXISTS** — 9 tests, all passing, committed as `8732feba` under #766 | Pass-through |

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Test-only scope |
| Interface clarity | PASS | AC maps 1:1 to existing test classes |
| Dependency correctness | N/A | Dep #784 is stale — moot for a pre-satisfied task |
| Module layering | PASS | Tests import from public API |
| TDD compliance | PASS | This IS the test task |
| KISS/YAGNI | PASS | No work needed |
| Premise challenge | PASS* | Task is a stale duplicate of #766 (now in `review`). All AC already satisfied. Approving for pipeline closure. |
| Pattern consistency | PASS | Existing tests follow strip-and-check pattern |
| Security surface | N/A | Test-only |
| Single domain | PASS | knowledge domain |

### Architecture Notes

- Canonical task #766 (parent #751) is in `review` — builder committed `8732feba`, all 9 tests GREEN
- This task (#789, parent #775 archived) is a stale decomposition artifact covering identical scope
- Previous arch review REJECTED → research confirmed T1 autonomous closure
- Approving to `todo` so downstream agents can process pass-through notes and close

### Challenge Results
- Challenger: SKIPPED — pre-satisfied duplicate closure, not a design decision

### Action Taken
Approved to `todo`. All AC deliverables pre-satisfied by canonical #766. Downstream agents should verify and advance as pass-through.
[[2026-04-11]]
## Test-Writer Notes
- Non-impl pass-through: pre-satisfied duplicate, advance for closure.
- Test file: `tests/test_llm_prompt_corporate_775.py` — exists, 9 tests, all GREEN (9 passed, 0 failed).
- AC coverage: all 4 AC lines satisfied by canonical task #766 (parent #751).
- Classes: `TestFromAC_CorpEntityDescriptiveHints` (5), `TestFromAC_CorpEntityContrastiveConcept` (2), `TestFromAC_RelationTypeDescriptiveGuidance` (2).
- No new tests written — tests already exist and pass; writing new RED tests would revert working implementation.
- Arch review (2nd pass) approved for closure: "Downstream agents should verify and advance as pass-through."
- Verified: `uv run pytest tests/test_llm_prompt_corporate_775.py` → 9 passed.
[[2026-04-11]]
## Builder Notes
- Non-implementation task — no code changes needed.
- Passing through to review.

**Evidence:** `uv run pytest tests/test_llm_prompt_corporate_775.py` → 9 passed, 0 failed.
All AC deliverables pre-satisfied by canonical task #766 (parent #751, now in `review`).
Test file `tests/test_llm_prompt_corporate_775.py` exists with 9 GREEN tests covering all AC lines.
No files changed.
[[2026-04-12]]
## Review Evidence

### Quality-Runner Status
Attempted, returned exit code 4 (no tests collected) due to documented WMI/pytest-xdist hang on Windows/Python 3.12 — worker processes freeze during platform.uname() init. This is a recurring environment limitation, not a test failure signal. Fell back to static analysis + prior-run evidence.

### Static Analysis — `LLM_EXTRACTION_PROMPT` vs. test assertions

**Source file:** `serve/knowledge/src/owlbear_knowledge/llm_extractor.py:19-65`
**Test file:** `tests/test_llm_prompt_corporate_775.py` (175 lines, 9 tests, 3 classes)
**Changed files check:** Neither `llm_extractor.py` nor `test_llm_prompt_corporate_775.py` appear in the 151 unstaged/staged changed files → no regression surface since last confirmed GREEN run.

All 9 assertions verified via static trace:

| Test | Assertion | Evidence | Verdict |
|------|-----------|----------|---------|
| `test_requirement_has_descriptive_text_beyond_enum_list` | `"requirement" in stripped.lower()` | llm_extractor.py:34: `- **requirement**: Specifies what must be done...` | PASS |
| `test_solution_has_descriptive_text_beyond_enum_list` | `"solution" in stripped.lower()` | llm_extractor.py:37: `- **solution**: A technical or process-level response...` | PASS |
| `test_procedure_has_descriptive_text_beyond_enum_list` | `"procedure" in stripped.lower()` | llm_extractor.py:40: `- **procedure**: Step-by-step operational instructions...` | PASS |
| `test_policy_has_descriptive_text_beyond_enum_list` | `"policy" in stripped.lower()` | llm_extractor.py:43: `- **policy**: An organizational rule...` | PASS |
| `test_standard_has_descriptive_text_beyond_enum_list` | `"standard" in stripped.lower()` | llm_extractor.py:46: `- **standard**: A normative specification...` | PASS |
| `test_corporate_type_and_concept_coreference_in_stripped_prompt` | paragraph w/ "concept" + corporate type | Lines 31–48 form one unsplit paragraph; contains "CONCEPT type", "distinct from a concept", "not a generic concept", "unlike a concept" alongside all 5 corporate types | PASS |
| `test_contrastive_language_between_corporate_type_and_concept` | same para + contrastive keyword | "distinct", "rather than", "not ", "unlike" all present in same paragraph | PASS |
| `test_governs_has_descriptive_text_beyond_relation_list` | `"governs" in stripped_relation.lower()` | llm_extractor.py:52: `- **governs**: Use when a policy or standard entity governs...` | PASS |
| `test_supersedes_version_has_descriptive_text_beyond_relation_list` | `"supersedes_version" in stripped_relation.lower()` | llm_extractor.py:55: `- **supersedes_version**: Use when a document...supersedes_version a prior version` | PASS |

### AC Compliance

| AC Line | Evidence | Status |
|---------|----------|--------|
| `LLM_EXTRACTION_PROMPT` contains examples for REQUIREMENT, SOLUTION, PROCEDURE, POLICY, STANDARD | `TestFromAC_CorpEntityDescriptiveHints` 5 tests; strip-and-check confirms all 5 remain after enum list removal | PASS |
| Prompt distinguishes corporate entity types from CONCEPT | `TestFromAC_CorpEntityContrastiveConcept` 2 tests; lines 34/37/40/43/46 contain "distinct from a concept", "rather than concept", "not a generic concept", "unlike a concept" — 4 contrastive keywords present | PASS |
| GOVERNS and SUPERSEDES_VERSION appear in relation type guidance | `TestFromAC_RelationTypeDescriptiveGuidance` 2 tests; llm_extractor.py:52-56 confirmed | PASS |
| File: `tests/test_llm_prompt_corporate_775.py` | File exists, 175 lines, 9 tests in 3 classes, read successfully | PASS |

### Test Quality Assessment
Strip-and-check technique is strong — would fail on a broken implementation where guidance text was missing. Contrastive keyword test is multi-condition and hard to accidentally satisfy. No weak assertions (no bare `assert "REQUIREMENT" in prompt` style). No `TestFromAC_*` classes modified (file not in git diff).

### TestFromAC_ Modifications
None detected. File not in changed files list.

### Deductions
- Quality-runner could not execute tests (-0.05): mitigated by (a) static analysis conclusive, (b) 2 prior independent runs confirmed 9/9 GREEN (arch reviewer 2nd pass + builder), (c) no changed files since those runs.

### Verdict
Confidence: .93 → PASS
[[2026-04-12]]
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Behavior/API change | No | N/A | Test-only pass-through duplicate closure. Builder stated "No files changed." No production code touched. |
| 2 | Module docstrings | No | N/A | No Python modules created or modified. Confirmed via builder notes and git diff evidence in review. |
| 3 | External attribution | No | N/A | Research phase confirmed purely internal duplicate verification (internal sources only: test file, #766, #767, #784). |
| 4 | CLI changes | No | N/A | No CLI additions or modifications. |
| 5 | Research doc | No | N/A | Researcher noted "Research doc: N/A — trivial duplicate verification." No `.owlbear/research/789-*.md` file exists — confirmed via search. |

### Files Updated
- None

### Scratch Files Cleaned
- None found (`.owlbear/scratch/789-*` search returned no results)
[[2026-04-12]]
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| Tests assert LLM_EXTRACTION_PROMPT contains examples for REQUIREMENT, SOLUTION, PROCEDURE, POLICY, STANDARD | TestFromAC_CorpEntityDescriptiveHints (5 tests), all GREEN, not in failure list | PASS |
| Tests assert prompt distinguishes corporate entity types from CONCEPT | TestFromAC_CorpEntityContrastiveConcept (2 tests), all GREEN | PASS |
| Tests verify GOVERNS and SUPERSEDES_VERSION in relation type guidance | TestFromAC_RelationTypeDescriptiveGuidance (2 tests), all GREEN | PASS |
| File: tests/test_llm_prompt_corporate_775.py | Exists, 175 lines, 9 tests in 3 classes, committed 9171fc59 | PASS |

### Test Results
- pytest: 3599 passed, 271 failed (pre-existing, none in task scope), 8 skipped, 6 errors (ImportError, unrelated)
- test_llm_prompt_corporate_775.py: 9/9 passed (confirmed not in failure list)
- ruff: all checks passed, zero violations

### Architect Quality: 4/5
AC was specific and verifiable with strip-and-check technique. Minor gap: task was a stale duplicate of #766 (parent #751), indicating upstream decomposition overlap. AC itself was well-written.

### Deduction Breakdown
- Start: 1.00
- AC lines without evidence: 0 (all 4 have specific evidence) = 0
- Lint violations: none = 0
- AC quality 4/5 (above 3 threshold) = 0
- Reviewer evidence: present, detailed, PASS at .93 with static analysis trace = 0
- Full-suite failures in task scope: none = 0

### Confidence: 1.00
### Action: archive

### Reviewer Evidence Check
Reviewer section present with thorough static trace of all 9 assertions against source lines in llm_extractor.py. PASS verdict at .93 (mitigated Quality-Runner unavailability with static analysis). Accepted.

### Commit Integrity
- 9171fc59: test file committed (test-writer, RED tests)
- 8732feba: GREEN implementation committed under #766
- 4e9bf3c3: leftover docstring attribution fix committed (auditor)

## Commits
| Commit | Type | Files | Tasks |
|--------|------|-------|-------|
| 4e9bf3c3 | chore | tests/test_llm_prompt_corporate_775.py | #789 |