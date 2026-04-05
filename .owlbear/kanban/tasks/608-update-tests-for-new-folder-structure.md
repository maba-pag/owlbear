---
id: 608
title: Update tests for new folder structure
status: todo
priority: needed
created: 2026-04-04T20:31:51.963696+02:00
updated: 2026-04-05T00:14:41.1636321+02:00
tags:
    - scope:infra
    - type:build
    - phase-2
    - test
parent: 598
depends_on:
    - 600
    - 601
    - 602
    - 603
    - 604
class: standard
---

## Summary

Update test files that assert on folder paths, fixture structures, or path assumptions that changed in the migration.

## Acceptance Criteria

- [ ] AC1: All tests referencing .github/agents/ updated to share/agents/
- [ ] AC2: All tests referencing .github/skills/ updated to share/skills/
- [ ] AC3: All tests referencing packages/ updated to serve/ (path constructions, pyproject.toml paths, AST-based references)
- [ ] AC4: All tests referencing data/ updated to store/
- [ ] AC5: All tests referencing kanban/ in integration tests and binary path defaults updated to .owlbear/kanban/. JSON fixture data (e.g., "file": "/kanban/tasks/42-sample.md") in unit test mocks does NOT need updating -- these are opaque test fixtures not resolved against the filesystem.
- [ ] AC6a: Tests referencing scripts/hooks/ updated to .owlbear/hooks/
- [ ] AC6b: Tests referencing scripts/validate_agents.py, scripts/validate_skills.py, scripts/e2e_smoke.py updated to .owlbear/scripts/
- [ ] AC6c: Tests referencing scripts/setup.py updated for setup/init.py location (imports, path constants, function signatures per #604 AC8)
- [ ] AC7: test_setup_script.py refactored or replaced to test setup/init.py API (init() function signature, CLI invocation, idempotency contract per #604 AC8-AC12)
- [ ] AC8: Tests that are OBSOLETED by the migration (their primary assertions contradict the new structure) are deleted. Known candidates: test_monorepo_skeleton.py, test_cleanup_github_agents_166.py, test_cleanup_github_skills_117.py, test_stale_agents_path_fixes.py. Builder must verify each -- delete only if ALL assertions in the file are superseded.
- [ ] AC9: uv run pytest passes with no failures (tests/ and serve/*/tests/)
- [ ] AC10: uv run ruff check passes

## Scope

### In scope
- Test files in tests/ (root-level test directory)
- Test files in serve/*/tests/ (package-internal tests, formerly packages/*/tests/)
- Path constructions (Path(...) / "old" / "path")
- Constant definitions (_REPO_ROOT / ".github" / "agents")
- Subprocess invocations referencing old script paths
- Import path adjustments (scripts/setup.py to setup/init.py)

### Out of scope (explicitly excluded)
- Red-phase test files written by sibling task test-writers that already reference new paths: test_rename_packages_601.py, test_rename_data_to_store_602.py, test_setup_init.py
- JSON mock data in kanban unit tests where "file" field is not asserted on (opaque fixtures)
- Historical docstrings/comments in archived test files (v1/ directory)

## Notes

Grep patterns for discovery: .github/agents, .github/skills, packages/, kanban/, scripts/, data/.
Focus order: path constructions first (cause test failures), then imports, then constants.

High-impact files (many old-path references):
- tests/test_monorepo_skeleton.py -- may be fully obsoleted (AC8)
- tests/test_setup_script.py -- major refactor for setup/init.py (AC7)
- tests/test_package_boundary.py -- _PACKAGES_DIR path + ALLOWED_IMPORTS
- tests/test_fix_attempt_agent_318.py -- .github/agents paths
- tests/test_session_context_hook_590.py -- scripts/hooks/ and .github/agents
- tests/test_deny_writes_hook_211.py -- scripts/hooks/ paths
- tests/test_deny_src_writes_hook_589.py -- scripts/hooks/ and packages/ paths
- tests/test_mcp_tool_references_483.py -- .github/skills/ paths
- tests/test_argument_hint_skills.py -- .github/skills/ paths
- packages/mcp-project/tests/test_server.py -- data/projects/ fixture paths
- packages/mcp-kanban/tests/test_integration.py -- kanban/ binary path

## Architecture Review

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | One concern: fix all test path references post-migration. Mechanically consistent scope despite many files. |
| Interface clarity | PASS (refined) | Original AC1-AC6 were "update X to Y" without handling obsolete tests, fixture data, or scripts/hooks split. Refined to 12 AC items with specific targets and exclusions. |
| Dependency correctness | PASS | Depends on #600, #601, #602, #603, #604 (all in-progress). Correct: moves must complete before test updates. No missing deps. |
| Module layering | N/A | Test file edits only, no new code modules. |
| TDD compliance | PASS | Tagged `test` (pass-through). Task IS the test update -- AC9 (pytest passes) and AC10 (ruff passes) are the verification gates. |
| KISS/YAGNI | PASS | Mechanical bulk-update. Scope limited to path references. No new abstractions or features. |
| Premise challenge | PASS | Tests WILL break after sibling moves (#600-#604). This task is mechanically necessary. |
| Pattern consistency | PASS | Follows existing test conventions (TestFromAC_ classes, _REPO_ROOT constants). |
| Security surface | PASS | No new system boundaries. Test file edits only. |
| Single domain | PASS | scope:infra, test tag. All changes are test infrastructure. |

### Challenge Results

- Challenger: reconsider (confidence: 0.65)
- Key concerns: (1) fixture data blind spot -- kanban mock JSON "file" fields pass pytest but are technically stale, (2) AC6 "or" ambiguity unresolvable by builder, (3) obsolete tests not addressed
- Architect response: Accepted all three via AC refinements
  - C1: AC5 now explicitly excludes opaque fixture mock data, scoping update to integration tests and binary path defaults only
  - C2: AC6 split into AC6a (hooks), AC6b (scripts), AC6c (setup.py) -- no ambiguity
  - C3: AC8 added: explicit obsolete-test deletion criteria with named candidates

### Refinements Applied

1. AC5 refined: distinguished integration test kanban/ paths (update) from unit test JSON fixture mocks (exclude)
2. AC6 split into AC6a/AC6b/AC6c: hooks to .owlbear/hooks/, CI scripts to .owlbear/scripts/, setup.py to setup/init.py
3. AC7 refined: explicit cross-reference to #604 AC8-AC12 for setup/init.py API contract
4. AC8 added: obsolete test deletion with named candidates and "delete only if ALL assertions superseded" gate
5. Added Scope section: in-scope (path constructions, imports, subprocess calls) and out-of-scope (sibling red-phase tests, opaque fixtures, v1/ archive)
6. Added high-impact file inventory for builder reference
7. Expanded from 9 AC items to 12 precise items

### Verdict: APPROVE
### Action Taken: Refined AC from 9 items to 12 with specific targets, scope boundaries, and obsolete-test handling. Advanced to todo.

[[2026-04-05]] Sun 00:14
APPROVED #608 -> todo | Refined AC from 9 to 12 items: split AC6 (hooks/scripts/setup.py), added AC8 (obsolete test deletion with named candidates), refined AC5 (fixture mock exclusion), AC7 (cross-ref #604 API contract). Added Scope section with in/out boundaries. Challenger overridden (0.65) -- all 3 concerns addressed via AC refinements.
