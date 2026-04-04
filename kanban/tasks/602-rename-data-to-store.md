---
id: 602
title: Rename data/ to store/
status: todo
priority: needed
created: 2026-04-04T20:30:39.4451838+02:00
updated: 2026-04-04T22:24:48.4182984+02:00
tags:
    - scope:infra
    - type:build
    - phase-2
parent: 598
class: standard
---

## Summary

Rename data/ to store/ using `git mv`. Update all default-path constants in Python code and config files. Documentation/markdown updates deferred to #607; test updates deferred to #608.

## Acceptance Criteria

- [ ] AC1: `git mv data/ store/` succeeds — store/memory/ and store/knowledge/ tracked with prior content
- [ ] AC2: `_DEFAULT_DB_PATH` updated to `store/memory/memory.db` in mcp-memory server.py, migrate.py, approve.py (including docstring on server.py L62)
- [ ] AC3: `_DEFAULT_KB_PATH` updated to `store/knowledge/knowledge.db` in mcp-knowledge server.py
- [ ] AC4: Knowledge loader default updated to `store/knowledge/knowledge.db` in knowledge/loader.py L252
- [ ] AC5: `project_list` reads `store/projects/` instead of `data/projects/` in mcp-project server.py L145
- [ ] AC6: `_DEFAULT_AUDIT_DIR` updated to `Path(store/audit/)` in analysis/_cli.py L13 (including help text on L37)
- [ ] AC7: `scripts/setup.py` creates `store/knowledge/` instead of `data/knowledge/` (code and docstring)
- [ ] AC8: `.gitignore` patterns updated from data/ to store/
- [ ] AC9: `.editorconfig` [data/**] section updated to [store/**]

## Files Affected

Python (default path constants):
- packages/mcp-memory/src/owlbear_mcp_memory/server.py (L30, L62 docstring)
- packages/mcp-memory/src/owlbear_mcp_memory/migrate.py (L18)
- packages/mcp-memory/src/owlbear_mcp_memory/approve.py (L39)
- packages/mcp-knowledge/src/owlbear_mcp_knowledge/server.py (L31)
- packages/knowledge/src/owlbear_knowledge/loader.py (L252)
- packages/mcp-project/src/owlbear_mcp_project/server.py (L145)
- packages/orchestrator/src/owlbear_orchestrator/analysis/_cli.py (L13, L37)
- scripts/setup.py (L113-116)

Config:
- .gitignore (L88-91)
- .editorconfig (L19-23)

## Scope Boundaries

- Documentation updates (README, setup-guide, sharing-guide, skill docs) -> #607
- Test updates (assertions referencing data/ defaults) -> #608
- Complex MCP path resolution (kanban binary, dual knowledge paths, .vscode/mcp.json) -> #606
- Env var NAMES (OWLBEAR_KB_PATH, OWLBEAR_MEMORY_DB_PATH) unchanged — only code default values change

[[2026-04-04]] Sat 22:24
## Architecture Review

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | One directory rename with all direct code/config impacts |
| Interface clarity | PASS | 9 AC items enumerate exact files, line numbers, and constants |
| Dependency correctness | PASS | No deps. Downstream #606, #607, #608 depend on this correctly |
| Module layering | N/A | Rename operation, no new modules |
| TDD compliance | PASS | Test-writer processes first; #608 handles test file updates |
| KISS/YAGNI | PASS | Minimal scope: git mv + constant updates + config |
| Premise challenge | PASS | Five-tier model approved at parent #598 |
| Pattern consistency | PASS | Follows same pattern as sibling #601 (rename + config) |
| Security surface | PASS | No new system boundaries, file moves only |
| Single domain | PASS | scope:infra, type:build |

### Challenge Results
- Challenger: proceed (confidence: 0.84)
- Concerns: minor — docstring/help-text updates not explicit in original AC
- Architect response: accepted — incorporated into refined AC2, AC6, AC7

### Refinements Applied
1. Expanded 7 vague AC items to 9 precise items with file paths and line numbers
2. Added 5 missing references: mcp-project project_list, analysis CLI audit dir, scripts/setup.py, .editorconfig, docstrings
3. Removed documentation updates (deferred to #607) to eliminate overlap
4. Added Files Affected section for builder reference
5. Added Scope Boundaries section clarifying handoff to #606, #607, #608

### Verdict: APPROVE
### Action Taken: Refined AC from 7 vague items to 9 precise verifiable items. Added file manifest and scope boundaries. Advanced to todo.

[[2026-04-04]] Sat 22:24
APPROVED #602 -> todo | Refined AC from 7 vague items to 9 precise verifiable items with exact file paths and line numbers. Added 5 missing code references (mcp-project, analysis CLI, setup.py, .editorconfig, docstrings). Clarified scope boundaries with #606/#607/#608. Challenger: proceed (0.84).
