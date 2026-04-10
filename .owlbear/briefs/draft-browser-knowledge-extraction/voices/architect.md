# Architect Voice — Authenticated Content Pipeline

## Architectural Stance

**Separate browser infrastructure package with protocol-based injection into the knowledge pipeline.**

Browser extraction is I/O transport infrastructure, not a knowledge concern. It gets its own core library (`serve/browser/` → `owlbear_browser`) and a thin agent-facing MCP server (`serve/mcp-browser/`). The knowledge pipeline stays browser-unaware — RefreshOrchestrator accepts an injected content-fetcher protocol that the MCP composition root wires at startup. Discovery (agent-interactive) and extraction (pipeline-mechanical) are cleanly separated by the KnowledgeSource record boundary. Entity model extends existing StrEnums directly.

## Structural Reasoning

### Q1: Standalone MCP server or integrated?

**Both — a core library plus a thin MCP server, with protocol injection into knowledge.**

The browser lifecycle (Edge CDP launcher, Playwright session management, SSO detection, content extraction) is ~1200 LOC of complex async infrastructure. It has nothing in common with knowledge graph operations. Collapsing it into `owlbear_knowledge` violates single-responsibility and bloats a foundation package that currently has zero owlbear-namespace dependencies.

Two consumption paths exist with different interaction models:
- **Agent-interactive** (discovery): Agent calls mcp-browser tools (navigate, click, read_text) during a conversation with the user. Requires interactive MCP tools.
- **Pipeline-mechanical** (refresh): RefreshOrchestrator calls a content-fetcher function programmatically during batch refresh. No user interaction.

Both paths use the same underlying `owlbear_browser` library. The MCP server is a thin tool wrapper; the knowledge pipeline gets a protocol injection.

**Package wiring:**
- `owlbear_browser` — core library, depends on Playwright, no owlbear imports
- `owlbear_mcp_browser` — MCP server, imports `owlbear_browser`
- `owlbear_mcp_knowledge` — imports `owlbear_knowledge` + lazily imports `owlbear_browser`
- `owlbear_knowledge` — unchanged, no new dependencies

The `owlbear_browser` import in mcp-knowledge is **lazy/guarded**: `try/except ImportError`. Without the browser package installed, mcp-knowledge runs normally — AUTHENTICATED_WEB sources produce a clear "browser package not installed" error. Playwright is a dependency of `owlbear_browser` only, keeping clone-to-install lightweight for non-browser use cases.

### Q2: AUTHENTICATED_WEB integration with RefreshOrchestrator

**New SourceType enum member with handler delegation to shared internals.**

Add `AUTHENTICATED_WEB = "authenticated_web"` to `SourceType`. RefreshOrchestrator gets a new `_handle_authenticated_web()` handler plus a shared private `_fetch_and_ingest_urls(urls, fetcher, source, cancel, *, fail_fast_on=None)` that both URL_LIST and AUTHENTICATED_WEB delegate to.

AUTHENTICATED_WEB is a distinct SourceType, not a config flag on URL_LIST, because:
- Different operational characteristics (browser session, rate-limited, sequential)
- Different error classification (auth failures vs HTTP errors)
- Different pre-flight (session warmth check before first fetch)
- Different metadata tagging (`source_type="authenticated_web"`)
- Subpage discovery capability (URL_LIST has static URL sets)

The content-fetcher protocol:
```python
ContentFetcher = Callable[[str], Awaitable[IntakeResult]]
```

