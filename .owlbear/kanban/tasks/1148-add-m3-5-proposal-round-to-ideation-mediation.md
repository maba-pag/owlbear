---
id: 1148
title: Add M3.5 proposal round to ideation mediation
status: research
priority: important
created: 2026-04-27T21:43:30.790296+00:00
updated: 2026-04-27T21:59:51.961783+00:00
tags:
- ideation
- pipeline
- agent
parent:
depends_on: []
blocked: true
block_reason: 'Pending DR: .owlbear/decisions/pending/1148-ac-scope-amendment.md —
  AC scope needs amendment to include agent file updates'
claimed_by:
claimed_at:
archival_reason:
archival_refs: []
---

## Objective

Add a gated "Design It Twice" proposal step to ideation Phase 2. When M3 landscape reveals genuine design ambiguity, domain panelists produce competing complete designs in parallel, enabling comparison-driven decisions before M4.

Inspired by Ousterhout's "Design It Twice", adapted to the existing multi-agent panel architecture.

Split from #1147.

## Acceptance Criteria

- [ ] `w-ideation-mediation` SKILL.md: new Step 1.5 (between current Steps 1 and 2) defining M3.5 gated proposal round
- [ ] M3.5 gate: Mediator evaluates M3 landscape for >=2 viable approaches with no dominant option; if single clear approach, skip M3.5 and proceed to Step 2 unchanged
- [ ] When triggered: Mediator dispatches 4 domain panelists in parallel, each via PROPOSE-mode prompt (directive passed through runSubagent prompt field, not a separate agent config)
- [ ] `h-ideation-panel` SKILL.md: new "Propose Mode" section under Late Domain Panel that defines panelist behavior: receive M3 landscape synthesis + directive to produce a complete design shaped by domain emphasis (not a domain-only slice)
- [ ] Propose-mode output: `stances/{name}-proposal.md` with required sections: Design Summary, Key Structural Choices, Trade-offs, Domain Rationale, Confidence
- [ ] `h-ideation` SKILL.md: blackboard artifacts section updated with `stances/*-proposal.md` paths
- [ ] After proposals collected: Mediator builds diff-oriented comparison matrix showing only divergences between proposals (omit ~80% common ground); format: table with columns Decision Point, architect, data, enduser, security, Tension Level
- [ ] `h-ideation-panel` Pragmatist Modes section: new `mode=compare` that reads `stances/*-proposal.md`, writes structured comparison to `synthesis.md` identifying common ground and open questions
- [ ] Modified Step 3 (M4): Pragmatist comparison feeds user decision turn; user may pick a direction or hybrid elements from multiple proposals
- [ ] Post-hybridization: two sequential `ideation-critic` passes: (1) synthesis critic verifying internal consistency of hybridized elements, (2) result critic challenging the final design on its own merits
- [ ] Both critic passes subject to O15 classification per existing Critic Validation rules in `w-ideation-mediation`
- [ ] Verification checklist in `w-ideation-mediation` updated with M3.5 items

## Architecture Notes

- Panelist agents already support parallel dispatch (h-ideation-panel "Parallel Batch" pattern): no new invocation mechanism needed
- PROPOSE mode is a behavioral directive via prompt text, not a config change: panelists load h-ideation-panel which defines both stance and propose modes
- `allow-stances-only.py` PreToolUse hook uses stances/ prefix: verify `stances/*-proposal.md` is covered by existing glob
- No new `.agent.md` files required: existing panelists serve both modes
- No Python code changes: all changes are skill/handbook markdown

## Out of Scope

- Changes to M1-M2 discovery phase
- Changes to early challengers (firstprinciples/outsider/simplifier)
- Making the proposal step mandatory (always gated on ambiguity)
- Panelist `.agent.md` changes (mode is prompt-driven)

[[2026-04-27]]
## Research
- Research doc: .owlbear/research/1148-m3-5-proposal-round.md
- Sources: 8 studied, 6 high-relevance (≥.85)
- Recommendation: Implementable with scope amendment — add 5 agent file updates to AC (confidence: .72)
- Follow-up tasks created: none (DR gates the amendment)
- Decision requests: 1 created (.owlbear/decisions/pending/1148-ac-scope-amendment.md)

## Challenge Results
- Challenger: block (confidence in original: .34)
- Key challenges: (C1) panelist output restrictions don't include proposal files, (C2) mandatory Critic loops conflict with propose mode, (C3) pragmatist only defines converge/denoise
- Researcher response: accepted C1-C3 — scope amendment required. Revised from T1 to T2. Created blocking DR for AC amendment.

## Key Findings
1. Prior art validated: Ousterhout "Design It Twice" + mattpocock design-an-interface skill confirm approach
2. Hook compatible: allow-stances-only.py regex covers stances/*-proposal.md
3. Parallel dispatch: existing Parallel Batch pattern supports propose-mode dispatch
4. Agent file conflicts: 3 contract conflicts require minor updates to 4 panelist + 1 pragmatist agent files
5. Step 2 flow: M3.5 replaces Step 2 when triggered (mutually exclusive paths to synthesis.md)
6. Critic loops: recommend skip in propose mode; dual post-hybridization Critic covers adversarial quality