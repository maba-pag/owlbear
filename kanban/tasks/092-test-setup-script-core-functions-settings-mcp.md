---
id: 92
title: 'Test: setup script core functions (settings, mcp, kanban, idempotency)'
status: todo
priority: needed
created: 2026-03-28T01:41:20.8115575+01:00
updated: 2026-03-28T04:23:55.0719895+01:00
tags:
    - phase-1
    - scope:cli
    - type:test
depends_on:
    - 7
class: standard
---

## Objective
TDD RED phase: write failing tests for setup.py core functions before builder implements.

## Test Scenarios
- [ ] settings.json contains all three location types: agentFilesLocations, agentSkillsLocations, instructionsFilesLocations
- [ ] Each location type maps to both {rel}/agents (or skills, instructions) and {rel}/.github/agents (etc.)
- [ ] Relative path uses forward slashes on all platforms
- [ ] Creates .vscode/mcp.json with three owlbear MCP server entries
- [ ] MCP server entries use correct module names (mcp_kanban, mcp_knowledge, mcp_project)
- [ ] MCP server args reference correct relative owlbear path
- [ ] Creates kanban/ with config.yml and tasks/ subdirectory
- [ ] Copied config.yml has clean next_id (reset from owlbear source)
- [ ] Copies kanban/setup.ps1 from owlbear source dir
- [ ] Creates data/knowledge/ directory
- [ ] Creates .github/copilot-instructions.md containing project name
- [ ] Idempotent: settings.json merges keys (preserves existing user keys, adds owlbear keys)
- [ ] Idempotent: mcp.json skips if file already exists
- [ ] Idempotent: kanban/config.yml skips if file already exists
- [ ] Idempotent: .github/copilot-instructions.md skips if file already exists
- [ ] Path auto-detection resolves owlbear dir from script location
- [ ] Prints success message with next steps (capsys)

## Test Isolation
- tmp_path sibling dirs: project_dir = tmp_path / proj, owlbear_dir = tmp_path / owlbear
- monkeypatch.chdir for path auto-detection test
- capsys for output verification
- json.loads for JSON assertions
- Follow TestFromAC_* class naming convention

## Context
Parent task: #12. Excludes project JSON tests (covered by #75).
See docs/research/setup-script.md and docs/research/test-setup-script-core.md.

[[2026-03-28]] Sat 04:23
## Architecture Review
**Verdict:** Approved

### AC Assessment
| AC Line | Assessment | Action |
|---------|------------|--------|
| settings.json 3 location types | Verifiable: check JSON keys | Keep |
| Each type maps to both dirs | Verifiable: 6 path entries | Keep |
| Forward-slash relative path | Verifiable: assert '/' not '\' | Keep |
| mcp.json with 3 servers | Verifiable: JSON key count | Keep |
| Correct module names | Verifiable: assert mcp_kanban etc. | Keep |
| MCP args rel path | Verifiable: assert {rel} in args | Keep |
| kanban/ + config.yml + tasks/ | Verifiable: Path.exists() | Keep |
| Clean next_id | Verifiable: parse YAML, check field | Keep |
| Copy setup.ps1 | Verifiable: Path.exists() | Keep (added from research) |
| data/knowledge/ dir | Verifiable: Path.exists() | Keep |
| copilot-instructions.md w/ name | Verifiable: read + assert name | Keep |
| Idempotent settings merge | Verifiable: pre-write, call, assert | Keep |
| Idempotent mcp.json skip | Verifiable: pre-write sentinel | Keep (added from research) |
| Idempotent kanban skip | Verifiable: pre-write sentinel | Keep |
| Idempotent instructions skip | Verifiable: pre-write sentinel | Keep (added from research) |
| Path auto-detection | Verifiable: monkeypatch.chdir | Keep |
| Success message | Verifiable: capsys | Keep |

### Architecture Notes
- Single domain (scope:cli) targeting scripts/setup.py tests only
- TDD RED phase: tests import from 3-line stub, all expected to fail
- No depends_on needed: stub exists at scripts/setup.py
- Follows TestFromAC_* class pattern per existing test conventions
- Scope boundary clean: project JSON excluded (covered by #75)
- Research doc thorough, 4 gaps identified and integrated

### Changes Made
- Consolidated two overlapping AC sections into single 17-item checklist
- Removed garbled literal \n formatting from researcher append
- Added Test Isolation section with fixture guidance

### Dependencies
- Verified: no depends_on needed (stub exists, RED phase)
- Verified: no overlap with #75 (project JSON scope)
- Parent #12 in ideation (fine for TDD ordering)
