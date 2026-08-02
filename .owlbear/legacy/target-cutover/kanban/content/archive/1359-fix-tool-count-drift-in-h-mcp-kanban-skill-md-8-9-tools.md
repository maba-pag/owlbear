---
id: 1359
title: Fix tool count drift in h-mcp-kanban SKILL.md (8 → 9 tools)
status: archived
priority: medium
created: 2026-05-05T08:55:03.657866+00:00
updated: 2026-05-05T11:01:59.400419+00:00
tags:
- docs
- mcp-kanban
parent: 1349
depends_on: []
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

## Context

`share/skills/h-mcp-kanban/SKILL.md` description says "8 tools" but the actual server exposes 9 (create_dr was added as the 9th). Flagged as informational drift in two consecutive review cycles for #1349.

## Acceptance Criteria

- [ ] SKILL.md description updated from "8 tools" to "9 tools"
- [ ] Tool listing in SKILL.md includes `create_dr` entry
- [ ] No other content drift between SKILL.md and serve/mcp-kanban/README.md

## Notes

- SKILL.md is agent-executable → architect scope, not doc-writer
- Parent: #1349


## Builder Guidance

Additional drift discovered during review: SKILL.md uses `id: int` for tool parameters (`show_task`, `edit_task`, `move_task`, `start_work`, `end_work`) but the MCP schema accepts `str | int` — align with README's `str | int` signatures.
[[2026-05-05]]
## Architecture Review

### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Single file update to fix documentation drift |
| Interface clarity | PASS | AC specifies exact changes (count, entry, drift check) |
| Dependency correctness | PASS | No dependencies needed |
| Module layering | N/A | Docs-only change |
| TDD compliance | PASS | Tagged `docs` — pass-through |
| KISS/YAGNI | PASS | Minimal mechanical fix |
| Premise challenge | PASS | Drift confirmed — SKILL.md says 8, README says 9, `create_dr` missing |
| Pattern consistency | PASS | Follows existing SKILL.md table format |
| Security surface | N/A | No system boundaries affected |
| Single domain | PASS | mcp-kanban docs domain only |

### Challenge Results
- Challenger: SKIPPED — all td:0
- Architect response: N/A

### Test Depth
- AC1: SKILL.md description "8" → "9" (td:0)
- AC2: Add `create_dr` entry to tool table (td:0)
- AC3: No other content drift (td:0)
- Max depth: 0
- Test-writer: SKIP

### Additional Drift Found
SKILL.md uses `id: int` for 5 tool signatures; README correctly uses `id: str | int`. Noted in Builder Guidance.

### Verdict: APPROVE
### Action Taken: Advanced to todo. Builder guidance appended for discovered type-parameter drift.
[[2026-05-05]]
## Test-Writer Notes
- Non-implementation task (tagged `docs`) — no tests applicable.
- All AC lines are (td:0) per architect review: SKILL.md description update, tool entry addition, drift check.
- Passing through to builder.
[[2026-05-05]]
## Builder Notes
- Implementation: updated share/skills/h-mcp-kanban/SKILL.md to align with serve/mcp-kanban/README.md.
- Fixes applied:
  - Frontmatter description updated from 8 tools to 9 tools.
  - Tool summary count updated to 9.
  - Added missing create_dr signature row.
  - Aligned id parameter signatures to str | int for show_task, edit_task, move_task, start_work, and end_work.
