---
id: 1782
title: Improve Ideas preview contrast and edit affordance
status: archived
priority: important
created: 2026-05-24T01:20:05.062245+02:00
updated: 2026-05-24T10:50:02.384793+02:00
tags:
  - cockpit-perfect-ui
  - scope:cockpit-web
  - visual-proof
  - ux
  - discussion
parent: 1773
depends_on:
  - 1781
ac:
  - At supported desktop widths, the Ideas saved preview state reads as active
    content, not disabled UI.
  - The Edit action is visually distinguishable as available when Save is
    disabled.
  - Preview text and notebook metadata meet the Cockpit's normal
    contrast/hierarchy expectations.
  - No implementation begins until the user approves this task.
blocked: false
block_reason:
claimed_at:
archival_reason: completed
archival_refs: []
---
## Observation
In stable 1024px evidence, the Ideas tab reads visually disabled or washed out even when it is in a normal saved preview state. The page title, preview content, notebook panel, and toolbar controls have low apparent contrast; the active Edit action is hard to distinguish from the disabled Save action.

## Evidence
- `.owlbear/scratch/1716-wide-cockpit/1781-1024-ideas-steady.png`
- Route readiness probe reported Ideas route opacity=1 and transform=none, so this is not just the earlier transition-fade artifact.
- The current screenshot shows the normal saved preview with `Saved`, `Edit`, and disabled `Save` controls, but the whole surface feels inactive.

## Current Interpretation
Observed supported-width UX harm, not a width issue. A desktop user may read the Ideas notebook as disabled or unavailable, and the main action to edit the notebook has weak affordance compared with the disabled save action.

## Value
Ideas is supposed to be a quick capture/review surface. If saved preview looks inert, users may hesitate before editing or assume the notebook is read-only.

## Decision Needed
Discuss whether to make the saved preview state more active and legible: stronger text hierarchy, clearer active Edit affordance, and less disabled-looking panel treatment while preserving the disabled Save state.

[[2026-05-24T01:56:07+02:00]]
## Reclassification
User judged this as a loading/capture artifact, not a product issue. Do not implement Ideas contrast changes from this evidence; use #1781-style stable capture first if Ideas UX is reconsidered later.
