---
id: 635
title: 'Fix #616 decision: scribe fabricated approval from needs-info response'
status: todo
priority: needed
created: 2026-04-05T22:45:51.0003611+02:00
updated: 2026-04-05T22:45:51.0003611+02:00
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
