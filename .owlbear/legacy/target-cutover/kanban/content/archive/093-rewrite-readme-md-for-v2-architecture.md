---
id: 93
title: Rewrite README.md for v2 architecture
status: archived
priority: medium
created: 2026-03-28 01:48:37.047642+01:00
updated: 2026-03-29 16:17:50.694915+02:00
started: 2026-03-29 16:17:50.371168+02:00
completed: 2026-03-29 16:17:50.371168+02:00
tags:
- phase-1
- scope:docs
- type:docs
depends_on:
- 28
class: standard
archival_reason: completed
archival_refs: []
---

Rewrite README.md per docs/research/readme-v2-rewrite.md. Use the recommended structure: title, overview, prerequisites, quick start, directory layout, how it works, development, license. Target ~60 lines.

AC:
- [ ] Title: On-demand AI development system built on GitHub Copilot
- [ ] Overview: 2-3 sentences, no v1 references
- [ ] Prerequisites: Python 3.12+, uv, VS Code + Copilot, Copilot CLI
- [ ] Quick Start: git clone, uv sync, kanban setup, open VS Code
- [ ] Directory layout table matching copilot-instructions.md
- [ ] How It Works: agents, skills, MCP servers, orchestrator
- [ ] Development: uv sync, pytest, ruff (keep existing commands)
- [ ] No v1 references: no daemon, bearclaw, PydanticAI, Slack, approval gates, browser automation, Qdrant
- [ ] Total length under 80 lines
- [ ] License section preserved

[[2026-03-29]] Sun 12:51
## Research
Research validated. Two existing docs cover this task:
- docs/research/readme-v2-rewrite.md (original structure, from #28)
- docs/research/readme-trim-assessment.md (gap analysis for #93)

Key finding: 9/10 AC items already met. Only gap is line count (104 vs 80 target). The 'Adding MCP Servers' section (lines 30-58, ~29 lines) is not in the recommended structure and pushes the README over budget. Removing it and replacing with a one-line pointer to scripts/setup.py brings the count to ~75 lines.

Architect note: This is a trim task, not a rewrite. Consider narrowing AC to: remove 'Adding MCP Servers' section, compress Quick Start, target <=80 lines.

[[2026-03-29]] Sun 14:17
## Architecture Review
**Verdict:** Approve

### AC Assessment
| AC Line | Assessment | Action |
|---------|------------|--------|
| Title: On-demand AI dev system | Already met (#28) | Removed from AC (verified) |
| Overview: 2-3 sentences | Already met (#28) | Removed from AC (verified) |
| Prerequisites | Already met (#28) | Removed from AC (verified) |
| Quick Start | Partially met (13 lines vs 10 target) | Kept: compress to <=10 lines |
| Directory layout table | Already met (#28) | Removed from AC (verified) |
| How It Works | Already met (#28) | Removed from AC (verified) |
| Development section | Already met (#28) | Removed from AC (verified) |
| No v1 references | Already met (#28) | Kept as guard rail |
| Total length under 80 lines | NOT MET (104 lines) | Refined: remove MCP section, <=80 |
| License preserved | Already met (#28) | Removed from AC (verified) |

### Architecture Notes
Docs-only trim task. No code, no module layering, no security surface.
The 'Adding MCP Servers' section (29 lines) is not in the recommended
README structure per docs/research/readme-v2-rewrite.md. Removing it
and adding a one-line pointer yields ~77 lines, under budget. The v1/
directory entry in the layout table describes a real directory and is
not a restricted v1 term per AC.

No TDD needed (type:docs task).

### Changes Made
- Rewrote AC body: narrowed from 10 rewrite items to 6 trim items
- Preserved research context and doc pointers in body

### Dependencies
- #28 (archived): prerequisite rewrite complete

[[2026-03-29]] Sun 15:03
## Test-Writer Notes

[[2026-03-29]] Sun 15:03
- Non-implementation task (tagged type:docs) -- no tests applicable.

[[2026-03-29]] Sun 15:03
- Passing through to builder.

[[2026-03-29]] Sun 15:42
## Builder Notes
- Files changed: README.md
- Change: removed 'Adding MCP Servers' section (35 lines), compressed Quick Start to single prose line
- Result: 104 lines reduced to 70 lines (under 80 AC target)
- No tests (type:docs task, pass-through from test-writer)
- Lint: N/A (markdown only)
- Commit: 1ee0865

[[2026-03-29]] Sun 16:02
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | .github/copilot-instructions.md | No | N/A | Docs-only trim task, no behavior or API change |
| 2 | Docstrings complete | No | N/A | No Python modules created or modified |
| 3 | sources/overview.md | No | N/A | No external patterns used; research was internal analysis |
| 4 | README.md updated | Yes | Pass | Builder commit 1ee0865: removed MCP section, Quick Start compressed; 104 to 70 lines (under 80 AC target) |
| 5 | Research docs linked | Yes | Pass | readme-v2-rewrite.md and readme-trim-assessment.md exist and referenced in task body |
| 6 | AC verified | Yes | Pass | Quick Start compressed, no v1 refs, 70 lines under 80, license preserved |

### Files Updated
- None (README.md updated by builder in commit 1ee0865)

### Scratch Files Cleaned
- None (no docs/scratch/93-* files found)
