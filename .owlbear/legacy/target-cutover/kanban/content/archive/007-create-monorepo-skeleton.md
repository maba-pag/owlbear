---
id: 7
title: Create monorepo skeleton
status: archived
priority: medium
created: 2026-03-26 17:19:31.791298+01:00
updated: 2026-03-28 01:39:00.139252+01:00
started: 2026-03-28 01:38:55.437886+01:00
completed: 2026-03-28 01:38:55.437886+01:00
tags:
- phase-1
- scope:build
- type:build
depends_on:
- 6
class: standard
archival_reason: completed
archival_refs: []
---

## Objective

Create the v2 monorepo directory structure with uv workspace configuration.

## Acceptance Criteria

### Package structure

- [ ] Root pyproject.toml with uv workspace members: `packages/*`
- [ ] packages/orchestrator/ with pyproject.toml and src/owlbear/__init__.py stub
- [ ] packages/knowledge/ with pyproject.toml and src/owlbear_knowledge/__init__.py stub
- [ ] packages/mcp-kanban/ with pyproject.toml and src/owlbear_mcp_kanban/__init__.py stub
- [ ] packages/mcp-knowledge/ with pyproject.toml and src/owlbear_mcp_knowledge/__init__.py stub
- [ ] packages/mcp-project/ with pyproject.toml and src/owlbear_mcp_project/__init__.py stub

### Directory structure

- [ ] agents/ at repo root with README.md (transition placeholder; .github/agents/ remains authoritative)
- [ ] skills/ at repo root with README.md (transition placeholder; .github/skills/ remains authoritative)
- [ ] instructions/ at repo root with README.md (transition placeholder; .github/instructions/ remains authoritative)
- [ ] kanban/ directory already exists, no changes
- [ ] docs/ structure (research/, sources/, decisions/, scratch/) already exists, verify complete
- [ ] scripts/ directory with setup.py placeholder
- [ ] data/knowledge/general/ directory created (with .gitkeep)

### Build verification

- [ ] uv sync succeeds with empty packages (zero errors)
- [ ] Each package importable after sync: python -c imports owlbear, owlbear_knowledge, owlbear_mcp_kanban, owlbear_mcp_knowledge, owlbear_mcp_project
- [ ] uv.lock committed after successful sync (reproducible builds per uv best practice)

### Config updates

