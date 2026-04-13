---
id: 850
title: 'GREEN: Add ctx: Context to all 6 mcp-browser tools, use lifespan allowlist'
status: in-progress
priority: important
created: '2026-04-12T12:52:52.115593+00:00'
updated: '2026-04-12T17:03:10.340109+00:00'
tags:
- phase-1
- scope:mcp-browser
- tdd-green
parent: 836
depends_on: []
blocked: false
block_reason: null
claimed_by: null
claimed_at: null
---
Add `ctx: Context` as first parameter to all 6 mcp-browser tools (navigate, click, type, select, read_text, snapshot). In navigate(), replace per-call `os.environ.get("BROWSER_ALLOWED_DOMAINS")` + `DomainAllowlist` construction with `ctx.request_context.lifespan_context.allowlist`.

**Source:** .owlbear/research/836-mcp-browser-ctx-refactor.md §3a

**AC:**
- [ ] `from mcp.server.fastmcp import Context, FastMCP` in server.py
- [ ] All 6 tools accept `ctx: Context` as first parameter
- [ ] navigate() uses `ctx.request_context.lifespan_context.allowlist` — no env var read
- [ ] All 22 tests in test_mcp_browser_775.py pass
- [ ] ruff clean

**Affected files:** `serve/mcp-browser/src/owlbear_mcp_browser/server.py`
[[2026-04-12]]
## Research
- Research doc: .owlbear/research/836-mcp-browser-ctx-refactor.md (validation pass — existing doc covers this task as §3a)
- Sources: 8 studied (parent doc), 5 high-relevance — all claims verified against current codebase
- Recommendation: Add ctx: Context to all 6 tool signatures, replace navigate() env read with ctx.request_context.lifespan_context.allowlist. Exact pattern from mcp-kanban/knowledge/memory servers. (confidence: .92)
- Follow-up tasks created: none — this IS the follow-up task from #836 research
- Decision requests: none
- Tier: T1 — autonomous refactor matching established convention

## Challenge Results
- Challenge: FALLBACK — trivial GREEN phase, single viable approach dictated by convention. No recommendation to challenge.

## Validation Evidence
- server.py L22-24: AppContext(allowlist: DomainAllowlist) exists
- server.py L56-61: app_lifespan already yields AppContext with allowlist
- server.py L69-76: navigate() duplicates env read (target for removal)
- 3 reference servers confirmed ctx: Context + lifespan_context pattern
- Mock pattern _make_mcp_ctx established in test_mcp_kanban_create_task_475.py L68-75
- Only 5 of 22 tests affected (TestFromAC_NavigateToolError) — handled by sibling #849

