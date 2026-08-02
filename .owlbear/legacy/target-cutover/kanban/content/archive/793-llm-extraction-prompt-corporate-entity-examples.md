---
id: 793
title: LLM extraction prompt corporate entity examples
status: archived
priority: medium
created: '2026-04-10T12:31:51.861669+00:00'
updated: '2026-04-13T11:11:22.999452+00:00'
tags:
- phase-1
- scope:knowledge
parent: 775
depends_on:
- 789
blocked: false
block_reason: null
claimed_by: null
claimed_at: null
---
## Acceptance Criteria

- `LLM_EXTRACTION_PROMPT` updated with corporate entity disambiguation examples (e.g., "a REQUIREMENT is a mandated specification, not a CONCEPT")
- Prompt includes GOVERNS and SUPERSEDES_VERSION relation examples
- All #789 tests pass; existing extraction tests still pass
- File: `serve/knowledge/src/owlbear_knowledge/llm_extractor.py`

## Context
- WS-B: Pipeline Quality
- Scope item 9 from #775
- See research F3: entity/relation/prompt must ship atomically

[[2026-04-12]]
## Architecture Review

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Prompt text update only, single file |
| Interface clarity | PASS | AC maps to string-presence checks; no interface changes |
| Dependency correctness | PASS | #789 (test task) is done |
| Module layering | PASS | No new imports, no layer violations |
| TDD compliance | PASS | #789 tests exist and cover all AC lines |
| KISS/YAGNI | PASS | Minimal, focused prompt additions |
| Premise challenge | NOTE | Implementation is **already complete** — shipped by #767. All AC content exists in `llm_extractor.py` lines 30-48. See below. |
| Pattern consistency | PASS | Follows existing prompt structure with `_ENTITY_VALUES`/`_RELATION_VALUES` interpolation |
| Security surface | PASS | No new system boundaries |
| Single domain | PASS | Knowledge domain only |

### Already-Implemented Notice

**All AC items are already satisfied by completed task #767** ("P1-14: Impl — Updated extraction prompt"):

- Corporate entity disambiguation (requirement, solution, procedure, policy, standard) with "distinct from CONCEPT" language: present at lines 31-43
- GOVERNS relation example ("a security policy governs a procedure"): line 45-46
- SUPERSEDES_VERSION relation example ("Policy v2.0 supersedes_version Policy v1.0"): lines 47-48
- EntityType/RelationType enums in `models.py` include all corporate types

**Builder guidance:** Verify all #789 tests pass. No code changes should be needed — this is a verification-only task. If tests pass, advance immediately.

### Challenge Results
- Challenger: BLOCK (confidence 0.95) — redundancy with #767
- Architect response: Overridden. Approve is faster than reject-to-research. Builder does no-op verification and closes cleanly. Redundancy noted for retro.

DEPENDS_ON-CORRECTION: depends_on [789] is correct (done). No corrections needed.

### Verdict: APPROVE
### Action Taken: Advanced to todo. Builder should verify tests pass (no code changes expected).
[[2026-04-12]]
## Test-Writer Notes

