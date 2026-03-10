---
id: 597
title: 'Research: raphaelmansuy/edgequake'
status: archived
priority: important
created: 2026-03-05T23:52:17.6488934+01:00
updated: 2026-03-10T21:56:54.1291565+01:00
started: 2026-03-06T22:55:16.8271487+01:00
completed: 2026-03-10T21:56:54.1291565+01:00
tags:
    - research
    - phase-research
    - scope:copilot
parent: 583
claimed_by: builder
claimed_at: 2026-03-10T21:13:34.7527401+01:00
class: standard
---

**Source:** https://github.com/raphaelmansuy/edgequake
Analyze for workflow efficiencies, developer tooling patterns, and automation ideas.

**Acceptance Criteria:**
1. Clone repo to `docs/scratch/research/edgequake/` for analysis (gitignored  ephemeral).
2. Identify architectural patterns, prompts, MCP server ideas, or code fragments reusable in OwlBear. Focus areas: agent orchestration, tool registration, CLI patterns, prompt engineering.
3. Document findings in `docs/research/edgequake-research.md` following research-docs guardrails. End with a **Follow-up Tasks** section listing concrete `kanban-md create` commands (each with AC).
4. Update `docs/sources/overview.md` with URL, license, what was studied, where used, and date.
5. Create follow-up kanban tasks for any actionable patterns discovered (at `backlog` status).
6. Delete `docs/scratch/research/edgequake/` after research is complete.

[[2026-03-10]] Tue 17:38
## Architecture Review
**Verdict:** APPROVED

### AC Assessment
| AC Line | Assessment | Action |
|---------|------------|--------|
| 1. Clone to docs/scratch/research/edgequake/ | Corrected from docs/research/  clones are ephemeral (gitignored) | Fixed |
| 2. Identify patterns (orchestration, tools, CLI, prompts) | Focus areas added for specificity | Fixed |
| 3. Document in docs/research/edgequake-research.md | Was vague (''task body or linked doc'')  now explicit path + research-docs guardrails | Fixed |
| 4. Update docs/sources/overview.md | Corrected from docs/sources.md | Fixed |
| 5. Create follow-up tasks at backlog | Added status requirement | Fixed |
| 6. Delete cloned repo after research | Was missing entirely  added per copilot-instructions | Added |

### Architecture Notes
Pure research task  no code changes, no module impacts. Single domain (research). No TDD compliance needed.
Corrected 5 issues from the original batch-created task template:
- Wrong clone path (docs/research/ -> docs/scratch/research/) per copilot-instructions file placement rules
- Wrong sources file (docs/sources.md -> docs/sources/overview.md) per attribution section
- Missing cleanup step for ephemeral clone
- Vague output location now pinned to docs/research/edgequake-research.md
- Follow-up tasks now required at backlog status with AC per research-docs guardrails

### Changes Made
- `kanban-md edit 597 --body` with corrected AC (6 verifiable criteria)
- `kanban-md move 597 todo`

### Dependencies
- None  standalone research task

[[2026-03-10]] Tue 17:54
## Test-Writer Notes
Non-implementation task (tagged research) - no tests applicable. Passing through to builder.

[[2026-03-10]] Tue 19:54
## Builder Notes
- Files changed: docs/research/edgequake-research.md (updated with MCP/tooling analysis), docs/sources/overview.md (added EdgeQuake entry)
- AC1: Cloned repo to docs/scratch/research/edgequake/ (partial clone, 7743 files)
- AC2: Identified 8 patterns; 3 applicable (MCP tool registration, orphaned task recovery, MCP prompt templates)
- AC3: Updated docs/research/edgequake-research.md with new S6 section covering MCP server, tool registration, prompt templates, auto-discovery, models.toml, doc-traceability, startup recovery, smart mocks
- AC4: Updated docs/sources/overview.md with EdgeQuake entry
- AC5: Created 3 follow-up tasks: #732 (LLM cost tracking), #733 (cooperative cancellation), #734 (gleaning bookmark)
- AC6: Deleted docs/scratch/research/edgequake/ after analysis

[[2026-03-10]] Tue 20:36
## Review Evidence

### Test Results
- N/A  research task, no code changes

### Lint Results
- N/A  research task, no code changes

### Coverage
- N/A  research task

### Test Quality
- N/A  research task (test-writer correctly passed through)

### Security Review
- No security issues  no code changes, only documentation files

### AC Compliance

| AC Line | Evidence | Status |
|---------|----------|--------|
| 1. Clone to docs/scratch/research/edgequake/ | Builder notes confirm 7743-file clone; Test-Path confirms deleted | PASS |
| 2. Identify patterns (orchestration, tools, CLI, prompts) | Research doc S3.2: 8 patterns evaluated; S6: 8 MCP/tooling findings | PASS |
| 3. Document in docs/research/edgequake-research.md | File exists, has owning-task ref, Follow-up Tasks with kanban-md commands | PASS |
| 4. Update docs/sources/overview.md | Entry present  NOTE: duplicate sections at lines 1123 and 1357 (cosmetic, not blocking) | PASS (minor) |
| 5. Create follow-up tasks at backlog | #732 (cost tracking), #733 (cancellation), #734 (gleaning)  all at backlog with AC | PASS |
| 6. Delete clone after research | Test-Path docs/scratch/research/edgequake/ = False | PASS |

### Research Quality
- 10 sources studied with relevance scores
- 16 patterns evaluated (8 initial + 8 in S6 update)
- Clear applicability ratings with confidence scores
- 3 actionable follow-up tasks with proper AC and back-references
- Non-applicable patterns explicitly listed (S6.8)

### Notes
- Minor: docs/sources/overview.md has two EdgeQuake sections (lines 1123 and 1357)  builder appended instead of consolidating. Not blocking but should be cleaned up in a future pass.

### Verdict: PASS (.90)

### Action Taken
- kanban move 597 docs

[[2026-03-10]] Tue 21:13
## Docs Gate

### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | copilot-instructions.md | No | N/A | Research task  no behavior/API/convention change |
| 2 | Docstrings | No | N/A | No Python modules created or changed |
| 3 | sources/overview.md | Yes | Updated | Consolidated duplicate EdgeQuake sections (lines 1123 and 1357) into single section; merged MCP/tooling findings into one row |
| 4 | README.md | No | N/A | No CLI changes |
| 5 | Research doc linked | Yes | Pass | docs/research/edgequake-research.md exists with owning-task ref #597; 3 follow-up tasks created (#732, #733, #734) at backlog |

### Files Updated
- docs/sources/overview.md (consolidated duplicate EdgeQuake sections)

### Scratch Files Cleaned
- None found for task 597
