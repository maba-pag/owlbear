---
id: 90
title: Update pytest-and-linting skill for v2 paths
status: archived
priority: medium
created: 2026-03-28 01:40:27.810303+01:00
updated: 2026-03-30 07:23:06.650421+02:00
started: 2026-03-30 07:22:23.882760+02:00
completed: 2026-03-30 07:22:23.882760+02:00
tags:
- phase-1
- docs
- scope:build
depends_on:
- 35
class: standard
archival_reason: completed
archival_refs: []
---

## Objective
Update the pytest-and-linting skill (skills/pytest-and-linting/SKILL.md) to fully document v2 test infrastructure configuration and close remaining knowledge gaps.

## Acceptance Criteria
- [ ] No references to v1 src/ layout, v1 module names, or pre-monorepo paths remain in the skill
- [ ] Coverage section explains source_pkgs approach: bare --cov reads [tool.coverage.run] source_pkgs from pyproject.toml; lists all installed package names
- [ ] Import mode note present: --import-mode=importlib is configured in addopts (no manual flag needed)
- [ ] Async mode documented: asyncio_mode = strict means async tests require explicit @pytest.mark.asyncio decorator
- [ ] V1 exclusion documented: norecursedirs = [v1] explains why v1 directory is excluded from test discovery
- [ ] Test markers section: document project markers (api, slow, integration) with example -m filter flags
- [ ] Testpaths note present: testpaths = [tests, packages] enables dual-directory discovery (root tests/ + per-package tests/)

## Scope
Single file: skills/pytest-and-linting/SKILL.md. Verify existing v2 content is correct, add missing items (async mode, norecursedirs, markers section). No Python code changes.

## Context
Depends on #35 (v2 test infrastructure, archived). The skill was partially updated alongside #35 but is missing three items (async mode, v1 exclusion, markers reference). Items 1-3 and 7 are verification checks; items 4-6 are new content.

## Architecture Notes
- This is a docs/skill-only task (SKILL.md markdown). No TDD applicable.
- Single domain: docs.
- Builder edits the SKILL.md; reviewer verifies completeness.

[[2026-03-29]] Sun 16:08
## Architecture Review
**Verdict:** APPROVED

### AC Assessment

| AC Line | Assessment | Action |
|---------|------------|--------|
| No v1 src/ references | Skill already uses v2 paths throughout | Verify only |
| Coverage source_pkgs section | Already documented correctly | Verify only |
| Import mode note | Already documented | Verify only |
| Async mode (strict) | MISSING from skill | Add new note/subsection |
| V1 exclusion (norecursedirs) | MISSING from skill | Add new note |
| Test markers section | Only partial (not api in one example) | Add dedicated section |
| Testpaths dual-directory | Already documented | Verify only |

### Architecture Notes
Domain: docs (single domain). Single file target: skills/pytest-and-linting/SKILL.md.
No TDD applicable (markdown skill file). No Python code changes.
Skill was partially updated alongside #35 infrastructure work.
Three items need addition: asyncio_mode=strict, norecursedirs=[v1], markers reference.
Four items are verification-only (already present and correct).

### Dependencies
- Verified: #35 (v2 test infrastructure) archived
- No new dependencies needed

[[2026-03-29]] Sun 19:06
## Test-Writer Notes
- Non-implementation task (tagged docs) — no tests applicable.
- Passing through to builder.

[[2026-03-29]] Sun 20:55
## Builder Notes
- Files changed: skills/pytest-and-linting/SKILL.md
- No code changes (docs-only task)
- Added: asyncio_mode=strict subsection with @pytest.mark.asyncio example
- Added: norecursedirs=[v1] subsection explaining legacy isolation
- Added: Test markers section with table (api, slow, integration) and -m filter examples
- AC items 1-3,7 verified already present; items 4-6 added
- Commit: 20d4638

[[2026-03-30]] Mon 03:06
## Review Evidence
See docs/scratch/90-reviewer.tmp for full evidence.

[[2026-03-30]] Mon 03:08
## Review Evidence
**Reviewer:** reviewer | **Date:** 2026-03-30

### Test Results
N/A â€” docs-only task (no Python code changed, no test files applicable)

### Lint Results
N/A â€” markdown file only, no ruff applicable

### AC Compliance

