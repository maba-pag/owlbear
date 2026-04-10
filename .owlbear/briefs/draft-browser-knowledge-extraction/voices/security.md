# Security Voice — Authenticated Content Pipeline

## Security Stance

**Accept the design with five hard requirements and three operational recommendations.** The trust model is sound for a single-user, laptop-resident tool. The CDP-via-shared-context approach is the correct trade-off — isolated contexts cannot carry SSO credentials, and SSO reuse is the entire point. The real risks are not in the architecture but in the execution details: what JavaScript runs in the browser session, who controls source configuration, and how the extraction pattern appears to corporate endpoint monitoring.

## Risk Assessment

### Trust Boundary: CDP Session (ACCEPTED RISK — with controls)

CDP grants full browser session control: navigate any URL, execute arbitrary JavaScript, read/modify cookies and localStorage, intercept network requests, access all open tabs. When attaching to the user's running Edge for SSO reuse, there is **no isolation** — OwlBear operates with the user's full authenticated browser session.

**Why this is acceptable:** The user is running OwlBear themselves on their own laptop. CDP access is functionally equivalent to the user operating the browser manually. The threat actor is "unintended software behavior," not "external attacker." Any local process on the machine already has equivalent access (keylogging, screen capture, memory inspection).

**Why this still needs controls:**
- A bug or LLM hallucination could navigate to unintended URLs, execute unintended JavaScript, or exfiltrate session data.
- The blast radius of a CDP bug is the **entire browser session** — all tabs, all cookies, all authenticated services.

### Trust Boundary: LLM → JavaScript Execution (CRITICAL)

The v1 BrowserToolset uses injected JavaScript for DOM parsing and content extraction. If the LLM can influence the JavaScript that executes in page context, it can:
- Read `document.cookie` (including HttpOnly cookies via CDP, not just JS-accessible ones)
- Access `localStorage`/`sessionStorage` containing tokens
- Make `fetch()` calls to any origin using the user's credentials (CSRF from the browser itself)
- Exfiltrate data to external endpoints

**Hard Requirement #1: All content extraction JavaScript MUST be static, pre-defined code.** Tool parameters must be structured data (URL strings, CSS selectors) — never raw JavaScript. No `eval()`, no template-string JavaScript construction from LLM inputs.

### Trust Boundary: Source Configuration → Navigation Scope

If the LLM generates or modifies source configurations (including domain allowlists), it controls where the browser navigates. An overly broad allowlist (`*`) or a hallucinated domain could lead to unintended site access.

**Hard Requirement #2: Source configurations — including domain allowlists — MUST require explicit user approval.** The source management agent proposes; the user confirms. No auto-approved source additions.

### Trust Boundary: Extracted Content → LLM Context (Indirect Prompt Injection)

Corporate intranet pages are not adversarial, but they are **untrusted** from the LLM's perspective. A compromised or malicious page could embed prompt injection payloads. The existing research (tasks #724, #725) already identified this and proposed:
1. IDPI content scanning (pattern-matching for known injection phrases)
2. Untrusted content wrapping (`<untrusted_web_content>` delimiters)

**Hard Requirement #3: Both IDPI scanning and untrusted content wrapping MUST be implemented before browser extraction goes live.** These are defense-in-depth layers — neither is a security boundary alone, but together they materially reduce the blast radius of indirect prompt injection from extracted content.

### CDP Port Exposure: localhost:9222

When Edge runs with `--remote-debugging-port=9222`, any local process can connect to the CDP endpoint. Assessment:

- **Network exposure:** None if bound to localhost (127.0.0.1). Edge binds to localhost by default. Verify this is not overridden.
- **Local process access:** Any process running as the same user can connect. This is equivalent to the existing threat model — any same-user process can already inject keystrokes, read process memory, or access the user's files.
- **EDR/DLP monitoring:** Corporate endpoint detection and response (EDR) tools may flag `--remote-debugging-port` as suspicious. This is a **deployment risk**, not a security vulnerability.

**Hard Requirement #4: CDP must bind exclusively to 127.0.0.1. Verify this in the launcher code — do not pass `0.0.0.0` or a wildcard address.**

### Data Aggregation Effect

Individual page access is authorized. But programmatic extraction of hundreds of pages across HR SharePoint, Finance Confluence, and Security policies creates a local data aggregation that exceeds what any single browsing session would produce. This aggregation:
- May trigger DLP (Data Loss Prevention) tools that monitor bulk data movement patterns
- Creates a local knowledge base that persists beyond the user's current access authorizations (if access is later revoked)
- Cross-references content from sources that were never intended to be correlated