- **Pass-through: verification-only task — no new tests written**
- Architecture review (approved, on-task body) confirmed: implementation is complete (shipped by #767), all AC lines satisfied in `llm_extractor.py` lines 30–48.
- Existing tests from dependency #789 (`tests/test_llm_prompt_corporate_775.py`) cover all three AC items:
  - AC1 (corporate entity disambiguation beyond enum list): `TestFromAC_CorpEntityDescriptiveHints` — 5 tests
  - AC2 (contrastive CONCEPT language): `TestFromAC_CorpEntityContrastiveConcept` — 2 tests
  - AC3 (GOVERNS + SUPERSEDES_VERSION guidance): `TestFromAC_RelationTypeDescriptiveGuidance` — 2 tests
- Writing new tests would produce PASSING tests (implementation already complete) — violates RED-phase contract.
- Builder action: run `uv run pytest tests/test_llm_prompt_corporate_775.py tests/test_llm_extractor.py -q` to confirm all pass, then advance to done.
[[2026-04-12]]
## Builder Notes
- Verification-only task — no code changes made.
- Implementation was already complete (shipped by #767, `serve/knowledge/src/owlbear_knowledge/llm_extractor.py` lines 30–48).
- **Test run:** `uv run pytest tests/test_llm_prompt_corporate_775.py tests/test_llm_extractor.py -q --tb=short`
  - 23 passed, 0 failed
- Lint: no new code introduced, no lint run required.
- All AC items verified present in `llm_extractor.py`:
  - AC1: corporate entity disambiguation examples (REQUIREMENT, SOLUTION, etc.) with "distinct from CONCEPT" language ✓
  - AC2: GOVERNS relation example ✓
  - AC3: SUPERSEDES_VERSION relation example ✓
[[2026-04-12]]
## Review Evidence

### Source Control
- Changed files scanned via VCS. `serve/knowledge/src/owlbear_knowledge/llm_extractor.py` — **not present**. `tests/test_llm_prompt_corporate_775.py` — **not present**. `tests/test_llm_extractor.py` — **not present**. Confirms verification-only task; zero source code modified.

### Tests
Quality-Runner dispatch: **failed** — pytest crashed at coverage-plugin initialization on Windows (KeyboardInterrupt in `importlib._bootstrap_external._path_stat`). Not a code defect. Mitigation: VCS confirms neither test files nor source changed from their previously-green state (tasks #766, #767, #789 all archived). Relied on independent code-reading for assertion verification.

Test count reconciliation: `test_llm_prompt_corporate_775.py` has 9 test methods; `test_llm_extractor.py` has 14 test methods → 23 total. Matches builder's reported 23 passed, 0 failed.

### Lint
Not run (quality-runner failed). No source code changes introduced — no new lint surface.

### Coverage
N/A — no implementation changes made. Covered by #767 and #789 review cycles.

### TestFromAC Modifications
No modifications detected — test files are unchanged (VCS-confirmed). No WEAKENED or REMOVED tests.

### AC Compliance Table

| AC Line | Mapped Test(s) | Would Fail If AC Violated? | Verdict |
|---------|---------------|---------------------------|---------|
| `LLM_EXTRACTION_PROMPT` updated with corporate entity disambiguation examples | `TestFromAC_CorpEntityDescriptiveHints` (5 tests) — strip `_ENTITY_LIST`, assert each type name remains | YES — removal of guidance section drops type names after stripping | COVERED |
| Prompt explicitly differentiates corporate types from CONCEPT | `TestFromAC_CorpEntityContrastiveConcept` (2 tests) — checks paragraph co-references corp-type + "concept" + contrastive keyword ("distinct", "unlike", "not ", etc.) | YES — removing contrastive guidance collapses the paragraph check | COVERED |
| GOVERNS and SUPERSEDES_VERSION relation examples present | `TestFromAC_RelationTypeDescriptiveGuidance` (2 tests) — strip `_RELATION_LIST`, assert "governs" and "supersedes_version" remain | YES — removing guidance section drops both terms after stripping | COVERED |
| All #789 tests pass; existing extraction tests still pass | `tests/test_llm_extractor.py` (14 tests) — source unchanged, previously green | YES — VCS confirms no regressions possible | COVERED |

### Source Verification (llm_extractor.py lines 19–66)

All AC content present in prompt at read time:
- AC1: 5 corporate type guidance blocks with disambiguating language (e.g., "distinct from a concept", "not a generic concept", "rather than concept", "unlike a concept") — **PASS**
- AC2: Multi-keyword contrastive paragraph — "distinct from a concept (which defines a general idea); use requirement rather than concept" — **PASS**
- AC3: governs block: "e.g., a security policy governs a procedure" — **PASS**; supersedes_version block: "e.g., Policy v2.0 supersedes_version Policy v1.0" — **PASS**

### Test Quality Assessment

| Dimension | Rating | Notes |
|-----------|--------|-------|
| Assertion specificity | ADEQUATE | Substring checks on stripped prompt; precise enough — would fail on removal of any AC-relevant section |
| Negative/error-path coverage | N/A | Prompt-content tests have no error paths |
| Mutation resistance | STRONG | Stripping enum list then asserting remainder catches "enum-only" regressions; paragraph-based contrastive check prevents trivially passing by random keyword insertion |
| Test independence | STRONG | No shared mutable state; all tests read module-level constant |
| Descriptive names | STRONG | All names describe the specific contract being verified |

No WEAK dimension ratings.

### Security
No new code, no new boundaries, no new dependencies. 0 security concerns.

### Deductions
- Quality-runner failed to execute tests (-0.03): mitigated by VCS-confirmed zero source changes and historically-green state

### Verdict
Confidence: **0.97** → **PASS**
[[2026-04-13]]
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Behavior/API change | No | N/A | Verification-only task — no code changes. VCS review confirms `llm_extractor.py`, `test_llm_prompt_corporate_775.py`, `test_llm_extractor.py` unchanged. copilot-instructions.md has no references to LLM_EXTRACTION_PROMPT or corporate entity extraction — nothing to update. |
| 2 | Module docstrings | No | Verified | No modules modified. Read `llm_extractor.py` (lines 1–104): module docstring present, `LLMExtractor` class docstring with Args block, `extract()` method docstring with Args/Returns. All public API documented accurately. |
| 3 | External attribution | No | N/A | No external repos, articles, or patterns introduced. |
| 4 | CLI changes | No | N/A | No CLI changes. |
| 5 | Research doc | No | N/A | No research doc produced for #793. Reference to "research F3" is from parent task #775's existing research. |

### Files Updated
- None

### Scratch Files Cleaned
- None (no `.owlbear/scratch/793-*` files found)
[[2026-04-13]]
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| `LLM_EXTRACTION_PROMPT` updated with corporate entity disambiguation examples | `llm_extractor.py` lines 30–43: requirement, solution, procedure, policy, standard — each with contrastive "distinct from CONCEPT" language | PASS |
| Prompt includes GOVERNS and SUPERSEDES_VERSION relation examples | `llm_extractor.py` lines 45–48: "a security policy governs a procedure", "Policy v2.0 supersedes_version Policy v1.0" | PASS |
| All #789 tests pass; existing extraction tests still pass | `uv run pytest tests/test_llm_prompt_corporate_775.py tests/test_llm_extractor.py` → 23 passed, 0 failed | PASS |
| File: `serve/knowledge/src/owlbear_knowledge/llm_extractor.py` | File exists, content verified | PASS |

### Test Results
- pytest (task-scoped): 23 passed, 0 failed
- pytest (full suite): 468 passed, 5 failed, 1 skipped — all 5 failures outside task scope (orchestrator wave assembly, knowledge schema version, planner gates, agent validation, memory scaffold)
- ruff: All checks passed

### Architect Quality: 4/5
AC was specific and verifiable. Minor gap: task was redundant with #767 (implementation already shipped). Architect correctly identified this and overrode challenger's BLOCK with pragmatic reasoning. Planning-level redundancy noted for retro, but AC quality itself was adequate.

### Deduction Breakdown
- No AC lines without evidence: -0.00
- Lint clean: -0.00
- AC quality 4/5 (> 3): -0.00
- Reviewer evidence section present, detailed, PASS verdict: -0.00
- Full-suite failures all outside task scope: -0.00

### Confidence: 0.98
### Action: archive