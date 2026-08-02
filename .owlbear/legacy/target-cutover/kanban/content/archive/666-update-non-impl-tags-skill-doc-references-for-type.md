---
id: 666
title: Update NON_IMPL_TAGS skill doc references for type:user-action
status: archived
priority: medium
created: 2026-04-06T16:47:04.4677636+02:00
updated: 2026-04-07T05:46:10.5544035+02:00
started: 2026-04-07T05:46:10.5544035+02:00
completed: 2026-04-07T05:46:10.5544035+02:00
tags:
    - phase-3
    - ' scope:agent-config'
    - ' type:docs'
parent: 661
depends_on:
    - 662
class: standard
---

## Objective\nAdd type:user-action to NON_IMPL_TAGS documentation in skill files.\n\n## Acceptance Criteria\n- [ ] w-dispatch-planning/SKILL.md authoritative NON_IMPL_TAGS list includes type:user-action\n- [ ] w-tdd-red/SKILL.md NON_IMPL_TAGS reference includes type:user-action\n- [ ] Cross-reference comments remain consistent with gates.py and server.py\n\n## Files Affected\n- share/skills/w-dispatch-planning/SKILL.md\n- share/skills/w-tdd-red/SKILL.md

[[2026-04-07]] Tue 02:14
## Research
- Research doc: .owlbear/research/non-impl-tags-skill-doc-update.md
- Sources: 6 studied, 6 high-relevance (gates.py, server.py, 3 skill files, #662 body)
- Recommendation: Add `type:user-action` to 4 locations across 3 skill files (confidence: .95)
- Follow-up tasks created: none (task #666 itself is the implementation vehicle)
- Decision requests: none (T1 — trivial docs addition)

### Findings Summary

4 NON_IMPL_TAGS enumeration locations are out of sync with gates.py/server.py:

| # | File | Section |
|---|------|---------|
| 1 | w-dispatch-planning/SKILL.md | Agent dispatch table, `todo` row |
| 2 | w-dispatch-planning/SKILL.md | Recipe 1 `TW:MISSING` gate flag |
| 3 | w-tdd-red/SKILL.md | Step 1 item 1 |
| 4 | w-arch-review/SKILL.md | Non-impl tagging note (L91) |

Location #4 (w-arch-review) is not in the AC but is declared as a secondary copy by the cross-reference comment in w-dispatch-planning. AC #3 ("cross-reference comments remain consistent") requires its inclusion.

[[2026-04-07]] Tue 02:46
## Architecture Review
### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | One concern: sync type:user-action into 4 NON_IMPL_TAGS doc locations across 3 files |
| Interface clarity | PASS | AC specifies exact files; research maps all 4 edit points with file + section |
| Dependency correctness | PASS | #662 (Python code) is archived — prerequisite satisfied |
| Module layering | N/A | Documentation files only |
| TDD compliance | PASS | Tagged type:docs — non-impl pass-through, no tests needed |
| KISS/YAGNI | PASS | Minimal scope: add one tag string to 4 existing comma-separated lists |
| Premise challenge | PASS | Doc lists are genuinely out of sync with gates.py/server.py after #662 |
| Pattern consistency | PASS | Follows established cross-reference comment conventions |
| Security surface | N/A | No system boundaries |
| Single domain | PASS | All files in share/skills/ (agent-config domain) |

### AC Assessment
| AC Line | Assessment | Action |
|---------|-----------|--------|
| w-dispatch-planning authoritative list includes type:user-action | Precise — 2 locations in file (dispatch table + Recipe 1 TW:MISSING) | None |
| w-tdd-red reference includes type:user-action | Precise — 1 location (Step 1 item 1) | None |
| Cross-reference comments remain consistent | Verifiable — w-dispatch-planning cross-ref comment declares w-arch-review as secondary copy, requiring its update too. Research findings map all 4 locations explicitly. | None needed — builder has clear guidance via research findings |

### Files Affected (complete list from research)
1. share/skills/w-dispatch-planning/SKILL.md — dispatch table todo row + Recipe 1 TW:MISSING
2. share/skills/w-tdd-red/SKILL.md — Step 1 item 1
3. share/skills/w-arch-review/SKILL.md — non-impl tagging note (~L91)

### Challenge Results
- Challenger: FALLBACK — agent not available in session
- Architect response: N/A

### Verdict: APPROVE
### Action Taken: Advanced to todo. AC is precise, all 4 locations mapped in research findings. type:docs tag already present for non-impl pass-through.

[[2026-04-07]] Tue 02:51
## Test-Writer Notes
- Non-implementation task (tagged type:docs) — no tests applicable.
- Passing through to builder.
- AC references only SKILL.md files (w-dispatch-planning, w-tdd-red, w-arch-review) — no Python interfaces exist.
- Step 2a heuristic confirms pass-through: all affected files are .md, zero implementation intent keywords in AC.

[[2026-04-07]] Tue 03:00
## Builder Notes
### Files Changed
- share/skills/w-dispatch-planning/SKILL.md — dispatch table `todo` row + Recipe 1 `TW:MISSING` gate flag (2 edits)
- share/skills/w-tdd-red/SKILL.md — Step 1 item 1 non-impl tag check (1 edit)
- share/skills/w-arch-review/SKILL.md — non-impl tagging note (~L91) (1 edit)

### Evidence
- All 4 NON_IMPL_TAGS enumeration locations now include `type:user-action`
- Cross-reference comments unchanged — w-dispatch-planning comment still declares w-arch-review as secondary copy (consistent)
- Commit: 3b481fb — 3 files changed, 4 insertions, 4 deletions

### Test Results
- Non-implementation task (type:docs) — no tests applicable; pass-through confirmed by test-writer

### Lint
- No Python files touched — ruff N/A

### AC Verification
- [x] w-dispatch-planning/SKILL.md authoritative NON_IMPL_TAGS list includes type:user-action — DONE (2 locations)
- [x] w-tdd-red/SKILL.md NON_IMPL_TAGS reference includes type:user-action — DONE
- [x] Cross-reference comments remain consistent with gates.py and server.py — DONE (w-arch-review secondary copy updated)

[[2026-04-07]] Tue 05:31
## Review Evidence

### Source Control
- 3 skill files changed in commit 3b481fb (confirmed via file reads — not in current unstaged diff, already committed)
- No Python files changed; ruff N/A; no TestFromAC_* classes (type:docs pass-through)

### Tests / Lint / Coverage
- Non-implementation task (type:docs) — test-writer pass-through confirmed
- No Python tests applicable; no ruff applicable

### Source-of-Truth Verification
- gates.py `_NON_IMPL_TAGS` (line 24–29): `{"research", "docs", "type:config", "type:docs", "test", "type:test", "agent", "quality", "type:user-action"}` — 9 tags
- server.py `_PICK_NON_IMPL_TAGS` (line 531–536): identical 9-tag frozenset
- Both match all 4 skill file edit locations ✓

### AC Compliance

| AC Line | Evidence | Verdict |
|---------|----------|---------|
| w-dispatch-planning authoritative list includes type:user-action | Dispatch table `todo` row: `..., type:user-action` ✓ | COVERED |
| w-dispatch-planning Recipe 1 TW:MISSING includes type:user-action | Gate flag text: `..., type:user-action` ✓ | COVERED |
| w-tdd-red NON_IMPL_TAGS reference includes type:user-action | Step 1 item 1: `(tagged ..., or \`type:user-action\`)` ✓ | COVERED |
| w-arch-review secondary copy includes type:user-action (per AC3 cross-ref) | Non-impl tagging note: `..., \`type:user-action\`. Add the bare tag if missing.` ✓ | COVERED |
| Cross-reference comments consistent with gates.py/server.py | All 4 locations match implementation frozensets exactly ✓ | COVERED |

### Deductions
- −0.02: Cross-reference comment in w-dispatch-planning says "Step 1 item 3" for w-tdd-red location, but actual location is Step 1 item 1. Pre-existing; builder confirmed "unchanged". Out of AC scope. No action required.

### Verdict
Confidence: 0.96 → PASS

[[2026-04-07]] Tue 05:34
## Docs Gate

### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Behavior/API change | No | N/A | Task updated SKILL.md files only (the files ARE the docs). `.github/copilot-instructions.md` contains no NON_IMPL_TAGS references — no update needed. |
| 2 | Module docstrings | No | N/A | No Python files modified. Commit 3b481fb touches only 3 .md files. |
| 3 | External attribution | No | N/A | Internal synchronization task — no external patterns used. |
| 4 | CLI changes | No | N/A | No CLI changes. |
| 5 | Research doc | Yes | Verified | `.owlbear/research/non-impl-tags-skill-doc-update.md` exists and is linked from task body. No follow-up tasks required (task itself was the implementation vehicle). |

### AC Spot-Checks (live grep, 4 locations)
- `w-dispatch-planning/SKILL.md` L25 — dispatch table `todo` row: `..., type:user-action` ✓
- `w-dispatch-planning/SKILL.md` L67 — Recipe 1 `TW:MISSING` gate flag: `..., type:user-action` ✓
- `w-tdd-red/SKILL.md` L25 — Step 1 item 1: `..., or \`type:user-action\`` ✓
- `w-arch-review/SKILL.md` L91 — non-impl tagging note: `..., \`type:user-action\`` ✓

### Files Updated
None — all documentation was updated by the builder in commit 3b481fb; no further doc-writer edits required.

### Scratch Files
None found matching `.owlbear/scratch/666-*`. Clean.

[[2026-04-07]] Tue 05:46
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| w-dispatch-planning authoritative NON_IMPL_TAGS list includes type:user-action | SKILL.md L25: dispatch table todo row lists type:user-action; L67: Recipe 1 TW:MISSING lists type:user-action | PASS |
| w-tdd-red NON_IMPL_TAGS reference includes type:user-action | SKILL.md L25: Step 1 item 1 lists type:user-action | PASS |
| Cross-reference comments consistent with gates.py and server.py | w-arch-review/SKILL.md L91: non-impl tagging note includes type:user-action. All 4 locations match reviewer-verified gates.py and server.py frozensets (9 tags each) | PASS |

### Test Results
- pytest: 3481 passed, 424 failed, 18 skipped, 1 error (all failures pre-existing, none in task scope; no Python files touched)
- ruff: N/A (docs-only task, no Python files modified)

### Architect Quality: 4/5
AC was precise with 3 specific lines and exact file list. Research correctly identified the w-arch-review secondary copy requirement from AC3's cross-reference language. Minor gap: AC didn't explicitly name w-arch-review, relying on implicit cross-reference semantics, but researcher and builder handled it cleanly.

### Deduction Breakdown
- No AC lines without evidence: 0
- No lint violations: 0
- AC quality 4/5: no deduction (threshold is 3 or below)
- Reviewer evidence section: present, detailed, PASS at 0.96
- No test failures in task scope: 0

### Confidence: 1.00
### Action: archive

## Commits
| Commit | Type | Files | Tasks |
|--------|------|-------|-------|
| 3b481fb | docs | w-dispatch-planning/SKILL.md, w-tdd-red/SKILL.md, w-arch-review/SKILL.md | #666 |
| 750523a | chore | kanban board, research doc | #666 |