| AC Line | Evidence | Status |
|---------|----------|--------|
| No v1 src/ layout references | Only v1 ref is the intentional norecursedirs doc â€” correct | PASS |
| Coverage section lists all installed package names | Skill says 'all 6' + lists 6 packages; pyproject.toml source_pkgs has 7 â€” owlbear_voice is missing | **FAIL** |
| Import mode note present | Line 19: --import-mode=importlib confirmed in addopts; skill documents this correctly | PASS |
| asyncio_mode strict documented | Section added with @pytest.mark.asyncio example; matches pyproject.toml line 21 | PASS |
| norecursedirs=[v1] documented | Section added; matches pyproject.toml line 20 | PASS |
| Test markers section present | Section added with table (api, slow, integration) + -m examples; matches pyproject.toml lines 22-27 | PASS |
| testpaths dual-discovery noted | Documented at line referencing testpaths = [tests, packages] | PASS |

### Failure Details

**AC 2 â€” source_pkgs list incomplete**

pyproject.toml source_pkgs (7 entries):
owlbear, owlbear_orchestrator, owlbear_knowledge, owlbear_mcp_kanban, owlbear_mcp_knowledge, owlbear_mcp_project, owlbear_voice

Skill states: 'all 6 installed package names' and lists only 6 (missing owlbear_voice).
Confirmed via uv pip list: owlbear-voice==0.1.0 is installed.

Builder notes say 'AC items 1-3,7 verified already present' but did not check that the listed count and names were accurate. The pre-existing text was incorrect (stale since voice package was added) and the builder failed to correct it during verification.

**Fix required:** Update skill to say '7' and add owlbear_voice to the list.

### Verdict: FAIL confidence .97

[[2026-03-30]] Mon 05:38
## Test-Writer Notes (retry)
- Retry reason: reviewer FAIL was about content accuracy (source_pkgs count says 6, should be 7 with owlbear_voice), not missing tests.
- Non-implementation task (tagged docs) - no test changes applicable.
- Existing pass-through preserved. Builder will address reviewer findings.

[[2026-03-30]] Mon 06:44
## Builder Notes (retry)\n- Fix: updated source_pkgs count from 6 to 7 and added owlbear_voice to the package list\n- Verified against pyproject.toml source_pkgs: 7 entries match exactly\n- Single-line change in skills/pytest-and-linting/SKILL.md\n- Commit: 9fba72b\n- No code changes (docs-only task)

[[2026-03-30]] Mon 07:10
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | .github/copilot-instructions.md | No | N/A | Skill-only task; no behavior/API/convention change |
| 2 | Docstrings complete | No | N/A | No Python files changed |
| 3 | docs/sources/overview.md | No | N/A | No external patterns used |
| 4 | README.md | No | N/A | No CLI commands changed |
| 5 | Research doc produced | No | N/A | No research phase |

All 7 AC items verified in skills/pytest-and-linting/SKILL.md: no v1 refs (PASS), source_pkgs lists all 7 with owlbear_voice (PASS), import mode noted (PASS), asyncio_mode strict section (PASS), norecursedirs section (PASS), markers table (PASS), testpaths documented (PASS).

### Files Updated
- None

### Scratch Files Cleaned
- None (docs/scratch/90-* not present)

[[2026-03-30]] Mon 07:22
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| No v1 src/ references | Only v1 ref is intentional norecursedirs doc | PASS |
| Coverage source_pkgs lists all 7 | Skill says 'all 7', lists 7 matching pyproject.toml L118-126 | PASS |
| Import mode note present | Documented in skill | PASS |
| Async mode strict documented | Section with @pytest.mark.asyncio example | PASS |
| V1 exclusion documented | norecursedirs section present | PASS |
| Test markers section | Table (api/slow/integration) + -m filter examples | PASS |
| Testpaths dual-discovery | Documented: testpaths = [tests, packages] | PASS |

### Test Results
- pytest: 1129 passed, 157 failed, 6 errors (all pre-existing RED-phase tests from other tasks; no failures in task scope)
- ruff: 2 PT018 in tests/test_necessity_check_196.py (unrelated to task)

### Architect Quality: 4/5
AC was specific with clear verify/add split. Minor gap: did not call out stale package count for explicit verification (reviewer caught it).

### Commits Verified
- 20d4638 docs: update pytest-and-linting skill for v2 paths (#90, builder)
- 9fba72b docs: fix source_pkgs count 6 to 7, add owlbear_voice (#90, builder)

### Deduction breakdown: None. All 7 AC lines verified with evidence.
### Confidence: 1.0
### Action: archive

[[2026-03-30]] Mon 07:23
## Commits
| Commit | Type | Files | Tasks |
|--------|------|-------|-------|
| c68cf5b | chore | kanban/tasks/090-*.md | #90 |
