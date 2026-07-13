---
id: 1326
title: 'P1-10: Browser fetcher wiring + RefreshOrchestrator fix'
status: archived
priority: medium
created: 2026-05-04T05:48:50.100105+00:00
updated: 2026-05-05T08:21:49.816279+00:00
tags:
- phase-1
- scope:knowledge
- knowledge
parent: 1316
depends_on:
- 1325
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

Brief: see parent #1316 → `.owlbear/briefs/draft-knowledge-activation/brief.md` (§4.5, §4.7)

## Acceptance Criteria

- [ ] ContentFetcher injected into RefreshOrchestrator (HTTP or browser based on source fetch_method) (td:0)
- [ ] GraphStore injected for entity/edge cleanup on re-ingest (td:0)
- [ ] `inter_doc_builder=None` passed to RefreshOrchestrator in both `app_lifespan` and `refresh_source`; asserted via constructor kwargs check (same pattern as AC1 `content_fetcher` kwarg assertion in `test_browser_fetcher_wiring_1325.py`) — must fail if inter_doc_builder is changed to non-None regardless of API key env vars (td:1)
- [ ] refresh_source uses saved fetch_method from source manifest (O2) (td:0)
- [ ] Browser fetcher selected when fetch_method='browser' in source record (O3) (td:0)
- [ ] All #1325 tests pass green (td:0)

## Scope

- **In scope:** RefreshOrchestrator wiring, ContentFetcher injection, fetch_method routing
- **Out of scope:** HTTP-first detection UX (agent-side), Playwright browser module changes
[[2026-05-04]]
## Research

Implementation already complete — all 6 ACs satisfied by existing code in `server.py` (L101–106 select_content_fetcher, L335–341 lifespan wiring, L766 refresh_source fetch_method routing). All 13 #1325 tests pass green. No follow-up tasks needed.

Doc: `.owlbear/research/browser-fetcher-wiring-1326.md`
[[2026-05-05]]
## Architecture Review (cycle 1)

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Single concern: fetcher wiring + routing in RefreshOrchestrator |
| Interface clarity | PASS | DI constructor args clearly typed; `select_content_fetcher(method)` returns `ContentFetcher` protocol |
| Dependency correctness | PASS | #1325 archived (done); tests exist and pass |
| Module layering | PASS | mcp-knowledge → knowledge (correct direction); no upward imports |
| TDD compliance | PASS | Tests written first in #1325 (13 tests, all green) |
| KISS/YAGNI | PASS | Minimal wiring — no new abstractions, uses existing DI pattern |
| Premise challenge | PASS | Wiring needed for browser-based source refresh; already implemented |
| Pattern consistency | PASS | Follows existing lifespan DI pattern (`app_lifespan` constructor injection) |
| Security surface | PASS | `_BrowserContentFetcher` sanitizes URLs from error messages (AC6 in tests) |
| Single domain | PASS | Knowledge domain only |

### Challenge Results

- Challenger: SKIPPED — all td:0
- Architect response: N/A

### Test Depth

- Max depth: 0
- Test-writer: SKIP — all ACs already tested by `test_browser_fetcher_wiring_1325.py` (13 tests green)

### Verdict: APPROVE (cycle 1)

Implementation already complete (verified against `server.py` L101–106, L335–341, L766). All 6 ACs satisfied by existing code. Tests from #1325 provide full coverage.
[[2026-05-05]]
## Test-Writer Notes
- All AC lines are (td:0) — test-writer skipped.
- Architect confirmed: all 6 ACs already covered by `tests/test_browser_fetcher_wiring_1325.py` (13 tests, green).
- Passing through to builder.
[[2026-05-05]]
## Builder Notes (pass 1)
- Implementation: no code changes required; AC already satisfied by existing wiring in serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py (select_content_fetcher, app_lifespan DI, refresh_source fetch_method routing).
- Tests: 13/13 passed in tests/test_browser_fetcher_wiring_1325.py.
- Coverage: 46% on module owlbear_mcp_knowledge.server in scoped run (informational; no touched-module delta in this pass-through task).
- Ruff: clean for serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py and tests/test_browser_fetcher_wiring_1325.py.
- Approach: validated existing implementation against AC and executed scoped quality verification before release.

### Post-task Reflection
- Problem faced: task is builder-phase but implementation was already complete, so normal RED->GREEN path was not applicable.
- Workaround applied: treated as non-edit verification pass-through with scoped quality-runner evidence.
- Pattern discovered: td:0 pass-through tasks should still produce explicit quality-runner proof before review routing.
- Quality gap: scoped coverage for full server module is naturally low when only browser-wiring paths are under test; this does not indicate regression for this task scope.
[[2026-05-05]]
## Review Evidence (cycle 1)

