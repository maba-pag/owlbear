---
id: 1002
title: Add agent-extraction markers to h-agent-structure
status: backlog
priority: needed
created: 2026-04-18T21:34:45.363367+00:00
updated: 2026-04-18T21:34:45.363367+00:00
tags:
- agent
- agent-ecosystem
parent: 984
depends_on:
- 1000
blocked: false
block_reason:
claimed_by:
claimed_at:
---
## Objective

Add a section to `share/skills/h-agent-structure/SKILL.md` defining concrete markers for when to extract a concern into a dedicated agent or subagent, and counter-markers for premature extraction.

## Context

No formal criteria exist for deciding when a concern warrants its own agent vs. remaining part of an existing agent. The quality-runner extraction from builder is a precedent but undocumented. The audit prompt (Task 2, sibling) will use these markers to flag missed extraction opportunities.

## Acceptance Criteria

- [ ] New `## Agent Extraction Markers` section in `share/skills/h-agent-structure/SKILL.md`.
- [ ] 3-5 extraction markers (signals a concern warrants its own agent), each as a single-line conditional. Examples: "Concern requires a distinct `tools:` allowlist"; "Concern has an independent failure domain (its failure should not abort the parent)"; "Same delegation pattern appears in 2+ agents."
- [ ] 2-3 counter-markers (signals extraction is premature), same format. Examples: "Concern is invoked from exactly one call site"; "No distinct tool or model requirements."
- [ ] At least one precedent from the current ecosystem cited inline (quality-runner extraction from builder, with 1-line rationale).
- [ ] No rationale prose beyond the precedent line — markers and counter-markers only.

## Files

- `share/skills/h-agent-structure/SKILL.md`
