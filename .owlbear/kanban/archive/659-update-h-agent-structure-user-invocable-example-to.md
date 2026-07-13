---
id: 659
title: Update h-agent-structure user-invocable example to not list deprecated skill
status: archived
priority: medium
created: 2026-04-06T07:23:34.6813674+02:00
updated: 2026-04-06T21:48:19.2541601+02:00
started: 2026-04-06T21:48:19.2541601+02:00
completed: 2026-04-06T21:48:19.2541601+02:00
tags:
    - phase-4
    - ' scope:ideator'
    - ' type:chore'
depends_on:
    - 643
class: standard
---

## Acceptance Criteria

- [ ] `share/skills/h-agent-structure/SKILL.md` line 182 no longer lists `w-project-scoping` as an active `user-invocable` example
- [ ] Replacement example or annotation added (e.g., use `w-retro` or `h-excalidraw-diagram` as sole examples)

## Context

Research: `.owlbear/research/deprecate-w-project-scoping.md`
Current text at L182: `Set true only for skills users invoke directly via / menu (e.g., w-project-scoping, w-retro, h-excalidraw-diagram).`
After w-project-scoping is deprecated, this example should not suggest it as a model reference.
Parent task: #643

[[2026-04-06]] Mon 15:12
## Research
- Work already completed by parent task #643 (commit `98727c1`, archived with 1.00 audit confidence)
- The architect's refined AC for #643 explicitly subsumed #659: "tasks #658 and #659 are redundant (subsumed by this refined AC)"
- Verified current file state: `share/skills/h-agent-structure/SKILL.md` L182 lists only `w-retro` and `h-excalidraw-diagram` — `w-project-scoping` already removed
- Research doc: `.owlbear/research/deprecate-w-project-scoping.md` (from parent #643)
- Sources: 1 studied (parent task #643 body with full pipeline trail)
- Recommendation: No further action needed (confidence: .98)
- Follow-up tasks created: none — both ACs already satisfied
- Decision requests: none (T1 autonomous, already resolved)
- Tier: T1 — Autonomous (redundant task, work subsumed by parent)

## Challenge Results
- Challenger: SKIPPED — task is already complete, no recommendation to challenge
- Confidence in original: .98

[[2026-04-06]] Mon 16:30
## Architecture Review

### Pre-condition: Both ACs Already Satisfied

Verified independently — not from researcher self-report:

1. **AC1** — `share/skills/h-agent-structure/SKILL.md` L182 reads: `Set 'true' only for skills users invoke directly via '/' menu (e.g., 'w-retro', 'h-excalidraw-diagram').` — `w-project-scoping` is absent. **SATISFIED.**
2. **AC2** — Replacement examples `w-retro` and `h-excalidraw-diagram` are present on that line. **SATISFIED.**

Parent task #643 is `archived` (audit confidence 1.00, commit `98727c1`). The architect's review of #643 explicitly subsumed #659.

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | One file, one line change (already done) |
| Interface clarity | PASS | ACs are specific: file, line, exact text |
| Dependency correctness | PASS | #643 archived — dependency satisfied |
| Module layering | N/A | No code change |
| TDD compliance | N/A | Markdown-only change, no testable code |
| KISS/YAGNI | PASS | Minimal scope — single line edit |
| Premise challenge | NOTE | Task is redundant — work already done by #643. Advancing to close it out. |
| Pattern consistency | PASS | Follows existing SKILL.md conventions |
| Security surface | N/A | No system boundary impact |
| Single domain | PASS | Agent-structure skill docs only |

### Challenge Results
- Challenger: FALLBACK — challenger agent not available in current subagent list
- Architect response: N/A — task is trivially pre-satisfied, challenge would add no value

### Pass-through Tag Note
Task has `type:chore` but produces no testable Python. Recommend downstream agents treat as pass-through. `edit_task` unavailable to add `type:docs` tag.

### Verdict: APPROVE
### Action Taken: Advanced to todo. Both ACs pre-satisfied by parent #643. No development work needed — downstream agents should pass through.

[[2026-04-06]] Mon 17:21
## Test-Writer Notes
- Non-impl pass-through: AC references only `share/skills/h-agent-structure/SKILL.md` (Markdown/SKILL doc) — no Python source files, functions, classes, or modules.
- No testable Python interfaces exist. Both ACs already satisfied by parent #643 (commit `98727c1`).
- Task tagged `type:chore`; architect explicitly noted TDD compliance N/A.
- Passing through to builder.

[[2026-04-06]] Mon 20:14
## Builder Notes
- Non-implementation task — no code changes needed.
- Both ACs pre-satisfied by parent #643 (commit `98727c1`).
- AC1: `share/skills/h-agent-structure/SKILL.md` L182 — `w-project-scoping` absent, confirmed.
- AC2: Replacement examples `w-retro` and `h-excalidraw-diagram` present on that line, confirmed.
- No tests to run (Markdown-only change, `type:chore`).
- Passing through to review.

[[2026-04-06]] Mon 21:16
## Review Evidence

### Test Results
N/A — Markdown-only `type:chore`. No Python source, no test files, no testable interfaces.

### Lint Results
N/A — No Python files touched.

### Coverage
N/A

### AC Compliance

| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| L182 no longer lists `w-project-scoping` | grep confirms L182: `(e.g., 'w-retro', 'h-excalidraw-diagram')` — `w-project-scoping` absent | N/A | PASS |
| Replacement example added (`w-retro` or `h-excalidraw-diagram`) | grep confirms both present at L182 | N/A | PASS |

### Pass 1 Checks
- **5.0 Test-Writer Audit**: SKIP — no TestFromAC_* classes (Markdown-only task)
- **5.1 Security**: N/A — no code changes
- **5.2 TestFromAC Integrity**: SKIP — no TestFromAC_* classes
- **5.3 Test Quality**: N/A — no tests
- **5.4 Data Safety**: N/A — no code
- **5.5 Implementation-Aware Gap**: N/A — no code paths
- **5.6 Necessity**: SKIP — no new dependencies
- **5.7 Builder Process**: CLEAN — single pass-through, no retries

### Deductions
None. Both ACs verified independently via grep (not from builder/architect self-reports).

### Verdict
**PASS** — confidence .97

[[2026-04-06]] Mon 21:22
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Behavior/API change | No | N/A | SKILL.md change only (removing deprecated example from examples list) — `copilot-instructions.md` grepped for `w-project-scoping`, zero matches, no update needed |
| 2 | Module docstrings | No | N/A | No Python modules modified |
| 3 | External attribution | No | N/A | No external patterns or sources used |
| 4 | CLI changes | No | N/A | No CLI commands added or modified |
| 5 | Research doc | Yes | Verified | `.owlbear/research/deprecate-w-project-scoping.md` exists on disk and is linked from task body |

### Files Updated
None — both ACs pre-satisfied by parent #643 (commit `98727c1`). `share/skills/h-agent-structure/SKILL.md` L182 already reads `(e.g., 'w-retro', 'h-excalidraw-diagram')` — `w-project-scoping` absent, confirmed by file search.

### Scratch Files
None found matching `.owlbear/scratch/659-*`.

### Commit
N/A — no documentation files required updating.

[[2026-04-06]] Mon 21:48
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| L182 no longer lists w-project-scoping | share/skills/h-agent-structure/SKILL.md L182: `(e.g., 'w-retro', 'h-excalidraw-diagram')` w-project-scoping absent | PASS |
| Replacement example added (w-retro or h-excalidraw-diagram) | Same line: both w-retro and h-excalidraw-diagram present | PASS |

### Test Results
- pytest: 3169 passed, 452 failed, 18 skipped (all failures pre-existing, none in task scope; Markdown-only chore)
- ruff: 5 pre-existing errors, none in task scope (no Python files touched)

### Architect Quality: 4/5
ACs were specific (file, line, exact text). Task was redundant (subsumed by parent #643), but the ACs themselves were well-written and independently verifiable. Minor: could have been auto-closed instead of pipelined.

### Deduction Breakdown
- Start: 1.00
- AC lines without evidence: 0 (both verified via file read)
- Lint violations in scope: 0
- AC quality > 3: no deduction
- Reviewer evidence section: present, detailed, PASS .97
- Full-suite failures in task scope: 0
- Total deductions: 0

### Confidence: 1.00
### Action: archive

### Commit Verification
- Deliverable file change in commit 98727c1 (parent #643, already archived with 1.00 confidence)
- No new files to commit for #659 (pass-through task, no additional deliverables)
