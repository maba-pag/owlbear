---
id: 570
title: Register owlbear-memory server in .vscode/mcp.json
status: archived
priority: medium
created: 2026-04-03 11:04:47.564933+02:00
updated: 2026-04-05 04:18:26.595617+02:00
started: 2026-04-05 04:18:26.595617+02:00
completed: 2026-04-05 04:18:26.595617+02:00
tags:
- scope:config
- phase-2
class: standard
archival_reason: completed
archival_refs: []
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

[[2026-04-04]] Sat 23:47
## Builder Notes

**Files changed:** `scripts/setup.py`, `.vscode/mcp.json`

**Test results:** 18 TestFromAC tests PASSED, ruff clean. 3 pre-existing `TestFromAC_VscodeSettings` failures unchanged (not this task's concern — noted by previous builder).

**Lint:** ruff: All checks passed

**Evidence:**
- `scripts/setup.py` `create_mcp_config()`: renamed camelCase keys → kebab-case (`owlbear-kanban`, `owlbear-knowledge`, `owlbear-memory`, `owlbear-project`), removed `--project` flag + `rel` computation, args now `["run", "python", "-m", module]`
- `.vscode/mcp.json`: added `owlbear-memory` stdio entry matching existing pattern
- `_owlbear_dir` rename to suppress ARG001 (param now unused after removal of `--project` path)

**Commit:** `7c4acb0` — fix: kebab-case MCP server keys + add owlbear-memory to mcp.json (#570, builder)

[[2026-04-05]] Sun 00:06
## Builder Notes

**Files changed:** `scripts/setup.py`, `.vscode/mcp.json` (committed `7c4acb0` by previous builder — no new changes needed)

**Test results:** 18 TestFromAC tests PASSED
- `TestFromAC_McpServerNames` (6): all PASSED
- `TestFromAC_GithubRemoteServer::test_three_owlbear-servers_still_present_alongside_github`: PASSED (within 62-test suites)
- `TestFromAC_SetupMcp` (6): all PASSED

**Pre-existing failures (not this task):** 3 `TestFromAC_VscodeSettings` failures — documented by previous builder, unrelated to #570 scope.

**Lint:** `ruff check scripts/setup.py` → All checks passed

**Evidence summary:**
- `scripts/setup.py` `create_mcp_config()`: camelCase → kebab-case keys (`owlbear-kanban`, `owlbear-knowledge`, `owlbear-memory`, `owlbear-project`), `--project` flag removed, args now `["run", "python", "-m", module]`
- `.vscode/mcp.json`: `owlbear-memory` stdio entry added, matching existing pattern
- Commit `7c4acb0` implements all AC changes; this builder verified correctness and advanced the task.

[[2026-04-05]] Sun 01:32
## Review Evidence

### Test Results

| Suite | Tests | Result |
|-------|-------|--------|
| `TestFromAC_McpServerNames` (6 tests) | All 6 | PASS |
| `TestFromAC_GitHubMcpServer::test_three_owlbear_servers_still_present_alongside_github` | 1 | PASS |
| `TestFromAC_SetupMcp` (6 tests) | All 6 | PASS |
| Pre-existing failures (VscodeSettings ×3, DataAndInstructions ×1, PathDetection ×1) | 5 | FAIL — documented pre-existing, not #570 scope |

**Total AC-relevant tests: 13 passed, 0 failed.**

### Lint

`uv run ruff check scripts/setup.py tests/test_setup_script.py tests/test_scaffold_mcp_memory_524.py` → All checks passed.

### Changed Files (commit 7c4acb0)

- `scripts/setup.py` — `create_mcp_config()` signature: `owlbear_dir` → `_owlbear_dir` (unused param suppressed). Four server keys renamed camelCase → kebab-case. `--project` flag + `rel` computation removed. Args now `["run", "python", "-m", module]`.
- `.vscode/mcp.json` — `owlbear-memory` stdio entry added matching existing pattern.

Builder touched **no test files**. Test-writer commit `26e9ef7` performed the test changes (not the builder).

### TestFromAC Integrity

| Test | Change | Assessment |
|------|--------|------------|
| `TestFromAC_McpServerNames` (6 new tests) | Added by test-writer (189ab73) | PRESERVED |
| `TestFromAC_SetupMcp` (6 tests) | Updated by test-writer from `owlbearMemory` string to `owlbear-memory` | STRENGTHENED — now checks no `--project` flag explicitly |
| `TestFromAC_McpConfig::test_mcp_server_args_reference_relative_path_to_owlbear` | Removed by test-writer (26e9ef7) | LEGITIMATE REMOVAL — AC #570 explicitly removes `--project`/relative-path behavior; old test directly contradicted new AC. Builder did not touch it. |
| `TestFromAC_GitHubMcpServer::test_three_owlbear_servers_still_present_alongside_github` | Expanded by test-writer: 3 → 4 servers in loop | STRENGTHENED |

No builder-originated `TestFromAC_*` modifications detected.

### AC Compliance

| AC Line | Evidence | Status |
|---------|----------|--------|
| `.vscode/mcp.json` has `owlbear-memory` entry (stdio, `uv`, `["run","python","-m","owlbear_mcp_memory"]`, no `--project`) | `Get-Content .vscode/mcp.json` confirms entry; `test_create_mcp_config_owlbear_memory_entry_shape` PASS | COVERED |
| `setup.py create_mcp_config()` uses kebab-case: `owlbear-kanban`, `owlbear-knowledge`, `owlbear-memory`, `owlbear-project` | `test_mcp_server_names_are_kebab_case` asserts exact set equality — PASS | COVERED |
| `TestFromAC_McpServerNames` (6): all kebab-case assertions | All 6 PASS | COVERED |
| `TestFromAC_GithubRemoteServer::test_three_owlbear-servers_still_present_alongside_github` (actual: `TestFromAC_GitHubMcpServer`) | PASS | COVERED |
| `TestFromAC_SetupMcp` (6): owlbear-memory entry shape + docstring checks | All 6 PASS | COVERED |
| Tool pattern resolution: `owlbear-kanban/*` resolves correctly | Tested via `test_mcp_server_names_are_kebab_case` exact-set match; workspace mcp.json confirms consistent kebab-case | COVERED |

### Security

No issues. Config file write only; no user input paths, no subprocess calls, no secrets. `_owlbear_dir` param unused — no attack surface.

### Deductions

- None. Note: AC Line 2 has a typo ("owlbear_knowledge" with underscore) — both test and implementation correctly use `owlbear-knowledge` (kebab-case). Documentation issue, not a defect.

### Verdict

Confidence: .94 → **PASS**

[[2026-04-05]] Sun 01:37
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Behavior/API change | Yes | N/A | `create_mcp_config()` behavior changed (kebab-case keys, removed `--project` flag, added owlbear-memory). `.github/copilot-instructions.md` lists MCP server package names (already accurate — 5 servers, includes mcp-memory); does not document key-naming convention. No update needed. |
| 2 | Module docstrings | Yes | Verified | `scripts/setup.py` `create_mcp_config()` docstring: "five MCP server entries… github remote + four owlbear stdio servers" — correct after owlbear-memory addition (1 remote + 4 stdio = 5 total). All other public functions have accurate docstrings. |
| 3 | External attribution | Yes | Verified | `docs/sources/overview.md` §"Register owlbear-memory MCP Server (Task #570)" already present (line 42–46) with VS Code MCP config reference attribution. No addition needed. |
| 4 | CLI changes | No | N/A | No user-facing CLI commands added or modified. `setup.py` changes are internal bootstrap implementation not documented in README CLI sections. |
| 5 | Research doc | Yes | Verified | `docs/research/register-owlbear-memory-mcp.md` exists, status "Complete", linked from task body. Follow-ups noted (duplicate #571 flagged for archiving). |

### Files Updated
- None

### Scratch Files Cleaned
- None (`docs/scratch/570-*` — no files found)

[[2026-04-05]] Sun 04:18
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| `.vscode/mcp.json` has `owlbear-memory` entry (stdio, uv, no `--project`) | `Get-Content .vscode/mcp.json` confirms entry; `test_create_mcp_config_owlbear_memory_entry_shape` PASS | PASS |
| `setup.py` kebab-case keys: `owlbear-kanban`, `owlbear-knowledge`, `owlbear-memory`, `owlbear-project` | grep confirms 4 keys at L67/72/77/82; `test_mcp_server_names_are_kebab_case` PASS | PASS |
| All affected tests updated (McpServerNames x6, GitHubMcpServer x1, SetupMcp x6) | 18/18 AC-scoped tests PASS | PASS |
| Tool pattern resolution (`owlbear-kanban/*` resolves) | mcp.json keys are kebab-case; `test_mcp_server_names_are_kebab_case` exact-set match PASS | PASS |

### Test Results
- pytest (AC-scoped): 18 passed, 0 failed
- pytest (full suite): 2655 passed, 502 failed — all failures pre-existing (voice, v2 infra, session hooks, skill frontmatter). Zero task-scope failures.
- ruff: All checks passed

### Architect Quality: 4/5
AC specific and verifiable. Challenger review improved test surface. Minor cosmetic typo in AC line 2 (underscore vs kebab). Builder reject/re-route handled cleanly.

### Deduction Breakdown
- AC lines with no evidence: 0 → -.00
- Lint violations: 0 → -.00
- AC quality <= 3: no (4/5) → -.00
- Missing reviewer evidence: no → -.00
- Full-suite task-scope failures: 0 → -.00
- Reviewer listed no deductions but scored .94 → -.02

### Confidence: .98
### Action: archive
