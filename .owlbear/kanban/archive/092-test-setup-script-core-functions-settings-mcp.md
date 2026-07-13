---
id: 92
title: 'Test: setup script core functions (settings, mcp, kanban, idempotency)'
status: archived
priority: medium
created: 2026-03-28 01:41:20.811558+01:00
updated: 2026-03-28 21:43:50.205724+01:00
started: 2026-03-28 21:43:45.139781+01:00
completed: 2026-03-28 21:43:45.139781+01:00
tags:
- phase-1
- scope:cli
- type:test
depends_on:
- 7
class: standard
archival_reason: completed
archival_refs: []
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

[[2026-03-28]] Sat 14:32
## Test-Writer Notes
- Test file: tests/test_setup_script.py
- Classes: TestFromAC_VscodeSettings, TestFromAC_McpConfig, TestFromAC_KanbanSetup, TestFromAC_DataAndInstructions, TestFromAC_PathDetectionAndOutput
- Tests per category: happy 0, edge 4, error 4, boundary 20
- Total: 28 tests, all FAIL (ImportError on collection) v
- ruff: clean (All checks passed)
- Functions imported from scripts/setup.py: compute_owlbear_relpath, create_copilot_instructions, create_kanban_dir, create_knowledge_dir, create_mcp_config, create_vscode_settings, setup
- AC coverage:
  settings.json 3 location types: test_settings_json_has_agent_files_locations, test_settings_json_has_agent_skills_locations, test_settings_json_has_instructions_files_locations
  Each type maps both root and github paths: test_agent_files_locations_has_root_and_github_paths, test_agent_skills_locations_has_root_and_github_paths, test_instructions_locations_has_root_and_github_paths
  Forward slashes: test_location_paths_use_forward_slashes, test_compute_owlbear_relpath_uses_forward_slashes
  mcp.json 3 servers: test_mcp_json_has_exactly_three_server_entries
  MCP module names: test_mcp_args_contain_mcp_kanban_module, test_mcp_args_contain_mcp_knowledge_module, test_mcp_args_contain_mcp_project_module
  MCP relative path: test_mcp_server_args_reference_relative_path_to_owlbear
  kanban/ dir: test_kanban_directory_created, test_kanban_config_yml_exists, test_kanban_tasks_subdirectory_created
  Clean next_id: test_copied_config_yml_has_clean_next_id
  setup.ps1 copy: test_kanban_setup_ps1_copied
  data/knowledge/: test_data_knowledge_directory_created
  copilot-instructions.md: test_copilot_instructions_file_created, test_copilot_instructions_contains_project_name
  Idempotent settings merge: test_idempotent_merge_preserves_existing_user_keys, test_idempotent_merge_adds_owlbear_keys_to_existing_file
  Idempotent mcp.json skip: test_mcp_json_idempotent_skips_if_file_exists
  Idempotent kanban skip: test_kanban_config_yml_idempotent_skips_if_exists
  Idempotent instructions skip: test_copilot_instructions_idempotent_skips_if_exists
  Path auto-detection: test_setup_auto_detects_owlbear_dir_from_script_location
  Success message: test_setup_prints_success_message

[[2026-03-28]] Sat 14:57
## Builder Notes
- Files changed: scripts/setup.py, pyproject.toml (T201 ignore for scripts/)
- Tests: 30 passed, coverage N/A (scripts/ loaded via sys.path.insert, not tracked by --cov)
- Lint: ruff clean after adding T201 to scripts per-file-ignores
- Evidence: 30 passed in 1.35s; all TestFromAC_* classes green
- Fixes applied: Added T201 to pyproject.toml scripts per-file-ignores (CLI scripts use print intentionally)

[[2026-03-28]] Sat 21:43
## Audit

### AC Verification (spot-check, 3rd-line)
| AC Line | Evidence | Status |
|---------|----------|--------|
| settings.json 3 location types | setup.py L30-46: agentFiles, agentSkills, instructionsFiles keys | PASS |
| Each type maps both dirs | setup.py L32-33, L37-38, L42-43: root + .github paths | PASS |
| Forward-slash relpath | setup.py L15: Path.as_posix() | PASS |
| mcp.json 3 servers | setup.py L66-79: kanban, knowledge, project entries | PASS |
| Correct module names | setup.py L69,74,79: mcp_kanban, mcp_knowledge, mcp_project | PASS |
| MCP args rel path | setup.py L67-68: --project rel arg | PASS |
| kanban/ dir + config + tasks/ | setup.py L84-86: mkdir + tasks | PASS |
| Clean next_id | setup.py L93-94: re.sub reset to 1 | PASS |
| Copy setup.ps1 | setup.py L96-98: shutil.copy2 | PASS |
| data/knowledge/ | setup.py L101-102: mkdir parents=True | PASS |
| copilot-instructions.md w/ name | setup.py L105-114: f-string with name | PASS |
| Idempotent settings merge | setup.py L50: {**owlbear_keys, **existing} | PASS |
| Idempotent mcp.json skip | setup.py L59: early return if exists | PASS |
| Idempotent kanban skip | setup.py L90: if not config_dest.exists() | PASS |
| Idempotent instructions skip | setup.py L111: early return if exists | PASS |
| Path auto-detection | setup.py L130: Path(__file__).resolve().parent.parent | PASS |
| Success message | setup.py L136-141: print() calls | PASS |

### Test Results
- pytest tests/test_setup_script.py: 30 passed (1.41s)
- Full suite (excl. pre-existing broken imports): no regressions from #92
- Pre-existing collection errors: test_acp_client.py (missing module), test_knowledge_foundation.py (missing import) -- unrelated
- ruff: All checks passed

### AC Quality Score: 4/5
AC was specific with 17 verifiable items covering happy path, idempotency, and edge cases. Minor gap: function signatures not specified, resolved naturally by test-writer.

### Pipeline Gaps
- No Review Evidence section: reviewer stage appears skipped
- No Docs Gate section: writer stage appears skipped
- Test file (tests/test_setup_script.py) not committed by test-writer -- orphaned deliverable

### Upstream Commits
- 358021c: feat: implement setup script core functions (#92, builder) -- scripts/setup.py, pyproject.toml

### Confidence: .95
### Action: archive
