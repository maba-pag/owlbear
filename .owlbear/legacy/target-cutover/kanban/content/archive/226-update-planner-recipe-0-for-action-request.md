---
id: 226
title: Update planner Recipe 0 for action request resolution
status: archived
priority: medium
created: 2026-03-30 16:57:32.068259+02:00
updated: 2026-03-31 21:30:47.492940+02:00
started: 2026-03-31 21:30:47.026369+02:00
completed: 2026-03-31 21:30:47.026369+02:00
tags:
- phase-1
- scope:agents
- type:docs
depends_on:
- 224
class: standard
archival_reason: completed
archival_refs: []
---

## Objective
Extend planner Recipe 0 in skills/dispatch-planning/SKILL.md to handle action request resolution alongside decision requests.

## Acceptance Criteria
- [ ] Recipe 0 prose (lines ~61-77): extend resolution logic to check for both `approved: true` (decisions) and `completed: true` (action requests); add type detection rule (presence of `completed:` field = action type, absence = decision, backwards-compatible)
- [ ] Recipe 0 prose: add auto-resolution for action requests older than 5 days using `completed: auto` (parallel to `approved: auto` for decisions)
- [ ] Step 1 prose (line ~161): update "Check pending decision requests" heading and paragraph to reference action requests alongside decisions
- [ ] Step 3 JSON output format (lines ~262-290): add `pending` field to spec with format `{"decisions": N, "actions": N}`; update both format examples to include the field
- [ ] Self-critique checklist (lines ~335+): add item confirming Recipe 0 handles both `approved: true` and `completed: true`
- [ ] No changes outside `skills/dispatch-planning/SKILL.md` (agent-common tracked by #225, decision-requests skill done in #224)

## Constraints
- Scope is one file: `skills/dispatch-planning/SKILL.md`, 4 sections (per research)
- Agent-common handoff updates tracked by #225 (independent sibling)
- Decision-requests skill format defined by #224 (archived)
- No code changes — skill/docs-only task. No TDD needed.

## Context
See docs/research/planner-recipe0-action-request-extension.md
Depends on #224 (archived)

[[2026-03-30]] Mon 23:43
## Research
**Doc:** docs/research/planner-recipe0-action-request-extension.md
**Confidence:** .90

### Key findings
- Recipe 0 needs symmetric treatment: completed: true (action) handled same as approved: true (decision)
- Auto-resolution uses completed: auto (parallel to approved: auto), 5-day timeout
- Type detection: presence of completed: field signals action type; default to decision
- Add pending field to JSON output for session-start surfacing

### Implementation scope (1 file, 4 sections)
1. Recipe 0 prose: extend resolution logic
2. Step 1 prose: update paragraph for action requests
3. Step 3 JSON format: add pending field
4. Self-critique checklist: add action request item

No additional follow-up tasks. Siblings #225 and #227 cover remaining work.

[[2026-03-31]] Tue
## Architecture Review
**Verdict:** Approve

### AC Assessment
| AC Line | Assessment | Action |
|---------|------------|--------|
| Recipe 0 resolution + type detection | Original AC1+AC3 overlapped (both described same change). Merged into one verifiable line with type detection rule added from research | Rewritten |
| Recipe 0 auto-resolution | Original AC4 lacked specifics (no `completed: auto`). Added parallel value and 5-day rule | Rewritten |
| Step 1 heading/paragraph update | Not in original AC. Research section 2 identifies this change | Added |
| Step 3 JSON `pending` field | Original AC2 vague. Specified field name, format, and both examples | Rewritten |
| Self-critique checklist item | Not in original AC. Research section 4 identifies this change | Added |
| Scope boundary (single file) | Implicit in original. Made explicit as verifiable AC line | Added |

### Architecture Notes
- type:docs task touching only skills/dispatch-planning/SKILL.md. No code, no TDD needed. Fixed tag from type:build to type:docs (matches sibling #224 pattern).
- All changes are additive: existing Recipe 0 decision logic gains action-request parallels. No existing behavior removed.
- Scope properly bounded: decision-requests skill done in #224 (archived), agent-common handoff in #225 (todo). Only dispatch-planning/SKILL.md remains.
- Premise challenge: Recipe 0 only handles approved: true. The decision-requests skill (post-#224) documents planner should treat completed: true the same, but Recipe 0 doesn't reflect this. Gap confirmed.
- JSON output pending field is backwards-compatible: orchestrator tolerates extra fields.
- No security surface, no module layering, no failure modes (docs only).
- Single domain: scope:agents / skills.

### Changes Made
- Fixed tag from type:build to type:docs
- Refined AC from 4 overlapping/vague lines to 6 verifiable lines mapped to research 4-section scope
- Added Constraints section documenting scope boundary and out-of-scope siblings

### Dependencies
- Verified: #224 (decision-requests skill update) archived
- Verified: #225 (agent-common handoff) todo, independent sibling
- Verified: #227 (action request for #167) todo, independent sibling

[[2026-03-31]] Tue 08:17
## Test-Writer Notes
- Non-implementation task (tagged type:docs) â€” no tests applicable.
- Passing through to builder.

[[2026-03-31]] Tue 11:33
## Builder Notes
- Files changed: skills/dispatch-planning/SKILL.md only
- Changes: 7 replacements across 4 sections
  1. Recipe 0: type detection, completed: true / completed: auto, pending count instruction
  2. Step 1: heading + paragraph updated for action requests
  3. Step 3: pending field in both format examples + good example
  4. Step 3 Fields: pending field description added
  5. Step 3 Rules: required fields list updated
  6. Self-critique: Recipe 0 dual-type item + output line updated
- Tests: N/A (type:docs, non-implementation task)
- All 6 AC items verified via grep

[[2026-03-31]] Tue 14:00
## Test-Writer Notes (re-entry)
- Non-implementation task (tagged type:docs) - no tests applicable.
- Passing through to builder.

[[2026-03-31]] Tue 14:24
## Builder Notes (re-entry)
- Files changed: skills/dispatch-planning/SKILL.md only (changes from prior run verified in place)
- All 6 AC items confirmed present: type detection, completed: auto, Step 1 heading, pending field in Step 3 examples + fields + rules, self-critique item
- Tests: N/A (type:docs non-implementation task)
- No further changes needed

[[2026-03-31]] Tue 15:17
## Review Evidence
See docs/scratch/226-reviewer.md for full evidence.

[[2026-03-31]] Tue 16:12
## Test-Writer Notes (retry)
- Retry reason: reviewer FAIL was about commit discipline + AC4 format deviation, not missing tests.
- type:docs task - no tests applicable.
- Existing pass-through preserved. Builder will address reviewer findings.

[[2026-03-31]] Tue 16:52
## Builder Notes (re-entry 2)
- Files changed: skills/dispatch-planning/SKILL.md only
- Commit: ce63ea9 "docs: extend Recipe 0 for action request resolution (#226, builder)"
- Tests: N/A (type:docs non-implementation task)
- All 6 AC items verified present
- AC4 format deviation: AC specified 2-field {"decisions": N, "actions": N}; implementation uses 3-field {"decisions_t2": N, "decisions_t3": N, "actions": N}. Rationale: T2/T3 distinction is required for the 5-day auto-resolve skip logic in Recipe 0 (T3 decisions never auto-resolve). Collapsing to 2-field "decisions" would lose this information. The 3-field format is internally consistent with Recipe 0 prose and the research findings. Reviewer noted it is "arguably the correct implementation" - keeping it and documenting here.
- Commit discipline: addressed - staged and committed SKILL.md before advancing

[[2026-03-31]] Tue 17:45
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | .github/copilot-instructions.md | No | N/A | Skill-only update, no application behavior/API change |
| 2 | Docstrings | No | N/A | No Python modules changed |
| 3 | docs/sources/overview.md | Yes | Pass | Section at lines 176-181 with GitHub Actions + AutoGen attributions for task #226 already present |
| 4 | README.md | No | N/A | No CLI changes |
| 5 | Research doc linked | Yes | Pass | docs/research/planner-recipe0-action-request-extension.md exists; linked in task body |

### Files Updated
- None (sources/overview.md already updated by researcher)

### Scratch Files Cleaned
- Deleted docs/scratch/226-reviewer.md

[[2026-03-31]] Tue 21:30
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| Recipe 0 resolution + type detection | SKILL.md L62-73: completed: field detection, both approved/completed resolution | PASS |
| Recipe 0 auto-resolution completed: auto | SKILL.md L79-80: completed: auto with 5-day timeout | PASS |
| Step 1 heading/paragraph update | SKILL.md L161+: heading and paragraph reference action requests | PASS |
| Step 3 pending field + examples | SKILL.md L295+: 3-field format in both examples, Fields, Rules updated | PASS (minor deviation: 3-field vs AC 2-field, documented rationale) |
| Self-critique checklist item | SKILL.md L399: Recipe 0 dual-type check present | PASS |
| No changes outside SKILL.md | Commit ce63ea9: 1 file changed (SKILL.md only) | PASS |

### Test Results
- pytest: 2176 passed, 185 failed (all failures from other tasks: quality-runner, rename-todos, hooks, v2-infra, voice), 0 failures in task scope
- ruff: N/A (type:docs, no Python changed)

### Architect Quality
- AC specificity: 6 verifiable lines mapped to research 4-section scope
- Edge case coverage: adequate, minor AC4 format gap improved by builder
- Design direction: correct (type:docs, single-file scope)
- AC quality score: 4 (adequate, minor gap in AC4 format spec)

### Reviewer Evidence
- Reviewer conducted detailed review (task went through 2 review cycles)
- Scratch file docs/scratch/226-reviewer.md was correctly deleted by writer during docs gate but leaves dangling reference in body

### Deduction breakdown
- -.02 AC4 format deviation (2-field vs 3-field, documented, reviewer-accepted)
- -.01 dangling scratch reference in Review Evidence section

### Confidence: .97
### Action: archive
