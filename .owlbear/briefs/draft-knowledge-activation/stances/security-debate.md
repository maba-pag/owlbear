# Security Debate Log — Knowledge Engine Activation

## Cycle 1

### Initial Position

Assessed 8 security concerns across the converged approach. Key judgments:

1. **SSRF** — Strong existing protection (low residual risk). Multi-layered defense with DNS rebinding mitigation, IP blocklist, redirect blocking, 30s timeout. Browser TOCTOU gap mitigated by default-deny allowlist.
2. **Data poisoning / prompt injection** — Defended but not foolproof (medium risk). ContentInjectionGuard + untrusted content wrapping + user preview validation.
3. **Browser SSO** — Contained (low risk). Content extraction only, no credential scraping, non-headless launch.
4. **copilot_auth removal** — Requires cleanup (medium risk). Cached token with 0o600 perms, proxy-ep URLs, no delete on removal.
5. **sources.yaml** — Clean (no risk). Only file globs and local paths.
6. **SQLite** — Adequately protected (low risk). All parameterized queries.
7. **MCP tool access** — Advisory only (medium risk). No per-tool auth, but KNOWLEDGE_TOOLS_EXCLUDE env var available.
8. **Enrichment workers** — Acceptable (low-medium risk). Pydantic schema constrains extraction output.

Overall confidence: 0.85.

### Critic Challenges (8 challenges, pressure: high)

**Challenge 1 (Critical):** Content guard is NOT wired to the MCP tool path. `IngestPipeline` constructed at server.py:305 without `content_guard` parameter. The guard and wrapping logic exist in the library (ingest.py:146, 222, 224) but are not on the live ingest tool path. Two controls described as existing are actually inactive.

**Verdict: Accepted.** Verified — `IngestPipeline(doc_store, extractor, chunker)` has no content_guard. This is a real gap. Upgraded prompt injection risk from "defended" to "defense exists but is not wired."

**Challenge 2 (Critical):** User preview is aspirational, not implemented. The preview flow exists in the brief's design decision (decisions.md:123-128) but refresh.py:245-284 and bookmark_pipeline.py:132-150 auto-ingest without preview. The "strongest claimed control" is not in code.

**Verdict: Accepted.** The preview is an agent workflow pattern the brief prescribes, not an enforced code gate. refresh_source and bookmark ingestion bypass any preview step entirely. Revised to treat preview as a design requirement that must be enforced, not an existing defense.

**Challenge 3 (Moderate):** Browser SSRF residual risk understated. The browser server itself documents accepted TOCTOU and redirect SSRF gaps (server.py:66-70), and click-triggered navigation bypass is an accepted limitation (research doc 950-ssrf-browser-navigate.md:31, 56).

**Verdict: Accepted.** My residual-risk assessment was more confident than the code authors'. Revised to align with documented limitations.

**Challenge 4 (Moderate):** Browser is an authenticated automation surface, not just passive extraction. navigate, click, type_input, select tools operate on a persistent authenticated Chromium session. A misbehaving agent could perform actions on corporate systems.

**Verdict: Accepted.** This is the most significant upgrade to my stance. The browser module isn't "equivalent to leaving Edge open" — it's a scriptable automation surface on an authenticated session. Agents with browser MCP access can drive actions on Confluence, Jira, SharePoint with the user's SSO credentials. This requires explicit trust boundary treatment.

**Challenge 5 (Moderate):** Token persistence priority is wrong. Bearer token itself is the primary sensitivity, not proxy-ep URLs.

**Verdict: Accepted.** Reprioritized — the bearer token on disk is the core concern; proxy endpoint exposure is secondary.

**Challenge 6 (Moderate):** Current server exports 17+ tools, not the brief's 8. Bookmark, consolidation, and scope transfer tools are all live. The mutation surface is wider than analyzed.

**Verdict: Accepted.** The brief plans to cut to 8 active + 4 deferred, but the current code exports everything. The tool exclusion mechanism exists but must be actively configured. Until the cut is implemented, the attack surface is the full 17-tool set.

**Challenge 7 (Moderate):** Poisoned entities/edges affect agent reasoning, not just "data quality." search_knowledge returns graph-expanded results. Corrupted entities change what downstream agents see and reason over.

**Verdict: Accepted.** Graph expansion feeds entity-neighbor relationships back into search results. A spurious entity connected to a real one means agents see fabricated relationships. This is a prompt injection amplification vector — initial poisoning gets reinforced through graph traversal. Upgraded from "data quality" to "security effect."

**Challenge 8 (Minor):** sources.yaml will contain external URLs per the brief's design. "No risk" is premature.

**Verdict: Partially accepted.** URLs are not credentials, but the manifest will contain corporate-internal URLs (Confluence, SharePoint, Jira) that could reveal organizational structure. Revised from "no risk" to "low risk — no credentials, but organizational URLs should be reviewed before sharing."

### Post-Critic Revision

All 8 challenges accepted or partially accepted. Major upgrades:
- Content guard: defense exists but is NOT wired → must be wired in activation
- User preview: design requirement, not existing code → must be enforced
- Browser: passive extraction → authenticated automation surface requiring explicit trust boundary
- Enrichment poisoning: data quality → security effect via graph amplification
- Tool surface: current 17 tools, not planned 8 → exclusion must be configured

Confidence revised from 0.85 → 0.80 (strong position but several defenses are aspirational, not implemented).
