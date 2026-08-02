---
id: 106
title: Document setup process for new users
status: archived
priority: medium
created: 2026-03-28 14:56:10.844147+01:00
updated: 2026-03-29 07:50:56.953369+02:00
started: 2026-03-29 07:50:56.633242+02:00
completed: 2026-03-29 07:50:56.633242+02:00
tags:
- phase-1
- scope:docs
- type:docs
depends_on:
- 12
class: standard
archival_reason: completed
archival_refs: []
---

## Objective
Document the owlbear setup process for new users (friends, coworkers).

## Acceptance Criteria

### README.md updates (Bootstrap a New Project section)
- [ ] Bootstrap section includes a Next Steps subsection after the artifacts table listing 3 post-setup steps: (1) open the project in VS Code, (2) run kanban/setup.ps1 to download kanban-md, (3) verify agent discovery by opening Copilot Chat
- [ ] Bootstrap section includes a one-line prerequisites note linking back to the Prerequisites section (e.g. Requires Python 3.12+ and uv, see Prerequisites)
- [ ] Existing content preserved: command example, artifacts table, section heading all remain as-is; only new subsections and cross-references added

### Scope boundary
- Does NOT modify scripts/setup.py or any Python/config files
- Does NOT create a separate getting-started doc; all content stays in README.md
- Existing Quick Start section (for owlbear developers) is not changed

## Context
Split from #12 Additional AC (docs concerns removed from build task).
See docs/research/setup-script.md for architecture rationale.
The README already has the Bootstrap a New Project section with command and artifacts table. This task fills the gaps (next steps, prerequisite cross-ref).
Depends on #12 (setup script must be stable before docs are finalized).

[[2026-03-28]] Sat 21:12
## Architecture Review\n**Verdict:** APPROVED\n\n### AC Assessment\n| AC Line | Assessment | Action |\n| Next Steps subsection | Precise: 3 enumerated steps, clear location (after artifacts table) | Keep |\n| Prerequisites cross-ref | Precise: links back to existing section | Keep |\n| Existing content preserved | Precise: names what must not change | Keep |\n\n### Architecture Notes\n- Single domain: scope:docs targeting README.md only\n- No code changes, no TDD pair needed (type:docs)\n- README.md already has Bootstrap section (lines 33-54) with command and artifacts table\n- Task fills two specific gaps: post-setup next steps and prerequisite cross-reference\n- Added depends_on #12 (setup script behavior must be stable before docs finalized)\n- Scope boundary explicitly excludes Quick Start section and Python files\n\n### Changes Made\n- Rewrote 3 vague AC lines into 3 precise verifiable lines grouped by target file\n- Added scope boundary section\n- Added depends_on: 12 in frontmatter\n- Updated context to note existing README coverage\n\n### Dependencies\n- Added: #12 (setup script build) in backlog

[[2026-03-29]] Sun 06:00
## Test-Writer Notes
- Non-implementation task (tagged type:docs) - no tests applicable.
- README.md documentation only; no testable code will be produced.
- Passing through to builder.

[[2026-03-29]] Sun 07:15
## Review Evidence
Reviewed: 2026-03-29

### Task type
type:docs - Markdown-only change, no code, no tests, no lint applicable.

### Changed files
- README.md only (git show bd9fe0d --name-only)

### AC Compliance

| AC Line | Evidence | Status |
|---------|----------|--------|
| Next Steps subsection (3 steps) after artifacts table | README.md: Next Steps with 3 numbered items: open VS Code, run kanban/setup.ps1, Copilot Chat agent discovery | PASS |
| Prerequisites one-line cross-ref in Bootstrap section | README.md: Requires Python 3.12+ and uv, see Prerequisites (link) present before command block | PASS |
| Existing content preserved (heading, command, artifacts list) | Before/after diff: heading, command block, 5-bullet artifacts list, and idempotent note all unchanged | PASS |
| Scope: no scripts/setup.py or Python/config changes | Only README.md in commit bd9fe0d | PASS |
| No separate getting-started doc created | Single file commit confirmed | PASS |
| Quick Start section unchanged | git diff 3d6016c bd9fe0d: Quick Start section identical | PASS |

### Test-writer audit
Passthrough - test-writer confirmed non-implementation task, no tests applicable.

### Security
N/A - Markdown-only change.

### Verdict
PASS - confidence .97. 3 AC lines verified with line-level evidence. Existing content confirmed preserved via before/after diff. Scope boundary respected.

[[2026-03-29]] Sun 07:50
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| Next Steps subsection (3 steps) after artifacts table | README.md L59-62: 3 numbered steps (VS Code, kanban setup, agent discovery) | PASS |
| Prerequisites cross-ref in Bootstrap section | README.md L37: cross-ref with link to Prerequisites | PASS |
| Existing content preserved (heading, command, artifacts) | Commit bd9fe0d: +8 lines, no deletions. Heading, command block, artifacts list unchanged | PASS |
| Scope: no scripts/setup.py or Python/config changes | git show bd9fe0d --stat: README.md only | PASS |
| No separate getting-started doc | Single-file commit | PASS |
| Quick Start section unchanged | README.md L20-31 intact | PASS |

### Test Results
- pytest: 517 passed, 104 failed (all pre-existing RED-phase tests from other tasks), 0 regressions from #106
- ruff: All checks passed

### Architect Quality
- AC specificity: 3 precise verifiable lines with clear locations and scope boundary
- Edge case coverage: N/A (docs-only, no edge cases)
- Design direction: Minimal scope, well-contained
- AC quality score: 4/5 (specific and complete; minor naming mismatch in AC context vs actual heading)

### Reviewer Evidence
Reviewer PASS at .97 with line-level evidence for all 6 AC items. Detailed and complete.

### Commits
| Commit | Type | Files | Tasks |
|--------|------|-------|-------|
| bd9fe0d | docs | README.md | #106 |

### Confidence: .97
### Action: archive
