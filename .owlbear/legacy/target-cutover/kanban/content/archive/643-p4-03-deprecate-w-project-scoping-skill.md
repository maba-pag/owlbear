---
id: 643
title: 'P4-03: Deprecate w-project-scoping skill'
status: archived
priority: medium
created: 2026-04-06T07:00:16.8966876+02:00
updated: 2026-04-06T12:17:29.1037377+02:00
started: 2026-04-06T12:17:29.1037377+02:00
completed: 2026-04-06T12:17:29.1037377+02:00
tags:
    - phase-4
    - ' scope:ideator'
    - ' type:chore'
class: standard
---

## Acceptance Criteria

- [ ] `w-project-scoping/SKILL.md` frontmatter marked as deprecated
- [ ] Deprecation note in body pointing to ideator agent
- [ ] No pipeline agents or skills reference `w-project-scoping` as active

## Context

Spec: `.owlbear/research/thinking-companion-framework.md` - Section 13, prerequisite #9.
The Ideator replaces the project-scoping skill's function. The old skill should be marked deprecated, not deleted (consumers may still reference it).

[[2026-04-06]] Mon 07:23
## Research
- Research doc: .owlbear/research/deprecate-w-project-scoping.md
- Sources: 4 studied, 3 high-relevance
- Recommendation: Follow DEPRECATED pattern (h-kanban-md precedent) — add description prefix + body banner (confidence: .90)
- Follow-up tasks created: #658 (deprecate frontmatter+body), #659 (update h-agent-structure example)
- Decision requests: none (T1 autonomous)

## Challenge Results
- Challenger: SKIPPED — trivial deprecation following established patterns
- Confidence in original: .90
- Key findings: two precedents exist (DEPRECATED vs ARCHIVED); no active pipeline dependencies; ideator not yet built so deprecation (not archive) is correct
- Tier: T1 — Autonomous

[[2026-04-06]] Mon 07:46
## Architecture Review

### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | One concern: deprecate w-project-scoping skill |
| Interface clarity | REFINE | Original AC lacks exact strings; refined below |
| Dependency correctness | PASS | No deps needed; standalone deprecation |
| Module layering | N/A | No code; .md skill file edits only |
| TDD compliance | PASS | Non-impl task; needs pass-through tag (see below) |
| KISS/YAGNI | PASS | Minimal scope, follows established DEPRECATED pattern |
| Premise challenge | PASS | Spec mandate: thinking-companion-framework.md Section 13, prerequisite #9 |
| Pattern consistency | PASS | Follows h-kanban-md DEPRECATED precedent (description prefix + body banner) |
| Security surface | N/A | No system boundaries |
| Single domain | PASS | Skill configuration/documentation only |

### Refined AC (supersedes original)
The original AC is directionally correct but imprecise. Builder should follow these tightened criteria:

1. In `share/skills/w-project-scoping/SKILL.md`, change `description` to: `"Workflow (DEPRECATED): Project scoping — use ideator agent instead"`
2. Add deprecation banner after frontmatter: `> **Deprecated.** Superseded by the Ideator agent (Phase 4). Retained for reference until ideator ships.`
3. Keep `user-invocable: true` (consumers may still invoke until ideator ships)
4. Preserve existing body content below the banner
5. In `share/skills/h-agent-structure/SKILL.md` L182, replace or remove `w-project-scoping` from the user-invocable example list (keep `w-retro` and `h-excalidraw-diagram`)
6. `tests/test_argument_hint_skills.py` must still pass (file persists, just deprecated)

Pattern reference: `share/skills/h-kanban-md/SKILL.md` (DEPRECATED prefix + banner)

### Follow-up Task Disposition
Tasks #658 and #659 (at ideation, depends_on [643]) are subsumed by this task's refined AC. They should be archived after #643 completes to avoid duplicate work. The orchestrator should handle cleanup.

### Missing Pass-Through Tag
This task produces no testable Python code. Needs `docs` pass-through tag added before test-writer processes it. (edit_task not available to architect; flagging for downstream.)

### Challenge Results
- Challenger: FALLBACK — no challenger agent available
- Override justification: T1 autonomous chore, established DEPRECATED pattern, trivial scope, research already verified no active pipeline dependencies

