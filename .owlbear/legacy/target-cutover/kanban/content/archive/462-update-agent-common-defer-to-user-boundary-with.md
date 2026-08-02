---
id: 462
title: Update agent-common defer-to-user boundary with tier classification
status: archived
priority: medium
created: 2026-03-31 03:40:17.761738+02:00
updated: 2026-03-31 08:03:43.148191+02:00
started: 2026-03-31 08:03:42.748887+02:00
completed: 2026-03-31 08:03:42.748887+02:00
tags:
- process
- scope:agents
- quality
class: standard
archival_reason: completed
archival_refs: []
---

Update the "Defer-to-user boundary" section of instructions/agent-common.instructions.md (currently lines ~42-75) with tier classification references from docs/research/mandatory-user-decision-gate.md.

Scope: instructions/agent-common.instructions.md only. Action requests section, Blocking convention section, and everything below remain untouched.

AC:
- [ ] Bullets 1-2 in the "Defer to the user only when:" list replaced with tier-aware language referencing T2 (advisory) and T3 (mandatory) with deterministic trigger descriptions
- [ ] Bullets 3-4 (credentials/access and repeated test/lint failures) remain unchanged
- [ ] Inline tier summary block (T1/T2/T3 one-line definitions with examples) added between the async deferral paragraph and the "Decision requests" subheading so agent-common is self-contained without loading the decision-requests skill
- [ ] Decision requests per-role triggers table: Researcher row references T3 mandatory gate (blocking DR, no auto-resolve) and T2 advisory DR explicitly
- [ ] Decision requests per-role triggers table: other rows add tier context parenthetically where applicable (Architect: T3-origin check; Builder: T3 design fork)
- [ ] Action requests section and Blocking convention section NOT modified
- [ ] No functional behavior changes; language clarification pass only; no new concepts introduced

Dependency note: #459 (impact_tier in decision-requests skill) is at todo. Agent-common changes are self-contained (the inline tier summary provides sufficient context). Ideal ordering: #459 lands first, but not blocking.

[[2026-03-31]] Tue 03:54
## Research
Validated. See docs/research/agent-common-tier-classification-update.md for full analysis.

Three changes to defer-to-user boundary (lines 40-75):
1. Replace vague bullets 1-2 with tier-aware language (T2 advisory, T3 mandatory)
2. Update per-role triggers table with tier references (Researcher row: T3 mandatory gate)
3. Add inline tier summary before the table for self-contained reference

Soft dependency on #459 (decision-requests skill gets impact_tier field first). Agent-common changes are self-contained enough to land independently.

No additional follow-up tasks needed - #462 is the implementation task.

[[2026-03-31]] Tue 04:29
## Architecture Review
**Verdict:** Approve

### AC Assessment
| AC Line | Assessment | Action |
|---------|------------|--------|
| Bullets 1-2 replaced with tier language | Clear, verifiable by diff | Kept |
| Bullets 3-4 unchanged | Regression guard | Kept |
| Inline tier summary block added | Testable (search for T1/T2/T3 defs) | Kept |
| Researcher row references T3/T2 | Specific and verifiable | Kept |
| Other rows add tier context | Verifiable by inspection | Kept |
| Action requests/Blocking unchanged | Regression guard | Kept |
| No functional changes | Scope guard | Kept |

### Architecture Notes
Pure documentation task: edits one .instructions.md file. No code, no tests needed. Changes are mechanical text replacements guided by the tier definitions in docs/research/mandatory-user-decision-gate.md. The inline tier summary is essential so agents don't need to load the decision-requests skill just to understand T1/T2/T3 in context.

Soft dependency on #459 (impact_tier field in decision-requests skill, currently at todo). Agent-common changes are self-contained since the inline summary provides tier definitions directly. No blocking dependency needed.

### Changes Made
- Refined AC from 3 vague lines to 7 verifiable checklist items
- Added scope constraint and dependency note

### Dependencies
- Soft: #459 (impact_tier in decision-requests skill) at todo, not blocking

[[2026-03-31]] Tue 05:01
## Test-Writer Notes
- Non-implementation task (tagged quality) — no tests applicable.
- Passing through to builder.

[[2026-03-31]] Tue 06:10
## Builder Notes\n- Files changed: instructions/agent-common.instructions.md\n- Change type: documentation-only (no tests applicable)\n- Commit: 0f6ce82\n- AC verified:\n  - Bullets 1-2 replaced with T2 advisory and T3 mandatory tier language\n  - Bullets 3-4 (credentials, test/lint failures) unchanged\n  - Inline tier summary table (T1/T2/T3) added before Decision requests subheading\n  - Researcher row: T3 mandatory blocking DR + T2 advisory DR explicitly\n  - Architect row: T3-origin check + downstream scope (T2/T3)\n  - Builder row: T3 design fork wording preserved\n  - Action requests and Blocking convention sections untouched
