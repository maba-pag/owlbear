---
id: 570
title: Register owlbear-memory server in .vscode/mcp.json
status: todo
priority: needed
created: 2026-04-03T11:04:47.5649332+02:00
updated: 2026-04-04T06:46:54.5028347+02:00
tags:
    - scope:config
    - phase-2
claimed_by: fawn-staff
claimed_at: 2026-04-04T06:46:54.5028347+02:00
class: standard
---

## Acceptance Criteria

- [ ] `.vscode/mcp.json` includes `owlbear-memory` server entry (stdio, `command: uv`, `args: ["run", "python", "-m", "owlbear_mcp_memory"]` — no `--project` flag, matching existing entries)
- [ ] `scripts/setup.py` `create_mcp_config()` uses kebab-case server keys: `owlbear-kanban`, `owlbear_knowledge`, `owlbear-memory`, `owlbear-project` (fixes tool-routing bug for consumer projects)
- [ ] All affected tests updated to expect kebab-case keys:
  - `tests/test_setup_script.py::TestFromAC_McpServerNames` (6 tests asserting camelCase)
  - `tests/test_setup_script.py::TestFromAC_GithubRemoteServer::test_three_owlbear-servers_still_present_alongside_github`
  - `tests/test_scaffold_mcp_memory_524.py::TestFromAC_SetupMcp` (6 tests asserting `owlbearMemory`)
- [ ] Existing `owlbear-kanban/*` agent tool patterns resolve correctly (mcp.json key matches tool pattern prefix)

## Context

See docs/research/register-owlbear-memory-mcp.md

Key facts:
- Task #12 originally chose camelCase for setup.py, but workspace mcp.json already uses kebab-case. Agent tool patterns (`owlbear-kanban/*`) require kebab-case server keys for routing. The camelCase in setup.py is a bug affecting consumer projects.
- Workspace `.vscode/mcp.json` is Copilot-ignored — use terminal for verification (`Get-Content .vscode/mcp.json`)
- setup.py `create_mcp_config()` has early return if mcp.json exists — changes only affect new consumer projects
- #571 is exact duplicate — planner should archive it

## Architecture Notes

- Follow existing workspace mcp.json pattern exactly (no `--project` flag in args)
- The naming fix touches all 4 server keys in the same dict literal — this is one atomic change, not scope creep
- setup.py docstring already says "five MCP server entries" — no docstring change needed for server count

[[2026-04-03]] Fri 12:14
## Architecture Review
**Verdict:** APPROVED
**DR Verification:** N/A — T1 autonomous (config fix + bug fix), not research-driven T3

### AC Assessment
| AC Line | Assessment | Action |
|---------|------------|--------|
| mcp.json owlbear-memory entry | Clear, verifiable, pattern specified | Kept |
| setup.py kebab-case keys | Clear, verifiable, all 4 keys named | Kept |
| Test updates | Challenger found missing tests; expanded to 3 test locations | Refined |
| Tool pattern resolution | Verifiable by running tests | Kept |

### Architecture Notes
Task #12 originally chose camelCase for setup.py, but workspace mcp.json already uses kebab-case and agent tool patterns require kebab-case for routing. This is a bug fix, not a convention change. No DR required.
Scope is atomic: one dict literal rename in setup.py + one mcp.json entry + test updates in the same test classes.
Duplicate #571 exists with stale architect claim — planner should archive it.

### Changes Made
- Rewrote AC with precise test surface (3 locations, not 1)
- Added architecture notes about workspace vs consumer mcp.json args difference
- Added note about Copilot-ignored verification path

### Dependencies
- None required. owlbear-memory package already exists (packages/mcp-memory/).

### Challenge Results
- Challenger: reconsider (confidence .55)
- Key challenges: incomplete test surface (critical), scope creep (moderate), prior AC contradiction (task #12)
- Architect response: accepted test-surface expansion (added 2 missing test locations). Rebutted split proposal — all changes are in the same function's dict literal, splitting creates unnecessary task overhead. Rebutted prior-AC concern — camelCase was a bug (tool routing requires matching), not a deliberate convention.
- Final confidence in verdict: .90

[[2026-04-04]] Sat — Builder REJECT
## Builder Notes

**REJECT → todo — conflicting `TestFromAC_*` tests; test-writer must update old test**

### Conflict

Implementing the AC (removing `--project` flag per `TestFromAC_McpServerNames::test_mcp_server_args_have_no_project_flag`) **breaks** the previously-passing `TestFromAC_McpConfig::test_mcp_server_args_reference_relative_path_to_owlbear`. Builder cannot modify either `TestFromAC_*` class.

| Test | Class | Requires |
|------|-------|---------|
| `test_mcp_server_args_have_no_project_flag` | `TestFromAC_McpServerNames` (#570) | NO `--project` flag in args |
| `test_mcp_server_args_reference_relative_path_to_owlbear` | `TestFromAC_McpConfig` (older task) | At least one arg with `..` |

**Old args**: `["run", "--project", "../owlbear", "-m", "owlbear_mcp_kanban"]` — `../owlbear` has `..` → old test passes
**New args**: `["run", "python", "-m", "owlbear_mcp_kanban"]` — no `..` → old test fails

### Required fix (test-writer)

Remove or update `tests/test_setup_script.py::TestFromAC_McpConfig::test_mcp_server_args_reference_relative_path_to_owlbear` — it tests the old `--project` behavior that the new AC explicitly removes.

### Pre-existing failures (not this task's concern)
- `TestFromAC_VscodeSettings::test_agent_files_locations_has_root_path_only`
- `TestFromAC_VscodeSettings::test_agent_skills_locations_has_root_path`
- `TestFromAC_VscodeSettings::test_instructions_locations_has_root_path_only`

### Progress in working tree (apply once old test is resolved)
- `scripts/setup.py`: kebab-case keys, `--project` removed — `TestFromAC_McpServerNames` (6) PASS
- `.vscode/mcp.json`: `owlbear-memory` entry added — `TestFromAC_SetupMcp` (6) PASS
