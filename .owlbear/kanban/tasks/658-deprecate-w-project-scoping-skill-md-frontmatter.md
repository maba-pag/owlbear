---
id: 658
title: Deprecate w-project-scoping SKILL.md frontmatter and body
status: backlog
priority: nice-to-have
created: 2026-04-06T07:23:34.0157731+02:00
updated: 2026-04-06T15:04:28.5238758+02:00
tags:
    - phase-4
    - ' scope:ideator'
    - ' type:chore'
depends_on:
    - 643
class: standard
---

## Acceptance Criteria

- [ ] `description` field reads: `"Workflow (DEPRECATED): Project scoping — use ideator agent instead"`
- [ ] Deprecation banner added after frontmatter: `> **Deprecated.** Superseded by the Ideator agent (Phase 4). Retained for reference until ideator ships.`
- [ ] Existing body content preserved below banner
- [ ] `user-invocable` remains `true` (consumers may still invoke until ideator ships)
- [ ] `tests/test_argument_hint_skills.py` still passes

## Context

Research: `.owlbear/research/deprecate-w-project-scoping.md`
Pattern to follow: `share/skills/h-kanban-md/SKILL.md` (DEPRECATED prefix + banner)
Parent task: #643

[[2026-04-06]] Mon 15:04
## Research
- **Finding:** Task #658 is fully redundant — all 5 AC items were already completed by parent task #643 (archived, commit `98727c1`).
- **Evidence:** Direct file reads confirm: `w-project-scoping/SKILL.md` L3 has DEPRECATED description, L4 has `user-invocable: true`, L8 has deprecation banner, body content preserved. Test `test_argument_hint_skills.py` references file structurally (unaffected).
- Sources: 2 — parent task #643 body (auditor confirmed 1.00 confidence), current file state
- Recommendation: Archive this task as duplicate/subsumed (confidence: .95)
- Follow-up tasks created: none (work already done)
- Decision requests: none (T1 autonomous)
- Research doc: `.owlbear/research/deprecate-w-project-scoping.md` (pre-existing from #643)

## Challenge Results
- Challenger: SKIPPED — trivial redundancy verification, no recommendation to challenge
- Confidence in original: .95
- Tier: T1 — Autonomous (redundant task, all AC pre-satisfied)
