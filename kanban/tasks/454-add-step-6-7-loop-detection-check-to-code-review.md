---
id: 454
title: Add Step 6.7 loop-detection check to code-review skill
status: backlog
priority: needed
created: 2026-03-30T23:40:39.0685332+02:00
updated: 2026-03-31T04:12:35.1227041+02:00
tags:
    - scope:agents
    - phase-2
claimed_by: architect
claimed_at: 2026-03-31T04:12:35.1227041+02:00
class: standard
---

## Context
Add a new CRITICAL check (Step 6.7) to the code-review skill that inspects builder Channel B notes for loop patterns.

See docs/research/reviewer-loop-pattern-detection.md for full analysis.

## Acceptance Criteria
- [ ] New Step 6.7 'Builder process quality (loop detection)' added to code-review skill after Step 6.6
- [ ] Step counts Builder Notes retry sections and checks for approach variation
- [ ] LOOP assessment (identical approaches or tier-3 without handoff) triggers automatic FAIL
- [ ] FRICTION assessment (retries with variation) is informational, does not block PASS
- [ ] CLEAN assessment (no retries or single retry) noted but no action needed