### Codebase Evidence
- DEPRECATED pattern verified at share/skills/h-kanban-md/SKILL.md (description prefix + body banner)
- ARCHIVED pattern at share/skills/w-dispatch-planning/SKILL.md (not applicable here; ideator not yet built)
- Active references: only h-agent-structure/SKILL.md L182 (documentary example)
- Test references: test_argument_hint_skills.py L8,L19 (structural test, unaffected by deprecation)
- Research doc at .owlbear/research/deprecate-w-project-scoping.md: thorough, 4 sources, .90 confidence

### Verdict: APPROVE
### Action Taken: Refined AC with exact strings and file references. Advanced to todo. Flagged #658/#659 as redundant and pass-through tag needed.

[[2026-04-06]] Mon 08:18
## Test-Writer Notes
- Non-impl pass-through: AC references only `share/skills/w-project-scoping/SKILL.md` and `share/skills/h-agent-structure/SKILL.md` — both are `.md` SKILL files with no testable Python interfaces.
- AC item 6 (`tests/test_argument_hint_skills.py` must still pass) is a constraint on the builder, not a new test to write. That test checks file existence/structure and will remain passing after deprecation since the file is not deleted.
- Heuristic: no `implement`, `function`, `method`, `class`, `module`, `src/`, `serve/`, `.py` implementation keywords in AC.
- Architect note confirmed: "This task produces no testable Python code."
- Passing through to builder.

[[2026-04-06]] Mon 09:33
## Builder Notes
- Non-implementation task — `.md` file edits only, no Python code changed.
- Files changed (2):
  - `share/skills/w-project-scoping/SKILL.md` — updated `description` to `"Workflow (DEPRECATED): Project scoping — use ideator agent instead"`; added deprecation banner `> **Deprecated.** Superseded by the Ideator agent (Phase 4). Retained for reference until ideator ships.` immediately after frontmatter
  - `share/skills/h-agent-structure/SKILL.md` L182 — removed `w-project-scoping` from user-invocable example list (kept `w-retro` and `h-excalidraw-diagram`)
- AC compliance:
  - [x] `description` prefix changed to `Workflow (DEPRECATED):`
  - [x] Deprecation banner added, pointing to ideator agent
  - [x] `user-invocable: true` preserved
  - [x] Existing body content preserved below banner
  - [x] `h-agent-structure/SKILL.md` L182 updated (w-project-scoping removed)
  - [x] `tests/test_argument_hint_skills.py::TestFromAC_ProjectDefinitionArgumentHint` — 4/4 passed (file still exists, frontmatter intact including `argument-hint`)
