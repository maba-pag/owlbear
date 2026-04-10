---
id: 732
title: 'Research: LLM cost tracking per operation'
status: archived
priority: nice-to-have
created: 2026-03-10T19:53:20.222927+01:00
updated: 2026-03-17T22:44:13.5478431+01:00
started: 2026-03-17T22:44:07.9208706+01:00
completed: 2026-03-17T22:44:07.9208706+01:00
tags:
    - research
    - scope:core
    - phase-research
class: standard
---

**Source:** #597 edgequake-research S3.3
EdgeQuake tracks per-operation LLM costs. OwlBear already has cost tracking for the main agent path (UsageTracker, calc_estimated_cost, get_premium_requests, budget limits). The gap is **secondary LLM call sites** (condenser, retrospective hook, source evaluator, entity/graph extractors, planning extractor) that create standalone Agent() instances and bypass the tracker.

**AC:**
1. Catalog all OwlBear LLM call sites (OwlBearAgent.turn, SummarizingCondenser, RetrospectiveHook, SourceEvaluator, EntityExtractor, IntraDocGraphBuilder, InterDocGraphBuilder, ProjectDefinitionExtractor, SessionMemoryHook summarizer). For each, note whether it is tracked by UsageTracker or not.
2. Evaluate the existing UsageTracker / calc_estimated_cost / get_premium_requests infrastructure in src/owlbear/memory/usage*.py and src/owlbear/providers/copilot_multipliers.py. Identify any gaps in the token-counting or cost-estimation logic itself.
3. Propose a pattern for extending usage tracking to secondary call sites (those using standalone Agent instances). Consider: (a) passing UsageTracker through to internal agents, (b) PydanticAI usage parameter on Agent.run, (c) a middleware/hook approach.
4. Document findings in docs/research/llm-cost-tracking.md following research-docs guardrails.
5. Create follow-up implementation tasks if warranted (expect 0-2 tasks for secondary call-site tracking, not infrastructure -- that already exists).

[[2026-03-17]] Tue 10:05
## Architecture Review
**Verdict:** APPROVED

### AC Assessment
| AC Line | Assessment | Action |
|---------|------------|--------|
| 1. Catalog all LLM call sites | Rewritten: original said 'Survey LLM call sites' (vague). Now lists 9 specific call sites and requires tracked/untracked annotation per site. | Refined |
| 2. Evaluate existing infrastructure | Rewritten: original said 'Evaluate token-counting patterns' as if none exist. Now points to existing UsageTracker/calc_estimated_cost/get_premium_requests and asks for gap analysis. | Refined |
| 3. Propose pattern for secondary sites | Rewritten: original said 'Propose minimal cost tracker for httpx transport' -- wrong layer (tracking is Agent-level not transport-level) and ignores existing infrastructure. Now correctly scopes to extending tracking to standalone Agent instances. | Refined |
| 4. Document in docs/research/llm-cost-tracking.md | Clear and verifiable as-is. | Kept |
| 5. Create follow-up tasks | Refined: added expectation of 0-2 tasks (infrastructure already exists). | Refined |

### Architecture Notes
The edgequake research (S3.3) claimed 'OwlBear has no cost visibility' but this is factually stale. The main agent path already has:
- UsageTracker (JSONL persistence, windowed queries, aggregation) in src/owlbear/memory/usage.py
- calc_estimated_cost via genai_prices in src/owlbear/memory/usage_cost.py
- get_premium_requests for Copilot multipliers in src/owlbear/providers/copilot_multipliers.py
- OwlBearAgent._record_usage() called after every turn() in src/owlbear/core/agent.py
- Budget limits with BUDGET_WARNING hook + BudgetExceededError

The real gap: 8 secondary LLM call sites create standalone Agent() instances and bypass UsageTracker entirely:
- SummarizingCondenser, RetrospectiveHook, SourceEvaluator, EntityExtractor, IntraDocGraphBuilder, InterDocGraphBuilder, ProjectDefinitionExtractor, SessionMemoryHook summarizer

All 5 original AC lines were corrected to reflect existing infrastructure and target the actual gap.

Pure research task -- single domain (research). No module changes, no TDD needed. No dependencies.

### Changes Made
- Rewrote task body with corrected premise and 5 refined AC lines
- Moved to todo

### Dependencies
- None -- standalone research task

[[2026-03-17]] Tue 17:26
## Test-Writer Notes
- Non-implementation task (tagged research) -- no tests applicable.
- Passing through to builder.

[[2026-03-17]] Tue 17:42
## Builder Notes
- Research deliverable: docs/research/llm-cost-tracking.md
- Cataloged 12 LLM call sites: 3 tracked, 9 untracked, 1 placeholder
- Evaluated existing infrastructure -- solid, gap is wiring only
- Proposed Option A: pass UsageTracker through constructors + shared helper
- Follow-up tasks: #844 (wire tracker to 8 secondary sites), #845 (daemon dispatch)
- Commit: 83db5a7

