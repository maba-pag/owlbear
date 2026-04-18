# SSRF Pre-Flight Check for navigate() in mcp-browser

> **Owning task:** #950 — Add SSRF pre-flight check to navigate() in mcp-browser server
> **Date:** 2026-04-18 **Status:** Complete

## 1. Context and Question

Task #949 identified three code-level SSRF gaps in `navigate()` (mcp-browser server.py). This task validates the implementation approach for the pre-flight check, resolves the `_is_blocked_ip` sharing question, and documents known limitations.

The `DomainAllowlist` checks hostnames but not resolved IPs or URL schemes. `page.goto()` cannot connect to pre-resolved IPs — Playwright's constraint makes the `_web_read`-style TOCTOU mitigation (URL rewrite + Host header) impossible here.

## 2. Sources Studied

| # | Source | Relevance | What was taken |
|---|--------|-----------|----------------|
| 1 | `serve/mcp-browser/src/owlbear_mcp_browser/server.py` | 1.0 | navigate() code paths: 2 direct `page.goto()` + 1 indirect via `fetcher.fetch()` |
| 2 | `serve/mcp-browser/src/owlbear_mcp_browser/allowlist.py` | 1.0 | Closed-by-default, domain-only check; `javascript://host` passes if host is allowlisted |
| 3 | `.owlbear/research/949-ssrf-browser-fetcher.md` | 0.9 | Option A/B/C/D analysis, Playwright constraint, recommendation |
| 4 | `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py` L156-227 | 0.9 | Proven `_is_blocked_ip` + `_web_read` SSRF pattern from #946 |
| 5 | Task #947 AC (in-progress) | 0.7 | Plans `_ssrf.py` utility in `owlbear_knowledge` — NOT a shared package |
| 6 | Playwright `page.goto()` docs | 0.8 | No IP+Host support; `browser_context.route()` intercepts all requests |

## 3. Analysis

### 3.1 Implementation Approach: Option C (pre-flight DNS + IP check + scheme check)

| Criterion | Option C (pre-flight) | Option B (context.route interceptor) |
|-----------|----------------------|--------------------------------------|
| LOC | ~25 | ~40 |
| Covers navigate() paths | Yes (all 3) | Yes (all 3) |
| Covers click-triggered nav | No | Yes |
| Covers redirect SSRF | No | Yes |
| TOCTOU risk | Yes (DNS rebinding) | No |
| KISS score | .80 | .65 |
| Priority-appropriate | Yes (nice-to-have) | Over-engineered for priority |

### 3.2 `_is_blocked_ip` Sharing Decision

| Option | Pros | Cons |
|--------|------|------|
| Import from `owlbear_knowledge._ssrf` | DRY | Wrong dep direction: `mcp-browser` → `owlbear-knowledge` for 20 LOC |
| Duplicate locally (~20 LOC) | Self-contained, correct layering | 4th copy (DRY tech debt) |
| New shared utility package | True DRY | YAGNI for 20-line function |

**Decision:** Duplicate locally. The function is pure stdlib (`ipaddress`), stable, and small. Cross-package dep for utility code violates KISS. Acknowledged as tech debt — a future shared-utility extraction task is warranted after #947/#948 complete.

### 3.3 Scheme Check Criticality

The challenger identified that `urlparse("javascript://example.com/...")` yields `hostname='example.com'`. If that domain is allowlisted, `DomainAllowlist.check()` passes the URL. The scheme check is a **required security control**, not optional defense-in-depth.

### 3.4 Known Limitations (post-challenge)

| Limitation | Risk | Mitigation |
|------------|------|------------|
| TOCTOU: DNS rebinding between `getaddrinfo()` and `page.goto()` | Low — requires compromised DNS for allowlisted domain | DomainAllowlist closed-by-default; agent-only access |
| Click-triggered navigation bypasses pre-flight | Low — requires allowlisted page with link to internal IP | Would require Option B to cover; accepted for nice-to-have priority |
| `BrowserContentFetcher.fetch()` is a public API without its own check | Low — not wired outside navigate() today | Future callers should add protection; navigate() covers current paths |

## 4. Recommendation

**(rec:)** Implement Option C in `navigate()`:
1. Validate URL scheme is `http` or `https` (required control, not defense-in-depth)
2. Resolve hostname via `asyncio.to_thread(socket.getaddrinfo)` and check all IPs via local `_is_blocked_ip()`
3. On blocked IP/scheme: raise `ToolError` (matches existing allowlist error pattern)
4. Accept TOCTOU and click-triggered navigation as documented limitations

Confidence: **.75**

Challenge: **reconsider** — confidence in original: .55. Accepted: scheme check elevated to required control (C4), click-triggered navigation documented as limitation (C1/B1), DRY tech debt acknowledged (C3), line count correction (C2). Rejected: Option B upgrade (not warranted at nice-to-have priority), check in DomainAllowlist (async DNS in sync method changes API contract), BrowserContentFetcher protection (out of scope — not currently reachable outside navigate()).

## 5. Follow-up Tasks

No new follow-up tasks needed — #950 IS the implementation task. The AC is well-specified and incorporates the research findings. The task should advance to `backlog` with the implementation notes below appended.

**Implementation notes for builder:**
- Duplicate `_is_blocked_ip` from mcp-knowledge/server.py L156-175 as a local private function
- Add `_check_ssrf(url: str) -> None` that does scheme check + DNS resolve + IP check, raises `ToolError`
- Call `_check_ssrf(url)` at the top of `navigate()`, before `allowlist.check(url)`
- Use `asyncio.to_thread(socket.getaddrinfo, hostname, port)` for non-blocking DNS
- No URL rewrite (Playwright constraint) — document in code comment
- Test file: `serve/mcp-browser/tests/test_ssrf_preflight_950.py`
