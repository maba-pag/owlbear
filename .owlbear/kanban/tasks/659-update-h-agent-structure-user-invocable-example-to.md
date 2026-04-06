---
id: 659
title: Update h-agent-structure user-invocable example to not list deprecated skill
status: in-progress
priority: nice-to-have
created: 2026-04-06T07:23:34.6813674+02:00
updated: 2026-04-06T17:21:36.541817+02:00
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
