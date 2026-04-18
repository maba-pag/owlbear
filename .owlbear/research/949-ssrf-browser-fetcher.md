# SSRF Surface in BrowserContentFetcher (page.goto)

> **Owning task:** #949 — Assess SSRF surface in BrowserContentFetcher (page.goto)
> **Date:** 2026-04-18 **Status:** Complete

## 1. Context and Question

After #946/#947/#948 fixed SSRF in `_web_read`, `read_url`, and `HttpxContentFetcher`, task #949 asks whether `BrowserContentFetcher` (Playwright's `page.goto()`) has a comparable vulnerability and what mitigation patterns apply.

## 2. Sources Studied

| # | Source | Relevance | What was taken |
|---|--------|-----------|----------------|
| 1 | `serve/browser/src/owlbear_browser/fetcher.py` | 1.0 | No IP/scheme validation before `page.goto(url)` |
| 2 | `serve/mcp-browser/src/owlbear_mcp_browser/allowlist.py` | 1.0 | Domain-only check; closed-by-default (empty = blocks all) |
| 3 | `serve/mcp-browser/src/owlbear_mcp_browser/server.py` | 1.0 | 3 `page.goto()` call sites in `navigate()` (lines 111, 117, 126) |
| 4 | `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py` | 0.9 | RefreshOrchestrator has no `content_fetcher` — browser path unreachable |
| 5 | Playwright docs: `page.goto()` | 0.8 | No IP+Host header support; follows redirects by default |
| 6 | Playwright docs: `browser_context.route()` | 0.7 | Can intercept all requests including redirects for IP validation |

## 3. Analysis

### 3.1 Reachability Assessment

`BrowserContentFetcher` is **NOT reachable from user-controlled input today.** `RefreshOrchestrator` in mcp-knowledge is instantiated without `content_fetcher=None`. The only caller is the `mcp-browser` server's `navigate()` tool, invoked by agents (not users). The `DomainAllowlist` (env: `BROWSER_ALLOWED_DOMAINS`) is closed-by-default — empty frozenset blocks ALL navigation.

### 3.2 Vulnerability Surface

Despite unreachability, three code-level gaps exist:

| Gap | Location | Severity | Reachable? |
|-----|----------|----------|------------|
| No IP validation before `page.goto()` | `navigate()` L111/L117/L126 | Medium | Agent-only, behind allowlist |
| Redirect-based SSRF | `page.goto()` follows 3xx | Medium | If allowlisted domain redirects to internal IP |
| No scheme validation | `BrowserContentFetcher.fetch()` | Low | `file://`, `data:` accepted (Chromium blocks most) |
| IP-literal bypass of DomainAllowlist | `allowlist.py` L29 | Low | Only if admin adds IP to env var |

### 3.3 Mitigation Options

| Option | Approach | Covers redirects? | TOCTOU risk | Complexity | KISS score |
|--------|----------|-------------------|-------------|------------|------------|
| A | Pre-flight DNS + IP check in `navigate()` | No | Yes (DNS rebind) | Low (~20 LOC) | .85 |
| B | `browser_context.route("**/*")` interceptor | Yes | No | Medium (~40 LOC) | .65 |
| C | A + scheme check in `navigate()` | No | Yes | Low (~25 LOC) | .80 |
| D | Document risk, defer until user-reachable path exists | N/A | N/A | None | 1.0 |

### 3.4 Playwright Constraint

Playwright's `page.goto()` does NOT support connecting to a pre-resolved IP with Host header (the pattern `_web_read` uses). This means:
- Pre-flight DNS resolution has inherent TOCTOU risk (DNS rebinding)
- The TOCTOU is mitigated by the fact that rebinding requires compromising DNS for an allowlisted domain — a different threat tier entirely
- `browser_context.route()` can intercept post-redirect requests but adds complexity and disables HTTP cache

### 3.5 Key Correction from Challenge

The SSRF check belongs in `navigate()` (the MCP tool function), NOT in `BrowserContentFetcher.fetch()`. The `navigate()` function has three `page.goto()` call paths — only one goes through the fetcher. Fixing only the fetcher creates false coverage.

## 4. Recommendation

**(rec:)** Option C — add pre-flight DNS resolution + IP blocklist + scheme check to `navigate()` in `server.py`, as a single follow-up task at `nice-to-have` priority.

Confidence: **.72**

Rationale: The vulnerability is real but not exploitable through any current code path. The DomainAllowlist's closed-by-default posture provides adequate protection for the current deployment model. Defense-in-depth is warranted but not urgent.

**Rejected alternatives:**
- **(bp:)** Option B (`page.route()` interceptor): More thorough but violates KISS; the redirect-based SSRF requires a compromised/malicious allowlisted domain — low probability.
- Option D (document only): Acceptable given unreachability, but per-#946 precedent the project is hardening all ContentFetcher paths.

Challenge: **reconsider** — confidence in original: .45. Key challenges accepted: fix belongs in `navigate()` not fetcher, redirect SSRF is more realistic than DNS rebinding, priority should be `nice-to-have`. Rebutted: "document only" rejected because sibling tasks establish a pattern of proactive hardening.

## 5. Follow-up Tasks

Created at `research` status:
- **#950** — Add SSRF pre-flight check to `navigate()` in mcp-browser server (`nice-to-have`)