This is an **operational risk**, not a technical vulnerability. The user is the data controller and is authorized to view each page individually.

### URL Domain Guard Sufficiency

The v1 `URLSafetyGuard` uses regex blocklist/allowlist via `HookRegistry.PRE_TOOL_USE`. For v2:

**Hard Requirement #5: Migrate to an allowlist-per-source model.** Each configured source declares its allowed domain patterns. The default is deny-all — no navigation without an explicit domain match. This is a positive security model (fail-closed).

The v1 regex approach is adequate for the threat model (preventing LLM hallucination, not adversarial external input). browser-use's O(1) set-based domain matching is a performance optimization worth studying but not a security concern at this scale.

## Compliance Implications

### Data Residency
- Extracted content stored locally in SQLite + Qdrant on the same corporate laptop where it's already viewable via browser
- **No data leaves the device** — this is functionally equivalent to the user saving web pages or taking notes
- BitLocker (standard on corporate Windows laptops) provides at-rest encryption. Application-level encryption would be security theater on top of FDE.

### DLP Considerations
- Rapid sequential page loads from intranet sites followed by local file writes (SQLite, Qdrant) may trigger DLP agents that distinguish bulk extraction from normal browsing
- **Operational Recommendation #1:** Implement rate limiting not just for politeness but for DLP profile management. Default delays (1.5–2s between pages) help the extraction pattern resemble normal browsing.

### Access Lifecycle
- When the user's access to a source is revoked (team change, project end), refresh cycles will fail. But previously extracted content remains in the local KB.
- This is equivalent to notes taken while the user had access — it's not an access control violation, but it may conflict with corporate data retention policies.
- **Operational Recommendation #2:** When refresh fails with an authentication error, flag the source as stale and surface it prominently to the user. Provide a one-command source purge that cascade-deletes all associated documents, entities, and edges.

## Least-Privilege Recommendations

1. **CDP connection scope:** Use CDP only during active extraction, not as a persistent connection. The BrowserManager's async context manager pattern already supports this — ensure it's the only usage pattern.
2. **Extraction JavaScript scope:** Content extraction functions should only read DOM text content and structural metadata. They should NOT access `document.cookie`, `localStorage`, `sessionStorage`, `navigator.credentials`, or make any `fetch()`/`XMLHttpRequest` calls.
3. **Tool surface:** The v2 browser MCP server should expose only read-only tools for the knowledge extraction use case: `navigate`, `read_text`, `snapshot`. Do NOT expose `click`, `type`, `select` in the extraction pipeline — those are interactive tools for a different use case and expand the attack surface unnecessarily.
4. **Batch approval for discovered pages:** The source management agent's discovery step should present pages per-domain with clear titles, not as a bulk "approve all 500" action. The user should approve at domain-scope granularity.

## Warnings

1. **JavaScript injection is the single highest-risk vector.** If any code path allows LLM-influenced JavaScript to execute in a page context that has the user's SSO session, the blast radius is every authenticated service the user has access to. This is a hard boundary — no exceptions.
2. **The HookRegistry swallows exceptions** (confirmed in approval-gates research). If URL safety guards are implemented as `PRE_TOOL_USE` hooks, `BlockedURLError` will be logged but the navigation **will still proceed**. For v2, URL guards must be enforced at the tool implementation level (inside the navigate function), not as hooks.
3. **Content classification is a trap.** Automated classification of intranet content (PII detection, sensitivity labeling) would add complexity without a clear enforcement path. The user is already authorized to view the content. Classification would create false confidence ("the system said it was safe") and wouldn't change any behavior. The user's judgment via the source review step is the correct control.

## Confidence

**0.85** — High confidence in the trust model and hard requirements. The main uncertainty is in the corporate endpoint monitoring space (EDR/DLP), which is environment-specific and cannot be fully assessed without knowing the specific tools deployed.

### Operational Recommendation #3 (Pre-deployment)
Before deploying browser extraction, the user should:
1. Verify that `--remote-debugging-port` is not flagged by their corporate EDR agent (test by launching Edge with the flag and monitoring for alerts over 24h)
2. Verify that rapid sequential page loads from intranet sites don't trigger DLP alerts (test with 10–20 pages from a non-sensitive SharePoint site)
3. Confirm that BitLocker is active on the local drive where SQLite/Qdrant data resides (`manage-bde -status` in PowerShell)
