---
id: 2044
title: 'P6-02: Expose the native designer and admission challenger'
status: build
priority: high
created: 2026-07-25T14:28:55.328794+02:00
updated: 2026-07-25T14:28:55.328794+02:00
tags:
  - phase-6
  - scope:agent
  - designer
  - challenger
  - prompt
  - type:build
  - rigor:thorough
  - change:replace-delivery-pipeline
  - node:DN-005
  - packet:DN-005-PK-002
  - interface:IF-006
parent: 1982
depends_on:
  - 2043
ac:
  - 'AC-1: The `designer` agent requires `w-design-session`, can ask one user question,
    edit current change authority, inspect source, use `list_changes | show_change
    | validate_change | admit_change`, and delegate only declared read-only specialists
    including `designer-challenger`; validators and frontmatter/body audit verify
    the runtime contract.'
  - 'AC-2: The `designer-challenger` agent is read-only and returns one source-grounded
    `{disposition, evidence}` entry for each declared requirement, workflow, interface,
    migration, risk, proof, and node using only `pass | warning | error`; its contract
    forbids admission approval and tracked writes.'
  - 'AC-3: Invoking `/ideate` enters discovery mode and invoking `/design` enters
    or resumes direct design mode through the same `designer` agent and `w-design-session`
    authority; prompt and wiring inspection proves both entries share one change identity
    and neither routes to an OpenSpec handoff.'
  - 'AC-4: `share/WIRING.md` and executable frontmatter agree on designer required
    reading, designer-to-challenger delegation, prompt entries, tools, and read-only
    enforcement; agent and skill validators report no loading, delegation, or tool
    drift.'
proof_bundle: critical+challenge
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## Projection
`replace-delivery-pipeline` at `3f6c656289911320bb5e7faf37b5e86ffa8511e729ade201a03a19913e33d990`; `DN-005-PK-002`. Resolve normative behavior from `DN-005`, `IF-006`, `MOD-003`, `MIG-003`, and `PROOF-004`; this record is not specification authority.

## Outcome
Expose one native designer role, one read-only admission challenger, and shared `/ideate` and `/design` entries over the designer workflow.

## Envelope
In: designer and challenger agents, prompt entries, exact native tool grants, direct loading and delegation declarations, and `share/WIRING.md`.

Out: setup or seed propagation, OpenSpec deletion, planner or builder roles, runtime changes, and product implementation.

Proof guidance: run ecosystem validators and derive the prompt, agent, skill, delegate, tool, and hook graph from executable declarations.