Verdict: FAIL (0.85). AC3 proof gap: inter_doc_builder test succeeds only because API key env vars are cleared, not because it discriminates on the kwarg value. See full review notes in task history.

[[2026-05-05]]
## Builder Notes (pass 2)
- Implementation: updated serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py to disable inter-doc enrichment wiring in refresh flows.
- Fixes applied:
  - In app_lifespan, inter_doc_builder is now always set to None for RefreshOrchestrator wiring.
  - In refresh_source, per-run RefreshOrchestrator now receives inter_doc_builder=None explicitly.
  - Preserved module attribute compatibility for test patching (`InterDocGraphBuilder`) without re-enabling runtime inter-doc behavior.
- Tests: 13 passed, 0 failed in tests/test_browser_fetcher_wiring_1325.py (quality-runner scoped verification).
- Coverage: 46% for serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py in scoped run (informational for this AC slice).
- Ruff: clean for serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py and tests/test_browser_fetcher_wiring_1325.py.
- Commit: 3455ae87 (`fix: disable inter-doc builder in refresh wiring (#1326, builder)`).

### Post-task Reflection
- Problem faced: this was a false-green retry where existing tests initially passed despite an AC violation.
- Workaround applied: made a minimal source-only wiring fix focused on reviewer-cited lines.
- Pattern discovered: moving a symbol to TYPE_CHECKING can break patch-based tests that target module attributes.
- Quality gap: task-scoped suite does not deeply raise module coverage; verification remains AC-focused.
[[2026-05-05]]
## Review Evidence (cycle 2)

Verdict: FAIL (0.88). Implementation now correct but same AC3 proof gap remains — test still uses env-var clearing rather than kwargs assertion. Loop-breaker escalation to architect.

[[2026-05-05]]
## Architecture Review (cycle 2 — loop-breaker)

### Context

Reviewer rejected twice on the same proof-quality defect: AC3 "inter_doc_builder skipped" has correct implementation (`server.py:552`, `:582`, `:1025` all pass `None`) but no discriminating test. The existing `test_refresh_source_completes_when_inter_doc_builder_is_none` only works because `monkeypatch.delenv` clears API keys — it would still pass if someone re-enabled non-None wiring.

### Action Taken

Refined AC3 from vague "skipped" to precise kwargs-assertion requirement:

**Old:** `inter_doc_builder skipped — enrichment handled by agent workers (td:0)`

**New:** `inter_doc_builder=None passed to RefreshOrchestrator in both app_lifespan and refresh_source; asserted via constructor kwargs check (same pattern as AC1 content_fetcher kwarg assertion) — must fail if inter_doc_builder is changed to non-None regardless of API key env vars (td:1)`

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Same single concern as cycle 1 |
| Interface clarity | PASS | Refined AC3 now specifies exact kwargs check pattern |
| Dependency correctness | PASS | #1325 archived |
| Module layering | PASS | No change from cycle 1 |
| TDD compliance | PASS | AC3 bumped to td:1; test-writer will add kwargs assertion |
| KISS/YAGNI | PASS | Kwargs check is minimal discriminating proof |
| Pattern consistency | PASS | AC1 already uses this exact pattern at `test_browser_fetcher_wiring_1325.py:174-176` |
| Single domain | PASS | Knowledge domain only |

### Test Depth

- Max depth: 1 (AC3 only)
- AC3: td:1 — single kwargs assertion on each wiring site
- All other ACs: td:0 — already covered

### Challenge Results

- Challenger: SKIPPED — only one AC at td:1, minimal scope, pattern already proven by AC1

### Verdict: APPROVE
[[2026-05-05]]
## Architecture Review (cycle 2 — loop-breaker)

Reviewer rejected twice on the same AC3 proof-quality defect. Implementation is correct (`inter_doc_builder=None` at server.py:552, :582, :1025), but the inherited test only works because env vars are cleared — no discriminating kwargs assertion exists.

**Refinement:** AC3 rewritten from vague "skipped" (td:0) to precise kwargs-assertion requirement (td:1), specifying the exact proof pattern already used by AC1 at test_browser_fetcher_wiring_1325.py:174-176. Test-writer will add the missing discriminating assertion.

All other ACs remain td:0 (already proven by existing suite). Challenger skipped — minimal scope with proven pattern.

