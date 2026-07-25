---
id: 2046
title: 'P6-04: Prove successful native design admission'
status: verify
priority: high
created: 2026-07-25T14:29:08.002900+02:00
updated: 2026-07-25T14:58:00.576648+02:00
tags:
  - phase-6
  - scope:test
  - designer
  - admission
  - integration
  - type:build
  - rigor:thorough
  - change:replace-delivery-pipeline
  - node:DN-005
  - packet:DN-005-PK-004
  - interface:IF-006
  - proof:PROOF-004
parent: 1982
depends_on:
  - 2045
ac:
  - 'AC-1: Given a complete modular fixture, pass disposition for each declared requirement,
    workflow, interface, migration, risk, proof, and node, passing baseline, explicit
    approval, and current digest, the scenario invokes public `list_changes`, `show_change`,
    `validate_change`, and `admit_change`, then observes one admitted receipt, generation,
    and initial plan jobs bound to that digest.'
  - 'AC-2: Given the same immutable evidence and admitted fixture, a second public
    `admit_change` returns the persisted receipt, generation, and plan jobs while
    preserving artifact counts and bytes.'
  - 'AC-3: The maintained `PROOF-004` scenario derives `/ideate` and `/design` entry,
    designer delegation, one-question decision shape, challenge evidence, validation,
    approval, and admission from shipped prompt, agent, and workflow artifacts; replacing
    an entry or public tool call with an OpenSpec handoff or fixture-only adapter
    makes the scenario fail.'
proof_bundle: critical+challenge
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## Projection
`replace-delivery-pipeline` at `3f6c656289911320bb5e7faf37b5e86ffa8511e729ade201a03a19913e33d990`; `DN-005-PK-004`. Resolve normative behavior from `DN-005`, `IF-006`, and `PROOF-004`; this record is not specification authority.

## Outcome
Complete `PROOF-004` with the positive native design journey and exact admission replay through the real designer surface and public change tools.

## Envelope
In: assembled prompt, agent, workflow, native fixture, public change tools, publication observation, and exact replay.

Out: new admission evaluator semantics, frontier planning, setup or seed changes, OpenSpec deletion, and mocked MCP wrappers.

Proof guidance: exercise assembled `MOD-003` contracts plus public MCP functions; only an external research response may be replaced below the designer workflow.

[[2026-07-25T14:58:00+02:00]]
## Builder Notes
Completed the positive `PROOF-004` journey in the existing durable designer scenario module. No production, evaluator, frontier-planning, setup/seed, or OpenSpec files changed.

### AC Evidence
- AC-1: The new scenario copies the real admitted modular change and declared research, builds complete current-digest evidence with one pass disposition for every declared challenge family, a passing baseline, explicit approval, and limits, then directly invokes public `list_changes`, `show_change`, `validate_change`, and `admit_change`. It observes a no-error assessment, one digest-bound receipt and generation, and exactly one plan job for every real delivery node, all bound to the same digest and receipt.
- AC-2: After the first admission, the scenario snapshots every receipt, generation, sequence, and board-job byte. An identical second public `admit_change` returns an equal receipt/generation/assessment payload, preserves the complete snapshot byte-for-byte, and leaves exactly one receipt, one generation, and one job per node.
- AC-3: The maintained module reads the shipped `/ideate` and `/design` prompts, `designer` agent, and `w-design-session`; it requires both entries to delegate to designer and the shared workflow, requires their OpenSpec refusal, requires all four public tool contracts in the agent, and requires validate-then-admit with identical evidence in the workflow. The sibling resume case continues to prove exactly one question and concrete options, tradeoffs, risks, recommendation, and confidence. Direct public calls and artifact assertions make an OpenSpec handoff or fixture-only adapter substitution fail.

### Validation
- Focused `PROOF-004` module: 4 passed.
- Designer plus owning public MCP surface: 15 passed in 7.32 seconds; builder challenger independently reran it with 15 passed in 7.24 seconds.
- Focused lint: all hooks passed; only unrelated repository TODO warnings were reported.
- `builder-challenger`: pass; AC coverage, bypass sensitivity, durable-test rent, and minimum-change scope are supported.
