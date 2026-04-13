---
id: 836
title: 'Refactor mcp-browser tools to use ctx: Context + AppContext pattern'
status: in-progress
priority: important
created: '2026-04-11T15:28:49.513238+00:00'
updated: '2026-04-12T15:26:04.556004+00:00'
tags:
- phase-1
- scope:mcp-browser
- refactor
parent: 751
depends_on:
- 771
blocked: false
block_reason: null
claimed_by: null
claimed_at: null
---
Refactor all 6 mcp-browser tools (navigate, click, type, select, read_text, snapshot) to accept `ctx: Context` and access `DomainAllowlist` via `ctx.request_context.lifespan_context` instead of per-call env var reads.

**Source:** .owlbear/research/771-mcp-browser-server.md §3c (F2 tension)

**Why:** Current navigate() re-reads BROWSER_ALLOWED_DOMAINS on every call and creates a new DomainAllowlist. All 3 reference MCP servers use AppContext from lifespan_context. Tests in test_mcp_browser_775.py call navigate(url=...) directly, which prevents adding ctx without test updates.

**AC:**
- [ ] All 6 tools accept `ctx: Context` as first parameter
- [ ] navigate uses `ctx.request_context.lifespan_context.allowlist` instead of env read
- [ ] Tests updated to pass ctx (mock or via app_lifespan context)
- [ ] Existing test assertions unchanged (allowlist behavior preserved)
- [ ] ruff clean
[[2026-04-12]]
## Research
- Research doc: .owlbear/research/836-mcp-browser-ctx-refactor.md
- Sources: 8 studied, 5 high-relevance
- Recommendation: Add ctx: Context to all 6 tools, replace per-call env read in navigate() with lifespan allowlist. Only 5 of 22 tests need updating. (confidence: .90)
- Follow-up tasks created: #849 (RED — update AC3 tests), #850 (GREEN — add ctx to tools)
- Decision requests: none
- Tier: T1 — autonomous refactor to match established convention
[[2026-04-12]]
## Architecture Review

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Single concern: add ctx: Context to mcp-browser tools |
| Interface clarity | PASS | All 5 AC lines are specific and verifiable |
| Dependency correctness | PASS | #771 (impl) is done. See dependency correction below for children |
| Module layering | PASS | Changes stay within owlbear_mcp_browser.server, no upward imports |
| TDD compliance | PASS | Pipeline's natural RED/GREEN flow applies |
| KISS/YAGNI | PASS | Minimal scope matching established convention |
| Premise challenge | PASS | 3 other MCP servers use this pattern; browser is the outlier |
| Pattern consistency | PASS | Exact ctx: Context + AppContext pattern from mcp-kanban/knowledge/memory |
| Security surface | PASS | No new boundaries; allowlist behavior preserved (identical construction logic) |
| Single domain | PASS | scope:mcp-browser only |

### Codebase Evidence

- server.py already has AppContext(allowlist: DomainAllowlist) and app_lifespan wired to FastMCP
- navigate() lines 71-74 duplicate the env read + DomainAllowlist construction already in app_lifespan (lines 56-60)
- mcp-kanban server.py: `ctx: Context` first param, `app_ctx: AppContext = ctx.request_context.lifespan_context` (confirmed pattern)
- mcp-knowledge server.py: same pattern confirmed
- 5 tools (click, type_input, select, read_text, snapshot) take ctx for convention consistency and Phase 2 readiness (browser Page/session access), matching how mcp-knowledge tools accept ctx even when not all use it
- Only 5 of 22 tests affected (TestFromAC_NavigateToolError AC3) — mock pattern established in kanban tests

### AC Assessment

| AC Line | Assessment | Action |
|---------|-----------|--------|
| AC1: All 6 tools accept ctx: Context | Verifiable, pattern-consistent | None |
| AC2: navigate uses lifespan allowlist | Verifiable, specific attribute path given | None |
| AC3: Tests updated to pass ctx | Verifiable, 5 tests identified | None |
| AC4: Existing assertions unchanged | Verifiable, behavioral preservation | None |
| AC5: ruff clean | Verifiable, standard gate | None |

### Challenge Results

- Challenger: reconsider (confidence 0.72)
- Challenger confirmed architecture is sound; concerns were about subtask orchestration (#849/#850 dependency wiring), not #836 architecture
- Architect response: override justified — subtask wiring is an orchestration concern flagged below, does not affect #836's AC quality or architectural soundness

### Orchestration Notes

DEPENDS_ON-CORRECTION: task #850 should have depends_on [849] (GREEN must follow RED)

Children #849 (RED) and #850 (GREEN) overlap with #836's pipeline TDD flow. Orchestrator should decide: either process #836 through the pipeline directly (test-writer handles RED, builder handles GREEN) with #849/#850 superseded, or treat #836 as container and route work through children. Both paths produce the same result.

### Verdict: APPROVE
### Action Taken: Advanced to todo. Flagged #850 missing depends_on [849] for orchestrator correction.
[[2026-04-12]]
## Test-Writer Notes
- Test file: tests/test_mcp_browser_836.py
- Classes:
  - `TestFromAC_ToolsAcceptContext` — AC1: all 6 tools have ctx as first parameter
  - `TestFromAC_NavigateUsesLifespanAllowlist` — AC2: navigate reads allowlist from ctx, not env
  - `TestFromAC_AllToolsCallableWithCtx` — AC3: all tools invocable with mocked ctx
  - `TestFromAC_AllowlistBehaviorPreservedViaCtx` — AC4: blocked → ToolError, allowed → URL
- Tests per category: happy 6, edge 2, error 8, boundary 3
- Total: 19 tests, all FAIL (19 failed, 0 passed)
- Failure root cause: current tool signatures have no `ctx` param → TypeError on every call; AC1 signature assertions → AssertionError
- ruff: clean
- AC coverage:
  | AC line | Tests |
  |---------|-------|
  | AC1: 6 tools accept ctx | 6 signature tests (one per tool) |
  | AC2: navigate uses lifespan allowlist | 4 tests incl. env-vs-ctx inversion proofs |
  | AC3: tests pass ctx | 6 call tests (one per tool) |
  | AC4: allowlist behaviour preserved | 3 tests (blocked, allowed, deny-all) |
  | AC5: ruff clean | verified: 0 violations |
- Committed: 85868f00