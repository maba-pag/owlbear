---
id: 658
title: Deprecate w-project-scoping SKILL.md frontmatter and body
status: in-progress
priority: nice-to-have
created: 2026-04-06T07:23:34.0157731+02:00
updated: 2026-04-06T17:15:26.8401738+02:00
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

[[2026-04-06]] Mon 16:29
## Architecture Review

### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | One concern: deprecate w-project-scoping SKILL.md |
| Interface clarity | PASS | AC has exact strings and file references |
| Dependency correctness | PASS | Depends on #643 (archived, complete) |
| Module layering | N/A | No code; .md skill file only |
| TDD compliance | PASS | Non-impl task; has type:chore tag |
| KISS/YAGNI | PASS | Minimal scope |
| Premise challenge | FAIL (redundant) | All 5 AC items already satisfied by parent #643 (commit 98727c1, auditor confidence 1.00). Task is fully subsumed. |
| Pattern consistency | PASS | Follows h-kanban-md DEPRECATED precedent |
| Security surface | N/A | No system boundaries |
| Single domain | PASS | Skill configuration only |

### Redundancy Finding
This task is fully redundant. All 5 AC items were completed by parent task #643 (archived, commit 98727c1):
- AC1: w-project-scoping/SKILL.md L3 description = "Workflow (DEPRECATED): Project scoping -- use ideator agent instead" (exact match)
- AC2: L8 deprecation banner present (exact match)
- AC3: L4 user-invocable: true (confirmed)
- AC4: Body content preserved below banner (# Project Scoping + Steps 0-5 intact)
- AC5: tests/test_argument_hint_skills.py references file structurally (unaffected by deprecation)

Parent #643 architect note explicitly flagged #658 and #659 as "redundant (subsumed by this refined AC)". Auditor on #643 confirmed at confidence 1.00.

### Challenge Results
- Challenger: FALLBACK -- no challenger agent available
- Override justification: T1 autonomous, trivial redundancy verification, all AC pre-satisfied by archived parent with 1.00 auditor confidence

### Verdict: APPROVE (pre-satisfied, pass-through)
### Action Taken: Advanced to todo. All AC already complete -- downstream agents should pass through rapidly. No code changes needed.

[[2026-04-06]] Mon 17:15
## Test-Writer Notes
- Non-impl pass-through: config/docs only
- AC references only `share/skills/w-project-scoping/SKILL.md` (a `.md` file) — no testable Python interfaces, no Python implementation intent in AC keywords.
- All 5 AC items pre-satisfied by parent #643 (verified by direct file read):
  - AC1: description = "Workflow (DEPRECATED): Project scoping — use ideator agent instead" ✓
  - AC2: Deprecation banner present at L8 ✓
  - AC3: Body content preserved below banner ✓
  - AC4: user-invocable: true ✓
  - AC5: tests/test_argument_hint_skills.py references file structurally (unaffected) ✓
- No test file created — all deliverables are non-Python file edits already done.
