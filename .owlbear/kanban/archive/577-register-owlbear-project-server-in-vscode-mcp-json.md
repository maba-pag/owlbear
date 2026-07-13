---
id: 577
title: Register owlbear-project server in .vscode/mcp.json
status: archived
priority: medium
created: 2026-04-03 11:38:43.962885+02:00
updated: 2026-04-03 18:33:26.744866+02:00
started: 2026-04-03 18:33:03.518798+02:00
completed: 2026-04-03 18:33:03.518798+02:00
tags:
- scope:config
- phase-2
- type:config
class: standard
archival_reason: completed
archival_refs: []
---

## Acceptance Criteria

- [ ] `.vscode/mcp.json` includes `owlbear-project` server entry with `type: stdio`, `command: uv`, `args: [run, python, -m, owlbear_mcp_project]` â€” no `--project` flag, no `env` block (matching existing workspace entries)
- [ ] Entry key is `owlbear-project` (kebab-case, matching workspace convention)

## Context

See docs/research/register-mcp-project-server.md

- Workspace `.vscode/mcp.json` is Copilot-ignored â€” verify via terminal: `Get-Content .vscode/mcp.json`
- Package entry point: `packages/mcp-project/src/owlbear_mcp_project/__main__.py`
- #578 is exact duplicate (ideation) â€” planner should archive it

[[2026-04-03]] Fri 12:47
## Architecture Review
**Verdict:** APPROVED
**DR Verification:** N/A - T1 autonomous (additive config wiring), not research-driven T3

### AC Assessment

- mcp.json owlbear-project entry: Original vague; refined with explicit type/command/args, no-env, no-project constraints
- Entry key kebab-case: New line; prevents camelCase confusion from setup.py consumer pattern

### Architecture Notes
Follows exact pattern of existing entries (owlbear-kanban, owlbear_knowledge): bare stdio, uv run, no env block.
Entry point confirmed: packages/mcp-project/src/owlbear_mcp_project/__main__.py calls mcp.run().
project_info works: owlbear-project.json at root has correct schema (type: bare, owlbear-path: .).
project_list returns empty regardless of OWLBEAR_ROOT (no data/projects/ in owlbear workspace) - not a regression.
#578 (ideation) is exact duplicate - planner should archive.
Tagged type:config for test-writer pass-through.

### Changes Made
- Rewrote AC with precise entry format
- Added type:config tag
- Added architecture notes

### Dependencies
- None. Package and skill already exist.

### Challenge Results
- Challenger: reconsider (confidence .72)
- Key challenges: OWLBEAR_ROOT defaults to Path(..) affecting project_list; naming inconsistency with setup-guide.md; env block question
- Architect response: Rebutted OWLBEAR_ROOT - data/projects/ absent, project_list empty either way. Rebutted env block - existing entries have none. Naming fix tracked by #570 (out of scope).
- Confidence in verdict: .90

[[2026-04-03]] Fri 14:35
## Test-Writer Notes
- Non-implementation task (tagged type:config) - no tests applicable.
- AC deliverables: .vscode/mcp.json (owlbear-project server entry)
- Passing through to builder.

[[2026-04-03]] Fri 17:12
## Review Evidence

### Changed Files
- .vscode/mcp.json (unstaged, type:config)

### Tests
type:config task; test-writer passed through; no TestFromAC classes â€” conditional skip.

### Lint
JSON config change; no Python code modified; ruff not applicable.

### Security (6.1)
No secrets or credentials. Static JSON config, no user input, no new deps. Clean.

### AC Compliance

AC1: owlbear-project entry with type stdio, command uv, args [run python -m owlbear_mcp_project], no env block, no project flag
Evidence: git diff HEAD confirms exact structure matching owlbear-kanban/owlbear_knowledge
Status: PASS

AC2: Entry key owlbear-project (kebab-case)
Evidence: git diff confirms key owlbear-project
Status: PASS

### Entry Point
packages/mcp-project/src/owlbear_mcp_project/__main__.py exists and calls mcp.run() - confirmed.

### Notes
Builder left no Builder Notes section (minor process gap, not blocking).
Surgical 10-line addition. Exact pattern match.

### Verdict: PASS - confidence .97

[[2026-04-03]] Fri 17:28
Docs Gate complete - no docs impact

[[2026-04-03]] Fri 17:28
## Docs Gate
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | copilot-instructions.md | No | N/A | Already lists mcp-project as one of 4 custom servers; task wired mcp.json to match |
| 2 | Docstrings | No | N/A | type:config task - no Python changed |
| 3 | sources/overview.md | No | N/A | VS Code MCP docs already logged under #570 |
| 4 | README.md | No | N/A | No CLI changes |
| 5 | Research doc | Yes | Pass | docs/research/register-mcp-project-server.md exists, linked in task body; follow-ups confirmed |
Files Updated: None. Scratch Files: None.

[[2026-04-03]] Fri 18:32
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| mcp.json owlbear-project entry (type:stdio, uv, args, no --project, no env) | Verified via Get-Content: exact match to owlbear-kanban/owlbear_knowledge pattern | PASS |
| Entry key owlbear-project (kebab-case) | Confirmed in mcp.json diff | PASS |

### Test Results
- pytest: 2847 passed, 237 failed (all failures from other tasks RED-phase TDD or pre-existing), 0 failures in #577 scope
- ruff: N/A (type:config, no Python changes)

### Reviewer Evidence
Present and thorough (.97). Verified exact diff structure, entry point, AC compliance. PASS verdict.

### Architect Quality
- AC specificity: Excellent. Exact format constraints (type, command, args, no-env, no-project).
- Edge case coverage: Adequate for config wiring task.
- Design direction: Pattern match to existing entries was clear and productive.
- AC quality score: 5/5

### Upstream Commit Gap
Builder did not commit .vscode/mcp.json. Committed by auditor as orphaned deliverable: e73333a.

### Deduction breakdown
- No deductions. All AC verified with specific evidence, reviewer evidence present, AC quality 5, no task-scoped failures.
### Confidence: 1.0
### Action: archive

[[2026-04-03]] Fri 18:32
## Commits
| Commit | Type | Files | Tasks |
|--------|------|-------|-------|
| e73333a | chore | .vscode/mcp.json | #577 |
