---
id: 644
title: 'P4-04: Create critic-voice.agent.md'
status: backlog
priority: critical
created: 2026-04-06T07:00:33.6982746+02:00
updated: 2026-04-06T15:01:44.6171495+02:00
tags:
    - phase-4
    - ' scope:ideator'
    - ' type:build'
depends_on:
    - 641
class: standard
---

## Acceptance Criteria

- [ ] `share/agents/critic-voice.agent.md` exists with valid YAML frontmatter
- [ ] `user-invocable: false` set
- [ ] `model: GPT-5.4 (copilot)` configured for genuine model diversity
- [ ] System prompt is purely adversarial: challenges positions, never proposes alternatives
- [ ] Prompt includes Critic exit behavior: "If position is solid after honest examination, say so and exit. Do not manufacture objections."
- [ ] Agent receives voice's current position via prompt, reads `context.md` from Working Directory
- [ ] Returns adversarial challenges to the invoking voice (no direct file writes)
- [ ] Works when invoked by domain voices AND by the Mediator (standalone checks)

## Context

Spec: `.owlbear/research/thinking-companion-framework.md` - Sections 7, 12.
The Critic is the most-invoked subagent: 4 standalone calls per engagement (after M1, M2, M4, M5) plus up to 5 cycles per domain voice. Must work at two scopes: domain-level (invoked by voice) and meta-level (invoked by Mediator).

## Design

- Single agent file handles both standalone and voice-embedded invocations
- Scope determined by input context, not agent configuration
- Different model (GPT) from all other voices (Opus) is the key architectural requirement

[[2026-04-06]] Mon 15:01
## Research
- Research doc: .owlbear/research/critic-voice-agent.md
- Sources: 6 studied, 4 high-relevance
- Recommendation: Single file, dual-scope (Option A) — follows Challenger pattern with GPT-5.4 model, Working Dir context, exit behavior clause (confidence: 0.88)
- Follow-up tasks created: none (task #644 is itself the build task)
- Decision requests: none

### Key Findings
- **Dual-scope works from one file**: standalone (Mediator) vs embedded (voice) scopes differ only in input context, not agent config. Confirmed by spec §7.
- **No overlap with Challenger**: different pipeline stage, model, invokers, inputs. Distinct agents in distinct systems.
- **Model**: GPT-5.4 (copilot) as sole model (not fallback array) — model diversity is the architectural mechanism. 4 existing agents already use GPT-5.4.
- **Tools**: Read-only mirror of Challenger — `[read/readFile, read/viewImage, read/problems, search, vscode/memory]`.
- **Exit behavior**: prompt-embedded "If position is solid… say so and exit." Prevents manufactured objections.
- **Tier: T1** — agent file creation following established pattern, no new capability beyond what the spec already designed.
