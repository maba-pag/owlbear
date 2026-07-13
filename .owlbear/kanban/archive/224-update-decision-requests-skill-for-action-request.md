---
id: 224
title: Update decision-requests skill for action request type
status: archived
priority: medium
created: 2026-03-30 16:57:14.035359+02:00
updated: 2026-03-30 23:28:23.193891+02:00
started: 2026-03-30 23:28:17.023063+02:00
completed: 2026-03-30 23:28:17.023063+02:00
tags:
- phase-1
- scope:agents
- type:docs
class: standard
archival_reason: completed
archival_refs: []
---

## Objective
Add action request format to the decision-requests skill alongside the existing decision format.

## Acceptance Criteria
- [ ] Add `request_type` field to frontmatter spec in `skills/decision-requests/SKILL.md`: values `decision` (default, may be omitted for backwards compat) or `action`
- [ ] Document field applicability by type: `approved`/`decision`/`decision_type` are decision-only; `completed` is action-only; `notes`/`task_id`/`agent`/`created`/`urgency` are shared
- [ ] Add action request body template with sections: Context, Steps (checkbox list), Completion instructions
- [ ] Add "When to create an action request" section with triggers: manual testing, GUI verification, credential setup, deployments, external actions
- [ ] Add resolution rules for action requests: user checks off steps, sets `completed: true`; planner treats same as `approved: true`
- [ ] Clarify "Option presentation conventions" section applies to decision type only
- [ ] Update `docs/decisions/README.md` with parallel "Action requests" section including "Mark as complete" workflow
- [ ] Existing decision request files and format remain backwards-compatible (omitting `request_type` = decision)

## Constraints
- Planner Recipe 0 changes are OUT OF SCOPE -- tracked by #226 (depends on this task)
- `agent-common.instructions.md` handoff updates are OUT OF SCOPE -- tracked by #225

## Context
See docs/research/extend-decision-request-for-action-requests.md

[[2026-03-30]] Mon 19:25
## Architecture Review
**Verdict:** Approve

### AC Assessment
- request_type field: Clear — field name, values, default specified. Refined with backwards-compat default behavior.
- Field applicability: New AC — formalizes research note #2 (decision-only vs action-only vs shared fields).
- Action body template: Clear — sections enumerated. Kept.
- "When to create" section: New AC — formalizes research note #3 (manual testing, GUI, credentials, deploys).
- Resolution rules: Clear — user workflow and planner equivalence specified. Refined.
- Option conventions scope: New AC — formalizes research note #4. Added.
- README parallel section: Refined — specifies parallel section structure with "Mark as complete" workflow.
- Backwards-compatible: Clear constraint — omitting request_type = decision. Kept.

