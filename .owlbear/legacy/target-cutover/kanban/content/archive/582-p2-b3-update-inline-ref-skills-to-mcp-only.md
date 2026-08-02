---
id: 582
title: 'P2-B3: Update inline-ref skills to MCP-only'
status: archived
priority: medium
created: 2026-04-03 16:42:36.595601+02:00
updated: 2026-04-05 15:50:57.782642+02:00
started: 2026-04-05 15:50:57.782642+02:00
completed: 2026-04-05 15:50:57.782642+02:00
tags:
- scope:skills
- ' scope:mcp'
- ' phase-2'
- ' type:build'
- docs
parent: 484
class: standard
archival_reason: completed
archival_refs: []
---

**Source:** docs/research/phase-b-mcp-only-kanban-migration.md §3a\n\nUpdate 5 skill files that have inline (non-cheatsheet) CLI references: dispatch-planning, decision-requests, kanban-md, orchestration, research-workflow.\n\nThe kanban-md SKILL.md requires special handling: its claiming protocol examples should use MCP syntax. The skill's purpose shifts from CLI reference to MCP claiming protocol reference (the mcp-kanban skill already covers tool parameters).\n\n**AC:**\n- [ ] dispatch-planning, decision-requests, orchestration, research-workflow use MCP calls\n- [ ] kanban-md SKILL.md claiming protocol uses MCP tool syntax\n- [ ] kanban-md SKILL.md cross-references mcp-kanban for full tool parameters\n- [ ] 0 kanban\\kanban-md.exe matches in these 5 files (grep verification)

[[2026-04-05]] Sun 07:48
## Research (Scope Correction)

### Architect REJECT Override

The 2026-04-04 architect REJECT and 2026-04-05 validation both excluded h-kanban-md from scope, classifying it as "deprecated, out of scope." Incorrect: the AC explicitly names h-kanban-md as one of the 5 target files.

### Independent Grep Verification

| File | kanban-md.exe refs | Status |
|------|-------------------|--------|
| w-dispatch-planning | 0 | DONE |
| w-decision-routing | 0 | DONE |
| w-orchestration | 0 | DONE |
| w-research | 0 | DONE |
| h-kanban-md | 16 | NOT DONE |

4/5 files already use MCP tool names exclusively (list_tasks, show_task, etc.). h-kanban-md still has 16 CLI refs (claiming L34-36, recipes L96-175, escaping L133-175).

### Residual Scope: h-kanban-md Only

h-kanban-md is deprecated and orphaned (0 references from active agents, skills, or instructions). AC items 2-4 unsatisfied.

### Recommendation: Option A, Thin Redirect (.85 confidence)

Per prior research (inline-ref-skills-mcp-migration.md section 3b): strip CLI content, retain title + deprecation notice + board config (statuses/priorities) + cross-ref to h-mcp-kanban. Result: ~20-line file. h-mcp-kanban covers lifecycle, body gotchas, tool params — no duplication.

T1 classification. Pre-approved documentation migration.

### AC After Option A
- AC1: 4 files use MCP calls (done)
- AC2: Claiming protocol removed; deprecation points to h-mcp-kanban lifecycle
- AC3: Cross-reference to h-mcp-kanban retained
- AC4: 0 kanban-md.exe matches across all 5 files

### Challenge Results
- Challenger: FALLBACK (agent not available in session)
- Prior challenge (inline-ref-skills-mcp-migration.md section 4): reconsider, accepted and incorporated
- Confidence: .85

Follow-up tasks: none (this task IS the implementation)
Decision requests: none (T1)

[[2026-04-05]] Sun 10:19
Releasing claim for AC refinement and architecture review append.

[[2026-04-05]] Sun 10:19
## Architecture Review

