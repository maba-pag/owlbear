---
id: 1811
title: Use tag editor for memory categories and scope agents
status: research
priority: important
created: 2026-05-24T08:08:57+02:00
updated: 2026-05-24T08:08:57+02:00
tags:
  - cockpit-perfect-ui
  - scope:cockpit-web
  - ux
  - memory
  - edit-form
  - tags
  - discussion
parent: 1773
depends_on: []
ac:
  - Memory edit categories use the same add-and-dismissible-tag mechanic used on
    other Cockpit edit surfaces where practical.
  - Memory edit scope agents use the same add-and-dismissible-tag mechanic where
    practical, while preserving the all-agents semantics.
  - The form remains compact and usable at the 1024px support floor.
  - Save payload, validation, and conflict behavior remain unchanged.
  - Screenshot proof captures category and scope-agent editing.
proof_bundle: behavioral+reader
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## Observation
User feedback: Memory edit categories and scope agents are comma-separated text inputs. They could benefit from the same list-style add input plus dismissible tag mechanic used elsewhere in Cockpit for uniformity and lower edit friction.

## Current Interpretation
The current comma-separated inputs are compact but inconsistent with the task detail tag/reference editing grammar. A tag editor would make individual category/agent removal clearer and reduce CSV parsing mistakes.

## Boundary
Discussion task only. Do not implement until explicitly approved.