- Tests: N/A for td:0 docs-only task (no task-scoped tests).
- Coverage: N/A for docs-only change.
- Lint: markdownlint clean on share/skills/h-mcp-kanban/SKILL.md via quality-runner.
- Commit: 1fa39758 (docs: align h-mcp-kanban tool signatures and count (#1359, builder)).

### Post-task Reflection
- The primary risk was partial drift: fixing the table but missing frontmatter text; a second targeted check caught this.
- Docs-only tasks still benefit from explicit quality evidence; using quality-runner with markdownlint gave a clean, auditable gate.
- Keeping the diff to a single file prevented scope creep despite nearby protocol content that could have been refactored.
[[2026-05-05]]
## Review Evidence
### Test Results
- Review-scoped test execution not applicable. All AC lines are td:0 and the task changes only markdown content in share/skills/h-mcp-kanban/SKILL.md.

### Lint Results
- Review-scoped quality-runner lint was skipped for this td:0 docs-only review; verdict is based on direct artifact inspection rather than builder self-report.

### Coverage
- N/A for td:0 docs-only task.

### Source Scope
- Builder commit 1fa39758 is present in .git/logs/HEAD:1965 and .git/logs/refs/heads/dev:1806.
- Changed-file scope reconstructed from builder notes and direct inspection: share/skills/h-mcp-kanban/SKILL.md.

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---|---|---|---|
| SKILL.md description updated from "8 tools" to "9 tools" | share/skills/h-mcp-kanban/SKILL.md:3 and :17 now state 9 tools; serve/mcp-kanban/README.md:19 states 9 tools; workspace search found no remaining `8 tools` in the skill | N/A td:0 | PASS |
| Tool listing in SKILL.md includes create_dr entry | share/skills/h-mcp-kanban/SKILL.md:30 and serve/mcp-kanban/README.md:31 both list `create_dr(task_id: str, agent: str, request_type: str, body: str)` | N/A td:0 | PASS |
| No other content drift between SKILL.md and serve/mcp-kanban/README.md | Corrected id signatures align across show_task/edit_task/move_task/start_work/end_work at share/skills/h-mcp-kanban/SKILL.md:23,26,27,28,29 and serve/mcp-kanban/README.md:24,27,28,29,30. Shared contract sections also align at share/skills/h-mcp-kanban/SKILL.md:39,72,88,117 and serve/mcp-kanban/README.md:33,56,60,75. Workspace search found no remaining `id: int` in the skill. | N/A td:0 | PASS |

### Pass 1 Checks
- TestFromAC audit: not applicable; no TestFromAC classes for td:0 task.
- Security review: docs-only markdown change; no executable surface, credentials, or input-handling changes observed.
- Data safety: not applicable; no runtime behavior changes.
- Loop detection: first review cycle for task 1359; no prior Review Evidence section found in the task body.

### Deductions
- -0.03: Dirty-tree contamination and review-scoped lint re-execution were not independently verifiable from the available tool surface for this td:0 docs-only task.
- -0.02: start_work returned task content successfully, but the task projection still showed claimed: false; ownership state could not be independently confirmed.

### Verdict
- PASS. Confidence: 0.95

### Action
- Advance to docs.
[[2026-05-05]]
## Docs Gate

### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Descriptive prose docs | No | N/A | Changed file is share/skills/h-mcp-kanban/SKILL.md (OUT scope). No IN-scope prose docs reference this skill by name. |
| 2 | Module docstrings | No | N/A | No Python modules created or modified. |
| 3 | External attribution | No | N/A | Task fixes internal drift; no external patterns cited. |
| 4 | Research doc | No | N/A | No research doc produced. |
| 5 | Diagram maintenance (describes match) | No | N/A | share/diagrams/project-overview.excalidraw describes share/**, which covers the changed file — but the only changed file is OUT-of-scope (SKILL.md). Step 2 preamble: all changed files OUT-scope → no-impact. Footer update not triggered. |
| 6 | Explicit diagram creation | No | N/A | No explicit diagram creation request in task body. |
| 7 | Deletion detection | No | N/A | No deleted files. No orphaned IN-scope docs detected. |

### Scope Classification
| File | Scope | Action |
|------|-------|--------|
| share/skills/h-mcp-kanban/SKILL.md | OUT (agent-executable SKILL.md) | N/A — no doc-writer edits |

**No docs impact.** All changed files are OUT-of-scope. Task notes confirm: "SKILL.md is agent-executable → architect scope, not doc-writer."

### Files Updated
- None

### Child Tasks Created
- None

### Scratch Files Cleaned
- None (no 1359-* scratch files found)
[[2026-05-05]]
## Audit\n### AC Verification\n| AC Line | Evidence | Status |\n|---------|----------|--------|\n| SKILL.md description updated from "8 tools" to "9 tools" | share/skills/h-mcp-kanban/SKILL.md:3 frontmatter says "9 tools"; :17 says "Exactly 9 tools are exposed" | PASS |\n| Tool listing includes create_dr entry | share/skills/h-mcp-kanban/SKILL.md:30 lists create_dr(task_id: str, agent: str, request_type: str, body: str) | PASS |\n| No other content drift between SKILL.md and README.md | All id params show str | int across show_task/edit_task/move_task/start_work/end_work; no remaining id: int found | PASS |\n\n### Test Results\n- pytest: 4534 passed, 217 failed (all failures in unrelated task scopes, none in changed file scope)\n- ruff: 13 violations (all in .py files unrelated to this docs-only .md change)\n- Task-scope impact: zero; markdown skill file cannot introduce runtime regressions\n\n### Architect Quality: 4/5\nAC was specific and verifiable. Minor gap: type drift (id: int vs str | int) was discovered during the arch review cycle itself rather than in the initial AC, but was caught and added to Builder Guidance before implementation. Good recovery.\n\n### Deduction Breakdown\n- AC lines without evidence: 0 (all 3 verified directly)\n- Lint violations in scope: 0\n- AC quality: 4/5 (above threshold, no deduction)\n- Reviewer evidence: present and detailed (no deduction)\n- Full-suite failures in task scope: 0\n\n### Confidence: 0.98\n### Action: archive