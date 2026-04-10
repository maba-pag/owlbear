# CDP Spike Implementation — Validation Pass

> **Owning task:** #776 — P0-01: Implement cdp-spike.py per research #752
> **Date:** 2026-04-10 **Status:** Complete

## 1. Context and Question

#776 was created as a follow-up from #752's research. The design in
`.owlbear/research/cdp-spike-752.md` §3.3 provides a 10-step script design.
Question: Is the design complete enough for a builder to implement directly,
and are there any gaps between the design and the #776 AC?

This is a **validation pass** — the primary research was completed in #752.

## 2. Sources Studied

| # | Source | URL/Location | Relevance |
|---|--------|-------------|-----------|
| 1 | Playwright `connect_over_cdp` API | playwright.dev/python/docs/api/class-browsertype#browser-type-connect-over-cdp | .95 |
| 2 | Chrome 136 blog post | developer.chrome.com/blog/remote-debugging-port | .95 |
| 3 | CDP spike research #752 | .owlbear/research/cdp-spike-752.md | .95 |
| 4 | Brief security voice | .owlbear/briefs/draft-browser-knowledge-extraction/voices/security.md | .90 |
| 5 | Edge launcher research #755 | .owlbear/research/edge-launcher-cdp-tests-755.md | .85 |
| 6 | Edge impl research #758 | .owlbear/research/edge-launcher-cdp-impl-758.md | .85 |
| 7 | Existing scratch scripts | .owlbear/scratch/*.py | .70 |

## 3. Analysis

### 3.1 Source Verification (Primary Claims)

| Claim from #752 | Verified? | Source |
|-----------------|-----------|--------|
| `connect_over_cdp` stable since v1.9 | Yes | Playwright docs: "Added in: v1.9" [1] |
| `is_local` param since v1.58 | Yes | Playwright docs: "Added in: v1.58" [1] |
| Default timeout 30000ms | Yes | Playwright docs: "Defaults to 30000 (30 seconds)" [1] |
| `browser.contexts[0]` for default context | Yes | Playwright docs usage example confirms [1] |
| Chrome 136 requires `--user-data-dir` | Yes | "must now be accompanied by the `--user-data-dir` switch" [2] |
| No `playwright install` needed for CDP | Yes | `connect_over_cdp` connects to existing browser, not bundled [1] |

All primary claims hold. No API changes since #752 was written.

### 3.2 AC vs Design Gap Analysis

| AC | #752 §3.3 Coverage | Gap? |
|----|---------------------|------|
| 1. Script at `.owlbear/scratch/cdp-spike.py` | Step 1-10 yes | — |
| 2. Runnable with `uv run` | §3.6: `uv pip install playwright` | — |
| 3. Find Edge at standard Windows paths | Step 1 | — |
| 4. Launch with `--remote-debugging-port` + `--user-data-dir` | Steps 2-3 | **Gap A** |
| 5. `connect_over_cdp("http://127.0.0.1:9222", is_local=True)` | Step 5 | — |
| 6. Navigate configurable URL | Step 6 | **Gap B** |
| 7. Detect SSO redirect vs auto-auth vs login | Steps 7, §3.4 | — |
| 8. Extract `page.inner_text("body")` | Step 8 | — |
| 9. Error handling from §3.4 | §3.4 (8 cases) | — |
| 10. Log timestamps for EDR | §3.5 | — |
| 11. Cleanup on all exit paths | Step 10 | **Gap C** |

### 3.3 Gap Details

**Gap A — `--remote-allow-origins` missing from design.** Research #755 §3e and #758
§3.4 both specify `--remote-allow-origins=http://127.0.0.1:{port}` as a security
requirement from brief HR#4. The #752 design §3.3 omits this arg. While CDP already
binds to 127.0.0.1 by default, the flag provides defense-in-depth against Origin
header spoofing. Builder should add it to launch args.

**Gap B — URL configuration mechanism unspecified.** AC says "configurable target URL"
but neither AC nor design specifies how. For a scratch spike: `TARGET_URL` env var
with argparse fallback is the simplest approach. Matches existing scratch script
conventions (minimal, no frameworks).

**Gap C — Signal handler for cleanup.** Design says "disconnect, terminate subprocess"
but doesn't specify how to handle Ctrl+C or unexpected exit. For a spike script:
`try/finally` block is sufficient; `atexit` or signal handler is optional hardening.

### 3.4 Implementation Approach

| Aspect | Recommendation | Rationale |
|--------|---------------|-----------|
| API style | Sync Playwright (`sync_api`) | Spike is linear diagnostic, not concurrent |
| Subprocess | `subprocess.Popen` | Standard for simple scripts; codebase uses `asyncio.create_subprocess_exec` but that's for production async code |
| URL config | `argparse` + env var `TARGET_URL` | Minimal, self-documenting |
| Script size | ~120-140 LOC | Matches #752 estimate; gap fixes add ~20 LOC |
| Dependencies | `playwright` only | Install via `uv pip install playwright`; no `playwright install` needed |

### 3.5 Edge Paths (Windows, from #755 §3d)

| Priority | Path |
|----------|------|
| 0 (override) | `EDGE_PATH` env var |
| 1 | `C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe` |
| 2 | `C:\Program Files\Microsoft\Edge\Application\msedge.exe` |

## 4. Recommendation (.85 confidence)

**Proceed to implementation.** The #752 design is complete with three minor gaps
(A, B, C above). All are addressable by the builder without additional research.
The Playwright API and Chrome 136 restriction are verified against primary sources.

Builder instructions: implement #752 §3.3 design with these additions:
1. Add `--remote-allow-origins=http://127.0.0.1:9222` to Edge launch args (Gap A)
2. Use `argparse` with `TARGET_URL` env var fallback for URL config (Gap B)
3. Wrap Steps 5-9 in `try/finally` ensuring disconnect + subprocess terminate (Gap C)

Challenge: FALLBACK — validation pass of pre-existing design; no controversial
recommendation to challenge.

## 5. Follow-up Tasks

None created — #776 itself is the implementation task. Advancing to backlog.
