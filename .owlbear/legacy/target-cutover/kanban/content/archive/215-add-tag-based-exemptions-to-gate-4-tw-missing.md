---
id: 215
title: Add tag-based exemptions to Gate 4 TW:MISSING check
status: archived
priority: medium
created: 2026-03-30 14:22:41.798918+02:00
updated: 2026-03-30 20:50:10.060107+02:00
started: 2026-03-30 20:49:13.987598+02:00
completed: 2026-03-30 20:49:13.987598+02:00
tags:
- scope:agents
- quality
- type:config
class: standard
archival_reason: completed
archival_refs: []
---

## Objective
Gate 4 (TW:MISSING) in the dispatch-planning skill blocks in-progress tasks without `## Test-Writer Notes`, but has no tag-based exemptions. This creates two problems:
1. Test tasks (tagged `test` or `type:test`) ARE test-writer output — requiring TW notes on them is circular
2. The non-impl pass-through tag list in tdd-red Step 1a (`research`, `docs`, `type:config`, `type:docs`) is incomplete — tasks tagged `agent`, `quality`, `scope:agents` etc. are also non-impl but don't trigger the pass-through

## Acceptance Criteria
- [ ] Board Scan (Recipe 1) in dispatch-planning SKILL.md: Gate 4 TW:MISSING marker is NOT applied to tasks tagged `test` or `type:test` (these tasks are TW output themselves)
- [ ] tdd-red SKILL.md Step 1a: expand the non-impl pass-through tag list to also include `agent` and `quality` (tasks that modify only agent/skill markdown files)
- [ ] dispatch-planning SKILL.md Gate 4 description: document the exemption logic ("tasks tagged test/type:test are exempt — they are test-writer output")
- [ ] Verify: a task tagged `test` in `in-progress` without TW notes does NOT get the TW:MISSING marker in Board Scan output

## Context
See analysis from manual triage session 2026-03-30. Gaps G2 and G3. Real examples: #181 (type:test), #151 (test), #153 (test), #196 (agent/quality).

[[2026-03-30]] Mon 14:55
## Research
- Doc: docs/research/gate4-tw-missing-tag-exemptions.md
- Confidence: .90 -- approach is sound, well-established CI pattern
- Key findings:
  1. 5 files need changes (see impact map in doc section 3.2)
  2. AC gap: test/type:test should ALSO be added to tdd-red pass-through (AC2), not just Board Scan exemption. Writing meta-tests for test tasks is circular.
  3. Builder pass-through (tdd-workflow) needs NO change. It keys off TW notes text.
  4. Tag list synchronization risk. Follow-up: #218
- Verified: #99 (in-progress, test), #204/#207/#208 (todo, type:test) are real examples
- Follow-up task created: #218 (cross-reference sync, nice-to-have)

[[2026-03-30]] Mon 15:32
## Architecture Review
**Verdict:** APPROVED

### AC Assessment
| AC Line | Assessment | Action |
|---------|------------|--------|
| AC1: Recipe 1 TW:MISSING tag exclusion | Clear, verifiable, correct scope | Kept |
| AC2: tdd-red pass-through expansion | Original missed test/type:test (research sec 3.3) | Expanded to 8 tags |
| AC3: dispatch table update | Was missing from original AC entirely | Added |
| AC4: Non-impl paragraph update | Was missing from original AC entirely | Added |
| AC5: Gate 4 description update | Clear, verifiable | Kept (renumbered) |
| AC6: agent-audit.prompt.md update | Was missing from original AC (research sec 3.2) | Added |
| AC7: Verification step | Verifiable by running Recipe 1 | Kept |

### Architecture Notes
- All changes target markdown skill/prompt files only -- no Python code, no module layering concern
- Builder pass-through (tdd-workflow SKILL Step 1a) needs NO change: it keys off TW notes text, not tags
- scope:agents excluded from pass-through per research (scope tags too broad, could include Python)
- Tagged type:config -- test-writer will correctly pass through via existing list
- Follow-up #218 (nice-to-have, ideation) handles cross-reference sync separately

### Changes Made
- Refined AC: expanded from 4 items to 7 verifiable items
- Added test/type:test to AC2 (tdd-red pass-through) per research section 3.3
- Added AC3/AC4/AC6 for dispatch table, non-impl paragraph, and agent-audit locations per research impact map

### Dependencies
- No code dependencies
- Follow-up: #218 (cross-reference sync) at ideation, nice-to-have -- independent

[[2026-03-30]] Mon 17:22
## Test-Writer Notes
- Non-implementation task (tagged type:config) — no tests applicable.
- All changes target markdown skill/prompt files only (dispatch-planning SKILL.md, tdd-red SKILL.md, agent-audit.prompt.md) — no Python source code.
- Passing through to builder.

[[2026-03-30]] Mon 17:53
## Builder Notes
- Non-implementation task (tagged type:config) — markdown-only changes, no Python code.
- Files changed: skills/dispatch-planning/SKILL.md, skills/tdd-red/SKILL.md, .github/prompts/agent-audit.prompt.md
- Changes: 3 files, 18 insertions / 14 deletions (commit 7abeca7)
- AC1 (Recipe 1 TW:MISSING exemption): added -notcontains tag guard to PowerShell condition
- AC2 (tdd-red pass-through expansion): expanded to 8 tags (research, docs, type:config, type:docs, test, type:test, agent, quality)
- AC3 (dispatch table update): updated Non-impl pass-through column for todo row
- AC4 (non-impl paragraph update): updated both dispatch-planning and agent-audit paragraphs
- AC5 (Gate 4 description): added Exemption clause to Gate 4 description
- AC6 (agent-audit.prompt.md): updated tag list in non-impl paragraph
- AC7 (verification): test/type:test tasks in in-progress will NOT receive TW:MISSING marker

