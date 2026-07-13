---
id: 658
title: Deprecate w-project-scoping SKILL.md frontmatter and body
status: archived
priority: medium
created: 2026-04-06T07:23:34.0157731+02:00
updated: 2026-04-06T21:29:23.87231+02:00
started: 2026-04-06T21:29:23.87231+02:00
completed: 2026-04-06T21:29:23.87231+02:00
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

[[2026-04-06]] Mon 19:35
## Builder Notes
- Non-implementation task — no code changes needed.
- All 5 AC items pre-satisfied by parent #643 (commit 98727c1, auditor confidence 1.00).
- Evidence: `share/skills/w-project-scoping/SKILL.md` has DEPRECATED description (L3), deprecation banner (L8), user-invocable: true (L4), body preserved below banner. `tests/test_argument_hint_skills.py` unaffected.
- tests: n/a (non-impl pass-through)
- ruff: n/a
- coverage: n/a
- Passing through to review.

[[2026-04-06]] Mon 20:15
## Review Evidence

### Source Control Changes
Non-impl pass-through — no Python files changed. All deliverables are `.md` configuration edits completed by parent task #643 (commit `98727c1`).

### Test Evidence
AC5 requires `tests/test_argument_hint_skills.py` still passes. Test was read directly — it makes 4 structural assertions on `w-project-scoping/SKILL.md` frontmatter:
- `argument-hint:` key present in frontmatter
- `[project name or idea]` is the value
- value is exactly that phrase (no extra text)
- key is in frontmatter, not body

File at L5 contains `argument-hint: "[project name or idea]"` — all 4 assertions pass. No Python implementation changes means no regression risk.

### Lint
n/a — no Python files modified.

### AC Compliance

| AC | Evidence | Status |
|----|----------|--------|
| `description` = `"Workflow (DEPRECATED): Project scoping — use ideator agent instead"` | `share/skills/w-project-scoping/SKILL.md` L3 — exact string match | ✓ PASS |
| Deprecation banner after frontmatter | L8: `> **Deprecated.** Superseded by the Ideator agent (Phase 4). Retained for reference until ideator ships.` — exact match | ✓ PASS |
| Existing body content preserved below banner | L10–L50+: `# Project Scoping`, Steps 0–5, ProjectDefinition schema — all intact | ✓ PASS |
| `user-invocable: true` | L4 — confirmed | ✓ PASS |
| `test_argument_hint_skills.py` still passes | Frontmatter L5 satisfies all 4 test assertions; no code changes introduce regression | ✓ PASS |

### Deductions
None.

### Verdict
Confidence: .97 → **PASS**
All 5 AC items satisfied by direct file evidence. Non-impl pass-through correctly handled by builder.

[[2026-04-06]] Mon 20:35
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Behavior/API change | No | N/A | `copilot-instructions.md` has no direct reference to `w-project-scoping` description; change is entirely within the SKILL.md file itself (already updated by #643, verified by file read) |
| 2 | Module docstrings | No | N/A | No Python files created or modified; non-impl pass-through |
| 3 | External attribution | No | N/A | No external patterns or repositories referenced |
| 4 | CLI changes | No | N/A | No CLI commands added or modified |
| 5 | Research doc | Yes | Verified | `.owlbear/research/deprecate-w-project-scoping.md` exists; linked from task body under ## Context |

### Files Updated
- None — `share/skills/w-project-scoping/SKILL.md` was already updated by parent task #643 (commit `98727c1`). File verified at read: L3 DEPRECATED description ✓, L4 `user-invocable: true` ✓, L8 deprecation banner ✓, body content intact ✓.

### Scratch Files Cleaned
- None — no `.owlbear/scratch/658-*` files found.

[[2026-04-06]] Mon 21:29
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| description = "Workflow (DEPRECATED): ..." | SKILL.md L3 exact match | PASS |
| Deprecation banner after frontmatter | SKILL.md L8 exact match | PASS |
| Body content preserved below banner | SKILL.md L10-L60 intact (Steps 0-5, schema) | PASS |
| user-invocable remains true | SKILL.md L4 confirmed | PASS |
| test_argument_hint_skills.py passes | 4/4 ProjectDefinitionArgumentHint tests pass | PASS |

### Test Results
- pytest: 4/4 in-scope tests pass. Pre-existing failures: test_planner_gates.py (import error, #207), 16 RED tests in test_argument_hint_skills.py (other skills, not w-project-scoping). None in task scope.
- ruff: 5 pre-existing issues in serve/mcp-kanban/ only. None in task scope.

### Architect Quality: 4/5
Well-specified AC with exact string values, file references, and named test file. Task was redundant (subsumed by parent #643) but AC quality itself is solid.

### Deduction Breakdown
- AC lines without evidence: 0 (all 5 verified)
- Lint violations in scope: 0
- AC quality <= 3: no (4/5)
- Missing reviewer evidence: no (detailed section present)
- Full-suite failures in scope: 0
Total deductions: 0

### Confidence: 1.00
### Action: archive

## Commits
| Commit | Type | Files | Tasks |
|--------|------|-------|-------|
| 98727c1 | chore | share/skills/w-project-scoping/SKILL.md | #643 (parent, deliverable) |
| 0443366 | chore | kanban task + activity | #658 |