The browser implementation raises `AuthenticationRequired` when it detects SSO redirect or 401. The AUTHENTICATED_WEB handler catches this specifically:
- Records `last_error = "Authentication expired — re-open the source URL in Edge to refresh your session"`
- Uses **fail-fast semantics**: if auth fails on URL 3 of 50, abort remaining URLs immediately (they'll all fail the same way). URL_LIST sources don't have this concern — each URL is independent.
- RefreshResult surfaces the auth error clearly; the user re-warms the session and re-triggers.

The `_fetch_and_ingest_urls` shared method has a `fail_fast_on: type[Exception] | None` parameter to support this divergence cleanly.

### Q3: Phase boundary — discovery vs extraction

**Discovery populates the KnowledgeSource record. Extraction consumes it. The record is the boundary.**

Discovery is a conversational, agent-driven process:
1. User provides root URL to source management agent
2. Agent uses mcp-browser to navigate the root, discover child pages (BFS with depth/page limits)
3. Agent presents candidates to user, discusses scope and value
4. User confirms which pages to include
5. Agent calls mcp-knowledge to create a KnowledgeSource with `source_type=AUTHENTICATED_WEB` and `config.urls = [confirmed URLs]`

Extraction is pipeline-mechanical:
1. RefreshOrchestrator reads the KnowledgeSource config
2. Calls `_handle_authenticated_web` → `_fetch_and_ingest_urls` with browser fetcher
3. Content flows through IngestPipeline (chunk → extract entities → store)
4. Delta detection skips unchanged content

Incremental discovery (finding new subpages added since last discovery) is a separate agent action — it runs the discovery conversation again, comparing against existing source config URLs.

### Q4: Source management agent interaction

**Pure markdown agent (`.agent.md`), two MCP tool sets, conversational flow.**

The source management agent is the human-to-pipeline bridge. It:
- Uses **mcp-browser** tools for navigation and page discovery
- Uses **mcp-knowledge** tools for source CRUD and refresh triggers
- Mediates the user review step — no automation of the "what's valuable" decision

No Python code needed. Follows the established OwlBear agent pattern.

### Q5: Entity type extension

**Direct StrEnum extension. No plugin system.**

Add to `EntityType`: REQUIREMENT, SOLUTION, PROCEDURE, POLICY, STANDARD
Add to `RelationType`: GOVERNS, SUPERSEDES_VERSION

Rationale:
- Single-user, single-workspace system — no external consumers of the enum
- KISS/YAGNI — dynamic registration adds complexity for zero benefit
- The types are domain-model fundamentals, not configuration
- Adding enum values is a safe, mechanical change
- The entity extraction prompts must be updated to include the new types (execution detail)

## Key Trade-offs

| Decision | Gains | Costs |
|----------|-------|-------|
| Separate browser package | Clean boundaries, lazy loading, independent versioning | Two new packages to maintain, ALLOWED_IMPORTS update |
| Protocol injection for fetcher | Knowledge stays browser-unaware, testable with stubs | Composition complexity in mcp-knowledge lifespan |
| Fail-fast auth semantics | No silent 47-URL cascade failure | Divergence from URL_LIST handler behavior |
| SourceType enum over config flag | Semantic clarity, type-safe dispatch | One more handler method (shared internals mitigate) |
| Direct enum extension | Simple, zero infrastructure | Requires knowledge of all types at definition time |

## Warnings

1. **Content safety for authenticated_web sources.** The ingest pipeline's prompt-injection guard currently checks `metadata.get("source_type") == "url"`. Authenticated web content must also be wrapped in `<untrusted_web_content>` sentinel tags. The guard predicate should be **inverted**: wrap everything *except* known-safe source types (`"file"`, `"text"`) rather than enumerating every web source type. This prevents a security gap when new source types are added in the future.

2. **SSO session lifetime is unpredictable.** Corporate SSO token expiry varies by IdP configuration, conditional access policies, and browser state. The `AuthenticationRequired` detection (redirect patterns + 401) is necessary but not sufficient — some SSO failures manifest as 200 responses with login page HTML. The browser fetcher should also detect login-page patterns (form with password field, IdP-specific URL patterns) as auth failures.

3. **Playwright binary dependency.** Playwright requires browser driver binaries downloaded via `playwright install`. This is a one-time setup cost but breaks the "clone = install" promise for the browser feature. The setup guide must document this. Consider whether `playwright install chromium` (lighter) works with Edge CDP, or if `playwright install msedge` is required.

4. **Phase 3 risk (SharePoint REST API).** Deferring API-based extraction to Phase 3 is correct, but the architecture should not make it structurally difficult. The ContentFetcher protocol and AUTHENTICATED_WEB source type are general enough that a future API-based fetcher can be swapped in without architectural changes. This is already handled by the protocol abstraction.

## Confidence

**0.85**

High confidence on the structural decisions (package split, protocol injection, enum extension, phase boundary). Moderate uncertainty on SSO session detection robustness and Playwright deployment experience in policy-locked corporate environments. Both are execution risks, not architectural risks — the architecture accommodates failure gracefully.
