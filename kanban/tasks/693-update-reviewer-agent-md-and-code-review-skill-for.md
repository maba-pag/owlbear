---
id: 693
title: Update reviewer.agent.md and code-review skill for two-agent TDD test comparison
status: archived
priority: needed
created: 2026-03-08T16:39:52.6680114+01:00
updated: 2026-03-09T10:58:21.2598329+01:00
started: 2026-03-08T18:55:12.3169061+01:00
completed: 2026-03-09T10:58:21.2598329+01:00
tags:
    - scope:copilot
    - agent
    - phase-agent-arch
depends_on:
    - 692
class: standard
---

## Context
Split from #683. Depends on #692 (builder update with TestBuilderDiscovered convention  done). See docs/test-writer-agent-research.md.
With two-agent TDD, the reviewer gains a powerful new check: comparing the test-writer's original tests against the builder's final test file. If the builder weakened assertions to make tests easier to pass, the reviewer catches it.

## Acceptance Criteria

- [ ] code-review SKILL.md: new Step 5c 'Test Writer vs Builder Comparison' after security review (5b), before AC compliance (6):
  - Conditional: only applies when TestFromAC_* classes exist in the test file (skip for backward compatibility with old single-agent TDD tasks)
  - Procedure: read every TestFromAC_* test method, compare against builder's final test file, note any modifications
  - Defines weakened assertion patterns (canonical list): relaxed comparisons (== to in, exact match to contains), removed edge case tests, changed error types to broader exceptions, reduced boundary condition coverage
  - Produces comparison table: Original Test | Change Made | Assessment (PRESERVED / WEAKENED / REMOVED / STRENGTHENED)
  - Any WEAKENED or REMOVED assessment = automatic FAIL with structured rejection naming the specific test methods and the nature of the weakening
- [ ] code-review SKILL.md Step 7 output template: add conditional 'Test Writer vs Builder Comparison' table section (only when TestFromAC classes exist)
- [ ] reviewer.agent.md <workflow> summary: add test comparison to the summarized sequence, referencing code-review skill for details
- [ ] reviewer.agent.md <output_format>: add conditional 'Test Writer vs Builder Comparison' section with table (columns: Original Test | Change Made | Assessment)  include note that section is omitted when no TestFromAC classes exist
- [ ] reviewer.agent.md <boundaries>: new red flag  'You are about to issue PASS but TestFromAC tests were modified by the builder and you have not flagged it in the comparison table'
- [ ] reviewer.agent.md <boundaries> common failure rationalizations: add row  'The builder only made minor test changes' -> 'Any TestFromAC modification must be flagged. WEAKENED or REMOVED = automatic FAIL. Even improvements get documented.'

## Architecture Notes

- The reviewer remains strictly read-only  it compares by reading files, never edits
- The test comparison step only applies when TestFromAC classes exist (backward compatible with tasks that went through old single-agent TDD)
- code-review SKILL.md is the authoritative workflow; reviewer.agent.md references it
- Weakened patterns defined in code-review SKILL.md (authoritative source)  reviewer.agent.md enforces the FAIL policy but does not redefine the patterns (DRY)
- The comparison finding (WEAKENED/REMOVED) is distinct from the existing 5-dimension test quality rating  both can independently trigger FAIL

## Files Involved

- .github/skills/code-review/SKILL.md (primary  authoritative workflow)
- .github/agents/reviewer.agent.md (secondary  references skill)

[[2026-03-08]] Sun 18:21
## Architecture Review

### AC Assessment

| # | Original AC | Assessment | Action |
|---|------------|------------|--------|
| 1 | reviewer.agent.md workflow includes comparison step | Sound  but imprecise about skill being authoritative source | Refined: workflow summary references skill |
| 2 | reviewer.agent.md output_format new table | Missed code-review SKILL.md Step 7 output template | Refined: added SKILL.md Step 7 AC line |
| 3 | reviewer.agent.md defines weakened patterns | Split authority  patterns belong in SKILL.md (authoritative workflow) | Refined: patterns defined in SKILL.md Step 5c, not reviewer.agent.md |
| 4 | WEAK on TestFromAC = automatic FAIL | Conflates with existing 5-dimension WEAK rule  needs distinction | Refined: comparison WEAKENED/REMOVED is independent FAIL trigger |
| 5 | code-review SKILL.md new step between lint and AC | Placement too vague (lint=3, AC=6)  five steps in between | Refined: Step 5c after security (5b), before AC compliance (6) |
| 6 | reviewer.agent.md boundaries red flag | Sound as-is | Kept, refined wording |
|  | (missing) backward compatibility | In architecture notes but not in AC  builder needs testable criterion | Added: conditional on TestFromAC existence |
|  | (missing) failure rationalization | No defense against the builder only made minor changes excuse | Added: rationalization row |

### Architecture Validation

