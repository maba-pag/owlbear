---
id: 1307
title: 'P1-06: GREEN — Mutation tools + access control removal (6 tools, schemas,
  hints, env var cleanup)'
status: review
priority: critical
created: 2026-05-04T01:32:18.543007+00:00
updated: 2026-05-05T02:51:56.990171+00:00
tags:
- phase-2
- scope:mcp-memory
- memory
- mcp
parent: 1301
depends_on:
- 1306
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

Brief: see parent #1301

## Acceptance Criteria

- [ ] 6 MCP tools registered: save_memory, list_memories, read_memory, curate_memory, delete_memory, approve_memory (td:0)
- [ ] Each tool has correct parameter schema with types, required flags, and descriptions (td:0)
- [ ] Validation errors return teaching messages per Brief guidance hints table (td:0)
- [ ] State transitions delegate to state machine logic in tools.py (#1305) (td:0)
- [ ] OWLBEAR_MEMORY_CALLER env var and all references deleted from codebase (td:0)
- [ ] MEMORY_TOOLS_EXCLUDE env var and all references deleted from codebase (td:0)
- [ ] All role-check/caller-gating code removed (td:0)
- [ ] list_memories: sorted by curation priority (pending first, then by created_at) (td:0)
- [ ] All #1306 tests pass (td:0)

## Scope

- In: MCP tool registration, parameter schemas, handler implementations, access control removal
- Out: recall_memory handler (task #1309), git batch commit, consumer agent wiring
[[2026-05-05]]
## Research

Key findings: Implementation is 80% complete. All 6 tool functions exist in tools.py and all 47 #1306 tests pass. Remaining work is mechanical server.py rewiring.

**What the builder must do:**
1. Replace 5 old `@mcp.tool` registrations in server.py with 6 new ones (save_memory, list_memories, read_memory, curate_memory, delete_memory, approve_memory)
2. Remove `caller` field from AppContext + `OWLBEAR_MEMORY_CALLER` from lifespan
3. Remove `_caller_from_ctx` helper from tools.py (only used by old store_learning)
4. Fix test_mcp_memory_tools_1273.py line 28 (imports query_memory from server — change to import from tools)
5. Remove OWLBEAR_MEMORY_CALLER from README.md
6. Remove OWLBEAR_MEMORY_CALLER from `share/skills/h-mcp-memory/SKILL.md` (lines 143-145)
7. Remove MEMORY_TOOLS_EXCLUDE from `share/skills/h-mcp-memory/SKILL.md` (lines 143, 147) and `share/skills/r-architecture-standards/SKILL.md` (line 109)
8. Add hint to approve_memory ("Entry approved. Now visible to scoped agents.") per Brief guidance table

**Risks:** test_mcp_memory_tools_1273.py regression (1-line fix). No architectural decisions needed.

Trade-off matrix: n/a (single implementation path, no alternatives).
Classification: T1 (Autonomous). No DR.
Doc: .owlbear/research/mutation-tools-green-1307.md

## Architecture Review

**Verdict:** APPROVE → todo

**AC Assessment:**

| AC Line | Assessment | Action |
|---------|-----------|--------|
| 6 MCP tools registered | Clear, grep-verifiable | None |
| Correct parameter schema | #1306 tests validate | None |
| Validation → teaching messages | #1306 tests validate | None |
| State transitions delegate to #1305 | Done inline in tools.py; clarified wording | Wording fix |
| OWLBEAR_MEMORY_CALLER deleted | Grep-verifiable; server.py + README + 2 skill files | Builder note added |
| MEMORY_TOOLS_EXCLUDE deleted | Grep-verifiable; 2 skill files only (already gone from server.py) | Builder note added |
| Role-check code removed | Already done | None |
| list_memories sorted | Done in tools.py | None |
| All #1306 tests pass | Currently passing | None |

**Architecture Notes:**
- Single implementation path, no design alternatives
- State machine logic from #1305 is inline in tools.py (no separate module file) — AC wording corrected
- Research doc missed skill-file references to env vars; added to builder checklist (items 6-7)
- Deletion of env vars from r-architecture-standards removes the `MEMORY_TOOLS_EXCLUDE` row from the per-server env var table; builder should leave the `KNOWLEDGE_TOOLS_EXCLUDE` row intact

**Dependency Analysis:**
- #1305 (state machine): archived/done ✓
- #1306 (RED tests): archived/done, 47 tests passing ✓

**Test-writer: SKIP** — All AC lines are td:0 (GREEN phase with pre-existing RED test suite from #1306).
[[2026-05-05]]
Architecture review complete. APPROVE → todo. All AC lines td:0 (pre-existing RED suite from #1306). Builder checklist expanded with skill-file references for env var deletion. Test-writer: SKIP.
[[2026-05-05]]
## Test-Writer Notes
- All AC lines are (td:0) — test-writer skipped.
- Pre-existing RED test suite from #1306 (47 tests) covers all AC lines.
- Passing through to builder.
[[2026-05-05]]
## Builder Notes
- Implementation: rewired MCP server registration to expose 6 mutation tools (`save_memory`, `list_memories`, `read_memory`, `curate_memory`, `delete_memory`, `approve_memory`) in `serve/mcp-memory/src/owlbear_mcp_memory/server.py`.
- Access-control removal: removed `caller` from `AppContext`, removed `OWLBEAR_MEMORY_CALLER` use in lifespan, removed `_caller_from_ctx` usage/helper in `serve/mcp-memory/src/owlbear_mcp_memory/tools.py`.
- Hint behavior: added brief-required approve hint in `approve_memory` (`"Entry approved. Now visible to scoped agents."`).
- Docs cleanup: removed stale env-var references from `serve/mcp-memory/README.md`, `share/skills/h-mcp-memory/SKILL.md`, and `share/skills/r-architecture-standards/SKILL.md`.
- Test compatibility fix: updated `tests/test_mcp_memory_tools_1273.py` import alias to source `query_memory` from tools module instead of server module.
- Tests: quality-runner scoped pass on `tests/test_mutation_tools_1306.py` -> 47 passed, 0 failed.
- Coverage: scoped report `owlbear_mcp_memory.server` 100%, `owlbear_mcp_memory.tools` 72% (overall scoped 79%).
- Lint: clean (`ruff` via quality-runner scoped lint paths).
- Evidence summary: AC-targeted suite from #1306 remains green after rewiring; no new lint errors.

### Post-task Reflection
- Mechanical API-surface rewires are low risk when implementation already exists in `tools.py`; most work was import/wrapper parity.
- Running quality-runner before and after patch exposed one introduced lint regression immediately (unused noqa), resolved with a one-line fix.
- Existing legacy test file `tests/test_mcp_memory_tools_1273.py` has independent red tests unrelated to #1307; scoped evidence to #1306 avoided false routing.
- Env-var deletion AC in this task is interpreted as active code + docs/skills scope, not historical briefs/research artifacts under `.owlbear/`.