---
id: 682
title: 'Research: how to wire analysis detectors into the agent pipeline'
status: archived
priority: medium
created: 2026-04-08T19:03:48.470505+02:00
updated: 2026-04-09T01:21:43.813235+02:00
started: 2026-04-09T01:21:43.813235+02:00
completed: 2026-04-09T01:21:43.813235+02:00
tags:
    - scope:orchestrator
    - ' type:research'
    - ' source:analysis'
class: standard
---

## Context

The `serve/orchestrator/src/owlbear_orchestrator/analysis/` package contains 4 pattern detectors that analyze audit logs:
- `high_error_rate_detector` — identifies agents with unusually high failure rates
- `slow_agent_detector` — identifies agents taking too long
- `repeated_failure_detector` — identifies tasks failing repeatedly
- `stale_dispatch_detector` — identifies dispatches that never complete

These detectors produce `AnalysisProposal` objects. A CLI (`analysis/_cli.py`) exists for manual runs. But **nothing consumes proposals automatically**. The orchestrator doesn't read them. The curator doesn't know about them. They're analysis infrastructure without a consumer.

v1 had `core/improvement_proposals.py` which auto-generated self-improvement suggestions from event metrics — a similar concept that was more tightly integrated.

## Research Questions

1. **Who should consume analysis proposals?**
   - Option A: **Curator agent** — adds "system health" to its curation cycle; proposes pipeline adjustments as memory entries
   - Option B: **New "analyst" agent** — dedicated agent that runs analysis after each orchestrator cycle and surfaces findings
   - Option C: **Orchestrator itself** — reads proposals between cycles and adjusts behavior (e.g., skip agents with high error rates)
   - Option D: **Prompt injection** — analysis CLI runs pre-cycle, results injected as session context for orchestrator

2. **What actions should proposals trigger?**
   - Memory entries (record_learning with proposals)?
   - Kanban tasks (create follow-up tasks for systemic issues)?
   - Decision requests (escalate to user for pattern-breaking changes)?
   - Direct orchestrator behavior changes (circuit breaker, agent exclusion)?

3. **What's the minimal wiring?** Current detectors are ~140 LOC. What's the smallest integration that produces value?

## Acceptance Criteria

- [ ] AC1: Research doc evaluating consumer options with trade-off matrix
- [ ] AC2: Recommendation on which agent/mechanism should consume proposals
- [ ] AC3: Assessment of what actions are appropriate per proposal type
- [ ] AC4: Follow-up implementation task(s) created

[[2026-04-08]] Wed 21:16
## Research
- Research doc: .owlbear/research/analysis-detector-wiring.md
- Sources: 8 studied, 5 high-relevance (.85+)
- Recommendation: Manual-first validation, then deterministic router if demand proven (confidence: .82, revised from .78)
- Follow-up tasks created: #692 (doc analysis CLI in w-orchestration), #693 (validate proposal utility over 2-3 cycles)
- Decision requests: none (T1 — doc changes and operational validation only)

## Challenge Results
- Challenger: reconsider (confidence 0.82)
- Confidence in original: .78 → revised: .82
- Key challenges: (1) curator scope creep — memory hygiene ≠ pipeline health; (2) YAGNI means don't automate until CLI usage proves value; (3) LLM non-determinism routing deterministic proposals is a design smell; (4) v1 never consumed proposals automatically and it was fine
- Researcher response: accepted — revised recommendation from hybrid curator integration to manual-first phased approach. Challenger's YAGNI argument was strongest: prove demand before building automation.

[[2026-04-08]] Wed 21:47
## Architecture Review
### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Single research question — analysis detector wiring options |
| Interface clarity | PASS | AC clearly defines 4 research deliverables |
| Dependency correctness | PASS | No dependencies listed; none needed |
| Module layering | N/A | Research task — no code changes |
| TDD compliance | N/A | Research task — no testable code |
| KISS/YAGNI | PASS | Recommendation itself embraces YAGNI — manual-first, defer automation |
| Premise challenge | PASS | Analysis detectors exist without consumers; research question is valid |
| Pattern consistency | PASS | Follows standard research task pattern with doc + follow-up tasks |
| Security surface | N/A | No code changes or system boundaries |
| Single domain | PASS | Orchestrator domain only |

### AC Verification
| AC | Status | Evidence |
|----|--------|----------|
| AC1: Trade-off matrix | MET | .owlbear/research/analysis-detector-wiring.md section 3.1 — 4 options × 8 criteria |
| AC2: Consumer recommendation | MET | Section 4 — manual-first phased approach (revised from hybrid after challenge) |
| AC3: Actions per proposal type | MET | Section 3.3 — 4 proposal types with specific actions and rationale |
| AC4: Follow-up tasks | MET | #692 (doc CLI in w-orchestration, status: archived) and #693 (validate utility, status: archived) — both verified to exist with concrete AC |

### Challenge Results
- Challenger: Already run by researcher — reconsider (0.82)
- Researcher revised recommendation from hybrid curator to manual-first. YAGNI argument accepted.
- Architect assessment: Revised recommendation is sound. Deferring automation until CLI usage proves value is the right call. Follow-up #692 is T1 doc-only, #693 is operational validation — both appropriately scoped.

### Verdict: APPROVE
### Action Taken: Advanced to todo. Research complete, all AC met, follow-up tasks exist with pass-through tags.

[[2026-04-08]] Wed 22:38
## Test-Writer Notes
- Non-implementation task (tagged type:research) — no tests applicable.
- Passing through to builder.

[[2026-04-08]] Wed 23:01
## Builder Notes
- Non-implementation task — no code changes needed.
- Passing through to review.

