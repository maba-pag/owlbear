---
id: 1000
title: 'Expand h-agent-structure: instruction taxonomy + boundary fitness'
status: backlog
priority: needed
created: 2026-04-18T21:34:33.183531+00:00
updated: 2026-04-18T21:34:33.183531+00:00
tags:
- agent
- agent-ecosystem
parent: 984
depends_on: []
blocked: false
block_reason:
claimed_by:
claimed_at:
---
## Objective

Expand `share/skills/h-agent-structure/SKILL.md` with two additions: (1) instruction file taxonomy distinguishing stubs from authority files, and (2) boundary-fitness heuristics for content placement in the loading model.

## Context

The current `h-agent-structure` defines the loading model (4 tiers) and instruction stub format, but does not distinguish stub instruction files (3-line pointers) from authority instruction files (full protocol definitions like `agent-common.instructions.md`). The audit prompt (Task 2, sibling) needs this taxonomy to probe structural fitness. Additionally, no explicit heuristics exist for boundary fitness — determining whether content lives at the correct loading-model tier.

## Acceptance Criteria

- [ ] New `## Instruction File Types` section (after current `## Instruction Stub Format`) defining two types:
  - **Stub**: 3-line pointer file with `applyTo` glob; catches agents working in a domain without the skill loaded. Current stubs listed (reference or absorb existing table from `## Instruction Stub Format`).
  - **Authority**: Full protocol/convention content loaded deterministically from `<critical_rules>` (e.g., `agent-common.instructions.md`). Criteria for when content belongs here vs. in a skill.
- [ ] New `### Boundary Fitness` subsection under `## Loading Model` with 3-5 heuristics for placing content in the correct tier. Each heuristic is a single conditional rule (if X then tier Y). Must include: "If 80%+ agents need it, copilot-instructions.md" and "If loaded from critical_rules, skill-tier minimum."
- [ ] No new rationale prose — rules and tables only.
- [ ] Existing content and sections preserved; no regressions in current h-agent-structure coverage.

## Files

- `share/skills/h-agent-structure/SKILL.md`
