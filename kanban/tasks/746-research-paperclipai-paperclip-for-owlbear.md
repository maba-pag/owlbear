---
id: 746
title: Research paperclipai/paperclip for OwlBear
status: archived
priority: nice-to-have
created: 2026-03-12T08:26:22.5627602+01:00
updated: 2026-03-12T14:59:09.7696237+01:00
started: 2026-03-12T08:39:31.450871+01:00
completed: 2026-03-12T14:59:09.7696237+01:00
tags:
    - research
class: standard
---

Research the paperclipai/paperclip repo (<https://github.com/paperclipai/paperclip>) and evaluate which features/patterns would be good additions to OwlBear.

AC:

- [ ] Clone repo to docs/scratch/research/ and analyze architecture, key features, and patterns
- [ ] Identify features relevant to OwlBear (AI-assisted workflows, content processing, etc.)
- [ ] Write trade-off analysis: effort vs value for each candidate feature
- [ ] Create follow-up kanban tasks for approved additions
- [ ] Write research doc to docs/research/paperclip-research.md

## Research

**Doc:** `docs/research/paperclip-research.md`

### Key Findings

- **Adopt:** Budget thresholds for UsageTracker (.80 confidence) — auto-warn at 80%, auto-pause at 100%
- **Adopt:** Blocked-task dedup in poll_tick (.75 confidence) — skip tasks with no new context since last attempt
- **Defer:** Wake-reason context (.65 confidence) — marginal value given channel architecture
- **Skip:** Adapter model, org chart, PARA memory, multi-tenancy, goal ancestry, config rollback (YAGNI or N/A)

### Follow-up Tasks (for user review)

```powershell --priority needed --status backlog --tags "phase-4,config,agent,scope:core"
kanban\kanban-md.exe create "Add blocked-task dedup to poll_tick" --priority important --status backlog --tags "phase-4,agent,scope:core"
```

### Attribution

Added Paperclip entry to `docs/sources/overview.md`.

[[2026-03-12]] Thu 10:51
## Architecture Review
**Verdict:** APPROVED

### AC Assessment
| AC Line | Assessment | Action |
|---------|------------|--------|
| Clone repo and analyze architecture | Complete: thorough analysis in research doc | Kept |
| Identify features relevant to OwlBear | Complete: 12 patterns evaluated with KISS/YAGNI filter | Kept |
| Write trade-off analysis | Complete: effort vs value matrix with confidence scores | Kept |
| Create follow-up kanban tasks | NOT DONE by researcher (commands listed but not run) | Fixed: created #750, #755 |
| Write research doc | Complete: docs/research/paperclip-research.md | Kept |

### Architecture Notes
- Research quality is high: structured comparison matrix, rigorous YAGNI filter, clear adopt/defer/skip decisions
- Two adoptions are architecturally sound:
  - Budget thresholds (#750): extends existing UsageTracker + OwlBearSettings; check in OwlBearAgent._record_usage()
  - Blocked-task dedup (#755): extends OrchestratorState with last_attempted_at; filters in poll_tick step 5
- Both follow module layering (no upward imports) and existing patterns (pydantic-settings, dataclass state)
- Attribution logged in docs/sources/overview.md
- No TDD needed (pure research task)

### Changes Made
- Created #750: Add budget threshold to UsageTracker (backlog, needed)
- Created #755: Add blocked-task dedup to poll_tick (backlog, important)
- Deleted duplicates #752, #753
- Moved to todo

### Dependencies
- #750 depends on existing UsageTracker + OwlBearSettings (both done)
- #755 depends on existing OrchestratorState + poll_tick (both done)

[[2026-03-12]] Thu 12:04
## Builder Notes - Research task: no code changes - All 5 AC verified (doc, tasks, attribution, trade-off, analysis) - Follow-up tasks: #750, #755 created - TDD waiver: pure research task

[[2026-03-12]] Thu 13:14
[[2026-03-12]] Thu 13:30
## Review Evidence
Pure research task  no code changes, no pytest/ruff/coverage applicable.

### AC Compliance
| AC Line | Evidence | Status |
|---------|----------|--------|
| Clone + analyze architecture | paperclip-research.md Sec 2: 9 sources, Sec 3: 12-pattern matrix | PASS |
| Identify relevant features | Sec 3: 3 adoptable (.65-.80), 6 rejected with YAGNI/N-A reasons | PASS |
| Trade-off analysis: effort vs value | Matrix with Gap/KISS columns; per-pattern LOC estimates + confidence scores | PASS |
| Create follow-up kanban tasks | #750 (budget threshold, todo) + #755 (blocked-task dedup, archived) confirmed | PASS |
| Write research doc | docs/research/paperclip-research.md exists, 150 lines, 5 sections, task ref | PASS |

Attribution: docs/sources/overview.md line 15  Paperclip entry verified.

### Verdict: PASS (.95)
Research doc is thorough, well-structured, and actionable. Follow-up tasks exist with concrete AC. Attribution logged.

[[2026-03-12]] Thu 14:28
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | copilot-instructions.md | No | N/A | Pure research task, no behavior/API change |
| 2 | Docstrings complete | No | N/A | No Python modules created or modified |
| 3 | sources/overview.md | Yes | Pass | Paperclip entry at line 15 with MIT license, patterns, and date |
| 4 | README.md | No | N/A | No CLI changes |
| 5 | Research doc linked | Yes | Pass | docs/research/paperclip-research.md exists; follow-up tasks #750, #755 created |

### Files Updated
- None

### Scratch Files Cleaned
- None (no 746-* files found in docs/scratch/)

[[2026-03-12]] Thu 14:58
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| Clone repo + analyze architecture | paperclip-research.md Sec 2: 9 sources, Sec 3: 12-pattern matrix | PASS |
| Identify relevant features | Sec 3: 3 adoptable (.65-.80), 6 rejected with KISS/YAGNI | PASS |
| Trade-off analysis: effort vs value | Matrix with Gap/KISS columns, LOC estimates, confidence | PASS |
| Create follow-up kanban tasks | #750 (budget, review), #755 (dedup, archived) exist with AC | PASS |
| Write research doc | docs/research/paperclip-research.md: 150+ lines, 5 sections, task ref | PASS |

Attribution: docs/sources/overview.md line 15 -- Paperclip entry verified.
Scratch cleanup: no 746-* files, cloned repo removed.

### Confidence: .97
### Action: archive
