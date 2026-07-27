---
id: 2089
title: 'P16-05: Remove retired delivery agents and workflow surfaces'
status: build
priority: high
created: 2026-07-27T08:39:38.469917+02:00
updated: 2026-07-27T08:39:38.469917+02:00
tags:
  - phase-16
  - scope:agent
  - type:build
  - rigor:thorough
  - change:replace-delivery-pipeline
  - digest:6c95c70c81a1
  - node:DN-012
  - packet:T5
  - module:MOD-003
  - module:MOD-009
parent: 1989
depends_on: []
ac:
  - 'AC-1: Given the installed prompt, agent, skill, instruction, and orchestrator
    inventories, the exposed delivery roles are native design, plan, build, accept,
    audit, and graph-aware orchestration with purpose-specific job tools.'
  - 'AC-2: Given a lookup for shape, verify, collect, OpenSpec, opsx, or generic task-authority
    entry surfaces, the installed ecosystem exposes no dispatchable prompt, agent,
    skill, instruction, or tool grant for that workflow.'
  - 'AC-3: Given native builder, acceptor, auditor, and orchestrator write attempts,
    the installed hooks preserve their scoped path, tracked-write, commit-ownership,
    and read-only proof restrictions.'
proof_bundle: existing+challenge
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## Outcome
The installed agent ecosystem and write guards expose the native design, plan, build, accept, audit, and orchestration workflow without dispatchable shape/verify/collect or OpenSpec authority.

## Scope
In scope: MOD-003 and MOD-009 agents, prompts, skills, instructions, wiring, tool declarations, hooks, and seed hook equivalents.

Out of scope: Python/MCP/FastAPI runtime deletion, setup behavior, distribution documentation, and live-board retirement.

## Authority
DN-012 at delivery digest `6c95c70c81a13ef7a59206ac63bfd9b7338ccb87520d22d90517bf67d50167e9`; REQ-011, REQ-017, MIG-002/MIG-003 consumer inventories, RISK-005, KEEP-007, and completed IF-006 through IF-010.

Proof guidance: validate assembled agent/prompt/skill/instruction/hook inventories and native role write-guard behavior; use artifact validation rather than durable source-string absence tests.