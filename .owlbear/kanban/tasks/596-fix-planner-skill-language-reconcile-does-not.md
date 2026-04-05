---
id: 596
title: 'Fix planner skill language: reconcile "does NOT claim" with end_work usage'
status: todo
priority: nice-to-have
created: 2026-04-04T20:09:51.968555+02:00
updated: 2026-04-05T01:14:59.0675038+02:00
tags:
    - phase-2
    - ' scope:agent-config'
    - ' type:fix'
    - agent
class: standard
---

## Acceptance Criteria

- [ ] Step 0 (~L15): remove "does NOT claim a task" and replace with conditional language: when dispatcher-dispatched with a parent task ID, claim via `start_work`; when user-invoked, read via `show_task` without claiming
- [ ] Step 0 (~L15): for dispatcher-dispatched path, `start_work` replaces `show_task` (start_work returns the task body, making show_task redundant when claiming)
- [ ] Step 8 (~L92): verify `end_work` language is consistent with revised Step 0. Likely no change needed since it already says "release the claim"
- [ ] No functional changes to planner behavior. Documentation-only fix

## Context

Research doc: docs/research/rescope-575-lifecycle-blocks.md (section 3e)
w-task-decomposition L15 says "does NOT claim a task" but L92 references `end_work` to "release the claim." The planner IS dispatched from the board via orchestrator and needs to claim. The language describes task-creation intent, not operational reality.

## Files

share/skills/w-task-decomposition/SKILL.md

## Research
Research complete. Validation pass on existing docs/research/rescope-575-lifecycle-blocks.md section 3e.

Finding: L15 describes task-creation intent, not operational reality. Planner IS dispatched from board via orchestrator and needs to claim. Fix: replace 'does NOT claim' with conditional language, add start_work call for dispatch mode.

Classification: T1 autonomous. Confidence: .95

[[2026-04-05]] Sun 01:14
## Architecture Review
### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | One skill file, one inconsistency |
| Interface clarity | PASS | AC specifies exact lines and replacement logic |
| Dependency correctness | PASS | No dependencies needed |
| Module layering | N/A | Documentation-only fix |
| TDD compliance | PASS | Non-impl task; test-writer will process with pass-through note |
| KISS/YAGNI | PASS | Minimal scope: two paragraphs in one file |
| Premise challenge | PASS | Inconsistency confirmed in research (section 3e) and codebase (L15 vs L92) |
| Pattern consistency | PASS | Follows existing skill file conventions |
| Security surface | N/A | No system boundaries |
| Single domain | PASS | Agent config domain only |

### Refinements Applied
1. Fixed file path: `.github/skills/` does not exist; corrected to `share/skills/w-task-decomposition/SKILL.md`
2. Tightened AC1: specified that `start_work` replaces `show_task` for dispatch path (start_work returns body, making show_task redundant)
3. Added `agent` pass-through tag for non-impl task

### Challenge Results
- Challenger: FALLBACK (no challenger agent available)
- Architect response: proceeded with .90 confidence; minimal-scope doc fix with research backing

### Verdict: APPROVE (after REFINE)
### Action Taken: Refined AC (fixed file path, tightened start_work guidance, added agent tag), advanced to todo

[[2026-04-05]] Sun 01:14
APPROVED after REFINE. Fixed file path (.github/skills/ does not exist, corrected to share/skills/), tightened AC (start_work replaces show_task for dispatch path), added agent pass-through tag.
