---
id: 28
title: Update README.md for v2
status: archived
priority: medium
created: 2026-03-26 17:43:30.111972+01:00
updated: 2026-03-29 01:21:46.274496+01:00
started: 2026-03-29 01:21:41.655447+01:00
completed: 2026-03-29 01:21:41.655447+01:00
tags:
- phase-1
- scope:docs
- type:docs
depends_on:
- 7
class: standard
archival_reason: completed
archival_refs: []
---

## Objective
Rewrite README.md to describe v2 architecture and setup. Source of truth for v2 description is copilot-instructions.md (Project purpose, Tech stack, Directory structure sections).

## Acceptance Criteria
- [ ] Remove all v1 references: daemon, bearclaw CLI, approval gates, PydanticAI, Slack integration, browser automation, Qdrant
- [ ] Overview section: on-demand Copilot CLI agentic dev system (not a daemon); VS Code is the IDE; filesystem is the integration point
- [ ] Prerequisites: Python 3.12+, uv, VS Code with GitHub Copilot extension, Copilot CLI (gh copilot)
- [ ] Setup: git clone, uv sync, kanban/setup.ps1 (downloads kanban-md binary). Do NOT document owlbear setup command (task #12, not yet built)
- [ ] Directory layout table matching copilot-instructions.md (packages/, agents/, skills/, instructions/, docs/, kanban/, v1/)
- [ ] Usage: open VS Code in project root, agents auto-load from agents/, skills auto-load from skills/, MCP servers configured in workspace settings
- [ ] Testing section: uv run pytest / uv run ruff commands (adapt from current README, remove package-specific paths that don't exist yet)
- [ ] Keep concise -- quick-start guide, not full documentation. Target under 120 lines of markdown
- [ ] Preserve License section (MIT)
- [ ] Remove Inspiration section (attribution lives in docs/sources/overview.md per copilot-instructions.md)

## Context
No code dependencies. This task rewrites a single file (README.md) based on existing project metadata in copilot-instructions.md and the current directory structure. When task #12 (setup script) ships, a follow-up task should update the Setup section.

[[2026-03-28]] Sat 15:01
## Architecture Review
**Verdict:** Approve

### AC Assessment
- Remove v1 references: PASS -- explicit list of items to remove
- Overview section: REFINED -- added specifics (not a daemon, VS Code IDE, filesystem integration)
- Prerequisites: PASS -- concrete list
- Setup: REFINED -- scoped to current reality (git clone, uv sync, kanban/setup.ps1), excluded aspirational owlbear setup (#12 not built)
- Directory layout: PASS -- reference to canonical source
- Usage: PASS -- describes the VS Code agent loading flow
- Testing: PASS -- uv run commands, scoped to what exists
- Conciseness: REFINED -- added 120-line target for measurability
- License: PASS -- preserve existing
- Inspiration removal: ADDED -- attribution belongs in docs/sources/overview.md per project conventions

### Architecture Notes
Docs-only task, no code dependencies or module layering concerns. Single file (README.md), single domain (docs). Source of truth for v2 description is copilot-instructions.md. No TDD needed for docs tasks.

### Changes Made
- Rewrote AC body: tightened 7 original AC lines into 10 precise, verifiable lines
- Added explicit exclusion of owlbear setup command (depends on unbuilt #12)
- Added 120-line target for conciseness constraint
- Added Inspiration removal AC (attribution convention)

### Dependencies
- None required. Task #12 (setup script) is a future enhancement, not a blocker.

[[2026-03-28]] Sat 21:25
## Test-Writer Notes
- Non-implementation task (tagged type:docs) -- no tests applicable.
- Architect confirms: No TDD needed for docs tasks.
- Passing through to builder.

[[2026-03-28]] Sat 21:50
## Builder Notes
- Files changed: README.md
- Rewrote for v2: removed daemon, bearclaw CLI, Slack, browser automation, PydanticAI, Qdrant, Inspiration section
- Added: on-demand overview, Copilot CLI prerequisites, kanban/setup.ps1, directory layout table, Usage section
- Line count: 94 (under 120 target)
- No tests (non-implementation docs task)

[[2026-03-29]] Sun 00:37
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | copilot-instructions.md | No | N/A | README rewrite only; no behavior or API change |
| 2 | Docstrings | No | N/A | No Python modules changed |
| 3 | docs/sources/overview.md | No | N/A | No external patterns; content from internal copilot-instructions.md |
| 4 | README.md | Yes | PASS | Primary deliverable; 94 lines under 120 target; all 10 AC items verified |
| 5 | Research doc | No | N/A | No research phase |

### Files Updated
- None

### Scratch Files Cleaned
- docs/scratch/28-ac.tmp (deleted)

[[2026-03-29]] Sun 01:21
## Audit
See docs/scratch/28-auditor.md for full evidence.
Confidence: .97 Action: archive
