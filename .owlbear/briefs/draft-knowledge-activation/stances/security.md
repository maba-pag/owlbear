# Security Stance — Knowledge Engine Activation

## Security Stance

The converged approach has **above-average security hygiene for a laptop-local developer tool**, with one critical gap and several moderate concerns that must be addressed during activation. The codebase demonstrates defense-in-depth thinking (SSRF protection, content guards, parameterized queries) but key defenses are not wired to the live code paths. This stance distinguishes between defenses that exist in code vs. those that exist only in the brief's design.

### 1. SSRF Risk — STRONG (Low residual risk)

**HTTP fetcher:** Multi-layered defense exceeds typical standards — scheme validation, async DNS resolution with comprehensive IP blocklist (loopback, RFC-1918, link-local, reserved, unspecified, IPv6 mapped addresses), DNS rebinding TOCTOU mitigation via URL rewrite to resolved IP, redirects disabled, 30s timeout. Four dedicated test files validate all blocked ranges.

**Browser fetcher:** Weaker than HTTP path. The browser server documents accepted TOCTOU and redirect SSRF limitations — Playwright cannot connect to pre-resolved IPs, so DNS can rebind between the pre-flight check and `page.goto()`. Click-triggered navigation bypass is also an accepted limitation. The `DomainAllowlist` defaults to empty (all blocked), which is the correct default-deny posture. Residual risk is real but bounded by the allowlist — exploitation requires both DNS rebinding AND allowlist misconfiguration.

**Requirement for activation:** Ensure `BROWSER_ALLOWED_DOMAINS` is configured with the minimum set of corporate domains needed. Document the TOCTOU limitation.

### 2. Data Poisoning / Prompt Injection — CRITICAL GAP (High risk)

This is the most significant security concern. The trust chain is:

```
External content → ingest_document → [NO ACTIVE GUARD] → stored → search_knowledge → agent prompt
```

**What exists in the library (not wired):**
- `ContentInjectionGuard` with ~40 scan patterns (instruction override, role hijack, jailbreak, exfiltration, social engineering)
- `<untrusted_web_content>` wrapping with LLM advisory
- `strict_mode` flag for block vs. warn-and-proceed

**What is NOT wired:**
- `IngestPipeline` is constructed in the MCP server lifespan WITHOUT `content_guard` — the guard is bypassed on the live tool path
- `refresh_source` auto-ingests without any preview or validation step
- `bookmark_pipeline` can auto-ingest after evaluation without user confirmation

**What is aspirational (brief design, not code):**
- HTTP-first fetch with user preview validation before ingestion
- User confirmation that content "looks right" before proceeding

**Blast radius:** Ingested content becomes queryable by ALL pipeline agents via `search_knowledge`. Graph expansion amplifies the risk — a poisoned entity connected to legitimate entities means fabricated relationships appear in graph-augmented search results. This is not a data quality issue; it is a prompt injection amplification vector.