## Dependency Note
DEPENDS_ON-CORRECTION (flagged by architect on #836): #850 should have depends_on [849]. GREEN cannot proceed until RED (#849) completes test updates. Cannot set via edit_task — orchestrator should correct.
[[2026-04-12]]
## Architecture Review

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | One concern: add ctx: Context to 6 tools, wire navigate() to lifespan allowlist |
| Interface clarity | PASS | AC specifies exact import, parameter position, attribute path, test+lint gates |
| Dependency correctness | PASS | #849 (RED) must complete first. DEPENDS_ON-CORRECTION already flagged by #836 architect review — #850 should have depends_on [849]. Reaffirm here |
| Module layering | PASS | Changes scoped to owlbear_mcp_browser.server, no upward imports |
| TDD compliance | PASS | Sibling #849 (RED) precedes this GREEN task |
| KISS/YAGNI | PASS | Minimal scope matching established convention across 3 reference servers |
| Premise challenge | PASS | 3 MCP servers (kanban, knowledge, memory) use ctx: Context — browser is the outlier |
| Pattern consistency | PASS | Exact pattern: ctx: Context first param, app_ctx = ctx.request_context.lifespan_context |
| Security surface | PASS | No new boundaries. Allowlist behavior preserved — same DomainAllowlist, sourced from lifespan instead of per-call env read |
| Single domain | PASS | scope:mcp-browser only |

### Codebase Evidence

- server.py L13: currently imports FastMCP only — AC1 adds Context to import
- server.py L22-24: AppContext(allowlist: DomainAllowlist) already exists
- server.py L56-61: app_lifespan yields AppContext with allowlist — lifespan_context ready
- server.py L69-76: navigate() duplicates env read + DomainAllowlist construction (removal target)
- server.py L79-106: 5 other tools (click, type_input, select, read_text, snapshot) need ctx added
- mcp-kanban server.py: every tool takes ctx: Context first, uses ctx.request_context.lifespan_context (confirmed L106, L170, L178, L220, L287, L297, L379)
- mcp-knowledge server.py: same pattern across all 11 tools (confirmed L269-540)

### AC Assessment

| AC Line | Assessment | Action |
|---------|-----------|--------|
| AC1: import Context, FastMCP | Verifiable, one-line change | None |
| AC2: All 6 tools accept ctx: Context | Verifiable, matches reference servers | None |
| AC3: navigate() uses lifespan allowlist, no env read | Verifiable, specific attribute path | None |
| AC4: All 22 tests pass | Verifiable, standard test gate | None |
| AC5: ruff clean | Verifiable, standard lint gate | None |

### Failure Mode Map

No new failure modes. navigate() allowlist check is preserved — PermissionError raised as ToolError unchanged. Source of allowlist changes from per-call env read to lifespan context (identical DomainAllowlist construction in app_lifespan).

### Challenge Results

- Challenger: FALLBACK — no challenger agent available in current session
- Prior challenge from research phase: FALLBACK — trivial GREEN, single viable approach dictated by convention
- Confidence: .94

### Dependency Note (reaffirmed)

DEPENDS_ON-CORRECTION: #850 should have depends_on [849]. GREEN cannot proceed until RED completes. Originally flagged by architect on #836, reaffirmed here.

### Verdict: APPROVE
### Action Taken: Advanced to todo. Dependency correction on #850 reaffirmed for orchestrator.
[[2026-04-12]]
## Test-Writer Notes

**File:** `tests/test_mcp_browser_ctx_850.py`
**Classes:** `TestFromAC_CtxParameterOnAllTools`, `TestFromAC_NavigateUsesLifespanCtx`

### AC coverage

| AC | Tests |
|----|-------|
| AC1: `from mcp.server.fastmcp import Context, FastMCP` | Verified implicitly — ctx: Context type hint on all 6 tools requires the import; no standalone test needed |
| AC2: All 6 tools accept `ctx: Context` as first parameter | ✅ 5 tests (click, type_input, select, read_text, snapshot); navigate covered by `TestFromAC_NavigateToolError` in test_mcp_browser_775.py (#849) |
| AC3: navigate() uses lifespan_context.allowlist — no env var read | ✅ 3 tests (env-only allowlist blocked, ctx-only allowlist permitted, env-only domain blocked by ctx) |
| AC4: All 22 tests in test_mcp_browser_775.py pass | Gate for builder — not test-writer scope |
| AC5: ruff clean | ✅ applied to test file — clean |

### Test categories

| Category | Count |
|----------|-------|
| Happy path | 3 (click/type_input/select return value; navigate permits ctx-allowed URL) |
| Error path | 4 (navigate raises ToolError in 3 ctx-allowlist scenarios; read_text/snapshot type error confirms no ctx) |
| Boundary | 1 (env var has domain but ctx is empty — confirms source of allowlist) |
| **Total** | **8** |

### Fail verification
`pytest tests/test_mcp_browser_ctx_850.py -q` → **8 failed, 0 passed**
- `TestFromAC_CtxParameterOnAllTools`: `TypeError: <fn>() got multiple values for argument 'selector'` (click, type_input, select); `TypeError: <fn>() takes 0 positional arguments but 1 was given` (read_text, snapshot)
- `TestFromAC_NavigateUsesLifespanCtx`: `TypeError: navigate() got multiple values for argument 'url'` (navigate still has old signature)
- `ruff check`: All checks passed ✓

### Commit
`7d1e0383` — test: RED phase for ctx: Context on all 6 browser tools (#850, test-writer)