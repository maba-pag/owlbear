---
id: 226
title: Update planner Recipe 0 for action request resolution
status: todo
priority: needed
created: 2026-03-30T16:57:32.0682585+02:00
updated: 2026-03-31T04:39:26.0141676+02:00
tags:
    - phase-1
    - scope:agents
    - type:docs
depends_on:
    - 224
class: standard
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
