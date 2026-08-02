---
id: 1964
title: Define shaping repair re-entry and Product Promise coverage
status: archived
priority: high
created: 2026-07-20T00:33:28.466706+02:00
updated: 2026-07-20T01:03:23.243990+02:00
tags:
  - scope:shaping
  - agent-ecosystem
  - workflow-coherence
parent:
depends_on: []
ac:
  - 'AC1: `w-spec-shaping` contains a repair re-entry table mapping product outcome
    or scope, architecture or interface, normative behavior, and task-graph-only changes
    to named review stages, verified by artifact inspection.'
  - 'AC2: `w-task-repair` references the re-entry table and does not duplicate its
    stage-selection procedure, while retaining user approval for material changes.'
  - 'AC3: `w-task-decomposition` defines a Product Promise coverage map with Promise
    item or accepted exclusion, owning task or aggregate condition, and proving AC
    or outcome; an unowned active item blocks graph approval.'
  - 'AC4: `w-spec-shaping` and challenger inputs reference the decomposition-owned
    coverage map rather than restating an undefined completeness check.'
  - 'AC5: Ecosystem validators and focused shaping tests pass.'
proof_bundle: existing
blocked: false
block_reason:
claimed_at:
archival_reason: completed
archival_refs: []
---
## Objective
Make material task repair enter staged spec shaping at a deterministic review point and make Product Promise coverage an inspectable graph artifact.

## Scope
- `share/skills/w-task-repair/SKILL.md`
- `share/skills/w-spec-shaping/SKILL.md`
- `share/skills/w-task-decomposition/SKILL.md`
- shaper/challenger wording only if required to reference the owning procedure

## Boundaries
Preserve user approval for material changes. Do not alter ideation workflows or agents. Keep repair classification in `w-task-repair`, staged review ownership in `w-spec-shaping`, and graph coverage mechanics in `w-task-decomposition`.



## Implementation Notes

Completed directly without pipeline dispatch. Added a material-repair re-entry table to `w-spec-shaping`, routed `w-task-repair` to that authority, and defined a decomposition-owned Product Promise Coverage Map with an approval-blocking rule for unowned active items. Extended maintained shaping interaction contracts.

Evidence: focused shaping suite passed (16 tests); final integrated gate passed.
