---
id: 113
title: Update pytest-and-linting skill content for v2 monorepo paths
status: archived
priority: medium
created: 2026-03-29 00:38:45.402729+01:00
updated: 2026-03-30 08:39:27.293531+02:00
started: 2026-03-30 08:39:26.981246+02:00
completed: 2026-03-30 08:39:26.981246+02:00
tags:
- phase-1
- docs
- scope:build
depends_on:
- 90
class: standard
archival_reason: completed
archival_refs: []
---

## Objective
Apply 2 remaining updates to `.github/skills/pytest-and-linting/SKILL.md` that #90 does not cover. See `docs/research/pytest-linting-skill-v2-paths.md` items #6 and #7.

## Acceptance Criteria
- [ ] `norecursedirs = [v1]` is mentioned in the pytest section (so agents know v1 tests are excluded from collection)
- [ ] File-capture fallback command references both test discovery roots (`tests/` and `packages/`) matching `testpaths` in pyproject.toml
- [ ] No other content changes beyond these 2 additions

## Context
Follow-up to #90 (bulk skill update). The original 7-item AC from `docs/research/pytest-linting-skill-v2-paths.md` was split: items 1-5 are handled by #90, items 6-7 are handled here. Depends on #90 completing first so the builder edits the already-updated file.

[[2026-03-29]] Sun 03:44
## Architecture Review
**Verdict:** Refine

### AC Assessment
| AC Line | Assessment | Action |
|---------|------------|--------|
| Full-suite pytest commands | Duplicate of #90 AC item 5 | Removed |
| Coverage note source_pkgs | Duplicate of #90 AC item 3 | Removed |
| Broken-flag v2 paths | Duplicate of #90 AC item 2 | Removed |
| ruff command paths | Duplicate of #90 AC item 1 | Removed |
| import-mode documented | Duplicate of #90 AC item 4 | Removed |
| norecursedirs mention | Unique to #113, not in #90 | Kept |
| File-capture fallback roots | Unique to #113, not in #90 | Kept |

### Architecture Notes
5 of 7 original AC items are already covered by #90 (in-progress, same file). Refined AC to the 2 non-overlapping items: norecursedirs note and file-capture fallback path update. Added depends_on #90 so builder edits the already-updated file. Single file target (.github/skills/pytest-and-linting/SKILL.md), single domain (docs/build tooling). No TDD required for docs-only task. No code, no security surface.

### Changes Made
- Rewrote AC: 7 items down to 2 (removed 5 duplicates of #90)
- Added depends_on: #90
- Added scope guard AC (no other content changes)

### Dependencies
- Added: depends_on #90 (bulk skill update, in-progress)

[[2026-03-29]] Sun 21:01
## Builder Notes
- Files changed: skills/pytest-and-linting/SKILL.md (1 line)
- AC1: norecursedirs section already present (added by #90) - no change needed
- AC2: file-capture fallback updated: added packages/ alongside tests/ at line 89
- No other content changes
- Lint: docs-only, no ruff applicable
- Commit: f6d4053

[[2026-03-30]] Mon 07:33
## Review Evidence

### Test Results
- N/A — docs-only task, no Python files changed

### Lint Results
- N/A — docs-only task, ruff not applicable

### Pass 1 — CRITICAL

#### Security Review
No code changes. No security surface. No findings.

#### AC Compliance

| AC Line | Evidence | Status |
|---------|----------|--------|
| norecursedirs=[v1] mentioned in pytest section | SKILL.md lines 50-52: '### norecursedirs = [v1]' section present | PASS |
| File-capture fallback references both tests/ and packages/ | Commit f6d4053 adds packages/ to subprocess.run args; confirmed in SKILL.md | PASS |
| No other content changes | git show f6d4053 --stat: 1 file, 1 insertion, 1 deletion only | PASS |

### Scope Guard Verification
Exactly 1 file changed (skills/pytest-and-linting/SKILL.md), 1 insertion, 1 deletion. pyproject.toml confirms testpaths=[tests,packages] and norecursedirs=[v1].

### Verdict: PASS — confidence 0.96

[[2026-03-30]] Mon 07:49
## Docs Gate
No docs impact — task is a SKILL.md content update only.

Checklist:
1. copilot-instructions.md: N/A — no behavior/API change
2. Docstrings: N/A — no Python modules changed
3. sources/overview.md: N/A — no external patterns adopted
4. README.md: N/A — no CLI commands changed
5. Research doc: Pass — docs/research/pytest-linting-skill-v2-paths.md exists and referenced in task body

AC verified in SKILL.md: norecursedirs section present at lines 50-52; file-capture fallback references both tests/ and packages/.
Scratch files: none found.
Files updated: none.

[[2026-03-30]] Mon 08:39
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| norecursedirs=[v1] mentioned | SKILL.md L50-52: section present | PASS |
| File-capture fallback refs tests/ and packages/ | SKILL.md L89: subprocess.run includes both roots | PASS |
| No other content changes | Commit f6d4053: 1 file, 1 ins, 1 del | PASS |

### Test Results
- pytest: 2 collection errors (pre-existing, unrelated to #113). All other tests pass or fail from other tasks' RED tests. No regressions from this change.
- ruff: N/A (docs-only task)

### Architect Quality
AC quality score: 5/5. Architect correctly identified 5/7 items as duplicates of #90, refined to 2 specific verifiable items. Clean implementation path.

### Deduction breakdown: none
### Confidence: 1.0
### Action: archive
