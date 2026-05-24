---
id: 1803
title: Reorder task reference edit rows
status: done
priority: important
created: 2026-05-24T06:42:31.419990+02:00
updated: 2026-05-24T07:05:59.718909+02:00
tags:
  - cockpit-perfect-ui
  - scope:cockpit-web
  - ux
  - kanban
  - task-detail
  - forms
  - references
  - discussion
parent: 1773
depends_on: []
ac:
  - Task detail edit mode presents dependency controls as a compact input row 
    before the current dependency chips.
  - The dependency control label/field context reads as Dependencies, with 
    compact input placeholder 'Add dependency ID' and compact '+ Add' action.
  - Parent controls follow the same row-first pattern, with compact input 
    placeholder 'Set parent ID' and compact Set/Clear actions as appropriate.
  - Existing dependency/parent validation, dirty state, conflict handling, and 
    save payload behavior remain unchanged.
  - Screenshot proof captures dependency and parent edit rows at the 1024px 
    support floor.
proof_bundle: behavioral+reader
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## Observation
User feedback: in Kanban task detail edit mode, the dependency and parent sections read in an awkward order. Current sequence is roughly label, existing compact dismissible chips, then an add/set input row below; the input itself is full size while adjacent actions are compact.

## Requested Direction
Use a row-first edit pattern:
- Dependencies: label/context, compact input with placeholder 'Add dependency ID', compact '+ Add' button, then existing compact dismissible dependency chips.
- Parent: label/context, compact input with placeholder 'Set parent ID', compact Set/Clear actions, then the existing compact parent chip or value.

## Current Interpretation
The form should prioritize the action users take while editing, then show existing values below as removable chips. This matches the recently improved tag editor pattern.

## Boundary
Discussion task only. Do not implement until explicitly approved.

[[2026-05-24T07:01:36+02:00]]
## User Approval
User approved standardizing the dependency and parent edit rows now, following the requested input-first compact row pattern.

[[2026-05-24T07:05:59+02:00]]
Implemented input-first reference edit rows. Dependencies now use compact label Dependencies with placeholder Add dependency ID and compact Add action before chips; Parent now uses compact label Parent with placeholder Set parent ID and compact Clear action before the parent chip. Existing validation, dirty state, conflict preservation, and save payload behavior remain covered by focused suites (183 passed, 1 skipped). Screenshot proof: .owlbear/scratch/1716-wide-cockpit/1802-1803-task-reference-edit-1024.png.