### Refined AC (binding, supersedes original)
- [ ] AC1: w-dispatch-planning, w-decision-routing, w-orchestration, w-research contain 0 kanban-md.exe refs (pre-verified done, no action needed)
- [ ] AC2: h-kanban-md/SKILL.md reduced to thin redirect (~20 lines): YAML frontmatter (keep deprecated description) + title + deprecation notice + Board Configuration section (statuses/priorities from current L126-L130) + cross-refs to h-mcp-kanban (tool params, lifecycle) and r-pipeline-protocol (claiming conventions)
- [ ] AC3: h-kanban-md/SKILL.md contains 0 kanban-md.exe references (strip L11, L34-36, L96-175 — all CLI command/recipe/escaping content)
- [ ] AC4: grep verification: 0 matches for kanban-md.exe across share/skills/{w-dispatch-planning,w-decision-routing,w-orchestration,w-research,h-kanban-md}/

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | One concern: strip CLI content from h-kanban-md, replace with thin redirect |
| Interface clarity | PASS (after refinement) | Original AC2 ambiguous ("uses MCP tool syntax" vs remove-and-redirect); refined AC specifies exact end-state |
| Dependency correctness | PASS | No dependencies; 4/5 files pre-verified clean |
| Module layering | N/A | Documentation-only task |
| TDD compliance | N/A | No Python code; docs pass-through tag added |
| KISS/YAGNI | PASS | Thin redirect is minimal approach; no content duplication with h-mcp-kanban |
| Premise challenge | PASS | h-kanban-md has 16 CLI refs and 0 active consumers — cleanup justified |
| Pattern consistency | PASS | Deprecation notice pattern already in place (L7-9) |
| Security surface | N/A | No system boundaries |
| Single domain | PASS | Documentation migration only |

### Codebase Evidence
- h-kanban-md has 0 references from active agents/skills/instructions (grep verified)
- h-mcp-kanban covers: lifecycle (Agent Lifecycle Pattern), body gotchas, compound tools, tool params
- h-mcp-kanban does NOT cover board config (statuses/priorities) — retained in h-kanban-md
- 16 CLI refs all in h-kanban-md: L11, L34-36, L96, L102, L108, L114, L120, L133, L136, L145, L148, L157, L160, L175
- config.yml at .owlbear/kanban/config.yml is source of truth for board config

### Challenge Results
- Challenger: PROCEED (0.85)
- Key findings: zero active consumers confirmed; board config retention justified (not in h-mcp-kanban); PS escaping section obsolete with MCP
- Architect response: accepted

### Verdict: APPROVE (via REFINE)
### Action Taken: Refined AC2 from ambiguous "uses MCP tool syntax" to specific thin-redirect spec. Added docs pass-through tag. Advanced to todo.

[[2026-04-05]] Sun 11:16
## Test-Writer Notes
- Non-implementation task (tagged `docs`) — no tests applicable.
- AC references only SKILL.md documentation files; architecture review explicitly notes "TDD compliance: N/A — No Python code".
- Passing through to builder.

[[2026-04-05]] Sun 12:25
## Builder Notes

### Files Changed
- `share/skills/h-kanban-md/SKILL.md` — replaced 198-line CLI reference with 18-line thin redirect

### AC Verification

| AC | Description | Result |
|----|-------------|--------|
| AC1 | w-dispatch-planning, w-decision-routing, w-orchestration, w-research have 0 kanban-md.exe refs | PASS (pre-verified, confirmed 0 each) |
| AC2 | h-kanban-md/SKILL.md reduced to thin redirect: deprecation notice + Board Configuration + cross-refs | PASS (18 lines: frontmatter + title + notice + board config) |
| AC3 | h-kanban-md/SKILL.md has 0 kanban-md.exe refs | PASS (grep Count = 0) |
| AC4 | grep: 0 kanban-md.exe across all 5 files | PASS (0, 0, 0, 0, 0) |

### Test Results
Non-implementation task (docs) — no tests applicable. Test-Writer Notes confirmed pass-through.

### Lint
No Python files changed. Ruff N/A.

### Content Retained in Thin Redirect
- YAML frontmatter with deprecated description
- Title + deprecation notice with cross-refs to h-mcp-kanban and r-pipeline-protocol
- Board Configuration section (statuses/priorities — not covered by h-mcp-kanban)

[[2026-04-05]] Sun 13:16
## Review Evidence