**Requirements for activation:**
1. Wire `ContentInjectionGuard` to `IngestPipeline` on the MCP tool path — this is a one-line fix but it must be done
2. Enable `strict_mode` for web-fetched content by default
3. The user preview workflow must be enforced at the agent/prompt level (cannot be enforced in the MCP tool itself, but the ingestor agent's prompt must mandate it)
4. `refresh_source` should log content changes for user review, not auto-ingest silently

### 3. Browser Session — AUTHENTICATED AUTOMATION SURFACE (Medium risk)

The browser module is NOT "equivalent to leaving Edge open." The MCP browser server exposes `navigate`, `click`, `type_input`, and `select` tools operating on a persistent Chromium session with Edge SSO credentials. This is a scriptable automation surface on corporate-authenticated systems.

**Trust boundary implications:**
- Any agent with the browser MCP server configured can drive actions on Confluence, Jira, SharePoint using the user's SSO session
- Actions are visible (non-headless) but an inattentive user may not notice automated clicks/inputs
- The persistent Chromium profile (`~/.owlbear/chromium-profile`) retains SSO tokens between sessions

**Mitigating factors:**
- Default-deny domain allowlist (empty by default)
- Non-headless browser (user-visible)
- Content extraction does not scrape credentials/cookies
- Explicit `launcher.close()` cleanup on exit

**Requirements for activation:**
1. Only `knowledge-ingestor` should have the browser MCP server in its tools — pipeline agents must NOT have browser access
2. Browser tools should be restricted to read-only operations for the knowledge use case (navigate + extract, not click/type/select)
3. Document that the browser module is an authenticated automation surface, not a passive reader

### 4. copilot_auth Removal — REQUIRES TOKEN CLEANUP (Medium risk)

The cached Copilot token at `~/.owlbear/copilot_token.json` persists on disk with 0o600 permissions. The bearer token itself is the primary sensitivity — if exfiltrated, it provides access to the Copilot API. The proxy endpoint URL embedded in the token is a secondary concern.

**Requirements for activation:**
1. Delete `~/.owlbear/copilot_token.json` as part of the copilot_auth removal
2. Add a migration/cleanup step that removes the token file if it exists
3. Remove or deprecate the `copilot_auth.py` module from the knowledge package (not just the import)

### 5. sources.yaml — LOW RISK (No credentials, organizational URLs)

Currently contains only file globs and local paths — verified clean. The activation design adds external URLs (Confluence, SharePoint, Jira) and `fetch_method` to the manifest. These URLs are not credentials but reveal organizational structure (internal system names, project hierarchies).

**Requirement for activation:** Document that sources.yaml should be reviewed before sharing the repo — it will contain corporate-internal URLs.

### 6. SQLite Graph Store — ADEQUATELY PROTECTED (No risk)

All queries use parameterized placeholders. Metadata serialized via `json.dumps`/`json.loads` (no eval). DB file gitignored. No SQL injection risk. The data sensitivity (corporate doc extracts on disk) is inherent to the use case and mitigated by laptop-local storage + gitignore.

### 7. MCP Tool Access Control — WIDER THAN PLANNED (Medium risk)

The current MCP server exports 17+ tools including bookmark, consolidation, and scope transfer tools that are cut from the brief's planned 8+4 surface. Until the cut is implemented, every agent with the knowledge MCP server configured has access to the full mutation surface.

The `KNOWLEDGE_TOOLS_EXCLUDE` env var exists for runtime tool disabling, but it is not configured by default.

**Requirements for activation:**
1. Implement the tool surface cut (remove/disable bookmark, consolidation tools) before activation
2. Configure `KNOWLEDGE_TOOLS_EXCLUDE` as a safety net for any tools not yet removed from code
3. Per the consumer matrix: only `knowledge-ingestor` and `knowledge-enricher` should have the full tool set; pipeline agents should access only `search_knowledge` and `list_sources`
4. Enforce this via agent file configuration (MCP server inclusion), not runtime auth (which MCP doesn't support)

### 8. Enrichment Worker Security — GRAPH AMPLIFICATION RISK (Medium risk)

Enrichment workers process corporate document chunks via LLM to extract entities and relationships. A poisoned chunk could manipulate the extraction model to produce fabricated entities or edges.

**Why this is a security concern, not just data quality:**
- `search_knowledge` returns graph-expanded results — corrupted entities connected to real ones alter what downstream agents see
- Entity-neighbor relationships are fed back into agent context via graph traversal
- A single fabricated cross-source relationship could cause an agent to cite non-existent compliance evidence or miss real dependencies

**Mitigating factors:**
- Pydantic structured output constrains extraction to entity type + name + relationships
- The schema prevents arbitrary output — only valid entity types are accepted
- Enrichment is user-triggered, not automatic

**Requirement for activation:** The content guard (Section 2 fix) should scan chunks before enrichment, not just at ingest time.

## Risk Assessment

| Concern | Current Risk | Post-Activation (if requirements met) |
|---------|-------------|--------------------------------------|
| SSRF (HTTP) | Low | Low |
| SSRF (Browser) | Medium | Low |
| Data poisoning / prompt injection | **High** | Medium |
| Browser as automation surface | Medium | Low |
| copilot_auth token persistence | Medium | None (cleaned up) |
| sources.yaml credential leak | None | Low |
| SQLite injection | None | None |
| MCP tool surface exposure | Medium | Low |
| Enrichment graph amplification | Medium | Low-Medium |

## Compliance Implications

- **At-rest data:** SQLite DB contains extracts from corporate documents (Confluence, SharePoint, Jira). Gitignored but unencrypted on disk. If the organization has data classification policies for corporate content, this store may require encryption-at-rest.
- **SSO session persistence:** The Chromium profile retains corporate SSO tokens between sessions. This is standard browser behavior but should be documented for security review.
- **Credential lifecycle:** The copilot_auth token cache must be cleaned up — stale credential artifacts on disk are a compliance finding in most security audits.

## Least-Privilege Recommendations

1. **Agent → MCP server mapping:** Only knowledge-specific agents should have the knowledge MCP server configured. Pipeline agents (builder, reviewer, etc.) should access knowledge via `search_knowledge` and `list_sources` only — achieved by agent file configuration, not runtime auth.
2. **Browser MCP access:** Restrict to `knowledge-ingestor` only. No other agent should be able to drive browser automation on authenticated sessions.
3. **Tool exclusion:** Configure `KNOWLEDGE_TOOLS_EXCLUDE` to disable bookmark, consolidation, and scope transfer tools until they are needed.
4. **Domain allowlist:** Configure `BROWSER_ALLOWED_DOMAINS` with minimum necessary corporate domains. Do not use wildcard patterns.
5. **Content guard:** Wire to the live ingest path with `strict_mode=True` for web-fetched content.

## Warnings

1. **The content guard gap is the blocking security finding.** The guard exists in the library but is NOT wired to the MCP tool path. Activating the knowledge system without wiring the guard means all ingested web content enters the knowledge base without prompt injection scanning. This must be fixed before activation.
2. **The browser module is an authenticated automation surface.** Treating it as passive content extraction understates the trust boundary. Agent access to browser tools must be explicitly scoped.
3. **Graph amplification is a novel risk.** Poisoned entities don't just exist in isolation — they connect to real entities via graph edges and alter what agents see through graph-augmented retrieval. The content guard must run before enrichment, not just at ingest.

## Confidence

0.80 — Strong position grounded in verified code evidence. Two critical gaps identified and confirmed against source. Residual uncertainty: (a) whether the brief will actually wire the content guard as a hard requirement, (b) whether the agent file configuration approach is sufficient for tool access control without runtime enforcement.
