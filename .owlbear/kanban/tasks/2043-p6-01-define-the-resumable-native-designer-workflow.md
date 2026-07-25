---
id: 2043
title: 'P6-01: Define the resumable native designer workflow'
status: build
priority: high
created: 2026-07-25T14:28:48.796665+02:00
updated: 2026-07-25T14:28:48.796665+02:00
tags:
  - phase-6
  - scope:agent
  - designer
  - workflow
  - type:build
  - rigor:thorough
  - change:replace-delivery-pipeline
  - node:DN-005
  - packet:DN-005-PK-001
  - interface:IF-006
parent: 1982
depends_on: []
ac:
  - 'AC-1: Given `/ideate` rough input or `/design` with a change identity, `w-design-session`
    selects or creates one native change session, reads its existing intent, design,
    decisions, and delivery authority before writing, and preserves confirmed authority
    across resume; artifact inspection verifies both entry paths and resume ordering.'
  - 'AC-2: Given one unresolved material product or architecture choice, the workflow
    asks one `askQuestions` decision containing status quo, options, tradeoffs, risks,
    recommendation, and confidence, while repository-answerable facts route to read-only
    evidence gathering; workflow inspection verifies the decision contract.'
  - 'AC-3: Given confirmed scope, the workflow preserves Product Promise, accepted
    exclusions, canonical evidence states, qualified memory use, and adaptive architecture
    review while producing complete modular delivery authority; inspection maps `REQ-001`
    and `KEEP-001 | KEEP-002 | KEEP-003 | KEEP-008 | KEEP-009` to named stages and
    outputs.'
  - 'AC-4: Given unresolved material authority, non-pass challenge, failing baseline,
    failed validation, or absent approval, the workflow keeps the revision draft and
    forbids `admit_change`; given complete pass evidence, it invokes `validate_change`
    before `admit_change` with the current digest and records returned receipt, generation,
    and job identities.'
proof_bundle: existing+challenge
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## Projection
`replace-delivery-pipeline` at `3f6c656289911320bb5e7faf37b5e86ffa8511e729ade201a03a19913e33d990`; `DN-005-PK-001`. Resolve normative behavior from `DN-005`, `IF-006`, `REQ-001`, `KEEP-001`, `KEEP-002`, `KEEP-003`, `KEEP-008`, `KEEP-009`, and `PROOF-004`; this record is not specification authority.

## Outcome
Define one `w-design-session` workflow for native change selection or creation, durable authority updates, one-question decisions, specialist evidence, validation, challenge, baseline, approval, admission, and interruption resume.

## Envelope
In: the workflow skill and its direct loading contract.

Out: agent and prompt wiring, runtime code, setup or seed changes, OpenSpec deletion, frontier planning, and product implementation.

Proof guidance: inspect the assembled workflow against canonical admission models and public change-tool declarations; no model-response substitute proves this packet.