[[2026-03-17]] Tue 17:54
## Review Evidence

### Task Type
Research deliverable  no Python code changes, no tests to run, no lint or coverage applicable.

### Commit Scope
- Commit 83db5a7: single file `docs/research/llm-cost-tracking.md` (156 insertions). Clean scope.

### Pass 1  CRITICAL
#### Security Review
- No security issues. Research document only  no code changes.

#### Test Quality
- N/A  research task, no implementation code.

#### Data Safety
- N/A  no code changes.

### Research-Docs Guardrails Compliance
- [x] Task ref in document header (#732)
- [x] Follow-up Tasks section with concrete items (2 tasks)
- [x] Tasks actually created (#844, #845) at ideation status
- [x] Each task has concrete AC, priority, dependencies
- [x] Each task links back to research doc

### AC Compliance

| AC Line | Evidence | Status |
|---------|----------|--------|
| 1. Catalog all LLM call sites with tracked/untracked | 13 sites cataloged (§1): 3 tracked, 9 untracked, 1 placeholder. All 9 AC-specified sites present. Line refs verified: agent.py L166, condenser.py L184, retrospective_hook.py L96, extractor.py L65/L89, delegation.py L137, daemon.py L730/L796. | PASS |
| 2. Evaluate existing infrastructure, identify gaps | §2 covers 6 components with assessments. Identifies 4 gaps (no operation field, no tracker sharing, daemon untracked, knowledge pipeline multiplier). | PASS |
| 3. Propose pattern for secondary call sites | §3 recommends Option A (constructor injection) with sketch, alternatives table (3 options), and 5 specific changes required. | PASS |
| 4. Document in docs/research/llm-cost-tracking.md | File exists, follows guardrails, task ref present. | PASS |
| 5. Create follow-up tasks (0-2 expected) | 2 tasks created: #844 (wire tracker, ideation), #845 (daemon dispatch, ideation, depends on #844). Both have concrete AC and back-links. | PASS |

### Verdict: PASS
Confidence: .95  thorough catalog, verified line references, solid infrastructure evaluation, actionable follow-ups.

### Action Taken
kanban edit 732 --status docs --release

[[2026-03-17]] Tue 22:07
## Docs Gate

### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | copilot-instructions.md | No | N/A | Research task with no code/behavior changes; no updates needed |
| 2 | Docstrings complete | No | N/A | No new Python code added; research deliverable only |
| 3 | sources/overview.md | No | N/A | Research analyzes EdgeQuake (task #597 prior research) and OwlBear internal infrastructure; no new external patterns. Follow-up tasks #844/#845 reference external sources (PydanticAI, LangSmith) already in overview.md |
| 4 | README.md | No | N/A | No user-facing changes for research task |
| 5 | Research doc linked | Yes | Pass | docs/research/llm-cost-tracking.md complete, task #732 ref in header, properly formatted per research-docs guardrails |
| 6 | Follow-up tasks created | Yes | Pass | #844 (Wire UsageTracker, todo) and #845 (Track daemon dispatch, ideation, depends on #844) both created with concrete AC and back-links to research doc |

### Files Updated
- None (research deliverable only)

### Scratch Files Cleaned
- None (no 732-* files created in docs/scratch/)

[[2026-03-17]] Tue 22:44
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| 1. Catalog all LLM call sites (tracked/untracked) | docs/research/llm-cost-tracking.md Â§1: 12 sites cataloged (3 tracked, 9 untracked, 1 placeholder). All 9 AC-specified secondary sites present with file refs verified. | PASS |
| 2. Evaluate existing infrastructure, identify gaps | Â§2: 6 components assessed. 4 gaps identified: no operation field, no tracker sharing, daemon builder untracked, knowledge pipeline multiplier. | PASS |
| 3. Propose pattern for secondary call sites | Â§3: Option A (constructor injection) recommended with implementation sketch, 3-option alternatives table, and 5 specific required changes. | PASS |
| 4. Document in docs/research/llm-cost-tracking.md | File exists (156 lines, commit 83db5a7). Task ref #732 in header. Follows research-docs guardrails. | PASS |
| 5. Create follow-up tasks (0-2 expected) | #844 (todo, scope:core) and #845 (ideation, depends_on #844) created. Both have concrete AC and back-links (Source: docs/research/llm-cost-tracking.md S3). | PASS |

### Test Results
- pytest: SKIPPED  WMI service degraded (systemic environment hang, confirmed known issue per pytest-and-linting skill). Task is pure research  zero code changes; no tests could regress.
- ruff: 7 pre-existing errors (BLE001/auth.py, E501/screenshot.py, RUF100x2/conftest.py, N801x2/test_blocked_error_location.py, I001/test_loop_detection.py). None related to #732 deliverable.

### Confidence: .97
All 5 AC items verified against actual document content. Research doc is thorough and well-structured. Follow-up tasks properly created with concrete AC and back-links. Minimal deduction for inability to run full test suite (mitigated by zero code changes).

### Action: archive
