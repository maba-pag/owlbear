---
id: 225
title: Update agent-common handoff to reference action requests
status: review
priority: needed
created: 2026-03-30T16:57:22.0388952+02:00
updated: 2026-03-31T04:12:33.7273227+02:00
tags:
    - phase-1
    - scope:agents
    - type:docs
depends_on:
    - 224
claimed_by: reviewer
claimed_at: 2026-03-31T04:12:33.7262877+02:00
class: standard
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
