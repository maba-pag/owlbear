# Browser Graceful Degradation on macOS — Verification

> **Owning task:** #903 — Verify browser graceful degradation on macOS
> **Date:** 2026-04-17 **Status:** Complete

## 1. Context and Question

Parent task #890 (macOS compatibility) scopes browser features as deferred (D3). This task verifies that the existing browser code does not crash on macOS — it should fail gracefully with caught exceptions, not prevent the MCP server from running.

Three verification targets from the AC:
1. `playwright_launcher.py` — non-Windows exception handling
2. MCP browser server — startup on macOS
3. Chrome extension path discovery — no macOS paths attempted

## 2. Sources Studied

| # | Source | Type | Relevance |
|---|--------|------|-----------|
| S1 | `serve/browser/src/owlbear_browser/playwright_launcher.py` | Codebase | 1.0 |
| S2 | `serve/mcp-browser/src/owlbear_mcp_browser/server.py` | Codebase | 1.0 |
| S3 | `serve/browser/src/owlbear_browser/_errors.py` | Codebase | 0.9 |
| S4 | `serve/browser/src/owlbear_browser/fetcher.py` | Codebase | 0.7 |
| S5 | `.owlbear/briefs/draft-macos-compat/brief.md` (D3) | Brief | 0.8 |

## 3. Analysis

### AC 1: playwright_launcher.py — non-Windows exception handling

| Behaviour | Evidence |
|-----------|----------|
| `find_sso_extension()` checks `SSO_EXTENSION_PATH` env var first | L42–46: override path, raises `SSOExtensionNotFoundError` if missing |
| Falls back to `LOCALAPPDATA` (Windows-only) | L49: `os.environ.get("LOCALAPPDATA", "")` → empty string on macOS |
| Empty `LOCALAPPDATA` → non-existent relative path → `SSOExtensionNotFoundError` | L50–53: `ext_root.exists()` is False → raises named exception |
| `SSOExtensionNotFoundError` is a `RuntimeError` subclass | `_errors.py` L9 |
| No unhandled crash path — all failure modes raise typed exceptions | Verified: no bare asserts, no `sys.exit`, no uncaught OS calls |

**Verdict: PASS.** On macOS, `find_sso_extension()` raises `SSOExtensionNotFoundError`. This is a clean, typed exception — not a crash.

### AC 2: MCP browser server — startup doesn't crash

| Behaviour | Evidence |
|-----------|----------|
| `app_lifespan` wraps `launcher.launch()` in bare `except Exception` | `server.py` L58–64: catch-all sets launcher/page/fetcher to `None` |
| Server yields `AppContext` with all browser fields `None` | L66: `yield AppContext(allowlist=..., launcher=None, ...)` |
| `navigate()` degrades to dry-run (returns URL string) | L88–99: checks fetcher, then page, both None → returns url |
| `click/type/select` raise `ToolError("No browser session")` | L102–125: proper MCP error, not server crash |
| `read_text/snapshot` return empty `last_content` string | L128–145: `getattr(app_ctx, "last_content", "")` |

**Verdict: PASS.** MCP server starts, runs, responds to tool calls. Browser-dependent tools return errors/empty via MCP protocol. Server process never crashes.

### AC 3: Chrome extension path discovery — no macOS paths

| Behaviour | Evidence |
|-----------|----------|
| Only Windows path structure used | L24: `_EXT_REL = Path("Google") / "Chrome" / "User Data" / ...` |
| No `~/Library/Application Support/Google/Chrome/` reference | Grep for `darwin\|macos\|Library` across `serve/browser/` — zero hits |
| No `sys.platform` / `os.name` branching | Grep confirmed: no platform detection in either package |
| Aligned with D3 (browser features deferred) | Brief explicitly scopes out macOS browser discovery |

**Verdict: PASS.** No macOS-specific paths attempted. Extension discovery is Windows-only. Deferred per D3.

## 4. Recommendation

**No code changes needed.** All three verification targets pass. The existing exception handling and catch-all patterns provide clean graceful degradation on macOS.

Confidence: **.95** — high certainty from direct code inspection. All failure paths are typed exceptions caught by the MCP server lifespan.

Challenge: SKIP — info-only verification task with no design recommendation to challenge.

## 5. Follow-up Tasks

No follow-up tasks needed. The brief already tracks "Browser macOS support" as explicit future work (out of scope). No new issues discovered during verification.
