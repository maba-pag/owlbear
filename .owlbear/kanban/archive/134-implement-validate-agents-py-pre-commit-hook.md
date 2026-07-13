---
id: 134
title: Implement validate_agents.py pre-commit hook
status: archived
priority: medium
created: 2026-03-29 12:02:19.486995+02:00
updated: 2026-03-30 04:39:34.664939+02:00
started: 2026-03-30 04:38:30.041294+02:00
completed: 2026-03-30 04:38:30.041294+02:00
tags:
- phase-1
- scope:agents
- tooling
- type:build
class: standard
archival_reason: completed
archival_refs: []
---

## Objective
Create scripts/validate_agents.py and add pre-commit hook to block agent tool name regressions.

## Acceptance Criteria
- [ ] scripts/validate_agents.py reads agents/*.agent.md frontmatter, fails if tools: contains bare todo (not todos)
- [ ] Script also fails if resolveMemoryFileUri appears anywhere in any agent file
- [ ] repo: local hook added to .pre-commit-config.yaml with id: validate-agents, files: ^agents/.*\.agent\.md$
- [ ] pre-commit run validate-agents --all-files exits 0 on current HEAD (after tool name fixes)
- [ ] Hook runs in less than 1s
- [ ] Brief note added to README about the hook and the VS Code auto-staging trap

## Architecture Notes
- Follow validate_skills.py pattern: language: system, entry: python scripts/validate_agents.py
- Parse YAML frontmatter between --- delimiters, check tools: line for \btodo\b regex
- Check full file content for resolveMemoryFileUri
- Script ~30 LOC, no external dependencies
- See docs/research/pre-commit-agent-tool-guard.md

[[2026-03-29]] Sun 14:49
## Research\nResearch gate validated (owning research: #132, doc: docs/research/pre-commit-agent-tool-guard.md).\n\n**Checklist:** All 7 items pass. Prior art: validate_skills.py, pre-commit local hooks docs, test_agent_port_v2.py.\n\n**Precision note:** Check only the `tools:` YAML line for `\\btodo\\b`, not all frontmatter. The `argument-hint` field in planner.agent.md contains `status: archiveds` which would cause false positives if entire frontmatter is checked naively.\n\n**Deprecation note:** pre-commit 4.4.0 renamed `language: system` to `language: unsupported` (alias removal planned). Both hooks (validate-skills / validate-agents) use `system`. Migrate together later, not a blocker for this task.\n\n**Current state:** All 11 agent files use `todos` (correct). No `resolveMemoryFileUri` present anywhere.

[[2026-03-29]] Sun 14:56
## Architecture Review
**Verdict:** Approved (merged from #132)

### AC Assessment
All 6 AC lines are precise and verifiable. No changes needed.

### Architecture Notes
- Follows validate_skills.py pattern: language: system, repo: local
- files filter + pass_filenames: true is efficient (only runs on staged agent files)
- tools: line check (not full frontmatter) avoids false positives from argument-hint fields
- ~30 LOC script, no external dependencies, under 1s on 11 files
- Existing test pattern: test_validate_skills.py + test_validate_skills_ci.py -- test-writer should follow same shape

### Changes Made
- Deleted #132 (redundant -- research complete, implementation scope covered by this task)
- Moved #134 to todo

### Dependencies
None -- standalone tooling task

[[2026-03-29]] Sun 15:22
## Test-Writer Notes
- Test file: tests/test_validate_agents.py
- Classes: TestFromAC_ValidateAgentsTodoCheck, TestFromAC_ValidateAgentsResolveCheck, TestFromAC_ValidateAgentsPreCommitHook, TestFromAC_ValidateAgentsIntegration, TestFromAC_ValidateAgentsReadme
- Tests per category: happy 6, edge 3, error 5, boundary 5
- Total: 19 tests, all FAIL (ModuleNotFoundError at collection) checked
- ruff: clean
- AC coverage:
  AC1 (bare todo in tools) -> test_bare_todo_in_tools_fails, test_bare_todo_alone_in_tools_fails, test_todo_mixed_with_todos_still_fails, test_tools_todos_passes, test_multiline_tools_todos_passes
  AC1 precision (word boundary, arg-hint) -> test_todo_prefix_substring_does_not_trigger, test_argument_hint_with_todos_does_not_trigger
  AC2 (resolveMemoryFileUri) -> test_resolve_uri_in_tools_line_fails, test_resolve_uri_in_body_fails, test_resolve_uri_in_frontmatter_description_fails, test_no_resolve_uri_passes
  AC3 (pre-commit hook config) -> test_validate_agents_hook_id_present, test_validate_agents_files_pattern_present, test_validate_agents_under_local_repo
  AC4 (exit 0 on current HEAD) -> test_script_exits_zero_on_current_agents
  AC5 (under 1s) -> test_script_completes_under_one_second
  AC6 (README note) -> test_readme_mentions_validate_agents_hook, test_readme_mentions_auto_staging_trap

[[2026-03-30]] Mon 03:13
## Review Evidence

### Test Results
- pytest (test_validate_agents.py): 19 passed, 0 failed
- ruff: All checks passed on scripts/validate_agents.py and tests/test_validate_agents.py

### Coverage
- scripts\validate_agents.py: 69% (lines 25,29: malformed-file edge cases in _frontmatter_lines; lines 74-91: main() wrapper; line 95: __main__ guard)
- main() is simple pass-through (calls validate_agent, accumulates has_errors, returns 0/1). Correct by inspection. Subprocess integration test covers exit-0 path. No subprocess test for exit-1 path but validate_agent() error paths are all individually tested.

### TestFromAC Comparison
- git diff f90ee8e HEAD -- tests/test_validate_agents.py: no changes
- Builder did NOT modify any TestFromAC tests.

### AC Compliance
| AC Line | Evidence | Status |
| --- | --- | --- |
| AC1: bare todo check + word boundary | test_bare_todo_in_tools_fails, test_bare_todo_alone_in_tools_fails, test_todo_mixed_with_todos_still_fails, test_todo_prefix_substring_does_not_trigger, test_argument_hint_with_todos_does_not_trigger | PASS |
| AC2: resolveMemoryFileUri anywhere | test_resolve_uri_in_tools_line_fails, test_resolve_uri_in_body_fails, test_resolve_uri_in_frontmatter_description_fails | PASS |
| AC3: .pre-commit-config.yaml hook | test_validate_agents_hook_id_present, test_validate_agents_files_pattern_present, test_validate_agents_under_local_repo | PASS |
| AC4: exits 0 on current HEAD | test_script_exits_zero_on_current_agents (subprocess, verified) | PASS |
| AC5: < 1s | test_script_completes_under_one_second (0.65s measured) | PASS |
| AC6: README note | test_readme_mentions_validate_agents_hook, test_readme_mentions_auto_staging_trap | PASS |

### Security
Clean. No injection risks (stdlib only, no shell=True, no external deps). No secrets. Path inputs controlled by pre-commit.

### Test Quality
- validate_agent() function: STRONG - every error condition tested with specific assertions, word-boundary precision tested, argument-hint false-positive tested
- main() wrapper: ADEQUATE - exit-0 path tested via subprocess; exit-1 path untested but main() is trivial pass-through and correct by inspection
- Naming: STRONG - descriptive test names throughout

### Verdict: PASS
### Confidence: .92

[[2026-03-30]] Mon 04:38
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| AC1: bare todo check in tools: line | validate_agents.py L17: word-boundary regex. 5 tests: bare_todo_fails, alone_fails, mixed_still_fails, prefix_substring_no_trigger, argument_hint_no_trigger | PASS |
| AC2: resolveMemoryFileUri anywhere | validate_agents.py L63: full-file string check. 3 tests: tools_line, body, frontmatter_description | PASS |
| AC3: .pre-commit-config.yaml hook | Config lines 43-48: id: validate-agents, files: ^agents/.*\.agent\.md$, under repo: local | PASS |
| AC4: exits 0 on current HEAD | test_script_exits_zero_on_current_agents passes (subprocess integration test) | PASS |
| AC5: under 1s | test_script_completes_under_one_second passes (0.65s measured) | PASS |
| AC6: README note + auto-staging trap | README.md L73-81: hook description + VS Code auto-staging trap section | PASS |

### Test Results
- pytest: 19/19 task-scoped tests pass (29 total in file; 10 RED-phase tests from subsequent task)
- ruff: All checks passed on scripts/validate_agents.py and tests/test_validate_agents.py
- Full suite: no cross-task regressions (pre-existing fails in test_validate_skills_ci.py and test_planner_*/test_voice_* unrelated)

