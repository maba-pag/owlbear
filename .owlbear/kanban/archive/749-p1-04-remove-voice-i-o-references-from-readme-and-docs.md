---
id: 749
title: 'P1-04: Remove voice I/O references from README and docs'
status: done
priority: important
created: '2026-04-10T10:36:47.149977+00:00'
updated: '2026-04-12T12:49:59.954074+00:00'
tags:
- phase-1
- type:docs
- cleanup
- scope-reduction
parent: 745
depends_on:
- 747
blocked: false
block_reason: null
claimed_by: null
claimed_at: null
---
## Context
Brief: see parent #745. Scratch tier — documentation edit.

The README.md directory layout table includes a `serve/voice/` row that must be removed after the code is deleted.

## Acceptance Criteria
1. `serve/voice/` row removed from the directory layout table in `README.md`
2. No other voice I/O references remain in `README.md`
3. `README-consumer.md` checked — remove any voice I/O references if present
4. CRITICAL: Do NOT touch ideation domain voice references (architect-voice, critic-voice, etc.) in any README

## Files
- Edit: `README.md`
- Check: `README-consumer.md`

[[2026-04-11]]
## Builder Notes
- Non-impl pass-through — all AC already satisfied by #747 builder
- AC1: `serve/voice/` row absent from README.md (confirmed — zero matches for "serve/voice")
- AC2: No other voice I/O references in README.md (confirmed — zero matches for "voice")
- AC3: README-consumer.md has zero voice references (confirmed)
- AC4: Ideation domain voices untouched (only `share/agents/` and `share/skills/` contain those, never edited)
- No files changed
[[2026-04-11]]
Verification pass — all AC satisfied (already noted in Builder Notes above).
[[2026-04-12]]
## Review Evidence

**Type:** docs-only task — no code changes, no tests applicable.

**Changed files (builder report):** none — builder passed through as already satisfied by #747.

**Independent verification (direct file reads):**

| AC | Criterion | Evidence | Status |
|----|-----------|----------|--------|
| AC1 | `serve/voice/` row absent from README.md layout table | README.md lines 31–46 read directly: rows are `serve/orchestrator/`, `serve/knowledge/`, `serve/mcp-kanban/`, `serve/mcp-knowledge/`, `serve/mcp-memory/` — no `serve/voice/` row | PASS |
| AC2 | No other voice I/O references in README.md | Full 145-line read: zero "voice" occurrences anywhere | PASS |
| AC3 | README-consumer.md has zero voice references | Full 130-line read: zero "voice" occurrences anywhere | PASS |
| AC4 | Ideation domain voice references untouched | No files edited by #749; `.owlbear/briefs/README.md` ideation voice references intact and out of scope | PASS |

**Test coverage:** None required — `type:docs` scratch-tier task with no code paths.
**Security:** No code changes, no attack surface introduced.
**Deductions:** 0

**Verdict:** PASS #749 -> docs | confidence .97
[[2026-04-12]]
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Behavior/API change | No | N/A | Docs-only removal task; no behavior, API, or convention changed |
| 2 | Module docstrings | No | N/A | Zero Python files touched by this task |
| 3 | External attribution | No | N/A | No external patterns used |
| 4 | CLI changes | No | N/A | No CLI commands added or modified |
| 5 | Research doc | No | N/A | Scratch-tier `type:docs` task; no research doc produced |

### Independent Verification
- `grep "voice" README.md` (root) → 0 matches confirmed
- `grep "serve/voice" README.md` → 0 matches confirmed
- `grep "voice" README-consumer.md` → 0 matches confirmed
- All "voice" grep hits resolve to `.owlbear/briefs/README.md` (ideation domain, AC4 out-of-scope)
- `## Review Evidence` section present and complete

### Files Updated
- None

### Scratch Files Cleaned
- None (no `749-*` files found in `.owlbear/scratch/`)
[[2026-04-12]]
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| AC1: `serve/voice/` row removed from README.md layout table | grep "serve/voice" README.md → 0 matches; reviewer read lines 31-46 confirming no row | PASS |
| AC2: No other voice I/O references in README.md | grep "voice" README.md → 0 matches in root README.md | PASS |
| AC3: README-consumer.md checked for voice references | grep "voice" README-consumer.md → 0 matches | PASS |
| AC4: Ideation domain voice references untouched | All "voice" hits resolve to `.owlbear/briefs/README.md` (ideation domain, out-of-scope); zero files edited by #749 | PASS |

### Test Results
- pytest: 4021 passed, 315 failed, 3 errors, 8 skipped (175s). All failures pre-existing across unrelated modules (kanban, pick_tasks, analysis, contentfetcher, lint_guard). Zero files changed by #749 → no regressions possible.
- ruff: clean (0 violations in serve/ and tests/)

### Architect Quality: 4/5
AC lines are specific and verifiable with clear file targets. AC4 guard rail against over-removal is good design. Minor gap: "voice I/O" vs "ideation domain voice" distinction could be more precise, but AC4 compensates.

### Deduction Breakdown
- AC lines without evidence: 0 (all 4 verified) → 0
- Lint violations: none → 0
- AC quality ≤ 3: no (4/5) → 0
- Missing reviewer evidence: no (detailed, PASS) → 0
- Full-suite failures in task scope: none → 0

### Confidence: 1.00
### Action: archive

### Commits
No commits — docs-only pass-through task; AC already satisfied by #747 builder.