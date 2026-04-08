---
id: 682
title: 'Research: how to wire analysis detectors into the agent pipeline'
status: research
priority: nice-to-have
created: 2026-04-08T19:03:48.470505+02:00
updated: 2026-04-08T19:03:48.470505+02:00
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
