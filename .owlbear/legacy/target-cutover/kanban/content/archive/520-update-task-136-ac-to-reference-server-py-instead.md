---
id: 520
title: 'Update task #136 AC to reference server.py instead of tools.py'
status: archived
priority: medium
created: 2026-04-01 15:04:50.890777+02:00
updated: 2026-04-03 04:47:29.672163+02:00
started: 2026-04-03 04:45:48.531173+02:00
completed: 2026-04-03 04:45:48.531173+02:00
tags:
- phase-2
- scope:mcp
- scope:knowledge
- chore
- quality
depends_on:
- 223
class: standard
archival_reason: completed
archival_refs: []
---

## Objective
Fix stale AC in task #136 that references the deleted tools.py file, and guard #136's dependency graph against the race condition.

## Acceptance Criteria
- [ ] Task #136 AC line 4 updated: bookmark_source and list_bookmarks registered as MCP tools in packages/mcp-knowledge/src/owlbear_mcp_knowledge/server.py (not tools.py), following the v2 pattern established by #152
- [ ] Task #136 AC line 4 sub-criteria: AppContext extension updated to match server.py v2 pattern (fields initialized in app_lifespan, accessed via ctx.request_context.lifespan_context)
- [ ] Task #136 Architecture Review notes updated to reflect server.py as the registration target (current notes reference tools.py as the pattern to follow)
- [ ] Task #136 depends_on updated to include 223 (prevents executing #136 while tools.py still exists)

