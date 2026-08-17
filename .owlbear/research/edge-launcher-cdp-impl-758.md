# Edge Launcher + CDP Connection Manager — Implementation Research

> **Owning task:** #758 — P1-04: Impl — Edge launcher + CDP connection manager
> **Date:** 2026-04-10 **Status:** Complete

## 1. Context and Question

Task #758 is the GREEN phase for `serve/browser/` — implement `launcher.py` and
`cdp_manager.py` to pass the RED-phase tests from #755. Key questions:
1. What is the dependency chain status? Can this task proceed?
2. What package structure and implementation patterns should the builder follow?
3. What security constraints are non-negotiable?

## 2. Sources Studied

| # | Source | Location | Relevance |
|---|--------|----------|-----------|
| 1 | Playwright `connect_over_cdp` API | playwright.dev/python/docs/api/class-browsertype#browser-type-connect-over-cdp | .95 |
| 2 | Chrome 136 remote-debugging-port restriction | developer.chrome.com/blog/remote-debugging-port | .95 |
| 3 | #755 research (test strategy) | .owlbear/research/edge-launcher-cdp-tests-755.md | .95 |
| 4 | #752 research (CDP spike design) | .owlbear/research/cdp-spike-752.md | .90 |
| 5 | Brief — architect voice | .owlbear/briefs/draft-browser-knowledge-extraction/opinions/architect.md | .90 |
| 6 | Brief — security voice | .owlbear/briefs/draft-browser-knowledge-extraction/ | .90 |
| 7 | Existing package patterns | serve/knowledge/pyproject.toml, serve/orchestrator/src/ | .85 |
| 8 | ProcessSupervisor | serve/orchestrator/src/owlbear_orchestrator/process_supervisor.py | .80 |

## 3. Analysis

### 3.1 Dependency Chain Assessment

| Prerequisite | Task | Status | Ready? |
|--------------|------|--------|--------|
| CDP spike go-ahead | #753 | blocked (on #776) | **NO** |
| Spike script impl | #776 | research | **NO** |
| RED tests written | #755 | backlog | **NO** |

**#758 cannot proceed to implementation.** The CDP spike (#753) must produce a
GO decision before Phase 1 resources are committed (per brief risk §1). The
RED tests (#755) must exist and fail before GREEN phase begins (per TDD workflow).

### 3.2 Package Structure (validated against codebase patterns)

Following `serve/knowledge/` → `owlbear_knowledge` convention:

```
serve/browser/
  pyproject.toml          # name: owlbear-browser, deps: [playwright]
  src/owlbear_browser/
    __init__.py            # re-exports launcher + cdp public API
    launcher.py            # find_edge_binary(), launch_edge(), build_launch_args()
    cdp.py                 # CDPConnectionManager, connect/disconnect lifecycle
    _errors.py             # EdgeNotFoundError, CDPConnectionError, AuthenticationRequired
```

Workspace integration (automatic from `serve/*` glob in pyproject.toml):
- `tool.ruff.src` needs `"serve/browser/src"` entry
- `tool.coverage.run.source_pkgs` needs `"owlbear_browser"` entry
- `tests/test_package_boundary.py` ALLOWED_IMPORTS needs `owlbear_browser` entry

### 3.3 Implementation Approach Comparison

| Approach | Description | Risk | Fit |
|----------|-------------|------|-----|
| A: subprocess + connect_over_cdp | Find Edge, launch via subprocess, connect via Playwright CDP | Low — matches spike design, max diagnostic control | .85 |
| B: launch_persistent_context | Playwright manages lifecycle, channel="msedge" | Medium — abstracts away launch control, less diagnostic | .60 |
| C: Hybrid | launch_persistent_context for simple cases, subprocess for diagnostics | High — two code paths to maintain | .40 |

**Recommendation: Approach A** (.85 confidence). Matches the spike design (#752 §3.2),
maximizes diagnostic control, and tests in #755 are designed against this API shape.

### 3.4 Security Constraints (non-negotiable)

| Constraint | Source | Implementation |
|-----------|--------|----------------|
| CDP binds to 127.0.0.1 only | Brief security voice HR#4 | `--remote-allow-origins=http://127.0.0.1:{port}` |
| No wildcard origins | Brief security voice HR#4 | Never `--remote-allow-origins=*` |
| `--user-data-dir` mandatory | Chrome 136 [2] | Fresh profile dir, never default |
| Process cleanup on all exits | Architect warning §2 | async context manager with `__aexit__` |
| Subprocess error on missing binary | ProcessSupervisor pattern [8] | `EdgeNotFoundError` before launch |

### 3.5 Key Implementation Details

**Edge binary discovery (Windows):**
1. Check `EDGE_PATH` env var (override, priority 0)
2. Check `C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe` (priority 1)
3. Check `C:\Program Files\Microsoft\Edge\Application\msedge.exe` (priority 2)
4. Raise `EdgeNotFoundError` if all miss

**CDP connection lifecycle:**
```python
browser = await playwright.chromium.connect_over_cdp(f"http://127.0.0.1:{port}", is_local=True, timeout=30000)
context = browser.contexts[0]  # default context carries SSO session
```
- `is_local=True` — available since Playwright v1.58 [1], enables file-system optimizations
- Default timeout: 30s — appropriate for local CDP connection
- `browser.contexts[0]` accesses the default browsing context (SSO cookies live here)

**SSO detection patterns (from #752 §3.4, #755 §3g):**
- URL redirect to IdP: `page.url` differs from target, matches IdP URL pattern
- Login form present: `page.query_selector("input[type=password]")`
- HTTP 401/403 response status
- Fail-fast: raise `AuthenticationRequired`, caller aborts remaining URLs

## 4. Recommendation (.82 confidence)

**Block #758 until prerequisites clear.** The implementation approach is fully
validated and ready, but the dependency chain (#776 → #753 → go/no-go → #755 → #758)
must complete sequentially. Approach A (subprocess + connect_over_cdp) is confirmed
as the correct pattern.

**Tier: T1** — implementation follows approved architecture (brief + architect review
on #751). No new decisions needed beyond the CDP spike go/no-go gate (already a
T3 DR on #753's path).

Challenge: FALLBACK — no controversial recommendation to challenge; binary
dependency-chain assessment.

## 5. Follow-up Tasks

No new follow-up tasks needed. The prerequisite chain already exists:
- #776 → implement spike script (at research)
- #753 → execute spike, go/no-go (blocked on #776)
- #755 → RED tests (at backlog, awaiting #753 go-ahead)
- #758 → GREEN impl (this task, awaiting #755)

The task should remain at research status and advance to backlog only to indicate
the implementation approach is validated — but cannot proceed to in-progress until
#753 produces a GO decision and #755 tests exist.