### Files Changed
- `share/skills/h-kanban-md/SKILL.md` — replaced 198-line CLI reference with 18-line thin redirect

### Tests
N/A — docs-only task. No Python code changed. Test-writer pass-through confirmed by architecture review.

### Lint
N/A — no Python files changed.

### AC Compliance

| AC | Spec | Evidence | Status |
|----|------|----------|--------|
| AC1 | 0 kanban-md.exe refs in 4 workflow files | `Select-String` grep returned 0 matches; MCP tool names (list_tasks, show_task, start_work, end_work) confirmed present in all 4 files | PASS |
| AC2 | h-kanban-md/SKILL.md thin redirect: deprecated frontmatter + title + deprecation notice + Board Config (statuses/priorities) + cross-refs to h-mcp-kanban and r-pipeline-protocol | File verified line-by-line: all 6 required elements present, 18 lines (within ~20 spec) | PASS |
| AC3 | 0 kanban-md.exe refs in h-kanban-md/SKILL.md | grep returned 0 matches | PASS |
| AC4 | 0 kanban-md.exe across all 5 files combined | `Select-String` across all 5 paths returned no output | PASS |

### Deductions
0

### Verdict
Confidence: .97 → PASS #582 -> docs

[[2026-04-05]] Sun 13:59
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Behavior/API change | Yes | N/A (no update needed) | h-kanban-md SKILL.md converted to thin redirect; YAML description already reads "Handbook (DEPRECATED): kanban-md CLI reference — use h-mcp-kanban instead"; `copilot-instructions.md` grep: 0 references to h-kanban-md — no update required |
| 2 | Module docstrings | No | N/A | No Python files changed |
| 3 | External attribution | No | N/A | No external patterns cited in research doc or task body |
| 4 | CLI changes | No | N/A | No CLI commands added or modified |
| 5 | Research doc | Yes | Verified | `.owlbear/research/inline-ref-skills-mcp-migration.md` exists; owning task #582 at L3; referenced in task body (scope correction section); follow-ups assessed — none needed (task IS the implementation) |

### AC Re-verification
- grep `kanban-md\.exe` across all 5 files: **0 matches** (fresh run)
- h-kanban-md/SKILL.md: 18 lines — frontmatter + title + deprecation notice + Board Configuration + cross-refs ✓

### Files Updated
- None

### Scratch Files Cleaned
- None found (no `.owlbear/scratch/582-*` files)

[[2026-04-05]] Sun 15:50
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| AC1: 0 kanban-md.exe refs in 4 workflow files | Select-String grep: 0 matches; MCP tool names confirmed in w-dispatch-planning (list_tasks, show_task, create_task) | PASS |
| AC2: h-kanban-md thin redirect (~20 lines) | File read: 18 lines — frontmatter + title + deprecation notice + board config + cross-refs to h-mcp-kanban and r-pipeline-protocol | PASS |
| AC3: 0 kanban-md.exe refs in h-kanban-md | Select-String grep: 0 matches | PASS |
| AC4: 0 kanban-md.exe across all 5 files | Select-String across all 5 paths: no output | PASS |

### Test Results
- pytest: 2878 passed, 432 failed (all pre-existing, unrelated — docs-only task, no Python files changed), 18 skipped
- ruff: All checks passed

### Architect Quality: 4/5
Original AC2 ambiguous ("uses MCP tool syntax"); researcher scope correction and architect refinement fixed this. Minor gap: h-kanban-md initially excluded from scope by architect, needed researcher override.

### Deduction Breakdown
- 4 AC lines, all with specific evidence: 0
- Lint: clean: 0
- AC quality (4/5): 0
- Reviewer section: present, detailed, .97 PASS: 0
- Full-suite in-scope failures: 0
- Uncommitted builder deliverable: noted, committed as leftover (09ce2c6)

### Confidence: .98
### Action: archive

## Commits
| Commit | Type | Files | Tasks |
|--------|------|-------|-------|
| 09ce2c6 | docs | share/skills/h-kanban-md/SKILL.md | #582 |
