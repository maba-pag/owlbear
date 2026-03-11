---
id: 738
title: Add guided retry hints to planner stale-task detection
status: backlog
priority: nice-to-have
created: 2026-03-10T21:03:29.8172176+01:00
updated: 2026-03-10T21:03:29.8172176+01:00
tags:
    - scope:copilot
    - agent
    - phase-agent-arch
class: standard
---

## Context
The only unique value from the evaluator research (#681) was guided retry hints (Reflexion pattern). When the planner detects a stale task (in-progress too long or failed previously), it could read the task body for prior failure notes and include a retry_hint in the dispatch prompt. See docs/research/evaluator-agent-final-disposition.md section 3.4.

## Acceptance Criteria
- [ ] wave-planning SKILL.md updated: stale-task detection step reads task body for prior failure notes
- [ ] Planner dispatch JSON includes optional retry_hint field when re-dispatching a failed task
- [ ] retry_hint content extracted from prior agent notes in task body (e.g. reviewer FAIL reason)
- [ ] No new agent or agent file created -- this is a planner enhancement only