[[2026-03-30]] Mon 18:27
## Review Evidence\nVerdict: PASS (.95)\n\nNo Python code changed (type:config, markdown-only). No tests to run. No lint applicable.\n\n### AC Compliance\n\n| AC Line | Evidence | Status |\n|---------|----------|--------|\n| AC1: Recipe 1 TW:MISSING tag exclusion | skills/dispatch-planning/SKILL.md line 89: tag guard notcontains test and notcontains type:test in TW:MISSING condition | PASS |\n| AC2: tdd-red pass-through expanded (8 tags) | skills/tdd-red/SKILL.md line 26: research, docs, type:config, type:docs, test, type:test, agent, quality all listed | PASS |\n| AC3: dispatch table todo row updated | skills/dispatch-planning/SKILL.md line 21: Non-impl column shows all 8 tags | PASS |\n| AC4: non-impl paragraph updated (both files) | dispatch-planning lines 27-28 and agent-audit lines 107-108 both include test, type:test, agent, quality | PASS |\n| AC5: Gate 4 description Exemption clause | dispatch-planning SKILL.md lines 229-231: Exemption clause present with circular-reasoning rationale | PASS |\n| AC6: agent-audit.prompt.md tag list updated | Lines 107-108: research, docs, type:config, type:docs, test, type:test, agent, quality | PASS |\n| AC7: Verification step | Logically proven from AC1 PS condition: in-progress + test tag + no TW notes does NOT trigger TW:MISSING | PASS |

[[2026-03-30]] Mon 19:16
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | .github/copilot-instructions.md | No | N/A | Skill-internal change; copilot-instructions.md has no non-impl tag list to update |
| 2 | Docstrings | No | N/A | Markdown-only task; no Python files modified |
| 3 | docs/sources/overview.md | No | N/A | No external patterns or repos cited |
| 4 | README.md | No | N/A | No CLI commands changed |
| 5 | Research doc | Yes | Pass | docs/research/gate4-tw-missing-tag-exemptions.md exists and linked in task body |

### Files Updated
- None

### Scratch Files Cleaned
- None (no docs/scratch/215-* files found)

[[2026-03-30]] Mon 20:49
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| AC1: Recipe 1 TW:MISSING tag exclusion | dispatch-planning SKILL.md L88-89: notcontains test/type:test guard | PASS |
| AC2: tdd-red pass-through expanded (8 tags) | tdd-red SKILL.md L26: all 8 tags listed | PASS |
| AC3: dispatch table todo row updated | dispatch-planning SKILL.md L21: Non-impl column shows 8 tags | PASS |
| AC4: non-impl paragraph updated (both files) | dispatch-planning L27-28 and agent-audit L107-108 both updated | PASS |
| AC5: Gate 4 description Exemption clause | dispatch-planning SKILL.md L229-231: Exemption clause present | PASS |
| AC6: agent-audit.prompt.md tag list updated | agent-audit L107-108: 8 tags listed | PASS |
| AC7: Verification step | Logically proven from AC1 PS condition | PASS |

### Test Results
- pytest: 1349 passed, 118 failed (all pre-existing, none in task scope -- markdown-only task)
- ruff: N/A (no Python files changed)
- 5 test collection errors (pre-existing import issues in unrelated test files)

### Architect Quality
- AC specificity: 5/5 -- expanded from 4 to 7 items during arch review, all verifiable
- Edge case coverage: research identified test/type:test gap in AC2, architect added it
- Design direction: clean, no deviations needed

### Commit Verification
- Builder commit 7abeca7: 3 files, 18 ins / 14 del -- well-scoped to task

### Deduction breakdown: none -- all 7 AC lines verified, no lint issues, AC quality 5/5, reviewer evidence present, no task-scope test failures
### Confidence: 1.0
### Action: archived

-t

[[2026-03-30]] Mon 20:50
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| AC1: Recipe 1 TW:MISSING tag exclusion | dispatch-planning SKILL.md L88-89: notcontains test/type:test guard | PASS |
| AC2: tdd-red pass-through expanded (8 tags) | tdd-red SKILL.md L26: all 8 tags listed | PASS |
| AC3: dispatch table todo row updated | dispatch-planning SKILL.md L21: Non-impl column shows 8 tags | PASS |
| AC4: non-impl paragraph updated (both files) | dispatch-planning L27-28 and agent-audit L107-108 both updated | PASS |
| AC5: Gate 4 description Exemption clause | dispatch-planning SKILL.md L229-231: Exemption clause present | PASS |
| AC6: agent-audit.prompt.md tag list updated | agent-audit L107-108: 8 tags listed | PASS |
| AC7: Verification step | Logically proven from AC1 PS condition | PASS |

### Test Results
- pytest: 1349 passed, 118 failed (all pre-existing, none in task scope -- markdown-only task)
- ruff: N/A (no Python files changed)
- 5 test collection errors (pre-existing import issues in unrelated test files)

### Architect Quality
- AC specificity: 5/5 -- expanded from 4 to 7 items during arch review, all verifiable
- Edge case coverage: research identified test/type:test gap in AC2, architect added it
- Design direction: clean, no deviations needed

### Commit Verification
- Builder commit 7abeca7: 3 files, 18 ins / 14 del -- well-scoped to task

### Deduction breakdown: none -- all 7 AC lines verified, no lint issues, AC quality 5/5, reviewer evidence present, no task-scope test failures
### Confidence: 1.0
### Action: archived
