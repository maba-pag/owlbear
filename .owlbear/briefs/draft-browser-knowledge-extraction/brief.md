# Authenticated Content Pipeline

## Investment Tier: Production

## Problem

OwlBear agents lack access to corporate knowledge that spans authenticated intranet sources. When agents perform knowledge-intensive work (security concepts, architecture docs, implementation planning), they can't reference corporate security requirements, solution blueprints, operating procedures, or tool documentation — because that content lives behind SSO on SharePoint, Confluence, internal web tools, and GitHub repos, and no pipeline exists to bring it into the knowledge graph.

The existing ingestion pipeline works for unauthenticated content. The gap is authenticated content: extraction through authenticated sessions, discovery of subpages from user-provided roots, user review of value, and ingestion with cross-source entity interconnection.

Scale makes manual extraction impractical — dozens of SharePoint sites, multiple Confluence spaces with hundreds of pages each. Agent output quality is constrained because agents operate without corporate standards and context.

## Outcomes

1. **Authenticated web content can be extracted programmatically.** The system retrieves text from SSO-protected corporate pages through the user's authenticated Edge browser session via CDP. Given a URL to an SSO-protected page, the system returns cleaned text content without manual copy-paste.

2. **A source management agent interactively onboards new sources.** User provides a root URL. Agent discovers linked/child pages, discusses scope and depth with the user, and feeds confirmed pages into the ingestion pipeline. Success: user provides a SharePoint site URL → agent discovers site pages → user reviews → confirmed pages are ingested.

3. **Ingested corporate content is queryable by pipeline agents.** Pipeline agents search the KB and receive corporate content results with source attribution (URL, source system, last refresh date). No agent workflow changes.

4. **Cross-source concepts are linked in the knowledge graph.** The entity extraction pipeline recognizes corporate knowledge types (requirements, solutions, procedures, policies, standards) and creates cross-source edges when entities from different sources refer to the same concept.

5. **Content freshness is maintained through user-triggered refresh.** The user triggers refresh when their Edge session is active. Delta detection skips unchanged content. Changed pages are re-ingested with the old version replaced (not accumulated). New pages discovered during refresh are flagged for user review.

6. **Source removal cleans up completely.** Removing a source cascade-deletes all associated pages, documents, entities, and edges via source_id FK. Allowed URL domains prevent accidental ingestion of unintended sites.

## Approach

### Architecture
- **`serve/browser/`** — core browser library: Edge launcher, CDP manager, content extractor
- **`serve/mcp-browser/`** — MCP server exposing browser tools (navigate, click, type, select, read_text, snapshot) with URL domain allowlist enforcement at the tool implementation level
- **Protocol injection** — knowledge pipeline receives a `ContentFetcher` protocol; browser provides an authenticated implementation; existing httpx path remains default for unauthenticated sources
- **`AUTHENTICATED_WEB`** source type added to `SourceType` enum

### Pipeline Quality (ships with browser infrastructure, not after)
- **HTML→markdown cleaner** — normalizes web content before chunking. The chunker must never receive raw HTML.
- **Hash on cleaned content** — delta detection on normalized text, not raw HTML (prevents false-positive change detection from dynamic boilerplate)
- **Replace-on-change semantics** — when a page changes, the old document + entities + edges are cascade-deleted before re-ingestion. No entity accumulation.
- **Content safety predicate inverted** — wrap-by-default for untrusted content. `authenticated_web` is wrapped automatically. IDPI scanning before go-live.

### Schema Extensions
- **`source_pages` table** — individual URL lifecycle: discovered → approved/rejected → ingested → stale. Links source_id to URLs with approval state and extraction status.
- **`source_id` FK on `documents`** — enables cascade deletion from source through pages → documents → entities/edges
- Corporate **entity types**: REQUIREMENT, SOLUTION, PROCEDURE, POLICY, STANDARD
- Corporate **relation types**: GOVERNS, SUPERSEDES_VERSION
- **Updated extraction prompt** — LLM_EXTRACTION_PROMPT guidance text updated with corporate domain examples. Without this, everything collapses into CONCEPT.

### User Model
- **Source onboarding**: interactive agent conversation. User provides root URL → agent navigates with browser tools → discovers pages → presents categorized list → user approves/rejects → `source_pages` records created.
- **Scope-based approval**: for large sites, user can approve at path level ("include everything under /SitePages/Security/") with an exceptions list, rather than per-page.
- **Refresh**: user-triggered (requires active Edge session). Re-extracts approved pages, delta detection, new pages flagged for review at next interaction. Not cron-scheduled — the user's authenticated session must be alive.
- **Search results**: source attribution metadata (URL, source system, knowledge type, refresh date) surfaced in search results.

