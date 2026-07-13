---
id: 5
title: Copilot Memory boundary testing
status: archived
priority: medium
created: 2026-03-26 17:18:48.593531+01:00
updated: 2026-03-29 03:16:13.415476+02:00
started: 2026-03-29 03:16:08.985494+02:00
completed: 2026-03-29 03:16:08.985494+02:00
tags:
- research
- phase-1
- scope:knowledge
class: standard
archival_reason: completed
archival_refs: []
---

## Objective

Research Copilot Memory behavior and test boundary instructions to control what gets memorized.

## Acceptance Criteria

- [ ] Document how Copilot Memory works (storage, retrieval, scope)
- [ ] Test what Copilot memorizes by default during a coding session
- [ ] Write boundary instruction: 'Only memorize tool usage patterns, CLI flags, agent behavior. Do NOT memorize architecture decisions, research findings, or project-specific patterns.'
- [ ] Test boundary instruction effectiveness - verify it constrains memorization
- [ ] Document memory persistence across sessions and workspaces
- [ ] Document memory management commands (view, delete, export)
- [ ] Write findings to docs/research/copilot-memory.md
- [ ] Create follow-up tasks for any gaps discovered

## Context

Copilot Memory is the top layer of our three-layer knowledge architecture. It handles agent-centric learning (tool patterns, CLI flags, what worked/failed). We need boundary instructions to prevent it from duplicating what belongs in the general or project KB layers.

[[2026-03-28]] Sat 21:17

## Research

Research doc: docs/research/copilot-memory.md (132 lines, all AC covered).
Verified 2026-03-28 against latest VS Code settings ref (3/25/2026) and GitHub docs. Added S6 source (28-day auto-expiry, citation validation). Core findings unchanged.
Follow-ups: #11 (boundary instructions, ideation), #48 (disable setting, archived).

[[2026-03-28]] Sat 21:35

## Architecture Review

**Verdict:** APPROVE

### AC Assessment

| AC Line | Assessment | Action |
|---------|------------|--------|
| Document how Copilot Memory works | Covered in doc S3 (two systems, three scopes, ops) | Keep |
| Test default memorization | Covered in S3c (nothing by default, passive tool) | Keep |
| Write boundary instruction | S4 provides concrete instruction text | Keep |
| Test boundary instruction effectiveness | S4a documents manual test with pass/fail | Keep |
| Document persistence across sessions/workspaces | S5 table covers all scopes | Keep |
| Document management commands | S5 lists commands | Keep |
| Write findings to docs/research/copilot-memory.md | File exists (132 lines) | Keep |
| Create follow-up tasks | #11 (ideation), #48 (archived) | Keep |

### Architecture Notes

- Research-only task, no code deliverable, no TDD required
- Single domain: scope:knowledge
- Research doc follows format: sources table, analysis sections, follow-up tasks with kanban-md commands
- Two memory systems correctly distinguished (built-in vs GitHub-hosted)
- Follow-up #48 already archived (setting disabled), #11 at ideation for boundary instructions
- Scope is tight, no YAGNI concerns

### Changes Made

- No AC changes needed, all 8 lines are verifiable against doc sections

### Dependencies

- None required. Research-only task with no code deps.

[[2026-03-28]] Sat 22:52

## Test-Writer Notes

- Non-implementation task (tagged research) -- no tests applicable.
- Research doc exists: docs/research/copilot-memory.md
- Passing through to builder.

[[2026-03-29]] Sun 00:41
## Builder Notes
- Non-implementation task (research) -- no code changes needed.
- All 8 AC items verified against docs/research/copilot-memory.md (132+ lines).
- Section 3: two memory systems documented with criteria table.
- Section 3c: default memorization behavior (passive tool, nothing by default).
- Section 4: boundary instruction written with concrete do/do-not list.
- Section 4a: manual test recorded with pass/fail table and session artifact.
- Section 5: persistence table and management commands present.
- Follow-up tasks: #11 (ideation), #48 (archived) -- both created.
- Passing through to review.

[[2026-03-29]] Sun 01:37
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | .github/copilot-instructions.md | Yes | Pass | Line 65 already documents GitHub-hosted Copilot Memory disabled + rationale. No update needed. |
| 2 | Docstrings complete | No | N/A | Research-only task; no Python modules created or modified. |
| 3 | docs/sources/overview.md | Yes | Pass | Task #5 section present (lines 125-131): S1 VS Code settings, S2 VS Code cheat sheet, S6 GitHub Docs all logged. |
| 4 | README.md | No | N/A | No CLI changes introduced by this task. |
| 5 | Research doc linked | Yes | Pass | docs/research/copilot-memory.md (132 lines) exists, task body links it. Follow-ups confirmed: #11 (ideation), #48 (archived). |
| 6 | Scratch files | Yes | Pass | No docs/scratch/5-* files found. Nothing to clean. |

### Files Updated
- None

### Scratch Files Cleaned
- None

[[2026-03-29]] Sun 03:16
## Audit
### AC Verification
All 8 AC items PASS. Evidence: docs/research/copilot-memory.md (150 lines, 6 sources).
- Document how Memory works: S3 (two systems table, scopes, ops) PASS
- Test default memorization: S3c (passive tool, nothing by default) PASS
- Write boundary instruction: S4 (concrete do/do-not text) PASS
- Test boundary effectiveness: S4a (manual test, pass/fail table) PASS
- Document persistence: S5 (persistence table, 3 scopes) PASS
- Document management commands: S5 (commands listed) PASS
- Write findings doc: File exists, 150 lines, complete PASS
- Create follow-up tasks: #11 (ideation), #48 (archived) PASS

### Research Task Checks
- Doc: docs/research/copilot-memory.md
- Follow-ups: #11 references R5, #48 cites section 3b
- Sources: docs/sources/overview.md (3 entries)

### Test Results
- pytest: 435 passed, 60 failed (all pre-existing, unrelated)
- ruff: N/A (research-only)

### Quality Gaps
- Missing Review Evidence section in task body

### AC Quality Score: 4
### Confidence: .95
### Action: archive