### Architecture Notes
- type:docs task touching only .md files (SKILL.md + README.md). No code, no TDD needed.
- Extends existing decision-request format in-place (Option A from research). No new directories or config.
- Scope properly bounded: planner Recipe 0 changes in #226, agent-common handoff in #225.
- No security surface, no module layering, no failure modes (docs only).
- Premise challenge: no existing mechanism for structured action requests. The gap is real (evidenced by #167, #29, #174 using unstructured block text).

### Changes Made
- Refined AC from 5 lines to 8 verifiable lines incorporating researcher implementation notes
- Added Constraints section documenting out-of-scope siblings (#225, #226)
- Removed inline research notes (now formalized in AC)

### Dependencies
- Verified: #221 (research) complete, findings captured
- Verified: #226 (planner Recipe 0) depends_on #224, correctly sequenced
- Verified: #225 (agent-common handoff) exists in backlog, independent

[[2026-03-30]] Mon 21:00
## Test-Writer Notes
- Non-implementation task (tagged type:docs) -- no tests applicable.
- Task touches only .md files (SKILL.md + README.md). Architecture review confirms no code, no TDD needed.
- Passing through to builder.

[[2026-03-30]] Mon 21:27
## Builder Notes
- Files changed: skills/decision-requests/SKILL.md, docs/decisions/README.md
- Non-implementation task (type:docs) -- markdown-only changes, no tests applicable
- All 8 AC items satisfied:
  1. request_type field added to frontmatter spec (decision=default/omittable, action)
  2. Field applicability documented via Applies to column: approved/decision/decision_type=decision-only, completed=action-only, shared fields marked all
  3. Action request body template added with Context, Steps (checkbox list), Completion instructions sections
  4. When to create an action request section added with all 5 specified triggers
  5. Resolution rules added under ### Action requests in Resolution workflow
  6. Option presentation conventions heading renamed to include (decision type only)
  7. docs/decisions/README.md updated with parallel Action requests section + Mark as complete workflow
  8. Decision template unchanged -- omitting request_type defaults to decision (backwards compat)
- Commit: 72b0971

[[2026-03-30]] Mon 22:24
## Review Evidence

**Reviewer:** reviewer
**Scope:** docs-only -- skills/decision-requests/SKILL.md + docs/decisions/README.md (2 files, 93 insertions, commit 72b0971)
**No tests applicable** (type:docs, confirmed by test-writer and architect).
**No lint applicable** (markdown only).

### AC Compliance

All 8 AC lines verified:
- AC1: request_type field added to frontmatter table with 'decision (default, may be omitted) / action' -- PASS
- AC2: Field applicability column -- approved/decision/decision_type: decision; completed: action; notes/task_id/agent/created/urgency: all -- PASS
- AC3: Action template contains Context, Steps (checkboxes), Completion instructions -- PASS
- AC4: 'When to create an action request' section with all 5 triggers -- PASS
- AC5: Resolution subsection: check steps, completed: true, planner treats same as approved: true -- PASS
- AC6: Heading renamed to 'Option presentation conventions (decision type only)' -- PASS
- AC7: docs/decisions/README.md has Action requests section with Mark as complete workflow -- PASS
- AC8: Frontmatter table notes '(default, may be omitted)'; decision template omits request_type -- PASS

### Security
Markdown-only, no security surface.

### Verdict: PASS -- confidence .94

-t

[[2026-03-30]] Mon 22:52
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | .github/copilot-instructions.md | No | N/A | All references to 'decision request' are contextually correct; agent-common.instructions.md updates are out of scope (tracked by #225) |
| 2 | Docstrings | No | N/A | Markdown-only task - no Python modules changed |
| 3 | docs/sources/overview.md | Yes | Pass | Already updated by researcher (#221): 3 external sources logged with correct Where Used path |
| 4 | README.md | No | N/A | No CLI changes |
| 5 | Research doc | Yes | Pass | docs/research/extend-decision-request-for-action-requests.md exists and linked in task body; follow-up tasks #225 and #226 created |

### Files Updated
- None

### Scratch Files Cleaned
- None found for task #224

[[2026-03-30]] Mon 23:28
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| AC1: request_type field in frontmatter spec | SKILL.md frontmatter table row: request_type, decision (default, may be omitted) / action | PASS |
| AC2: Field applicability by type | Applies to column: approved/decision/decision_type=decision, completed=action, shared=all | PASS |
| AC3: Action request body template | Template with Context, Steps (checkbox), Completion instructions sections present | PASS |
| AC4: When to create an action request | Section with 5 triggers: manual testing, GUI, credentials, deployments, external actions | PASS |
| AC5: Resolution rules for action requests | Action requests subsection: check steps, completed: true, planner equivalence | PASS |
| AC6: Option conventions decision-only | Heading renamed to 'Option presentation conventions (decision type only)' | PASS |
| AC7: README.md parallel section | Action requests section with Mark as complete 5-step workflow present | PASS |
| AC8: Backwards-compatible | Decision template omits request_type; table notes '(default, may be omitted)' | PASS |

### Test Results
- pytest: 1588 passed, 135 failed (all pre-existing, none in task scope), 1 error (unrelated), 7 skipped
- ruff: 3 violations (all pre-existing, none in task scope: E902 src path, 2x PT018 in test_necessity_check_196.py)

### Architect Quality
- AC specificity: 8 concrete, verifiable lines covering format, content, and compatibility
- Edge cases: N/A (docs-only task, no runtime behavior)
- Design direction: Correctly identified as type:docs, no TDD needed
- AC quality score: 4/5 (adequate, well-structured; minor: trigger list could be more prescriptive)

### Reviewer Evidence
Present and detailed: 8/8 AC lines mapped with PASS verdicts, .94 confidence.

### Deduction breakdown
- No deductions: all 8 AC lines verified with specific evidence
- No task-scope test failures
- No task-scope lint violations
- AC quality 4 (no deduction, threshold is 3)
- Reviewer evidence present (no deduction)

### Confidence: 1.0
### Action: archive