- Single responsibility: task touches reviewer policy + its authoritative skill  tightly coupled, correct to co-modify
- DRY: weakened patterns defined once in SKILL.md, not duplicated in agent file
- Backward compat: step is conditional on TestFromAC existence  no breakage for old-style tasks
- Dependency: #692 (done) establishes TestFromAC/TestBuilderDiscovered convention  verified
- TDD: agent/skill file changes (prose), no test task needed
- No code files created or modified  reviewer and skill are .md files

### Dependencies Verified

- #692 (builder.agent.md + tdd-workflow for GREEN-only)  done

[[2026-03-08]] Sun 18:48
## Builder Notes
- Files changed: .github/skills/code-review/SKILL.md, .github/agents/reviewer.agent.md
- No tests (prose-only .md files, no Python code)
- Lint: N/A (markdown)
- AC evidence:
  1. SKILL.md Step 5c added (lines 127-175): conditional on TestFromAC, procedure, canonical patterns table, comparison table, FAIL policy
  2. SKILL.md Step 7 output template: conditional comparison table added after Security Review
  3. reviewer.agent.md workflow summary: test comparison added with skill Step 5c reference
  4. reviewer.agent.md output_format: conditional comparison table with omit-note
  5. reviewer.agent.md boundaries red flag: TestFromAC modification without comparison table
  6. reviewer.agent.md rationalizations: 'minor test changes' row added

[[2026-03-08]] Sun 18:52
## Review Evidence
### AC Compliance
| AC Line | Evidence | Status |
|---------|----------|--------|
| SKILL.md Step 5c after 5b, before 6 | Step 5c header at L145, between Step 5b (Security) and Step 6 (AC compliance). Conditional on TestFromAC_*. Procedure (3 steps), canonical patterns table (6 patterns), comparison table template, WEAKENED/REMOVED = automatic FAIL. | PASS |
| SKILL.md Step 7 output template | Conditional comparison table in review output format section with correct columns | PASS |
| reviewer.agent.md workflow summary | L62: Test Writer vs Builder Comparison in summary, references code-review skill Step 5c | PASS |
| reviewer.agent.md output_format | Conditional comparison table in Channel B template, columns match SKILL.md | PASS |
| reviewer.agent.md boundaries red flag | Red flag for issuing PASS when TestFromAC modified without comparison table | PASS |
| reviewer.agent.md rationalizations row | 'minor test changes' row added with FAIL policy | PASS |

### Cross-cutting
- DRY: weakened patterns defined only in SKILL.md, reviewer references skill
- Consistency: table columns match across all 3 locations
- Backward compat: both files gate on TestFromAC_* existence

### Test Quality / Security / Coverage
N/A - prose-only .md files, no Python code

### Verdict: PASS confidence .95

[[2026-03-08]] Sun 18:54
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | copilot-instructions.md | No | N/A | Internal review step added to skill/agent .md files. High-level summaries in copilot-instructions (reviewer, code-review) remain accurate. |
| 2 | Docstrings | No | N/A | No Python modules modified, only .md files |
| 3 | sources.md | No | N/A | No external patterns used, original OwlBear convention |
| 4 | README.md | No | N/A | No CLI changes |
| 5 | Research doc linked | Yes | Pass | Task body references docs/test-writer-agent-research.md |
| 6 | No impact | - | - | Items 1-4 N/A, item 5 passes |

### Files Updated
- None

### Scratch Files Cleaned
- None (no scratch files existed)

[[2026-03-09]] Mon 04:57
Wave 3, agent: auditor

[[2026-03-09]] Mon 10:58
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| SKILL.md Step 5c after 5b, before 6 | Step 5c header at L114, between 5b (L91) and Step 6 (L158). Conditional on TestFromAC_*, 3-step procedure, 6-row canonical patterns table, comparison table template, WEAKENED/REMOVED = auto FAIL. | PASS |
| SKILL.md Step 7 output template | L209-L212: conditional comparison table with columns Original Test |} Change Made |} Assessment | PASS |
| reviewer.agent.md workflow summary | L72: Test Writer vs Builder Comparison referencing code-review skill Step 5c | PASS |
| reviewer.agent.md output_format | L116: conditional table with omit-note when no TestFromAC classes exist | PASS |
| reviewer.agent.md boundaries red flag | L178: red flag for issuing PASS when TestFromAC tests modified without comparison table | PASS |
| reviewer.agent.md rationalizations row | L189: 'minor test changes' row with FAIL policy | PASS |

### Cross-cutting
- DRY: canonical patterns defined ONLY in SKILL.md (grep for 'Relaxed comparison' in reviewer.agent.md = 0 hits)
- Column consistency: all 3 locations use Original Test |} Change Made |} Assessment
- Backward compat: both files gate on TestFromAC_* existence

### Test Results
- N/A: prose-only .md files, no Python code

### Confidence: .96
### Action: archive
