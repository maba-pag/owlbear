---
id: 119
title: Fix MCP module names in setup.py (mcp_kanban -> owlbear_mcp_kanban)
status: archived
priority: medium
created: 2026-03-29 06:32:33.087279+02:00
updated: 2026-03-29 10:32:55.725350+02:00
started: 2026-03-29 10:32:55.417309+02:00
completed: 2026-03-29 10:32:55.417309+02:00
tags:
- phase-1
- scope:mcp
- type:build
class: standard
archival_reason: completed
archival_refs: []
---

## Objective
Fix incorrect Python module names in scripts/setup.py create_mcp_config().

## Acceptance Criteria
- [ ] setup.py uses owlbear_mcp_kanban instead of mcp_kanban
- [ ] setup.py uses owlbear_mcp_knowledge instead of mcp_knowledge
- [ ] setup.py uses owlbear_mcp_project instead of mcp_project
- [ ] test_setup_script.py assertions updated to match new module names
- [ ] All existing setup tests pass

## Context
See docs/research/mcp-server-registry.md section 3.1. The current module names do not match the actual installed package names (owlbear_mcp_*), so MCP servers fail to start.

[[2026-03-29]] Sun 06:57
## Research
Trivial fix validated via research checklist (gate only).
See docs/research/mcp-server-registry.md section 3.1 for original finding.

Evidence: pyproject.toml files confirm correct names (owlbear_mcp_kanban, owlbear_mcp_knowledge, owlbear_mcp_project). setup.py uses wrong names. Tests pass with wrong names because they assert string membership not execution.

Scope: 2 files, 6 string replacements (3 in setup.py, 3 in test_setup_script.py). Risk: none.

[[2026-03-29]] Sun 07:22
## Architecture Review
**Verdict:** Approve

### AC Assessment
| AC Line | Assessment | Action |
|---------|------------|--------|
| setup.py uses owlbear_mcp_kanban instead of mcp_kanban | Verifiable: literal string in args list at L64 | OK |
| setup.py uses owlbear_mcp_knowledge instead of mcp_knowledge | Verifiable: literal string in args list at L69 | OK |
| setup.py uses owlbear_mcp_project instead of mcp_project | Verifiable: literal string in args list at L74 | OK |
| test_setup_script.py assertions updated to match new module names | Verifiable: 3 assertions at L210/L218/L226 | OK |
| All existing setup tests pass | Verifiable: pytest exit code | OK |

### Architecture Notes
Confirmed bug: setup.py create_mcp_config() uses mcp_kanban/mcp_knowledge/mcp_project but pyproject.toml files declare owlbear_mcp_kanban/owlbear_mcp_knowledge/owlbear_mcp_project as the actual importable modules. 6 string replacements across 2 files. No interfaces, layering, or dependencies affected.

TDD note: tests already exist and cover the exact codepath. Builder should update test assertions first (RED: tests fail with new expected names) then fix setup.py (GREEN: tests pass). No separate test-writer task needed for this trivial bug fix.

### Changes Made
- Approved to todo

### Dependencies
- None required. Standalone bug fix.

[[2026-03-29]] Sun 08:18
## Test-Writer Notes
- Test file: tests/test_setup_script.py (existing file, updated assertions)
- Classes: TestFromAC_McpConfig (updated 3 existing tests)
- Tests per category: happy 3, edge 0, error 0, boundary 0
- Total: 3 tests updated, all FAIL
- ruff: clean
- AC coverage:
  - AC: setup.py uses owlbear_mcp_kanban - test_mcp_args_contain_mcp_kanban_module (happy)
  - AC: setup.py uses owlbear_mcp_knowledge - test_mcp_args_contain_mcp_knowledge_module (happy)
  - AC: setup.py uses owlbear_mcp_project - test_mcp_args_contain_mcp_project_module (happy)
  - AC: test_setup_script.py assertions updated - covered by these 3 test edits
  - AC: All existing setup tests pass - verified by full suite pass after builder fix

[[2026-03-29]] Sun 08:48
## Builder Notes
- Files changed: scripts/setup.py (3 string replacements)
- Tests: 38 passed in test_setup_script.py, 0 failed
- Lint: ruff clean
- Evidence: 3 TestFromAC_McpConfig tests FAIL pre-fix (owlbear_mcp_* not in args), GREEN post-fix
- Fixes applied: mcp_kanban -> owlbear_mcp_kanban, mcp_knowledge -> owlbear_mcp_knowledge, mcp_project -> owlbear_mcp_project in create_mcp_config()

[[2026-03-29]] Sun 09:51
## Docs Gate
### Checklist

1. copilot-instructions.md: No - N/A - Bug fix correcting wrong string literals, no behavior or API change visible to users
2. Docstrings: Yes - Pass - create_mcp_config() docstring is accurate, no update needed
3. docs/sources/overview.md: No - N/A - Pure string correction, no external patterns used
4. README.md: No - N/A - No CLI command changes
5. Research doc: Yes - Pass - docs/research/mcp-server-registry.md exists, linked from task body (section 3.1)

Files Updated: None
Scratch Files Cleaned: None (no docs/scratch/119-* files found)

[[2026-03-29]] Sun 10:32
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| setup.py uses owlbear_mcp_kanban | Line 69: owlbear_mcp_kanban in args list | PASS |
| setup.py uses owlbear_mcp_knowledge | Line 74: owlbear_mcp_knowledge in args list | PASS |
| setup.py uses owlbear_mcp_project | Line 79: owlbear_mcp_project in args list | PASS |
| test assertions updated | Lines 210, 218, 226 assert owlbear_mcp_* | PASS |
| All existing setup tests pass | 45 passed, 0 failed | PASS |

### Test Results
- pytest (task-specific): 45 passed in test_setup_script.py
- pytest (full suite): 349 passed, 4 failed (pre-existing test_copy_skills_to_root.py mismatches, unrelated)
- ruff: clean

### Upstream Commits
- acd00a3 test: update mcp module name assertions (#119, test-writer)
- 8f66f99 fix: correct MCP module names to owlbear_mcp_* (#119, builder)

### Architect Quality
AC quality score: 5/5 - Specific, complete, led to clean implementation. All AC lines were literal string verifications with clear file/line targets.

### Confidence: .97
### Action: archive
