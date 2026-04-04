---
id: 37
title: Research agent-scoped hooks for tool access, lifecycle, and pipeline enforcement
status: ideation
priority: important
created: 2026-03-26T18:45:09.795589+01:00
updated: 2026-04-04T07:25:23.5236508+02:00
tags:
    - research
    - phase-1
    - scope:agents
    - hooks
class: standard
---

## Objective
Design and evaluate agent-scoped hooks that regulate agent behavior at three control points: tool access, agent start/stop lifecycle, and pipeline boundary enforcement.

## Acceptance Criteria
- [ ] Research: catalog which tool-use guards are needed per agent role (e.g. builder can't write DRs, reviewer can't write tests except minor fixes, test-writer owns test files, scribe owns DRs)
- [ ] Research: define agent start hooks (context setup, claim validation, pre-conditions) and stop hooks (verification, cleanup, handoff)
- [ ] Research: identify which pipeline boundaries need enforcement (e.g. only test-writer writes to tests/, only scribe writes to docs/decisions/, builder can't modify TestFromAC classes)
- [ ] Design: propose a hook registration mechanism compatible with .agent.md tool restrictions and the existing MCP server architecture
- [ ] Design: document exception paths (e.g. reviewer making minor test fixes — when is it allowed, what guard relaxation is needed?)
- [ ] Produce a research document at docs/research/agent-scoped-hooks.md with findings and follow-up task proposals
