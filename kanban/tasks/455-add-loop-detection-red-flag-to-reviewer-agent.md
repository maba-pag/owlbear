---
id: 455
title: Add loop-detection red flag to reviewer agent
status: backlog
priority: important
created: 2026-03-30T23:40:45.9947194+02:00
updated: 2026-03-31T03:41:01.1594455+02:00
tags:
    - scope:agents
    - phase-2
depends_on:
    - 454
class: standard
---

## Context
Add a red flag entry to reviewer.agent.md that cross-references the new Step 6.7 loop-detection check.

See docs/research/reviewer-loop-pattern-detection.md for analysis.

## Acceptance Criteria
- [ ] New red flag in reviewer.agent.md: 'You have not checked builder notes for loop patterns (Step 6.7)'
- [ ] Red flag placed in the existing Red flags list alongside other review checks

[[2026-03-31]] Tue 03:40
## Research
Trivial task -- research already complete in parent #436 (docs/research/reviewer-loop-pattern-detection.md).

**Checklist (trivial):**
1. Theoretical validity -- sound; follows existing 16-item red flag pattern in reviewer.agent.md
2. Environment audit -- no existing red flag covers loop detection
3. Prior art -- 6 sources in parent research doc (deer-flow, AutoGen, #432 3-tier model)
4. Technical feasibility -- single markdown line addition, no blockers
5. Architecture fit -- fits in existing Red flags list at ~line 107
6. Implementation -- add one bullet: 'You have not checked builder notes for loop patterns (Step 6.7)'

**Dependency added:** depends_on #454 (Step 6.7 must exist in code-review skill before red flag can reference it).

No additional follow-up tasks needed.

-t

[[2026-03-31]] Tue 03:40
## Research
Trivial task -- research already complete in parent #436 (docs/research/reviewer-loop-pattern-detection.md).

**Checklist (trivial):**
1. Theoretical validity -- sound; follows existing 16-item red flag pattern in reviewer.agent.md
2. Environment audit -- no existing red flag covers loop detection
3. Prior art -- 6 sources in parent research doc (deer-flow, AutoGen, #432 3-tier model)
4. Technical feasibility -- single markdown line addition, no blockers
5. Architecture fit -- fits in existing Red flags list at ~line 107
6. Implementation -- add one bullet referencing Step 6.7

**Dependency added:** depends_on #454 (Step 6.7 must exist in code-review skill before red flag can reference it).

No additional follow-up tasks needed.
