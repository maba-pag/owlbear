---
id: 37
title: Research agent-scoped hooks for tool access, lifecycle, and pipeline 
  enforcement
status: archived
priority: medium
created: 2026-03-26 18:45:09.795589+01:00
updated: 2026-04-05 14:45:36.006096+02:00
started: 2026-04-05 14:45:36.006096+02:00
completed: 2026-04-05 14:45:36.006096+02:00
tags:
- research
- phase-1
- scope:agents
- hooks
class: standard
archival_reason: completed
archival_refs: []
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

[[2026-04-05]] Sun 11:04
## Builder Notes
- Non-implementation task — no code changes needed.
- Passing through to review.

[[2026-04-05]] Sun 13:10
## Review Evidence

### Source Control
Builder changed files: `.owlbear/kanban/tasks/037-*.md` only (builder notes appended, status → review). No source code or doc files changed by builder or test-writer — correct pass-through for a `research`-tagged task.

### Tests
- No `TestFromAC_*` classes exist for this task — Step 5.0 skip condition met.
- `tests/test_agent_scoped_hooks_research.py` exists but is scoped to task **#86** (`docs/research/agent-scoped-hooks-pipeline-enforcement.md`), not #37.
- Test-writer pass-through: correct. No Python interfaces to test.

### Lint
Not applicable — no Python files changed.

### Coverage
Not applicable.

### Pass 1 — CRITICAL Checks

#### 5.0 Test-Writer Audit
Skipped: no `TestFromAC_*` classes exist. Non-implementation task, correctly identified by test-writer.

#### 5.1 Security
No code changed. Research document contains no hard-coded secrets, injection surfaces, or security regressions. PASS.

#### 5.2 Test Integrity
Skipped: no `TestFromAC_*` classes.

#### 5.3 Test Quality
Skipped: no tests.

#### 5.4 Data Safety
Not applicable.

#### 5.5 Implementation-Aware Test Gap
Not applicable (pure research task).

#### 5.7 Builder Process Quality
| Metric | Value |
|--------|-------|
| Builder Notes sections | 1 |
| Approach variation | N/A |
| Assessment | CLEAN |

### AC Compliance

| AC Line | Evidence | Status |
|---------|----------|--------|
| AC1: catalog tool-use guards per agent role | Section 3.1 `.owlbear/research/agent-scoped-hooks.md` — 14-agent table with current guard, needed guard, priority, mechanism | PASS |
| AC2: define start/stop lifecycle hooks | Section 3.2 — 5 hook events (SessionStart, SubagentStart, SubagentStop, Stop, PreCompact) with value/feasibility/confidence ratings | PASS |
| AC3: identify pipeline boundaries needing enforcement | Section 3.3 — 6 boundaries tabulated with current enforcement, violation frequency, hook candidacy | PASS |
| AC4: propose hook registration mechanism, MCP compatibility | Section 3.4 — 4 scopes (per-agent, workspace, user, custom paths) with MCP orthogonality confirmed: "hooks intercept VS Code-native tools only, not MCP tools" | PASS |
| AC5: document exception paths | Section 3.5 — 5 cases: reviewer test fix, builder test discovery, test-writer conftest, doc-writer repo root, hook self-edit | PASS |
| AC6: research doc at `docs/research/agent-scoped-hooks.md` + follow-up tasks | **Document EXISTS** at `.owlbear/research/agent-scoped-hooks.md` (not `docs/research/`). Follow-up tasks #589 (review), #590 (backlog), #591 (ideation) exist. Path discrepancy is a v2 reorganization artifact — all `docs/` content moved to `.owlbear/` project-wide. Substantive intent fully met. | PASS (informational path note) |

### Pass 2 — Informational

**I1 (Path discrepancy):** AC6 specifies `docs/research/agent-scoped-hooks.md`; file is at `.owlbear/research/agent-scoped-hooks.md`. All upstream agents (researcher, arch review, test-writer, builder) cited the old path but acknowledged the document. This is a project-wide reorganization artifact, not a researcher choice. Deduction: -0.02. No action required.

### Deduction Summary
| Finding | Class | Deduction |
|---------|-------|-----------|
| AC6 path discrepancy (v2 reorg artifact) | Informational | -0.02 |

### Confidence: .95 − 0.02 = **.93 → PASS**

### Verdict: PASS → docs

[[2026-04-05]] Sun 13:24
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Behavior/API change | No | N/A | Pure research task — no hooks deployed, no code changed; copilot-instructions.md accurately reflects current system state |
| 2 | Module docstrings | No | N/A | No Python files created or modified; test-writer and builder both confirmed pass-through |
| 3 | External attribution | Yes | Verified | VS Code Agent Hooks docs (4/1/2026) already attributed in `.owlbear/sources/overview.md` under "Agent-Scoped Hooks Research (Task #37)" |
| 4 | CLI changes | No | N/A | No CLI commands added or modified |
| 5 | Research doc | Yes | Verified | `.owlbear/research/agent-scoped-hooks.md` exists, task body links it, follow-up tasks #589 (review), #590 (backlog), #591 (ideation) all exist |

### Files Updated
None — no documentation updates required.

### Scratch Files
None found matching `.owlbear/scratch/37-*`.

[[2026-04-05]] Sun 14:45
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| AC1: catalog tool-use guards | Section 3.1: 14-agent table | PASS |
| AC2: start/stop lifecycle hooks | Section 3.2: 5 events evaluated | PASS |
| AC3: pipeline boundary enforcement | Section 3.3: 6 boundaries mapped | PASS |
| AC4: hook registration + MCP compat | Section 3.4: 4 scopes, MCP orthogonality | PASS |
| AC5: exception paths | Section 3.5: 5 cases documented | PASS |
| AC6: research doc + follow-ups | .owlbear/research/agent-scoped-hooks.md (55a4d8c); #589, #590, #591 exist | PASS |

### Research Verification (Step 1a)
- Doc exists, committed. 3 follow-ups created, all reference doc.

### Test Results
- pytest: 2878 passed, 432 failed, 18 skipped (0 in #37 scope)
- ruff: N/A

### Architect Quality: 4/5
### Deductions: AC6 path discrepancy -0.02
### Confidence: .98
### Action: archive