- [ ] .gitignore: add packages/*/dist/, data/knowledge/*.db patterns
- [ ] .pre-commit-config.yaml: bandit target changed from -r src/ to -r packages/
- [ ] .vscode/settings.json: chat.agentFilesLocations includes both .github/agents/ and agents/
- [ ] .vscode/settings.json: chat.agentSkillsLocations includes both .github/skills/ and skills/
- [ ] .vscode/settings.json: chat.instructionsFilesLocations includes both .github/instructions/ and instructions/

## Context

Depends on #6 (monorepo tooling research, archived). See docs/research/monorepo-skeleton.md for research findings and module naming rationale.

Downstream: #39, #41, #46 depend on this task.

## TDD Exception

Pure scaffolding task (directories, config files, stub packages). No application behavior to test-drive. Build verification is embedded in the AC (uv sync, imports). No preceding test task required.

## Research

Findings: docs/research/monorepo-skeleton.md

Key findings:

- Gap analysis: 16 of 19 AC items need creation; kanban/, docs/ already exist
- VS Code settings confirmed: chat.agentFilesLocations, chat.agentSkillsLocations are real settings
- Module naming: orchestrator uses owlbear module, others use owlbear_knowledge etc
- Pre-commit bandit path needs update from src/ to packages/
- Commit uv.lock after sync (reproducible builds per uv best practice)

[[2026-03-27]] Fri 14:33
## Architecture Review
Verdict: APPROVED

### AC Assessment

Original AC refined. Changes made:

- AC 4-6: Added explicit module names (owlbear_mcp_kanban, owlbear_mcp_knowledge, owlbear_mcp_project) for consistency with AC 2-3
- AC 7-9: Added README.md requirement for transition placeholder dirs
- AC 13: Reworded to data/knowledge/general/ with .gitkeep
- AC 14: Changed vague 'cross-import' to explicit importability check per module name
- AC 15: Added 'uv.lock committed' (per research recommendation)
- AC 16: Removed redundant .gitignore patterns already covered by global globs, kept packages/*/dist/ and data/knowledge/*.db
- AC 17: Made bandit target explicit: from -r src/ to -r packages/
- Added: chat.instructionsFilesLocations setting (per research recommendation)
- Added: TDD Exception section documenting why no test task precedes this scaffolding task
- Added: Downstream dependency list (#39, #41, #46)

### Architecture Notes

This is a foundational scaffolding task, not application code. Creates the uv workspace skeleton that all subsequent phase-1 build tasks depend on. Patterns:

- Module naming follows uv convention (hyphens in package names, underscores in module names)
- src-layout per package (packages/X/src/module_name/) matches pydantic-ai precedent
- Root agents/skills/instructions/ are transition placeholders with both .github/ and root/ in VS Code settings
- No application behavior introduced, so TDD exception is justified

### Dependencies

- Verified: #6 (monorepo tooling research) archived
- Downstream: #39 (scaffold mcp-kanban), #41 (scaffold mcp-project), #46 (ACP deps) depend on #7

[[2026-03-27]] Fri 18:44
## Test-Writer Notes
- Test file: tests/test_monorepo_skeleton.py
- Classes: TestFromAC_PackageStructure, TestFromAC_DirectoryStructure, TestFromAC_BuildVerification, TestFromAC_ConfigUpdates
- Tests per category: happy 28, edge 5, error 0, boundary 0
- Total: 33 tests, all FAIL (AssertionError — scaffold does not exist yet)
- ruff: clean
- AC coverage:
  Root pyproject.toml exists: test_root_pyproject_toml_exists (happy)
  Root pyproject workspace members: test_root_pyproject_declares_workspace_members (happy)
  packages/orchestrator pyproject: test_orchestrator_pyproject_exists (happy)
  packages/orchestrator __init__.py: test_orchestrator_init_stub_exists (happy)
  packages/knowledge pyproject: test_knowledge_pyproject_exists (happy)
  packages/knowledge __init__.py: test_knowledge_init_stub_exists (happy)
  packages/mcp-kanban pyproject: test_mcp_kanban_pyproject_exists (happy)
  packages/mcp-kanban __init__.py: test_mcp_kanban_init_stub_exists (happy)
  packages/mcp-knowledge pyproject: test_mcp_knowledge_pyproject_exists (happy)
  packages/mcp-knowledge __init__.py: test_mcp_knowledge_init_stub_exists (happy)
  packages/mcp-project pyproject: test_mcp_project_pyproject_exists (happy)
  packages/mcp-project __init__.py: test_mcp_project_init_stub_exists (happy)
  agents/ README.md: test_agents_dir_has_readme (happy)
  skills/ README.md: test_skills_dir_has_readme (happy)
  instructions/ README.md: test_instructions_dir_has_readme (happy)
  scripts/setup.py: test_scripts_setup_placeholder_exists (happy)
  data/knowledge/general/.gitkeep: test_data_knowledge_general_gitkeep_exists (happy)
  uv.lock exists: test_uv_lock_exists (happy)
  uv sync succeeds: test_uv_sync_succeeds (happy)
  each package importable (x5): test_package_importable[owlbear/knowledge/mcp_kanban/mcp_knowledge/mcp_project] (happy)
  .gitignore packages/*/dist/: test_gitignore_has_packages_dist_pattern (happy)
  .gitignore data/knowledge/*.db: test_gitignore_has_data_knowledge_db_pattern (happy)
  bandit targets packages/: test_precommit_bandit_targets_packages_not_src (edge)
  bandit not targets src/: test_precommit_bandit_targets_packages_not_src (edge)
  agentFilesLocations .github: test_vscode_settings_agent_files_locations_github_agents (happy)
  agentFilesLocations root: test_vscode_settings_agent_files_locations_root_agents (edge)
  agentSkillsLocations .github: test_vscode_settings_agent_skills_locations_github_skills (happy)
  agentSkillsLocations root: test_vscode_settings_agent_skills_locations_root_skills (edge)
  instructionsFilesLocations .github: test_vscode_settings_instructions_files_locations_github (happy)
  instructionsFilesLocations root: test_vscode_settings_instructions_files_locations_root (edge)

[[2026-03-27]] Fri 22:41
## Builder Notes
- Files changed: pyproject.toml, uv.lock, packages/*/pyproject.toml, packages/*/src/*/__init__.py, agents/README.md, skills/README.md, instructions/README.md, scripts/setup.py, data/knowledge/general/.gitkeep, .gitignore, .pre-commit-config.yaml, .vscode/settings.json
- Tests: 33 passed, 100% coverage on test_monorepo_skeleton.py
- Lint: ruff clean
- Evidence: uv sync succeeded, all 5 packages importable, 33/33 AC tests green
- Fixes applied: Added pytest-cov to dev deps (missing from env); PS5.1 UTF-8 BOM work-around for settings.json
- Commit: 53cf529

