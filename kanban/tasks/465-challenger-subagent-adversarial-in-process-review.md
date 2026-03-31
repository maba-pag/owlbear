---
id: 465
title: Challenger subagent — adversarial in-process review for architect decisions
status: backlog
priority: important
created: 2026-03-31T04:06:56.7712879+02:00
updated: 2026-03-31T05:06:10.5597957+02:00
tags:
    - research
    - ' scope:agents'
    - ' phase-2'
class: standard
---

## Context

Pipeline agents (especially architect) make high-stakes decisions in isolation. Bad AC from the architect cascades to builder, reviewer, auditor — the most expensive failure mode in the pipeline. The reviewer catches code quality issues post-hoc, but cannot challenge the reasoning behind architectural decisions.

Proposal: a **Challenger** subagent — an adversarial discussion partner that runs as an L2 subagent during an agent's work. Unlike the closed #681 evaluator (post-hoc result assessment at orchestrator level), the Challenger operates **in-process**, challenging reasoning **before** the decision is committed. Think Socratic devil's advocate, not quality gate.

**Interaction model:** One-shot challenge report (VS Code subagents return once). The consuming agent sends its reasoning and proposed decision; the Challenger returns a structured adversarial analysis (holes, biases, missing alternatives, risk blind spots). The consuming agent digests the challenge and may revise. Multi-turn debate is a future opt-in after the pattern proves itself.

**Trigger model:** Mandatory at critical gates. For the architect, this means every APPROVE verdict must pass through the Challenger first. Optional invocation may be added for lower-stakes decisions.

**Initial consumer:** Architect agent (highest stakes — design decisions are hardest to reverse). Future expansion to researcher, test-writer, writer after the pattern is proven.

Infrastructure: uses subagent nesting confirmed in #228 (L2 depth, `allowInvocationsFromSubagents` already enabled). Independent of Quality-Runner (#263) and parallel fan-out (#265).

## Acceptance Criteria

- [ ] Define the Challenger agent persona and adversarial reasoning style (what makes it different from general review — structured devil's advocate, not validation)
- [ ] Design the I/O contract: input schema (agent reasoning, proposed decision, context) and output schema (challenges, blind spots, alternative angles, risk assessment, confidence in the original decision)
- [ ] Determine tool requirements and mode (assign vs inherit). The Challenger needs to read code/files to verify claims but should not edit anything
- [ ] Identify mandatory trigger points in the arch-review workflow (where exactly the challenge must happen before APPROVE)
- [ ] Evaluate model selection: adversarial reasoning may benefit from a strong model vs. cost savings of a lighter one
- [ ] Design the protocol for how the architect integrates the challenge results (revise AC, strengthen reasoning, or acknowledge and proceed with justification)
- [ ] Assess expansion path: identify critical gates in researcher, test-writer, and writer workflows where mandatory challenge would add value
- [ ] Create follow-up implementation tasks at ideation (challenger.agent.md, arch-review skill integration, expansion tasks)
- [ ] Write design doc to docs/research/challenger-subagent-design.md