### Upstream Commits
- f90ee8e: test: add failing tests for validate_agents.py hook (#134, test-writer)
- 2059efb: feat: implement validate_agents.py pre-commit hook (#134, builder)
Both properly scoped.

### Architect Quality
- AC specificity: all 6 lines concrete and verifiable
- Edge cases: argument-hint false positive addressed in architecture notes
- Design direction: validate_skills.py pattern followed exactly
- AC quality score: 5/5

### Deduction breakdown: none (all AC verified, lint clean, AC quality 5, reviewer evidence thorough, no regressions)
### Confidence: 1.0
### Action: archive

[[2026-03-30]] Mon 04:38
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| AC1: bare todo check in tools: line | validate_agents.py L17: word-boundary regex. 5 tests: bare_todo_fails, alone_fails, mixed_still_fails, prefix_substring_no_trigger, argument_hint_no_trigger | PASS |
| AC2: resolveMemoryFileUri anywhere | validate_agents.py L63: full-file string check. 3 tests: tools_line, body, frontmatter_description | PASS |
| AC3: .pre-commit-config.yaml hook | Config lines 43-48: id: validate-agents, files: ^agents/.*\.agent\.md$, under repo: local | PASS |
| AC4: exits 0 on current HEAD | test_script_exits_zero_on_current_agents passes (subprocess integration test) | PASS |
| AC5: under 1s | test_script_completes_under_one_second passes (0.65s measured) | PASS |
| AC6: README note + auto-staging trap | README.md L73-81: hook description + VS Code auto-staging trap section | PASS |

### Test Results
- pytest: 19/19 task-scoped tests pass (29 total in file; 10 RED-phase tests from subsequent task)
- ruff: All checks passed on scripts/validate_agents.py and tests/test_validate_agents.py
- Full suite: no cross-task regressions (pre-existing fails in test_validate_skills_ci.py and test_planner_*/test_voice_* unrelated)

### Upstream Commits
- f90ee8e: test: add failing tests for validate_agents.py hook (#134, test-writer)
- 2059efb: feat: implement validate_agents.py pre-commit hook (#134, builder)
Both properly scoped.

### Architect Quality
- AC specificity: all 6 lines concrete and verifiable
- Edge cases: argument-hint false positive addressed in architecture notes
- Design direction: validate_skills.py pattern followed exactly
- AC quality score: 5/5

### Deduction breakdown: none (all AC verified, lint clean, AC quality 5, reviewer evidence thorough, no regressions)
### Confidence: 1.0
### Action: archive

[[2026-03-30]] Mon 04:39
## Commits
Commit d322178: chore: archive task #134 (kanban/tasks/134-*.md)
