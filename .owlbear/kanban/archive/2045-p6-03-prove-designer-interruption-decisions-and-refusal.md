---
id: 2045
title: 'P6-03: Prove designer interruption, decisions, and refusal'
status: archived
priority: high
created: 2026-07-25T14:29:01.440279+02:00
updated: 2026-07-25T14:54:38.741372+02:00
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
archival_reason: completed
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

[[2026-07-25T14:48:03+02:00]]
## Builder Notes
Added one durable `PROOF-004` scenario module at `serve/mcp-kanban/tests/test_designer_interaction.py`. It copies the real admitted modular change into temporary authority, loads the shipped `/design` prompt, `designer` agent, and `w-design-session`, and exercises public MCP `show_change` and `validate_change`. No production, positive admission, setup/seed, OpenSpec, or evaluator-family work changed.

### AC Evidence
- AC-1: Resume scenario persists one accepted decision and one pending decision, calls public `show_change` twice through a real `AppContext`, observes identical authority/digest, and proves intent and decision bytes unchanged.
- AC-2: The same scenario derives the one-question contract from shipped Step 5, requiring exactly one `askQuestions` then stop with Status quo, Options, Tradeoffs, Risks, Recommendation, and Confidence; the public authority keeps the second choice pending and specialist evidence remains read-only.
- AC-3: Unresolved-decision scenario calls public `show_change`/`validate_change`, observes `DV-010` for the pending decision plus absent-approval `EV-004`, checks the shipped approval/admission gate, and proves no receipt, generation, sequence, or job bytes appear.
- AC-4: Resolved-draft scenario injects one representative challenge error, observes exactly `EV-002` for that target, checks the shipped report/keep-draft/no-admit contract, and proves publication snapshots unchanged. It does not assert evaluator-family completeness.

### Validation
- `uv run pytest serve/mcp-kanban/tests/test_designer_interaction.py -q --tb=short` — 3 passed.
- `uv run pytest serve/mcp-kanban/tests/test_designer_interaction.py serve/mcp-kanban/tests/test_mcp_surface_contract.py -q --tb=short` — 14 passed.
- `uv run lint serve/mcp-kanban/tests/test_designer_interaction.py` — pass.
- Editor diagnostics — none.
- `builder-challenger` — pass; independently reran the focused scenarios and Ruff.

[[2026-07-25T14:54:10+02:00]]
## Verify Notes
Adopted the interrupted verifier-local repair in `serve/mcp-kanban/tests/test_designer_interaction.py` and closed both AC-2 follow-up findings without changing production behavior or the accepted contract.

### AC Evidence
- AC-1: The scenario reloads shipped `/design`, `designer`, and `w-design-session` artifacts through public `show_change`; the two projections and delivery digest match, and `intent.md` plus `decisions.yaml` remain byte-identical.
- AC-2: The fixture follows structured `delivery/nodes.yaml` `authority.research` references and copies the real canonical research artifacts. It resolves `delivery-operating-model-reframe.md`, whose text explicitly grounds DEC-028 through DEC-033 and the selected Specification boundary, then ties that evidence to persisted accepted DEC-028. DEC-028 proves selected option membership, one recommendation, pros, cons, risks, and bounded confidence; DEC-029 remains pending with no selection. The shipped workflow still permits exactly one question and requires Status quo, Options, Tradeoffs, Risks, Recommendation, and Confidence.
- AC-3: The pending DEC-029 route uses public `show_change` and `validate_change`, observes targeted `DV-010` plus missing-approval `EV-004`, and leaves publication state unchanged under the shipped no-admit gate.
- AC-4: The representative challenge route observes exactly one targeted `EV-002` and byte-identical receipt, generation, sequence, and job snapshots.

### Validation
- Focused designer and public MCP boundary suite: 14 passed in 6.87 seconds.
- Focused lint: all hooks passed; only unrelated repository TODO warnings were reported.
- `verifier-challenger`: pass; both prior AC-2 failure keys are closed by a repository-grounded authority chain, and the one-file repair remains within scope and the durable-test rent boundary.

[[2026-07-25T14:54:38+02:00]]
## Collect Notes
Archived this leaf after confirming its two prerequisites are archived, all four AC have direct builder and verifier evidence, the final focused public-boundary suite passes 14 tests, focused lint passes, and the verifier challenger closed both prior AC-2 findings. The durable proof remains confined to one scenario module and the admitted `DN-005-PK-003` envelope.
