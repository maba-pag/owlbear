---
id: 635
title: 'Fix #616 decision: scribe fabricated approval from needs-info response'
status: archived
priority: medium
created: 2026-04-05T22:45:51.0003611+02:00
updated: 2026-04-06T00:09:36.3059286+02:00
started: 2026-04-06T00:09:36.3059286+02:00
completed: 2026-04-06T00:09:36.3059286+02:00
tags:
    - process
    - bugfix
class: standard
---

## Summary

Task #616's decision was incorrectly resolved. The user responded with `decision: "user needs more information, see notes"` and follow-up questions in `notes:`, but the scribe treated it as a full approval and wrote "Decision: Option A" to the task body — fabricating a decision the user never made.

## What happened

1. DR created for #616 as T3 blocking decision
2. User set `approved: true` (only mechanism available) but `decision: "user needs more information, see notes"` with risk questions in `notes:`
3. Scribe saw `approved: true`, ignored the `decision:` field content, wrote "Approved — Option A" to task
4. Task unblocked, pipeline continued — risk-depth research was done but no second DR was created for actual approval

## Root cause

Fixed in this session: the DR format now supports `approved: needs-info` and `approved: rejected` states (see updated `w-decision-routing` skill, `scribe.agent.md`, and `.owlbear/decisions/README.md`). The scribe also now validates the `decision:` field content before treating `approved: true` as a genuine approval.

## Acceptance Criteria

- [ ] Review task #616's current state — the "Decision Resolved" section contains a fabricated decision
- [ ] Correct the task body: replace fabricated "Approved — Option A" with actual user response
- [ ] Re-create the DR in pending if you want to properly approve the scope-params approach, OR manually write the correct approval to the task body if the risk-depth research (already done) answered your questions
- [ ] Verify #617 and #618 are in the right state given the corrected decision status

## Done\nCorrected directly in session:\n- Fixed #616 task body: replaced fabricated 'Approved — Option A' with actual user response\n- Corrected resolved DR file frontmatter: changed approved from true to needs-info\n- Corrected architecture review text referencing false approval\n- A new DR is needed for formal approval of the scope-params approach

[[2026-04-06]] Mon 00:08
## Audit

### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| AC1: Review #616 state | #616 body has Decision Resolved (CORRECTED): Status NOT approved | PASS |
| AC2: Correct task body | #616 shows actual user decision field and real risk questions | PASS |
| AC3: Re-create DR in pending | New DR at pending/616-scope-params-approval.md (approved: false). Old corrected | PASS |
| AC4: Verify #617/#618 states | #616 blocked, #617 backlog, #618 in-progress. Pipeline stalled by #616 block | PASS |

### Root Cause Fix (bonus deliverables)
- w-decision-routing: needs-info/rejected states, validation gate
- scribe.agent.md: validation rule for decision field
- decisions/README.md: user instructions for new workflows

### Test Results
- pytest: 2914 passed, 482 failed (all pre-existing), 18 skipped. Zero in #635 scope
- ruff: All checks passed

### Architect Quality: 3/5
AC1-3 specific. AC4 vague (right state undefined). Adequate for corrective task.

### Deduction Breakdown
- Missing reviewer evidence (process task): -.02
- AC quality 3/5: -.03

### Confidence: .95
### Action: archive

[[2026-04-06]] Mon 00:09
4 AC lines verified, all PASS. Root cause fix solid (needs-info/rejected DR states, scribe validation gate). Full suite: no #635-scope failures. Confidence .95.