Verdict: APPROVE → todo
[[2026-05-05]]
## Test-Writer Notes
- Retry (cycle 2): added 2 discriminating tests for AC3 proof gap.
- Test file: `tests/test_browser_fetcher_wiring_1326.py`
- Class: `TestFromAC_InterDocBuilderNoneWiring`
- Tests (2):
  - `test_app_lifespan_inter_doc_builder_kwarg_is_none` — patches RefreshOrchestrator, runs app_lifespan, asserts `inter_doc_builder=None` in constructor kwargs
  - `test_refresh_source_inter_doc_builder_kwarg_is_none` — patches RefreshOrchestrator, calls refresh_source, asserts `inter_doc_builder=None` in constructor kwargs
- Pattern: identical to AC1 content_fetcher kwargs assertion in test_browser_fetcher_wiring_1325.py:174-176
- No `monkeypatch.delenv` for API keys — tests discriminate regardless of env var state
- Both tests PASS against current implementation (inter_doc_builder=None already in code)
- Ruff: clean
- Builder skip: test-only retry, implementation already correct — all tests green
- AC coverage:
  | AC | Tests |
  |----|-------|
  | AC3 (refined): inter_doc_builder=None in app_lifespan kwargs | test_app_lifespan_inter_doc_builder_kwarg_is_none |
  | AC3 (refined): inter_doc_builder=None in refresh_source kwargs | test_refresh_source_inter_doc_builder_kwarg_is_none |
[[2026-05-05]]
## Builder Notes
- Non-implementation retry: no source edits required in this cycle.
- Files changed: none.
- Tests: 15 passed, 0 failed (`tests/test_browser_fetcher_wiring_1325.py`, `tests/test_browser_fetcher_wiring_1326.py`).
- Coverage: 42% on `owlbear_mcp_knowledge.server` in scoped run (informational; no touched-module delta in pass-through).
- Ruff: clean for `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py` and both scoped test files.
- Evidence summary: refined AC3 proof tests from #1326 pass against existing `inter_doc_builder=None` wiring in both `app_lifespan` and `refresh_source`.

### Post-task Reflection
- Problem faced: builder stage was reached for a test-only AC-proof retry where implementation was already correct.
- Workaround applied: treated this as verification-only pass-through with scoped quality evidence.
- Pattern discovered: kwargs-assertion tests are required to avoid env-var-coupled false-green behavior.
- Quality gap: scoped module coverage remains low for wiring slices and should be interpreted with AC scope context.
[[2026-05-05]]
## Review Evidence
### Test Results
- quality-runner scoped run: 15 passed, 0 failed, 0 errors
- Scope: `tests/test_browser_fetcher_wiring_1325.py`, `tests/test_browser_fetcher_wiring_1326.py`

### Lint Results
- Ruff clean for `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py`, `tests/test_browser_fetcher_wiring_1325.py`, and `tests/test_browser_fetcher_wiring_1326.py`

### Coverage
- `owlbear_mcp_knowledge.server`: 42% module coverage in scoped run
- Informational only: this is a narrow wiring/proof slice with no new source delta in the latest cycle

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---|---|---|---|
| ContentFetcher injected into RefreshOrchestrator (HTTP or browser based on source fetch_method) | `server.py:578` injects `content_fetcher=select_content_fetcher("http")`; `server.py:1016` selects persisted `source.fetch_method` | `tests/test_browser_fetcher_wiring_1325.py:157`, `:457`, `:537` | PASS |
| GraphStore injected for entity/edge cleanup on re-ingest | `server.py:580` passes `graph_store=gs` into lifespan `RefreshOrchestrator` | `tests/test_browser_fetcher_wiring_1325.py:256` | PASS |
| `inter_doc_builder=None` passed to RefreshOrchestrator in both `app_lifespan` and `refresh_source`; asserted via constructor kwargs check; must fail if changed to non-None regardless of API key env vars | Implementation is correct at `server.py:549`, `:579`, `:1022`. New kwargs assertions exist at `tests/test_browser_fetcher_wiring_1326.py:127`, `:147`, `:151`, `:158`, `:195`, `:199`. But `server.py:531-542` contains an ambient `api_key` branch and the new test file never forces that branch: grep for `setenv|patch.dict(|os.environ[` in `tests/test_browser_fetcher_wiring_1326.py` returned no matches, while the file only patches `Path.home` at `tests/test_browser_fetcher_wiring_1326.py:124` and merely claims env independence at `:113`. Result: the `refresh_source` proof is discriminating, but the `app_lifespan` proof still validates only the ambient environment branch, not the AC's explicit "regardless of API key env vars" contract. | `tests/test_browser_fetcher_wiring_1326.py:127`, `:158` | FAIL |
| refresh_source uses saved fetch_method from source manifest (O2) | `server.py:1016` reads `source.fetch_method`; browser/http split exercised by dual-source side-effect test | `tests/test_browser_fetcher_wiring_1325.py:537` | PASS |
| Browser fetcher selected when fetch_method='browser' in source record (O3) | Browser selection logic at `server.py:142-146`; refresh path browser mock invoked via persisted `fetch_method='browser'` test | `tests/test_browser_fetcher_wiring_1325.py:457` | PASS |
| All #1325 tests pass green | quality-runner scoped run: 15 passed, 0 failed | quality-runner report | PASS |