### Security
- URL domain allowlist enforced at tool level (not via HookRegistry hooks — hooks swallow exceptions)
- Static/pre-defined extraction JavaScript only — no LLM-influenced JS in authenticated page contexts
- Source configs require explicit user approval (LLM proposes, user confirms)
- IDPI scanning + untrusted content wrapping before browser extraction goes live
- CDP binds exclusively to 127.0.0.1
- Test EDR reaction to `--remote-debugging-port` and DLP reaction to bulk extraction in Phase 0

### Alternatives Considered
- **SharePoint REST API / Microsoft Graph API**: faster and parallelizable, but requires IT-approved OAuth setup, enterprise licenses, and separate authentication flow. Deferred as optional Phase 4 for scale.
- **Community MCP servers** (browser-use, crawl4ai, Stagehand): browser-use conflicts with PydanticAI agent loop; crawl4ai is crawl-only; Stagehand requires cloud. None fit.
- **Chrome extensions**: not viable — Edge is policy-locked, can't install extensions.

## Scope

**In:**
- Edge CDP browser extraction (port v1 launcher/manager)
- MCP browser server with full tool set
- HTML cleaning and normalized hashing
- Replace-on-change refresh semantics
- source_pages lifecycle table + source_id FK
- Corporate entity/relation types + extraction prompt update
- Content safety (IDPI + wrapping)
- URL domain allowlist at tool level

**Out (and why):**
- Scheduled/automated refresh — requires user's active Edge session; fundamentally user-triggered
- Confluence/Jira MCP integration — existing MCP servers cover this; Atlassian Cloud migration will improve them
- Office/PDF extraction — markitdown MCP server handles this
- SharePoint REST API — deferred to Phase 4; requires IT approval
- InterDocGraphBuilder extension for corporate types — Phase 3; entity model must be proven first
- Formal audit trail — personal productivity tool, not externally audited

## Risks & Mitigations

| Risk | Mitigation |
|------|-----------|
| CDP blocked by corporate security (EDR, DLP, policy) | Phase 0 spike validates connectivity before investing in architecture. If blocked: pivot to API-first approach (elevate Phase 4) or browser extension research. |
| Entity extraction collapses corporate types to CONCEPT | Extraction prompt update with domain examples is Phase 1 scope. Validate extraction quality on sample corporate pages before bulk ingestion. |
| Graph corruption from refresh churn | Hash on cleaned content + replace-on-change semantics + source_id FK cascade. All Phase 1 scope. |
| SSO session expires during extraction run | Fail-fast: detect login redirects/200-login-pages, abort remaining URLs, report to user. Resumable state. |
| SharePoint dynamic boilerplate causes false-positive changes | HTML cleaner normalizes content; hash on cleaned text. Test with real SharePoint pages in Phase 0. |

## Key Decisions

- **D1**: HTML cleaning + hash fix ships with browser infrastructure (parallel tracks converging). Rationale: without cleaning, every refresh corrupts the graph.
- **D2**: Full browser tool set, single surface. Rationale: simplicity over artificial security split. User approval is the gate.
- **D4**: URL guards at tool implementation level, not hooks. Rationale: hooks swallow exceptions — guards must block, not log.
- **D5**: New pages during refresh queued for user review. Rationale: consistent with user-as-gate principle. Scope-based approval reduces manual burden.

## Context

### Existing Pipeline (operational, reusable)
- IngestPipeline: text → chunks → entity extraction → graph storage → delta detection
- BookmarkPipeline: dedup → content evaluation → conditional ingestion
- RefreshOrchestrator: source refresh by type, cancellation support, content-hash skipping
- TextChunker: recursive separator-based splitting (markdown-oriented)
- EntityExtractor + LLMExtractor: PydanticAI agent for structured extraction

### v1 Reference
- 12 files, ~1200 LOC: launcher, manager, toolset, crawler, content extractor
- Edge CDP lifecycle: find Edge → probe port 9222 → launch/attach → Playwright
- BFS crawler with max_depth/max_pages, robots.txt, rate limiting
- Never reached production before v2 rewrite

### Delivery Phases
- **Phase 0**: Technical spike — validate Edge CDP on corporate laptop (go/no-go gate)
- **Phase 1**: Browser package + pipeline quality + schema + entity types + basic extraction
- **Phase 2**: Source management agent + interactive discovery + page review UX
- **Phase 3**: InterDocGraphBuilder for corporate types + cross-source linking
- **Phase 4** (optional): SharePoint REST API parallel path for scale
