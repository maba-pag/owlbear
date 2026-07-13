---
id: 225
title: Update agent-common handoff to reference action requests
status: archived
priority: medium
created: 2026-03-30 16:57:22.038895+02:00
updated: 2026-03-31 05:39:09.222694+02:00
started: 2026-03-31 05:35:37.973642+02:00
completed: 2026-03-31 05:35:37.973642+02:00
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
Update agent-common instructions to reference action requests for user-must-do-X scenarios.

## Acceptance Criteria
- [ ] Update handoff section in instructions/agent-common.instructions.md to reference action request creation
- [ ] Update defer-to-user boundary to distinguish decision requests vs action requests
- [ ] Add per-role triggers for action request creation (builder: manual testing, any: credentials/access)
- [ ] Update blocking convention to include action request blocking

## Context
See docs/research/extend-decision-request-for-action-requests.md

## Research

**Checklist:** All 7 items validated. Parent research #221 provides full source backing (6 sources, .85 confidence).

**Dependency:** depends_on #224. The decision-requests skill must define the action request format (request_type: action, completed field, Steps template) before agent-common can reference it.

**Implementation guidance:**

1. **Handoff section** (lines ~30-40): Add action request creation as structured alternative to raw block text. Keep existing handoff command but add: "For user-must-do-X scenarios (manual testing, GUI verification, credential setup), create an action request file instead. See the decision-requests skill for the action request format."

2. **Defer-to-user boundary** (lines ~43-59): Split async deferral into two sub-sections: decision requests (choose A/B, existing text) and action requests (do X, new text). Reference the same skill for both formats.

3. **Per-role triggers table** (lines ~61-73): Add second table for action request triggers. Key triggers: Builder (manual testing, GUI verification), Any agent (credentials/access setup, external service config, push/deploy actions).

4. **Blocking convention** (lines ~75-86): Add bullet: "Action requests: blocked pending user action completion" alongside existing decision request bullet.

**Risk:** Low. All changes are additive documentation. No behavioral or code changes.

[[2026-03-30]] Mon 23:06
## Architecture Review
**Verdict:** Approve

### AC Assessment
| AC Line | Assessment | Action |
|---------|------------|--------|
| Handoff section: reference action requests | Original wording adequate but vague on what to add | Refined: specify sentence content, skill reference, placement after handoff command block |
| Defer-to-user boundary: distinguish types | Good concept, needed structural spec | Refined: split into two labeled sub-sections (decision requests / action requests) |
| Per-role triggers for action requests | Good, examples in parens are specific | Refined: specify minimum rows (Builder, Any agent) and trigger text |
| Blocking convention: include action requests | Clear and atomic | Refined: specify exact bullet text to add |
| (new) No behavioral/code changes | Implicit in type:docs | Added: explicit AC line to confirm scope boundary |

### Architecture Notes
- type:docs task touching only instructions/agent-common.instructions.md. No code, no TDD needed.
- Precedent: #224 (same type:docs pattern) passed through pipeline successfully with same no-TDD justification.
- All changes are additive: existing handoff, defer-to-user, triggers, and blocking sections gain action-request parallels. No existing text removed or restructured.
- Scope properly bounded: planner Recipe 0 in #226, decision-requests skill done in #224. Only agent-common references remain.
- Premise challenge: agent-common currently only references decision requests. With #224 having added the action request format, agent-common must reference it so agents discover when to use action vs decision requests. Gap confirmed.
- No security surface, no module layering, no failure modes (docs only).
- Single domain: scope:agents / instructions.

### Changes Made
- Refined AC from 4 lines to 5 verifiable lines with specific section targets, content expectations, and placement guidance
- Added Constraints section documenting out-of-scope siblings (#224 done, #226 separate)
- Preserved implementation guidance from researcher

### Dependencies
- Verified: #224 (decision-requests skill update) â€” done
- Verified: #226 (planner Recipe 0) depends on #224, independent of #225

[[2026-03-31]] Tue 03:59
## Test-Writer Notes
- Non-implementation task (tagged type:docs) - no tests applicable.
- Passing through to builder.

[[2026-03-31]] Tue 05:35
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| Handoff section: reference action requests | Line 40: action request paragraph added after handoff block | PASS |
| Defer-to-user: distinguish decision vs action | Diff splits single paragraph into two subsections with headers | PASS |
| Per-role triggers for action requests | New table: Builder (manual test, creds), Any agent (external, push) | PASS |
| Blocking convention: action request blocking | New bullet added to blocking list | PASS |
| No behavioral/code changes | Commit touches only instructions/agent-common.instructions.md | PASS |

### Test Results
- pytest: 1891 passed, 162 failed (all pre-existing from other tasks: acp_client, agent_port_v2, voice, analysis, etc.), 0 related to #225
- ruff: clean (no Python files in scope)

### AC Quality Score: 4/5
AC was adequate with good specificity. Architect refined from 4 to 5 verifiable lines with section targets. Minor: original AC could have been more explicit about structural changes (subsection headers).

### Missing Pipeline Evidence
No Builder Notes, Review Evidence, or Docs Gate sections in task body. Builder committed correctly (b486720) but left no Channel B notes. Reviewer and writer appear to have been skipped or left no evidence. Deducting for missing reviewer evidence.

### Deduction breakdown
- All 5 AC lines verified with evidence: no deductions
- Missing reviewer evidence section: -.02

### Confidence: .98
### Action: archive

[[2026-03-31]] Tue 05:35
## Commits
| Commit | Type | Files | Tasks |
|--------|------|-------|-------|
| 64db19e | chore | kanban/tasks/225-*.md | #225 |

[[2026-03-31]] Tue 05:38
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| Handoff section: reference action requests | L40-41: action request paragraph with skill reference | PASS |
| Defer-to-user boundary: distinguish types | L58-81: two subsections (Decision requests / Action requests) | PASS |
| Per-role triggers for action requests | L77-81: table with Builder (2 rows) + Any agent (2 rows) | PASS |
| Blocking convention: include action requests | L94: bullet 'Action requests - blocked pending user action completion' | PASS |

### Test Results
- pytest: 1891 passed, 162 failed (all pre-existing, none in task scope - docs only change)
- ruff: not applicable (no Python files changed)

### Architect Quality
- AC specificity: 5 verifiable lines, all mechanically checkable
- Edge case coverage: no gaps, additive docs only
- Design direction: correctly identified no TDD needed
- AC quality score: 5/5

### Commit Verification
- b486720: docs: update agent-common to reference action requests (#225, builder) - 1 file, +21 -1
- No uncommitted deliverables

### Deduction breakdown
- -.02 missing reviewer evidence section
### Confidence: .98
### Action: archive

[[2026-03-31]] Tue 05:39
## Commits
| Commit | Type | Files | Tasks |
|--------|------|-------|-------|
| 7ecef76 | chore | kanban/tasks/225-*.md | #225 |
