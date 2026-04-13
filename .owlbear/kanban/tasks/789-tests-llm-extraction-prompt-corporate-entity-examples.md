---
id: 789
title: Tests — LLM extraction prompt corporate entity examples
status: todo
priority: needed
created: '2026-04-10T12:31:33.658191+00:00'
updated: '2026-04-13T00:16:01.518129+00:00'
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

[[2026-04-12]]
## Architecture Review

### Premise Challenge — FAIL: Task is redundant

The deliverable file `tests/test_llm_prompt_corporate_775.py` already exists (created by task #766 under parent #751) and fully satisfies all four AC lines:

| AC Line | Status | Evidence |
|---------|--------|----------|
| AC1: Tests assert `LLM_EXTRACTION_PROMPT` contains example text for REQUIREMENT, SOLUTION, PROCEDURE, POLICY, STANDARD | SATISFIED | `TestFromAC_CorpEntityDescriptiveHints` — 5 tests, all passing |
| AC2: Tests assert prompt distinguishes corporate entity types from CONCEPT | SATISFIED | `TestFromAC_CorpEntityContrastiveConcept` — 2 tests, all passing |
| AC3: Tests verify GOVERNS and SUPERSEDES_VERSION appear in relation type guidance | SATISFIED | `TestFromAC_RelationTypeDescriptiveGuidance` — 2 tests, all passing |
| AC4: File: `tests/test_llm_prompt_corporate_775.py` | SATISFIED | File exists at specified path (174 lines) |

The implementation under test (`LLM_EXTRACTION_PROMPT` corporate guidance in `serve/knowledge/src/owlbear_knowledge/llm_extractor.py`) is also already present — including descriptive classification hints, contrastive CONCEPT differentiation, and GOVERNS/SUPERSEDES_VERSION guidance blocks.

### Dependency Note

Dependency #784 ("Corporate entity and relation type extensions") is in `backlog` status, but the code it describes is already merged into `models.py` (EntityType has REQUIREMENT/SOLUTION/PROCEDURE/POLICY/STANDARD; RelationType has GOVERNS/SUPERSEDES_VERSION). Task #784 appears similarly redundant — likely completed under the #751 work stream.

### Verdict: REJECT
### Action Taken: Rejected to research — task is a duplicate of work completed under #766 (parent #751). All AC already satisfied. Recommend closing/archiving both #789 and reviewing #784 for the same redundancy.
[[2026-04-12]]
## Research

Validation pass on existing findings — no new research doc required.

### Verification Summary

| AC Line | Evidence | Status |
|---------|----------|--------|
| AC1: Entity type descriptive hints | `TestFromAC_CorpEntityDescriptiveHints` — 5 tests PASS | SATISFIED |
| AC2: Contrastive CONCEPT differentiation | `TestFromAC_CorpEntityContrastiveConcept` — 2 tests PASS | SATISFIED |
| AC3: GOVERNS/SUPERSEDES_VERSION guidance | `TestFromAC_RelationTypeDescriptiveGuidance` — 2 tests PASS | SATISFIED |
| AC4: File exists | `tests/test_llm_prompt_corporate_775.py` (175 LOC) | SATISFIED |

All 9 tests passing (GREEN phase already completed under #767). Task is a stale decomposition artifact — identical scope completed under #766 (parent #751). Dependency #784 is also confirmed stale/redundant with same pattern.

- Existing research doc: `.owlbear/research/766-extraction-prompt-tests.md`
- Sources: 3 verified (test file, SUT, existing research doc)
- Recommendation: Archive this task — confirmed duplicate (confidence: .95)
- Follow-up tasks created: none (all work complete)
- Decision requests: none
- Tier: T1 — duplicate cleanup, no decisions needed

## Challenge Results
- Challenger: SKIPPED — already-implemented finding, no recommendation to challenge
- Confidence in original: .95
- Key challenges: none
- Researcher response: N/A

**Recommend orchestrator archive #789 and #784 as stale duplicates.**
[[2026-04-13]]
[[2026-04-13]]
## Architecture Review (2nd pass)

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | One concern: prompt test coverage |
| Interface clarity | PASS | AC lines are specific and testable |
| Dependency correctness | STALE | Depends on #784 (also confirmed stale/redundant — enum members already in codebase) |
| Module layering | PASS | Test file only |
| TDD compliance | N/A | This IS the test task |
| KISS/YAGNI | PASS (no-op) | All AC already satisfied — task is a pass-through |
| Premise challenge | FAIL (redundant) | Deliverables already exist — see evidence below |
| Pattern consistency | PASS | Test file follows existing patterns |
| Security surface | N/A | No system boundaries |
| Single domain | PASS | knowledge domain only |

### Independent Verification — All AC Satisfied

| AC Line | Evidence | Status |
|---------|----------|--------|
| AC1: Entity type descriptive hints | `TestFromAC_CorpEntityDescriptiveHints` — 5 tests, all GREEN | DONE |
| AC2: Contrastive CONCEPT differentiation | `TestFromAC_CorpEntityContrastiveConcept` — 2 tests, all GREEN | DONE |
| AC3: GOVERNS/SUPERSEDES_VERSION guidance | `TestFromAC_RelationTypeDescriptiveGuidance` — 2 tests, all GREEN | DONE |
| AC4: File: `tests/test_llm_prompt_corporate_775.py` | File exists (175 LOC), 9/9 tests passing | DONE |

### Challenge Results
- Challenger: SKIPPED — APPROVE-as-pass-through verdict on confirmed-redundant task; no architectural decision to challenge
- Architect response: N/A

### Cycle Note
This task completed its 2nd backlog→arch cycle. Prior cycle (2026-04-12) correctly rejected to research; research confirmed redundancy at .95 confidence. Advancing as pass-through to prevent infinite loop. All deliverables verified independently — test file exists, 9/9 tests GREEN.

DEPENDS_ON-CORRECTION: task #789 should have depends_on [] — dependency #784 is itself a stale no-op (all enum members already in models.py).

### Verdict: APPROVE (pass-through)
### Action Taken: Advanced to todo. All AC already satisfied by work completed under #766 (parent #751). Downstream agents should confirm pass-through and advance. Recommend archiving after pipeline completion.