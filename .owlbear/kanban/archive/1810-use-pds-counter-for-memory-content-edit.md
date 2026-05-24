---
id: 1810
title: Use PDS counter for memory content edit
status: archived
priority: important
created: 2026-05-24T08:08:57+02:00
updated: 2026-05-24T10:50:02.762743+02:00
tags:
  - cockpit-perfect-ui
  - scope:cockpit-web
  - ux
  - memory
  - edit-form
  - pds
  - discussion
parent: 1773
depends_on: []
ac:
  - Memory edit mode uses the native Porsche Design System textarea counter for
    content length when practical.
  - The separate sticky header character chip is removed or justified by a
    stronger layout reason.
  - Content remains multiline, spell-checkable, and capped at 1024 characters.
  - Save payload, validation, and conflict behavior remain unchanged.
  - Screenshot proof captures Memory edit mode at the 1024px support floor.
proof_bundle: behavioral+reader
blocked: false
block_reason:
claimed_at:
archival_reason: completed
archival_refs: []
---
## Observation
User feedback: Memory edit mode has a separate character counter chip in the sticky edit header. Porsche Design System text fields/textarea support `maxLength` plus `counter`, so the counter may belong on the content control itself.

## Current Interpretation
The current separate counter likely predates or bypasses PDS built-in counter support. Because Memory content is multiline, the relevant control is `PTextarea`, not `PInputText`, but PDS v4 exposes `counter?: boolean` and `maxLength?: number` for `PTextarea`.

## Boundary
Discussion task only. Do not implement until explicitly approved.

[[2026-05-24T08:19:42+02:00]]
## User Approval
User approved implementing the PDS counter cleanup now.

[[2026-05-24T08:19:42+02:00]]
Implemented `counter` on the Memory edit `PTextarea` and removed the separate sticky-header character counter chip. The content field remains multiline and capped at 1024 characters. Verification: focused Memory suite passed (81 tests), ESLint passed for changed Memory files, and production build passed with the known Vite chunk-size warning only. Screenshot proof: `.owlbear/scratch/1716-wide-cockpit/1810-memory-edit-form-element-1024.png`, showing the native textarea counter (`125/1024`) and no duplicate header chip.