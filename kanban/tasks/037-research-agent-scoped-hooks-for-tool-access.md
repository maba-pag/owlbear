---
id: 37
title: Research agent-scoped hooks for tool access, lifecycle, and pipeline enforcement
status: backlog
priority: important
created: 2026-03-26T18:45:09.795589+01:00
updated: 2026-04-04T23:08:53.4419811+02:00
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

## Research (Validation Pass)
Existing research doc validated: docs/research/agent-scoped-hooks.md (complete, current).

All 6 AC items verified with specific evidence:
- AC1: Tool-use guard catalog in section 3.1 (14 agents mapped)
- AC2: Lifecycle hooks evaluated in section 3.2 (SessionStart recommended, Stop skipped)
- AC3: Pipeline boundary map in section 3.3 (6 boundaries, 2 hook candidates)
- AC4: Hook registration in section 3.4 (per-agent + workspace patterns)
- AC5: Exception paths in section 3.5 (5 cases documented)
- AC6: Research doc exists with 3 follow-up tasks

Follow-up tasks: #589 (in-progress), #590, #591 (ideation)
Confidence: .85 (original doc challenge was FALLBACK)

[[2026-04-04]] Sat 23:08
Research validated (.85). Complete doc at docs/research/agent-scoped-hooks.md. All 6 AC addressed. 3 follow-up tasks exist (#589 in-progress, #590, #591 ideation).
