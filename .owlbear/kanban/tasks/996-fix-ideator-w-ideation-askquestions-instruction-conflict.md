---
id: 996
title: Fix ideator/w-ideation askQuestions instruction conflict
status: research
priority: important
created: 2026-04-18T21:26:18.176169+00:00
updated: 2026-04-18T21:57:03.421980+00:00
tags:
- type:improvement
- scope:agents
- scope:skills
parent:
depends_on: []
blocked: false
block_reason:
claimed_by:
claimed_at:
---
## Problem
The ideator agent's critical_rules state "askQuestions for decisions ... never stop to wait for a plain-text reply when a structured question can capture the input" with examples (tier selection, approach choice, panelist veto, Brief approval, moment transitions). The w-ideation skill describes M1 (Understanding) as natural investigative dialogue and only mandates askQuestions for the inter-M1/M2 tier check.

These conflict. When executing M1 probes, the model can plausibly read the skill's narrative as "M1 is dialogue, not a decision point" and end a turn with prose questions. This causes a silent stall.

## Fix
1. Tighten `share/agents/ideator.agent.md` critical_rules: "askQuestions is the only way to end a turn that requires a user reply, including investigative probes. Use `allowFreeformInput: true` when there are no fixed options."
2. Update `share/skills/w-ideation/SKILL.md` Step 1 to explicitly say "every M1 probe ends with askQuestions."
3. Add a worked askQuestions-with-freeform example to one or both files.

## Acceptance Criteria
- ideator.agent.md critical_rules contains the unambiguous "askQuestions is the only way to end a user-facing turn" clause.
- w-ideation Step 1 has the explicit "every probe ends with askQuestions" instruction.
- One worked askQuestions example with `allowFreeformInput: true` exists in either file.
- No remaining conflict between the two documents.

## Context
Surfaced during ideation session for #973. See `.owlbear/briefs/draft-blocked-task-dr-enforcement/context.md`.

## Extension (added from ideation session for #984 — agent-audit prompt rewrite)

### Additional fix
The "use confidence (0.0–1.0) and one `recommended` choice when trade-offs exist" rule lives in `ideator.agent.md` critical_rules but is mentioned only briefly in `w-ideation` Step 4 and not at all in Step 5 walkthroughs or other askQuestions calls. Mediator agents trained to follow the skill (not the agent file) will miss it.

### Additional acceptance criteria
- `w-ideation` Step 4 contains a worked askQuestions example showing 3-4 options with **explicit per-option confidence (0.0–1.0)** and one option marked `recommended: true`.
- `w-ideation` Step 5 (Brief approval and walkthrough) contains a worked example or explicit instruction that any options-bearing askQuestions during walkthrough MUST carry per-option confidence when genuine trade-offs exist (not for procedural "next/back" choices).
- The rule is stated in `w-ideation` itself, not only in the agent file (skills are the authority per `r-pipeline-protocol`).

### Context
During ideation session for #984, Mediator presented a 4-option decision (scope/decomposition smell handling) without confidence scores. User had to explicitly call this out: *"whats your recommendation and your confidence in each option? (when done we need to improve your workflow, i am missing these info)"*. The rule existed in the agent file but not in the skill the Mediator was nominally following.