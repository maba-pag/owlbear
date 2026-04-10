# Architect Debate Log — Authenticated Content Pipeline

## Cycle 1

### Position Presented

1. Browser as separate core library + thin MCP server (serve/browser/ + serve/mcp-browser/)
2. AUTHENTICATED_WEB as new SourceType with injected fetcher in RefreshOrchestrator
3. Discovery (agent-interactive) and extraction (pipeline-mechanical) as separate phases, KnowledgeSource record as boundary
4. Source management agent as pure markdown using mcp-browser + mcp-knowledge
5. Extend existing StrEnums directly (REQUIREMENT, SOLUTION, PROCEDURE, POLICY, STANDARD + GOVERNS, SUPERSEDES_VERSION)

### Critic Challenges

**Objection 1 — Session continuity across the phase boundary (MATERIAL)**

Discovery happens with a live browser session carrying SSO cookies. Extraction happens later during refresh. SSO sessions are ephemeral — the refresh pipeline can't re-authenticate through SSO. Silent failure cascade: discovery succeeds → URLs stored → first refresh works → second refresh fails (session expired) → user doesn't notice.

**Response: ACCEPTED.** The architecture needs an explicit session-warmth strategy. Refined: browser fetcher raises typed `AuthenticationRequired` exception on SSO redirect/401. RefreshOrchestrator catches this specifically, records on source as `last_error`, surfaces in RefreshResult. The user is present (laptop-resident, manual trigger or while working). "Re-auth" = open URL in Edge once. Fully unattended refresh is explicitly out of scope for Phase 1.

**Objection 2 — SourceType + injected fetcher is one abstraction too many**

Both handlers would be identical 20-line iteration loops differing only in the fetcher call. The existing BookmarkPipeline pattern proves injected `web_read_fn` suffices without a new type. Proposed: `_handle_url_list` takes optional fetcher parameter, source config has `requires_browser: true` flag.

**Response: PARTIALLY ACCEPTED.** Kept AUTHENTICATED_WEB as separate SourceType (different operational semantics: session warmth, error classification, metadata tagging, subpage discovery capability). But accepted the structural critique on duplication: both handlers delegate to a shared `_fetch_and_ingest_urls(urls, fetcher, source, cancel)` method. Zero code duplication.

**Objection 3 — Playwright deployment coupling**

Adding `owlbear_browser` to mcp-knowledge's ALLOWED_IMPORTS pulls Playwright (heavy binary) into every mcp-knowledge install, breaking clone = install.

**Response: ACCEPTED.** Browser integration in mcp-knowledge is lazy/optional. Import is guarded with try/except. Lifespan wires fetcher only when available. Without browser package, AUTHENTICATED_WEB sources produce clear "browser package not installed" error. Playwright depends only on owlbear_browser, not owlbear_mcp_knowledge.

## Cycle 2

### Refined Position Presented

All three Cycle 1 corrections integrated: explicit auth-failure protocol, shared handler internals, lazy browser import.

### Critic Challenges

**Objection 1 — Content safety gap for authenticated_web (genuine risk)**

Ingest pipeline's prompt-injection guard checks `metadata.get("source_type") == "url"`. If browser fetcher returns `source_type="authenticated_web"`, wrapping won't trigger. Corporate intranet pages are still untrusted input. One-line fix but must be in the design.

Recommended: invert the predicate — wrap everything *except* known-safe source types (`"file"`, `"text"`) rather than enumerating web source types.

**Response: ACCEPTED.** Critical security point. Inverted predicate is the right pattern — prevents security gaps when future source types are added. Added as Warning #1 in final position.

**Objection 2 — Fail-fast semantics create minor divergence pressure**

If auth expires mid-refresh on URL 3 of 50, AUTHENTICATED_WEB should abort remaining URLs. URL_LIST has no equivalent. The shared `_fetch_and_ingest_urls` needs explicit fail-fast contract.

**Response: ACCEPTED.** Added `fail_fast_on: type[Exception] | None` parameter to the shared method's contract. AUTHENTICATED_WEB passes `fail_fast_on=AuthenticationRequired`. URL_LIST passes None. Clean, explicit divergence point.

**Critic assessment:** "Position is mostly solid" — both points are targeted refinements, not structural objections.

## Final Assessment

- **Cycles completed:** 2
- **Objections received:** 5
- **Accepted (full):** 4 (session continuity, deployment coupling, content safety, fail-fast)
- **Accepted (partial):** 1 (handler duplication — accepted shared internals, rejected config flag over SourceType)
- **Rejected:** 0

**What changed from initial position:**
- Added explicit AuthenticationRequired exception protocol and session-warmth handling
- Refactored handler design from duplicate methods to shared `_fetch_and_ingest_urls` with fetcher injection
- Made browser import in mcp-knowledge lazy/guarded
- Inverted content safety predicate (wrap-by-default instead of enumerate-web-types)
- Added fail-fast contract to shared handler method

**What held:**
- Browser as separate package (core lib + MCP server)
- AUTHENTICATED_WEB as distinct SourceType (not config flag)
- KnowledgeSource record as discovery/extraction phase boundary
- Pure markdown agent pattern
- Direct StrEnum extension for entity/relation types
