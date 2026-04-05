---
id: 37
title: Research agent-scoped hooks for tool access, lifecycle, and pipeline enforcement
status: in-progress
priority: important
created: 2026-03-26T18:45:09.795589+01:00
updated: 2026-04-05T10:09:58.3121256+02:00
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

[[2026-04-05]] Sun 01:02
## Architecture Review
### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Single research theme: agent-scoped hooks across three control points |
| Interface clarity | PASS | 6 AC lines each with clear, verifiable scope |
| Dependency correctness | PASS | No dependencies, none needed for standalone research |
| Module layering | PASS | Research task produces doc, no code |
| TDD compliance | PASS | Non-implementation; research pass-through tag present |
| KISS/YAGNI | PASS | Focused scope, no speculative expansion |
| Premise challenge | PASS | Research is actionable: #589 already in-progress with 35 tests |
| Pattern consistency | PASS | Research doc follows standard format |
| Security surface | PASS | No new system boundaries; follow-up hooks are security improvements |
| Single domain | PASS | Agent configuration domain exclusively |

### AC Assessment
| AC Line | Assessment | Action |
|---------|-----------|--------|
| AC1: tool-use guard catalog | Complete: section 3.1 maps 14 agents | None |
| AC2: start/stop lifecycle hooks | Complete: section 3.2 evaluates 5 events | None |
| AC3: pipeline boundary map | Complete: section 3.3 covers 6 boundaries | None |
| AC4: hook registration mechanism | Complete: section 3.4 documents 4 scopes, MCP compatibility | None |
| AC5: exception paths | Complete: section 3.5 covers 5 cases | None |
| AC6: research doc + follow-ups | Complete: doc exists, 3 follow-up tasks (#589, #590, #591) | None |

### Architecture Notes
- Research doc at docs/research/agent-scoped-hooks.md: 6 sources, per-agent guard catalog, phased rollout
- Existing patterns verified: deny-writes.ps1 (reviewer), lint-changed.ps1 (builder) both deployed and tested
- Follow-ups well-scoped: #589 (test-writer guard, in-progress), #590 (session context, backlog), #591 (doc-writer guard, ideation with #589 dep)
- T1 tier classification correct: all follow-ups are incremental additions to established hook patterns
- MCP/hooks orthogonality correctly identified

### Dependency Analysis
- No upstream dependencies
- Downstream: #589 (in-progress), #590 (backlog), #591 (ideation, depends on #589)

### Challenge Results
- Challenger: FALLBACK (not available in session)
- Mitigating evidence: #589 passed its own arch review with 35 tests validating findings; .85 confidence with all AC mapped; no T3 decisions

### Verdict: APPROVE
### Action Taken: Advanced to todo. All 6 AC verified with specific evidence. Research doc complete and current. 3 follow-up tasks exist with appropriate scoping.

[[2026-04-05]] Sun 10:09
## Test-Writer Notes
- Non-implementation task (tagged `research`) — no tests applicable.
- All 6 AC lines describe research deliverables and document production; no Python interfaces to test.
- Arch review confirmed: "Non-implementation; research pass-through tag present."
- Passing through to builder.