## Context
Merged from duplicate #370. Task #223 deletes tools.py (dead code). Task #136 AC line 4 still references tools.py as the MCP tool registration target. After #223 completes, #136's AC is impossible to satisfy. This task corrects the reference and adds a dependency guard.
See docs/research/dead-code-mcp-knowledge-tools.md section 3.3. tools.py was the v1 approach (#72); server.py is the v2 pattern (#152).
Identified by architect review of #223 (which created #520) and merged with duplicate #370.

[[2026-04-01]] Wed 20:20

## Architecture Review
**Verdict:** APPROVE (merged from duplicate #370)
**DR Verification:** N/A -- not research-driven (chore/meta task; research doc is informational)

### AC Assessment
| AC Line | Assessment | Action |
|---------|------------|--------|
| AC1: Update tools.py ref to server.py | Verifiable: file path check in #136 body | Kept from #520, tightened with v2 pattern reference |
| AC2: AppContext extension pattern | Verifiable: sub-criteria mentions lifespan pattern | Added from #370 detail, kept higher-level to avoid brittleness |
| AC3: Architecture Review notes update | Verifiable: #136 arch review section check | Kept from #520, added note that current arch review references tools.py as pattern |
| AC4: Add depends_on 223 to #136 | Verifiable: frontmatter check | Added per challenger C1 (prevents race condition) |

### Architecture Notes
- Purely kanban-editing task: modifies #136 task body and frontmatter, no application code
- v2 pattern evidence: server.py L40-81 shows AppContext dataclass with fields initialized in app_lifespan, accessed via ctx.request_context.lifespan_context
- #136 is at todo with depends_on [33, 135], both unresolved. Adding depends_on 223 is low-risk protective measure
- Tagged quality for test-writer pass-through (non-impl task)

### Changes Made
- Merged duplicate #370 into #520 (surviving task)
- Enhanced AC with AppContext pattern detail (#370's contribution) and dependency guard (challenger C1)
- Added quality tag for test-writer pass-through
- Deleted #370

### Dependencies
- Verified: depends_on [223] (in-progress, tools.py deletion)
- Added to AC: #136 should add depends_on [223] when this task executes

### Challenge Results
- Challenger: reconsider (confidence .72)
- Key challenges: (C1) #136 has no dependency on #520/223, (C2) #370 disposition unspecified, (C3) AppContext AC over-specified
- Architect response: Accepted C1 -- added AC4 requiring depends_on 223 on #136. Accepted C2 -- #370 deleted per merge procedure. Accepted C3 partially -- kept AC higher-level but retained pattern reference for builder guidance. Rejected A1/A3 (fix inline or skip pipeline) -- cross-task boundary rules prevent architect from editing #136 directly. Final confidence: .92

[[2026-04-03]] Fri 03:12
## Test-Writer Notes
- Non-implementation task (tagged quality) -- no tests applicable.
- Purely kanban-editing task: modifies #136 task body and frontmatter only.
- Passing through to builder.

[[2026-04-03]] Fri 04:15
## Review Evidence
- Task type: kanban-only (modifies #136 body + frontmatter)
- Tests: N/A
- Ruff: N/A

### Pass 1 -- CRITICAL

#### Test-Writer AC Coverage
No TestFromAC classes (non-implementation task). Step skipped.

#### Security Review
No code changes. No security issues.

#### Builder Process Quality
No Builder Notes in #520 body. Deliverables verified directly from #136.
Assessment: UNKNOWN (non-blocking for kanban-only).

### AC Compliance

| AC Line | Evidence | Status |
|---------|----------|--------|
| AC1: #136 AC line 4 references server.py not tools.py | #136 body line present: server.py, v2 pattern #152 | PASS |
| AC2: AppContext v2 pattern (app_lifespan/lifespan_context) | #136 body: bookmark_pipeline/store fields, app_lifespan, ctx.request_context.lifespan_context | PASS |
| AC3: Arch Review references server.py as target | #136 Arch Review: server.py v2 pattern; tools.py called out as v1 via #72 | PASS |
| AC4: #136 depends_on includes 223 | #136 frontmatter: depends_on [33, 135, 223] | PASS |

### Verdict: PASS
Confidence: .93

### Pass 2 -- INFORMATIONAL
- Builder omitted Builder Notes from task #520; deliverables independently verifiable.

[[2026-04-03]] Fri 04:19
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | .github/copilot-instructions.md | No | N/A | Kanban-only task; no behavior/API/convention change |
| 2 | Docstrings | No | N/A | No Python modules created or modified |
| 3 | docs/sources/overview.md | No | N/A | No external patterns adopted |
| 4 | README.md | No | N/A | No CLI changes |
| 5 | Research doc | No | N/A | Referenced doc (dead-code-mcp-knowledge-tools.md) exists and is linked from task body; this task did not produce a new research doc |

No docs impact. Pure kanban-metadata task: updated #136 body and frontmatter only.

### Files Updated
- None

### Scratch Files Cleaned
- None (no docs/scratch/520-* files found)

[[2026-04-03]] Fri 04:45
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| AC1: #136 AC references server.py | #136 AC line 4: 'registered as MCP tools in .../server.py' | PASS |
| AC2: AppContext v2 pattern | #136 AC sub-criteria: 'initialized in app_lifespan, accessed via ctx.request_context.lifespan_context' | PASS |
| AC3: Arch Review references server.py | #136 Arch Review: 'server.py (v2 pattern established by #152; tools.py was v1 approach via #72)' | PASS |
| AC4: #136 depends_on includes 223 | #136 frontmatter: depends_on [33, 135, 223] | PASS |

### Test Results
- pytest: N/A (kanban-only task, no code changes)
- ruff: N/A (no code changes)

### Architect Quality
- AC specificity: All 4 lines concrete and measurable (file path checks, frontmatter checks)
- Edge case coverage: Challenger integration added AC4 dependency guard
- Design direction: Merged #370 into #520, integrated challenger feedback; clean process
- AC quality score: 5

### Deduction breakdown: none (all AC verified with direct evidence, no code to lint/test)
### Confidence: 1.0
### Action: archive

### Notes
- #370 remains as a blocked duplicate in ideation (planner cleanup item)
- Builder omitted Builder Notes section (reviewer observation); deliverables independently verified

[[2026-04-03]] Fri 04:47
## Commits
| Commit | Type | Files | Tasks |
|--------|------|-------|-------|
| 36f3cd6 | chore | kanban/tasks/520,136,370 + activity.jsonl | #520 |
