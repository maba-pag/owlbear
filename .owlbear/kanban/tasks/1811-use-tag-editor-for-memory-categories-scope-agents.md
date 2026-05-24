---
id: 1811
title: Use tag editor for memory categories and scope agents
status: done
priority: important
created: 2026-05-24T08:08:57+02:00
updated: 2026-05-24T08:34:18+02:00
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

[[2026-05-24T08:34:18+02:00]]
## User Approval
User clarified that the wildcard behavior already exists and approved treating `*` as a normal dismissible scope-agent tag in the improved add/remove mechanic.

[[2026-05-24T08:34:18+02:00]]
Implemented Memory edit category and scope-agent add/remove editors. The comma-separated edit fields are replaced by compact add inputs, Add buttons, and `PTagDismissible` chips. Save payloads still send `categories` and `scope_agents` arrays, and `*` remains a normal scope-agent value when present. Verification: focused Memory suite passed (82 tests), ESLint passed for changed Memory files, and production build passed with the known Vite chunk-size warning only. Screenshot proof: `.owlbear/scratch/1716-wide-cockpit/1811-memory-tag-editors-1024.png`.