[[2026-04-08]] Wed 23:23
## Review Evidence

### Test Results
N/A — `type:research` task. No code changed. Test-writer and builder both correctly passed through.

### Lint
N/A — no source files changed.

### Coverage
N/A

### Pass 1 — CRITICAL
#### Test-Writer AC Coverage
N/A — no `TestFromAC_*` classes (research task, no tests applicable).

#### Security Review
No issues — no code changes, no new system boundaries, no new dependencies.

#### Test Integrity
N/A — no `TestFromAC_*` classes.

#### Test Quality
N/A

#### Data Safety
No issues.

#### Implementation-Aware Gaps
N/A

#### Builder Process Quality
| Metric | Value |
|--------|-------|
| Builder Notes sections | 1 (single pass-through) |
| Approach variation | N/A |
| Assessment | CLEAN |

### Pass 2 — INFORMATIONAL
- §3.2 heading ("Hybrid Recommendation") predates the challenger-revised recommendation in §4 (manual-first). Section is correctly retained as analysis context; §4 explicitly documents the revision with rationale. Minor continuity nit — not a defect.
- #693 architecture review flags that #692 may be questionable given invalid premise (no production audit JSONL path). This concern is downstream of #682 and properly scoped to #693/#692, not this task.

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| AC1: Research doc with trade-off matrix | `.owlbear/research/analysis-detector-wiring.md` §3.1 — 4 consumer options (A–D) × 8 criteria verified by direct read | N/A | PASS |
| AC2: Recommendation on consumer mechanism | §4 — manual-first phased approach (3 phases), confidence .82, challenger-revised from .78 hybrid | N/A | PASS |
| AC3: Actions per proposal type | §3.3 — 4 proposal patterns (high_error_rate, slow_agent, repeated_failure, stale_dispatch) with specific actions and rationale | N/A | PASS |
| AC4: Follow-up tasks created | #692 (doc CLI in w-orchestration, `in-progress`, concrete AC) and #693 (validate utility, `in-progress`, concrete AC) — both verified via show_task | N/A | PASS |

### Confidence: .96
### Verdict: PASS → docs

[[2026-04-08]] Wed 23:56
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Behavior/API change | No | N/A | Pure research task — no code created or modified |
| 2 | Module docstrings | No | N/A | No .py files touched |
| 3 | External attribution | No | N/A | All 8 sources are internal codebase refs; sources/overview.md §682 (line 33) already contains 2 prior-art entries (v1 improvement_proposals.py, #31 research) — complete |
| 4 | CLI changes | No | N/A | No code changes |
| 5 | Research doc | Yes | Verified | `.owlbear/research/analysis-detector-wiring.md` exists, linked from task body, content complete (§1–5); follow-up tasks #692 and #693 verified by reviewer to exist with concrete AC |

### Scratch Files
None found (`.owlbear/scratch/682-*` — no matches).

### Files Updated
None — no docs impact beyond research doc and sources entries already in place.

### Notes
Pre-existing ID reuse: a separate `## Orchestrator Rewrite: Pure Sequencer Research (Task #682)` entry exists at line 2679 of sources/overview.md using an older schema. This predates the current task and is not caused by #682 — out of scope for this gate.

[[2026-04-09]] Thu 01:21
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| AC1: Research doc with trade-off matrix | `.owlbear/research/analysis-detector-wiring.md` S3.1 -- 4 options x 8 criteria matrix verified | PASS |
| AC2: Recommendation on consumer mechanism | S4 -- manual-first phased approach, confidence .82, challenger-revised from .78 | PASS |
| AC3: Actions per proposal type | S3.3 -- 4 proposal types (high_error_rate, slow_agent, repeated_failure, stale_dispatch) with actions and rationale | PASS |
| AC4: Follow-up tasks created | #692 (doc CLI, status: archived, concrete AC) and #693 (validate utility, status: archived, concrete AC) -- both verified with source:research-682 tag | PASS |

### Research Task Verification (Step 1a)
1. Research doc exists at `.owlbear/research/analysis-detector-wiring.md` -- verified
2. Follow-up tasks #692 and #693 created at research or higher -- verified
3. Follow-up tasks reference the research doc -- verified (both bodies link to research doc)

### Test Results
- pytest: 3663 passed, 383 failed, 18 skipped (all pre-existing; zero code changes in this task)
- ruff: 5 issues (all pre-existing in mcp-kanban server.py and test_server.py; no files touched by #682)

### Reviewer Evidence
Present and detailed. Pass 1 (Critical) and Pass 2 (Informational) sections. All 4 AC lines mapped with evidence. Confidence .96, verdict PASS. Trusted.

### Architect Quality: 4/5
AC lines were specific and verifiable (4 concrete research deliverables). Minor gap: AC wording doesn't specify doc location convention, but researcher followed standard pattern. No builder improvisation needed beyond pass-through.

### Deduction Breakdown
- Start: 1.00
- AC lines without evidence: 0 (all 4 verified) -- 0.00
- Lint violations in task scope: 0 (no files touched) -- 0.00
- AC quality score 4/5 (above threshold of 3) -- 0.00
- Missing reviewer evidence: not missing -- 0.00
- Full-suite failures in task scope: 0 (zero code changes) -- 0.00

### Uncommitted Deliverables
Research doc was untracked. Committed as `cade1b0` (docs: add analysis detector wiring research).

### Confidence: .98
Capped at .98 rather than 1.00: research doc was uncommitted upstream (quality gap in researcher delivery, not in content).

### Action: archive

## Commits
| Commit | Type | Files | Tasks |
|--------|------|-------|-------|
| cade1b0 | docs | .owlbear/research/analysis-detector-wiring.md | #682 |