[[2026-03-28]] Sat 01:01
## Review Evidence

### Test Results
- pytest tests/test_monorepo_skeleton.py: **33 passed, 0 failed** (uv run output confirmed via `2>&1 | Out-String`)
- Note: PS5.1 treats uv's stderr build output as NativeCommandError; exit code 1 is from the shell, not pytest. All 33 assertions green.

### Lint Results
- ruff check tests/test_monorepo_skeleton.py packages/ scripts/ agents/ skills/ instructions/: **All checks passed!**

### TestFromAC Comparison
- git log shows test file has exactly ONE commit: `0d1492a test: add failing tests for monorepo skeleton (#7, test-writer)`
- Builder commit 53cf529 does NOT touch tests/test_monorepo_skeleton.py
- All 33 TestFromAC_* tests: **PRESERVED** (never modified)

### AC Compliance

| AC Line | Evidence | Status |
|---------|----------|--------|
| Root pyproject.toml with workspace members packages/* | test_root_pyproject_declares_workspace_members PASS; content confirmed packages/* in pyproject.toml line 1-2 | PASS |
| packages/orchestrator pyproject + stub | test_orchestrator_pyproject_exists + test_orchestrator_init_stub_exists PASS; files verified in git show 53cf529 | PASS |
| packages/knowledge pyproject + stub | test_knowledge_pyproject_exists + test_knowledge_init_stub_exists PASS | PASS |
| packages/mcp-kanban pyproject + stub | test_mcp_kanban_pyproject_exists + test_mcp_kanban_init_stub_exists PASS | PASS |
| packages/mcp-knowledge pyproject + stub | test_mcp_knowledge_pyproject_exists + test_mcp_knowledge_init_stub_exists PASS | PASS |
| packages/mcp-project pyproject + stub | test_mcp_project_pyproject_exists + test_mcp_project_init_stub_exists PASS | PASS |
| agents/ with README.md | test_agents_dir_has_readme PASS | PASS |
| skills/ with README.md | test_skills_dir_has_readme PASS | PASS |
| instructions/ with README.md | test_instructions_dir_has_readme PASS | PASS |
| scripts/setup.py placeholder | test_scripts_setup_placeholder_exists PASS | PASS |
| data/knowledge/general/.gitkeep | test_data_knowledge_general_gitkeep_exists PASS | PASS |
| uv sync succeeds | test_uv_sync_succeeds PASS | PASS |
| All 5 packages importable | test_package_importable[owlbear/knowledge/mcp_kanban/mcp_knowledge/mcp_project] PASS | PASS |
| uv.lock committed | test_uv_lock_exists PASS; file present in 53cf529 commit | PASS |
| .gitignore: packages/*/dist/ + data/knowledge/*.db | test_gitignore_has_packages_dist_pattern + test_gitignore_has_data_knowledge_db_pattern PASS; grep confirmed both patterns at .gitignore lines 78,81 | PASS |
| bandit targets packages/ not src/ | test_precommit_bandit_targets_packages_not_src PASS; .pre-commit-config.yaml shows `args: [-c, pyproject.toml, -r, packages/]` | PASS |
| .vscode/settings.json agent/skill/instruction locations | 6 VSCode settings tests PASS (both .github/ and root paths for each key) | PASS |

### Security Review
- No application code in this task (pure scaffolding -- stubs and config files)
- __init__.py stubs are empty (3 lines each); no secrets, injection, or unsafe patterns
- No new production dependencies introduced (dev deps: pytest-cov added)
- Config files: no sensitive data

### Test Quality
- Assertion specificity: **STRONG** -- file existence, TOML content, YAML structure, JSON key checks
- Error-path coverage: **ADEQUATE** -- scaffolding has no error paths beyond file existence
- Test independence: **STRONG** -- each test reads filesystem independently
- Test names: **STRONG** -- all names describe scenario and expected outcome

### Verdict: PASS (.95 confidence)

[[2026-03-28]] Sat 01:17
## Docs Gate
### Checklist

| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | .github/copilot-instructions.md | Yes | Pass | Directory structure table already lists all 5 packages, agents/, skills/, instructions/, docs/, kanban/, v1/ â€” matches implementation exactly |
| 2 | Docstrings complete | Yes | Pass | All 5 __init__.py stubs have module docstrings; no public classes or functions beyond stubs |
| 3 | docs/sources/overview.md | Yes | Pass | Monorepo Skeleton Implementation Research (Task #7) section present with 4 source rows (uv workspace, uv init, VS Code Copilot settings, VS Code customization docs) |
| 4 | README.md | No | N/A | Scaffolding task â€” no CLI commands added or changed |
| 5 | Research doc linked | Yes | Pass | docs/research/monorepo-skeleton.md exists and linked in task body |

### Files Updated
- None

### Scratch Files Cleaned
- None (no docs/scratch/7-* files found)

[[2026-03-28]] Sat 01:38
## Audit

### AC Verification (spot-check, 3rd-line)

Reviewer produced full AC compliance table (17/17 PASS). Spot-checked:

- Root pyproject.toml: workspace members = packages/* confirmed
- Package stubs: owlbear/__init__.py, owlbear_mcp_kanban/__init__.py present with docstrings
- .gitignore: packages/*/dist/ at line 78 confirmed
- Pre-commit: bandit args [-c, pyproject.toml, -r, packages/] at line 29 confirmed
- VS Code settings: 6 tests cover agent/skill/instruction locations (both .github/ and root)

### Test Results

- Task tests: 33 passed, 0 failed (test_monorepo_skeleton.py)
- Full suite: 122 passed, 72 failed (all failures from other tasks: test_argument_hint_skills, test_disable_model_invocation, test_rename_todo_to_todos, test_resolve_memory_file_uri_removal, test_scratch_dir_enforcement -- pre-existing RED-phase tests for unimplemented tasks)
- 2 collection errors: test_process_supervisor.py (owlbear_orchestrator), test_validate_skills.py (skills_ref) -- modules not yet implemented
- Ruff: All checks passed (packages/ scripts/ tests/test_monorepo_skeleton.py)

### Commit Integrity

- Test-writer: 0d1492a test: add failing tests for monorepo skeleton (#7, test-writer)
- Builder: 53cf529 feat: create monorepo skeleton (#7, builder)
- Builder did NOT modify test file (confirmed via git log)

### AC Quality Score: 5/5

AC was exceptionally specific: exact file paths, module names, verification commands, config patterns. Architect refined 7 items from the original AC (added explicit module names, README.md requirements, .gitkeep, instructionsFilesLocations). 33 tests mapped 1:1 to AC lines with zero improvisation needed.

### Confidence: .97
### Action: archive
