---
id: 630
title: Fix TDD gate to exempt non-impl pass-through tags
status: backlog
priority: important
created: 2026-04-05T12:02:40.4394245+02:00
updated: 2026-04-05T14:18:11.1673612+02:00
tags:
    - scope:mcp
    - scope:orchestrator
    - phase-2
    - type:bug
parent: 619
class: standard
---

## Acceptance Criteria

- serve/orchestrator/src/owlbear/planner/gates.py check_tdd() updated to skip tasks with non-impl pass-through tags (research, docs, type:config, type:docs, test, type:test, agent, quality)
- pick_tasks implementation in owlbear-kanban server.py includes the same exemption
- w-dispatch-planning SKILL.md Gate 4 spec (line 65, 114, 158) matches the code behavior
- Tests verify: in-progress task with quality tag but no Test-Writer Notes passes check_tdd()

## Context

Discovered during #619 architect review. gates.py check_tdd() fails any in-progress task without "## Test-Writer Notes" but w-dispatch-planning explicitly exempts tasks with non-impl pass-through tags. This mismatch pre-exists the pick_tasks migration but will be copied into server.py by #621.

[[2026-04-05]] Sun 14:18
## Research
- Research doc: .owlbear/research/fix-tdd-gate-non-impl-exemption.md
- Sources: 8 studied, 8 high-relevance (all internal codebase)
- Recommendation: Add _NON_IMPL_TAGS frozenset + intersection check to both check_tdd() in gates.py and _check_pick_gates() in server.py (~5 LOC each). Approach A -- inline copy pattern. (confidence: .92)
- Follow-up tasks created: none (#630 AC already covers all work)
- Decision requests: none

## Challenge Results
- Challenger: N/A -- T1 bug fix, no design trade-off to challenge
- Tier: T1 (autonomous) -- code-spec alignment fix
- Key finding: test-writer Step 1a mitigates the bug in happy path by always adding Test-Writer Notes to pass-through tasks, but defense-in-depth requires the gate to match the spec
- Key finding: w-dispatch-planning SKILL.md lines 65, 114, 158 already correct -- no doc changes needed
- Key finding: neither test_planner_gates.py nor test_pick_tasks_620.py has any tag-based TDD gate tests