- Pre-existing failures: 16 tests in `test_argument_hint_skills.py` for other skills (`w-retro`, `h-excalidraw-diagram`, etc.) — unrelated to this task, unchanged by these edits
- Lint: no Python files modified; ruff N/A
- Commit: `98727c1` — chore(skills): deprecate w-project-scoping skill (#643)
- Architecture follow-up: tasks #658 and #659 are redundant (subsumed by this refined AC) — see architect note for cleanup

[[2026-04-06]] Mon 10:40
## Review Evidence

### Step 1 — Changed Files
Builder reports 2 `.md` files changed (committed `98727c1`):
- `share/skills/w-project-scoping/SKILL.md`
- `share/skills/h-agent-structure/SKILL.md`

No Python files changed. Committed — absent from staged/unstaged diff as expected.

### Steps 2–4 — Tests / Lint / Coverage
N/A — non-implementation pass-through (type:chore, no Python code). Quality-Runner not applicable.

### Step 5.0 — TestFromAC_* Audit
No `TestFromAC_*` classes exist. Pass-through classification correctly applied by test-writer.

### Step 5.1 — Security Review
No code changes, no system boundaries. No OWASP issues.

### Step 5.2 — TestFromAC Comparison
N/A — no TestFromAC_* tests to compare.

### AC Compliance Table (Refined AC — supersedes original)

| AC | Requirement | Evidence (direct file read) | Status |
|----|------------|------------------------------|--------|
| AC1 | description = `"Workflow (DEPRECATED): Project scoping — use ideator agent instead"` | `w-project-scoping/SKILL.md` L3: exact match | PASS |
| AC2 | Banner = `> **Deprecated.** Superseded by the Ideator agent (Phase 4). Retained for reference until ideator ships.` | `w-project-scoping/SKILL.md` L8: exact match | PASS |
| AC3 | `user-invocable: true` preserved | `w-project-scoping/SKILL.md` L4: confirmed | PASS |
| AC4 | Existing body content preserved below banner | `# Project Scoping` section and Steps 0–5 all present | PASS |
| AC5 | h-agent-structure/SKILL.md L182 — `w-project-scoping` removed | Current text: `(e.g., \`w-retro\`, \`h-excalidraw-diagram\`)` — no `w-project-scoping` | PASS |
| AC6 | `test_argument_hint_skills.py::TestFromAC_ProjectDefinitionArgumentHint` passes | `argument-hint: "[project name or idea]"` in frontmatter; banner is outside YAML block — no interference with `_get_frontmatter()` regex; all 4 assertions satisfied by inspection | PASS |

### Deduction Breakdown
- All 6 refined AC lines verified by direct file read: 0 deduction
- Lint violations: N/A (0 deduction)
- TestFromAC_* modifications: N/A (0 deduction)
- Security: clean (0 deduction)

### Confidence: .97
### Verdict: PASS

[[2026-04-06]] Mon 10:48
## Docs Gate

### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Behavior/API change | Yes | Verified | `w-project-scoping/SKILL.md` description = `"Workflow (DEPRECATED): Project scoping — use ideator agent instead"` (L3 exact match); deprecation banner present (L8); `h-agent-structure/SKILL.md` L182 area — `w-project-scoping` absent, only `w-retro` and `h-excalidraw-diagram` listed; `.github/copilot-instructions.md` — no `w-project-scoping` reference, no update needed |
| 2 | Module docstrings | No | N/A | No Python files modified (builder confirmed; commit `98727c1` is `.md`-only) |
| 3 | External attribution | No | N/A | Pattern is internal (h-kanban-md DEPRECATED precedent), no external sources used |
| 4 | CLI changes | No | N/A | No CLI commands added or changed |
| 5 | Research doc | Yes | Verified | `.owlbear/research/deprecate-w-project-scoping.md` exists; linked from task body; follow-up tasks #658/#659 noted as redundant (subsumed by refined AC) |

### Files Updated
None — all documentation changes were the builder's deliverable (committed `98727c1`). No doc-writer edits required.

### Scratch Files
None found matching `.owlbear/scratch/643-*` — no cleanup needed.

[[2026-04-06]] Mon 12:17
## Audit
### AC Verification (Refined AC)
| AC | Requirement | Evidence | Status |
|----|------------|----------|--------|
| AC1 | description = "Workflow (DEPRECATED): ..." | w-project-scoping/SKILL.md L3: exact match | PASS |
| AC2 | Deprecation banner after frontmatter | w-project-scoping/SKILL.md L8: exact match | PASS |
| AC3 | user-invocable: true preserved | w-project-scoping/SKILL.md L4: confirmed | PASS |
| AC4 | Existing body content preserved | L10+: # Project Scoping and full Steps 0-5 present | PASS |
| AC5 | h-agent-structure L182: w-project-scoping removed | Text: (e.g., w-retro, h-excalidraw-diagram) only | PASS |
| AC6 | test_argument_hint_skills passes | TestFromAC_ProjectDefinitionArgumentHint 4/4 PASSED | PASS |

### Test Results
- pytest full suite: 3085 passed, 446 failed, 18 skipped (437.94s)
- All 446 failures are pre-existing (test_voice_*, test_session_context_hook_590, test_skill_frontmatter, test_validate_skills_ci, etc.) -- zero in task scope
- AC6 test: 4/4 PASSED (direct run verified)
- ruff: 5 pre-existing violations in serve/mcp-kanban/ -- not in task scope

### Architect Quality: 5/5
Refined AC was exemplary -- exact strings, specific file paths and line numbers, pattern reference (h-kanban-md DEPRECATED precedent), and identified redundant tasks (#658/#659) as subsumed.

### Deduction Breakdown
- AC lines with no evidence: 0 (all 6 verified by direct file read)
- Lint violations in scope: 0
- AC quality score: 5/5 (no deduction)
- Reviewer evidence section: present, detailed, .97 confidence PASS verdict
- Full-suite failures in task scope: 0

### Confidence: 1.00
### Action: archive

## Commits
| Commit | Type | Files | Tasks |
|--------|------|-------|-------|
| 98727c1 | chore(skills) | w-project-scoping/SKILL.md, h-agent-structure/SKILL.md | #643 |
| 4731ebd | chore(kanban) | activity.jsonl, 643 task file | #643 |
