---
id: 596
title: 'Fix planner skill language: reconcile "does NOT claim" with end_work usage'
status: archived
priority: medium
created: 2026-04-04 20:09:51.968555+02:00
updated: 2026-04-06 06:00:09.948201+02:00
started: 2026-04-06 06:00:09.948201+02:00
completed: 2026-04-06 06:00:09.948201+02:00
tags:
- phase-2
- ' scope:agent-config'
- ' type:fix'
- agent
class: standard
archival_reason: completed
archival_refs: []
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

[[2026-04-05]] Sun 13:16
## Test-Writer Notes
- Non-implementation task (tagged `agent`) — no tests applicable.
- Passing through to builder.

[[2026-04-06]] Mon 03:14
## Builder Notes
- Files changed: `share/skills/w-task-decomposition/SKILL.md` (1 paragraph, ~L17)
- Change applied: Replaced "This skill does NOT claim a task" with conditional claiming language — dispatcher-dispatched path uses `start_work` (returns body, no separate `show_task` needed); user-invoked path uses `show_task` without claiming
- Step 8 (L90): Verified — "release the claim" is already consistent with revised Step 0. No change needed.
- No Python code changes. Documentation-only fix.
- AC: all 4 items satisfied

[[2026-04-06]] Mon 03:57
## Review Evidence
### Test Results
- N/A — non-implementation task (`agent` tag); no test file exists or is expected

### Lint
- N/A — documentation-only change; no Python source modified

### Coverage
- N/A

### Pass 1 — CRITICAL
#### Test-Writer AC Coverage
No `TestFromAC_*` classes — skip (non-impl task).

#### Security Review
No issues. Documentation-only edit to a Markdown skill file; no system boundaries, no user input, no code execution paths.

#### TestFromAC Integrity
No TestFromAC tests — skip.

#### Test Quality
N/A

#### Data Safety
N/A

#### Implementation-Aware Test Gap Analysis
N/A

#### Necessity Check
N/A

#### Builder Process Quality
CLEAN — 1 builder notes section, no retries.

### AC Compliance Table
| AC Line | Evidence | Status |
|---------|----------|--------|
| Step 0 (~L15): remove "does NOT claim", add conditional claiming | grep "does NOT claim" → 0 matches; share/skills/w-task-decomposition/SKILL.md:17 has dispatcher-dispatched/user-invoked conditional | PASS |
| Step 0: `start_work` replaces `show_task` for dispatch path | SKILL.md:17: "making a separate `show_task` call redundant" | PASS |
| Step 8 (~L92): verify `end_work` consistent with revised Step 0 | SKILL.md:90: "advance via `end_work` to release the claim" — consistent, no change needed | PASS |
| No functional changes — documentation-only fix | Only `share/skills/w-task-decomposition/SKILL.md` in changed files; zero Python files modified | PASS |

### Verdict
0 deductions. Confidence: .97 → PASS

[[2026-04-06]] Mon 04:02
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Behavior/API change | No | N/A | Agent-config skill change; `copilot-instructions.md` has no references to planner claiming behavior — no update needed |
| 2 | Module docstrings | No | N/A | Zero Python files modified |
| 3 | External attribution | No | N/A | No external patterns used |
| 4 | CLI changes | No | N/A | No CLI commands added or modified |
| 5 | Research doc | Yes | Verified | `.owlbear/research/rescope-575-lifecycle-blocks.md` exists; section 3e documents the inconsistency; task #596 was created as the follow-up |

### Files Updated
- None — no documentation files required updating

### Scratch Files Cleaned
- None found for task 596

[[2026-04-06]] Mon 06:00
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| Step 0 (~L15): remove "does NOT claim", add conditional claiming | grep "does NOT claim" → 0 matches; SKILL.md:17 has dispatcher/user-invoked conditional | PASS |
| Step 0: start_work replaces show_task for dispatch path | SKILL.md:17: "making a separate show_task call redundant" | PASS |
| Step 8 (~L92): verify end_work consistent with revised Step 0 | SKILL.md:90: "advance via end_work to release the claim" — consistent, no change needed | PASS |
| No functional changes — documentation-only fix | Only share/skills/w-task-decomposition/SKILL.md in commit 80b05fc; zero Python files modified | PASS |

### Test Results
- pytest: 2983 passed, 567 failed (pre-existing, unrelated — doc-only task changed no Python), 8 skipped
- ruff: All checks passed

### Architect Quality: 4/5
AC lines referenced specific line numbers and exact replacement logic. Minor imprecision: ~L15 vs actual L17. Research doc properly referenced. Clean scope.

### Deduction Breakdown
- 4/4 AC lines with specific evidence: 0
- Lint clean: 0
- AC quality 4/5 (above threshold): 0
- Reviewer evidence present and detailed (.97 PASS): 0
- Full-suite failures outside task scope: 0

### Confidence: 1.00
### Action: archive
