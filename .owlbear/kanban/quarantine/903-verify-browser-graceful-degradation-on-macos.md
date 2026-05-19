---
id: 903
title: Verify browser graceful degradation on macOS
status: archived
priority: important
created: 2026-04-16T22:54:41.795853+00:00
updated: 2026-04-17T03:21:42.002039+00:00
tags:
- phase-3
- scope:browser
- type:test
- platform
parent: 890
depends_on: []
blocked: false
block_reason:
claimed_by:
claimed_at:
---
Brief: see parent #890 and `.owlbear/briefs/draft-macos-compat/brief.md`

## Acceptance Criteria

- [ ] playwright_launcher.py reviewed: confirm non-Windows platforms handled gracefully (exception caught, not crash)
- [ ] MCP browser server reviewed: confirm startup on macOS does not crash (may return errors, but should not prevent server from running)
- [ ] Chrome extension path discovery reviewed: confirm macOS paths not attempted (deferred per D3)
- [ ] Evidence documented: file paths, line numbers, exception handling patterns found
- [ ] No code changes needed (verify only) — if changes ARE needed, create follow-up task

## Files

- `serve/browser/` (read only)
- `serve/mcp-browser/` (read only)
[[2026-04-17]]

## Research

- Research doc: .owlbear/research/browser-macos-degradation-903.md
- Sources: 5 studied, 3 high-relevance (playwright_launcher.py, server.py,_errors.py)
- Recommendation: No code changes needed — graceful degradation verified (confidence: .95)
- Follow-up tasks created: none (future browser macOS support already tracked in brief)
- Decision requests: none

## Challenge Results

- Challenger: SKIP — info-only verification, no design recommendation to challenge
- Confidence in original: .95
- Key challenges: n/a
- Researcher response: n/a

## Findings Summary

1. `playwright_launcher.py` raises `SSOExtensionNotFoundError` on macOS (typed exception, not crash)
2. MCP server `app_lifespan` catches all launch exceptions — degrades to no-browser mode, server keeps running
3. No macOS-specific Chrome extension paths attempted — aligned with D3 deferral
4. All browser tools handle None page/fetcher gracefully: navigate returns URL, click/type/select raise ToolError, read_text/snapshot return empty string
[[2026-04-17]]

## Architecture Review

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | One concern: verify browser graceful degradation on macOS |
| Interface clarity | PASS | AC specifies exact files, behaviors, exception types, and evidence format |
| Dependency correctness | PASS | No dependencies — independent verification task |
| Module layering | PASS | Read-only, no code changes |
| TDD compliance | PASS | Tagged `type:test` — pass-through |
| KISS/YAGNI | PASS | Minimal scope — audit only |
| Premise challenge | PASS | Required by parent #890; #905 depends on this |
| Pattern consistency | PASS | N/A — no code changes |
| Security surface | PASS | No new system boundaries |
| Single domain | PASS | Browser domain only |

### Codebase Verification

Independently confirmed all 3 research findings:

