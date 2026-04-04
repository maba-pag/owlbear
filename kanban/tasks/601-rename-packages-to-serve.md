---
id: 601
title: Rename packages/ to serve/
status: todo
priority: needed
created: 2026-04-04T20:30:31.2520737+02:00
updated: 2026-04-04T22:25:35.8034648+02:00
tags:
    - scope:infra
    - type:build
    - phase-2
parent: 598
class: standard
---

## Summary

Rename packages/ to serve/ using git mv. Update all build/tool configuration references in the root config files.

**Scope boundary:** Only the directory rename and root-level config files (pyproject.toml, .gitignore, .pre-commit-config.yaml). Agent files, skill files, README, docs, and test files referencing packages/ are updated by #607 (live references) and #608 (tests).

## Acceptance Criteria

- [ ] AC1: serve/ contains all 7 sub-packages (orchestrator, knowledge, mcp-kanban, mcp-knowledge, mcp-memory, mcp-project, voice)
- [ ] AC2: pyproject.toml `[tool.uv.workspace] members` updated to `["serve/*"]`
- [ ] AC3: pyproject.toml `[tool.ruff] src` paths updated from `packages/*/src` to `serve/*/src` (all 7 entries)
- [ ] AC4: pyproject.toml `[tool.ruff.lint.per-file-ignores]` keys updated from `packages/` to `serve/` (examples and tests patterns)
- [ ] AC5: pyproject.toml `[tool.pytest.ini_options] testpaths` updated from `["tests", "packages"]` to `["tests", "serve"]`
- [ ] AC6: `uv sync` succeeds (exit code 0)
- [ ] AC7: All 7 namespace packages importable: `uv run python -c "import owlbear; import owlbear_knowledge; import owlbear_mcp_kanban; import owlbear_mcp_knowledge; import owlbear_mcp_memory; import owlbear_mcp_project; import owlbear_voice"` (exit code 0)
- [ ] AC8: MCP server launch commands unchanged (`uv run python -m owlbear_mcp_kanban.server` etc. still resolve)
- [ ] AC9: .gitignore pattern updated from `packages/*/dist/` to `serve/*/dist/`
- [ ] AC10: .pre-commit-config.yaml bandit args updated from `packages/` to `serve/`

## Notes

- `[tool.coverage.run] source_pkgs` uses Python namespace names (not paths) — no changes needed.
- Sub-package pyproject.toml files use relative paths (`packages = ["src/..."]`) — no changes needed.
- Pre-existing tests (test_monorepo_skeleton.py, test_v2_test_infrastructure.py, etc.) will fail after this task until #608 updates them. This is expected and by design.

## Architecture Review

[[2026-04-04]]

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | One operation: rename directory + update config paths. Scope boundary explicitly limits to root config files. |
| Interface clarity | PASS | All 10 AC lines are mechanically verifiable with specific file paths, values, and commands. |
| Dependency correctness | PASS | Leaf starter (no depends_on). Downstream #606, #607, #608 correctly depend on this task. |
| Module layering | N/A | Directory rename only — no new modules or cross-package imports. |
| TDD compliance | PASS | Test-writer can verify config state (serve/ exists, pyproject.toml values). |
| KISS/YAGNI | PASS | Minimal scope: git mv + 3 config files. Broader updates deferred to #607 and #608. |
| Premise challenge | PASS | Rename is required by parent #598 five-tier restructure. packages/ → serve/ aligns with the tier taxonomy. |
| Pattern consistency | PASS | Sub-packages use src-layout with namespace packages. Python namespaces are path-independent — rename is transparent to runtime. |
| Security surface | PASS | No new system boundaries. File moves and config edits only. |
| Single domain | PASS | scope:infra, type:build. All changes are build tooling configuration. |

### Failure Mode Map

| Codepath | Failure Mode | Exception | Handled? | User Impact |
|----------|-------------|-----------|----------|-------------|
| uv sync after rename | workspace members point to old path | uv error | Yes — AC2 verifies | All package installs fail |
| ruff check after rename | src paths stale | ruff warning/error | Yes — AC3, AC4 verify | Lint misses or false positives |
| pytest discovery | testpaths stale | tests silently skipped | Yes — AC5 verifies | Package tests not discovered |
| pre-commit bandit | bandit -r packages/ fails | FileNotFoundError | Yes — AC10 verifies | Pre-commit hook fails |

### Challenge Results

- Challenger: proceed (confidence: 0.92)
- Key finding: No runtime failures from rename. 50+ test-level assertion failures are expected and deferred to #608.
- Architect response: accepted — all refinements confirmed.

### Refinements Applied

1. AC7 replaced: "uv run pytest passes" → namespace import check (full pytest unreachable until #608)
2. AC9 added: .gitignore dist pattern update
3. AC10 added: .pre-commit-config.yaml bandit path update
4. Scope boundary note added: docs/README/agents/skills/tests deferred to #607 and #608
5. Notes section added: coverage config and sub-package pyproject.toml analysis

### Verdict: APPROVE
### Action Taken: Refined AC (replaced AC7, added AC9-AC10, added scope boundary), advanced to todo.

[[2026-04-04]] Sat 22:25
APPROVED #601 -> todo | Rename packages/ to serve/. Refined AC: replaced unreachable AC7 (full pytest) with namespace import check, added AC9 (.gitignore) and AC10 (.pre-commit-config.yaml), added explicit scope boundary deferring docs/tests to #607 and #608. Challenger confirmed: proceed (0.92). No runtime risks — all 50+ hardcoded test refs are test-level failures handled by #608.