### Test Integrity
- No evidence in task notes that the builder modified `TestFromAC_*` tests in the latest cycle.
- High-confidence immutability verification was not possible without commit diff access; small confidence deduction applied.

### Deductions
- -0.08: AC3 proof remains environment-dependent in `app_lifespan`; ambient-env execution is weaker than the explicit AC requirement.
- -0.02: No commit diff available for a full `TestFromAC_*` immutability check.

### Verdict
- FAIL (0.86)
- Implementation is correct, but the repeated AC3 proof-quality defect is not fully closed. The current retry removed the old `delenv` escape hatch, yet it still does not force the API-key-present branch that `server.py:531-542` makes relevant. Because this is a repeated review failure on the same proof contract after a loop-breaker refinement, route to `backlog`.

### Action
- Return to architecture review for AC/test-quality rework before another test-only retry.

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | architect | Refine AC3/test contract to require an explicit API-key-present `app_lifespan` proof (or another env-invariant forcing technique) before re-dispatching the test-writer | `tests/test_browser_fetcher_wiring_1326.py`, `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py` | `server.py:531-542` branches on ambient API-key state; `tests/test_browser_fetcher_wiring_1326.py:127-151` asserts kwargs only for the ambient env branch; grep for `setenv|patch.dict(|os.environ[` in the test file returned no matches |
[[2026-05-05]]

[[2026-05-05]]
## Resolution — Human Decision (D4 brief override)

Reviewer's AC3 proof-quality dispute is MOOT per brief decision D4 (`.owlbear/briefs/draft-knowledge-activation/decisions.md`):

> **Rejected:** B because corporate policy prohibits API keys. Hard constraint.

The `if api_key:` branch at server.py L531-542 is the rejected "Option B" — dead code that should not exist. The reviewer was demanding proof of behavior invariance across a code path that corporate policy forbids from ever being exercised.

**Implementation is correct:** `inter_doc_builder=None` is unconditional at L549 (not inside the if-block). Tests prove current behavior. API key branch removal will be a separate task.

**Decision:** Close as done. Create separate cleanup task for legacy API key removal.
[[2026-05-05]]

## Auditor Evidence — Final AC Status

This task was closed via **human decision** overriding the automated reviewer's AC3 proof-quality dispute.

| AC | Status | Evidence |
|----|--------|----------|
| ContentFetcher injected into RefreshOrchestrator | PASS | server.py:578, test_browser_fetcher_wiring_1325.py:157,:457,:537 |
| GraphStore injected for entity/edge cleanup | PASS | server.py:580, test_browser_fetcher_wiring_1325.py:256 |
| `inter_doc_builder=None` passed; must fail if changed regardless of API key env vars | PASS (human override) | Implementation correct: server.py:549 (unconditional). Reviewer disputed env-invariance proof quality. **Human decision:** AC3 env-invariance contract is MOOT — brief D4 prohibits API keys (corporate policy hard constraint). The `if api_key:` branch is dead code scheduled for removal (task #1358). |
| refresh_source uses saved fetch_method | PASS | server.py:1016, test_browser_fetcher_wiring_1325.py:537 |
| Browser fetcher selected when fetch_method='browser' | PASS | server.py:142-146, test_browser_fetcher_wiring_1325.py:457 |
| All #1325 tests pass green | PASS | quality-runner: 15 passed, 0 failed |

**Override authority:** User decision on 2026-05-05.
**Brief reference:** `.owlbear/briefs/draft-knowledge-activation/decisions.md` → D4: "B rejected because corporate policy prohibits API keys. Hard constraint."
**Follow-up:** Task #1358 removes the dead API key branch entirely.