1. `playwright_launcher.py` L44-59: `find_sso_extension()` raises typed `SSOExtensionNotFoundError` on macOS (LOCALAPPDATA empty → path doesn't exist)
2. `server.py` L78-82: `app_lifespan` bare `except Exception` catches all launch failures, sets launcher/page/fetcher to None. Tools degrade: navigate returns URL, click/type/select raise ToolError, read_text/snapshot return cached content
3. Zero macOS-specific paths in `serve/browser/` or `serve/mcp-browser/` — no darwin/Library/Application Support references

### Challenge Results

- Challenger: FALLBACK — no challenger agent available in session
- Architect assessment: verification-only task with no design decisions to challenge; research confidence .95 with direct code evidence

### Verdict: APPROVE

### Action Taken: Advanced to todo. Read-only verification task with precise AC and thorough research backing. Already tagged `type:test` for pass-through

[[2026-04-17]]

## Test-Writer Notes

- Non-implementation task (tagged `type:test`) — pass-through per w-tdd-red Step 1a.
- Passing through to builder.

**Why no RED tests:**
All three verification targets are already fully implemented in the codebase:

1. `playwright_launcher.py` — `find_sso_extension()` raises `SSOExtensionNotFoundError` (RuntimeError subclass) when LOCALAPPDATA absent; this behavior is already exercised by `tests/test_playwright_launcher_868.py` (5 passing tests).
2. `app_lifespan` — bare `except Exception` on lines 78-82 of `server.py` already catches all launch failures and degrades to `AppContext(launcher=None, page=None, fetcher=None)`; covered by `tests/test_mcp_browser_server_871.py`.
3. Tool degradation (navigate returns URL, click/type/select raise ToolError, read_text/snapshot return empty) — covered by `tests/test_mcp_browser_session_853.py`, `test_mcp_browser_877.py`, et al.
4. No macOS Chrome paths — confirmed by research (grep verified zero `darwin`/`Library` references in `serve/browser/`).

Any new tests verifying these behaviors would be GREEN immediately, contradicting the RED-phase requirement.

Architect confirmed pass-through: "TDD compliance | PASS | Tagged `type:test` — pass-through" (see Architecture Review in task body).
[[2026-04-17]]

## Builder Notes

- Non-implementation task — no code changes needed.
- Passing through to review.
[[2026-04-17]]

## Review Evidence

### Test Results

- pytest: 69 passed, 0 failed (test_playwright_launcher_868, test_mcp_browser_server_871, test_mcp_browser_session_853, test_mcp_browser_877)

### Lint: clean

### Coverage

- `owlbear_browser.playwright_launcher`: 95%
- `owlbear_mcp_browser.server`: 82%

### Pass 1 — CRITICAL

#### Test-Writer AC Coverage

No `TestFromAC_*` classes for task #903 — pass-through task, conditional skip.
Existing tests cited by test-writer were verified independently (see AC Compliance below).

#### Security Review

No code changes — no new security surface. No issues.

#### Test Integrity

No `TestFromAC_*` classes introduced — conditional skip.

#### Test Quality

Pass-through task — no new tests written. Existing tests evaluated for AC coverage adequacy (see AC Compliance).

#### Data Safety

No code changes — no data safety concerns.

#### Implementation-Aware Gaps

No code changes — not applicable.

#### Builder Process Quality

| Metric | Value |
|---|---|
| Builder Notes sections | 1 |
| Approach variation | N/A (pass-through) |
| Assessment | CLEAN |

### Pass 2 — INFORMATIONAL

- None.

### AC Compliance

| AC Line | Evidence | Mapped Test | Status |
|---|---|---|---|
| playwright_launcher.py reviewed: non-Windows platforms handled gracefully (exception caught, not crash) | `find_sso_extension()` ~L41-59: reads `LOCALAPPDATA` env var (empty on macOS) → path doesn't exist → raises typed `SSOExtensionNotFoundError`. Not a crash. | `TestFromAC_SSOExtensionDiscovery::test_raises_when_extension_dir_missing` (test_playwright_launcher_868.py) | PASS |
| MCP browser server reviewed: startup on macOS does not crash | `server.py` L78-82: bare `except Exception: # noqa: BLE001` catches all launch exceptions including `SSOExtensionNotFoundError` → sets launcher/page/fetcher=None → yields degraded AppContext. Server continues running. | test_mcp_browser_server_871.py (lifespan wiring tests) | PASS |
| Chrome extension path discovery reviewed: macOS paths not attempted (deferred per D3) | Grep over `serve/browser/` and `serve/mcp-browser/`: zero matches for `darwin`, `Library/Application Support`, `macos`, `macOS`. Only `LOCALAPPDATA` (Windows env var) used for path resolution. | Structural verification — no test needed | PASS |
| Evidence documented: file paths, line numbers, exception handling patterns found | Research doc in task body references: playwright_launcher.py L44-59, server.py L78-82, grep-verified zero macOS paths. All three independently confirmed by reviewer. | N/A | PASS |
| No code changes needed (verify only) | Builder confirmed no changes. No changed files in workspace. No follow-up tasks created. | N/A | PASS |

### Confidence: .93

### Verdict: PASS

[[2026-04-17]]

## Docs Gate

| # | Item | Applies? | Status | Evidence |
|---|------|----------|--------|---------|
| 1 | Behavior/API change → copilot-instructions.md | No | N/A | Read-only verification task; no code changes |
| 2 | Module docstrings | No | N/A | No Python modules created or modified |
| 3 | External attribution → sources/overview.md | No | N/A | All 5 sources are internal (codebase files + brief); no external URLs or articles |
| 4 | CLI changes → README.md | No | N/A | No CLI changes |
| 5 | Research doc | Yes | PASS | `.owlbear/research/browser-macos-degradation-903.md` exists and is linked from task body; follow-up tasks noted as none (future macOS browser support tracked in brief) |

**Files updated:** none
**Scratch files cleaned:** none found (`.owlbear/scratch/903-*` — zero matches)
[[2026-04-17]]

## Audit

### AC Verification

| AC Line | Evidence | Status |
|---------|----------|--------|
| playwright_launcher.py reviewed: non-Windows handled gracefully | playwright_launcher.py L41-59: find_sso_extension() raises typed SSOExtensionNotFoundError on empty LOCALAPPDATA. Confirmed independently. | PASS |
| MCP browser server startup on macOS does not crash | server.py L78-82: bare except Exception catches all launch failures, sets launcher/page/fetcher=None. Server continues. Confirmed independently. | PASS |
| Chrome extension path discovery: macOS paths not attempted | Grep verified zero matches for darwin/Library/Application Support/macOS in serve/browser/ and serve/mcp-browser/. | PASS |
| Evidence documented: file paths, line numbers, patterns | Research doc at .owlbear/research/browser-macos-degradation-903.md exists. Line numbers cited throughout task body (L41-59, L78-82). | PASS |
| No code changes needed (verify only) | Builder confirmed no changes. No modified files. No follow-up tasks created. | PASS |

### Test Results

- pytest (full suite): 4470 passed, 230 failed, 196 skipped. 230 failures are pre-existing (task changed zero files). Browser-scoped tests: 69 passed, 0 failed (per reviewer).
- ruff: clean (exit 0)

### Architect Quality: 5/5

Precise AC: named specific files, behaviors to verify, exception types, evidence format, and guard rail for follow-up task creation. Clean verification path.

### Deduction Breakdown

- AC lines with no evidence: 0 (all 5 PASS)
- Lint violations: 0
- AC quality: 5/5 (no deduction)
- Reviewer evidence: present and thorough (no deduction)
- Full-suite failures in task scope: 0 (no deduction)
- Note: 230 pre-existing full-suite failures observed, none attributable to this task (zero code changes)

### Confidence: 1.00

### Action: archive
