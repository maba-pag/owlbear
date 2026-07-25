---
id: 2045
title: 'P6-03: Prove designer interruption, decisions, and refusal'
status: build
priority: high
created: 2026-07-25T14:29:01.440279+02:00
updated: 2026-07-25T14:29:01.440279+02:00
tags:
  - phase-6
  - scope:test
  - designer
  - interaction
  - type:build
  - rigor:thorough
  - change:replace-delivery-pipeline
  - node:DN-005
  - packet:DN-005-PK-003
  - interface:IF-006
  - proof:PROOF-004
parent: 1982
depends_on:
  - 2043
  - 2044
ac:
  - 'AC-1: Given an interrupted fixture after confirmed intent and one decision are
    persisted, the `PROOF-004` scenario reloads the real `/design` prompt, `designer`
    agent, and `w-design-session` workflow for the same change identity and observes
    those authority records unchanged before continuation.'
  - 'AC-2: Given one material choice and repository-grounded specialist evidence,
    the scenario observes one permitted question whose options include tradeoffs,
    risks, recommendation, and confidence, while a proposed second material choice
    remains pending for a later turn.'
  - 'AC-3: Given an unresolved material decision, the scenario follows the real designer
    contract through public `show_change` and `validate_change`, observes a non-admitted
    assessment for the current draft, and confirms the designer neither requests approval
    nor invokes `admit_change`.'
  - 'AC-4: Given a resolved draft whose public `validate_change` returns a non-admitted
    assessment from one representative DN-002-proven failure, the scenario observes
    the designer keep the revision draft, report the returned finding, and leave receipt,
    generation, sequence, and job snapshots unchanged; it does not assert evaluator-family
    completeness.'
proof_bundle: critical+challenge
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## Projection
`replace-delivery-pipeline` at `3f6c656289911320bb5e7faf37b5e86ffa8511e729ade201a03a19913e33d990`; `DN-005-PK-003`. Resolve normative behavior from `DN-005`, `IF-006`, and `PROOF-004`; this record is not specification authority.

## Outcome
Maintain real prompt, agent, and workflow scenario evidence for native session continuity, one-question choices, specialist evidence, unresolved-authority refusal, and failed-assessment routing.

## Envelope
In: durable agent scenario evidence over a temporary native change and local defects inside the accepted interaction contract.

Out: positive admission publication, admission evaluator-family completeness, setup or seed changes, OpenSpec deletion, and alternate prompt or MCP adapters.

Proof guidance: exercise shipped prompt, agent, and workflow artifacts; only an external research response may be replaced below the designer workflow.