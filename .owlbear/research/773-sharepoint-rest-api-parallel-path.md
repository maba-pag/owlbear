# SharePoint REST API / Microsoft Graph API — Parallel Extraction Path

> **Owning task:** #773 — P4-00: Phase 4 — SharePoint REST API parallel path (optional)
> **Date:** 2026-04-14  **Status:** Complete

## 1. Context and Question

Task #773 is a deferred research placeholder from the Authenticated Content Pipeline (#751)
brief. The question: should OwlBear add Microsoft Graph API or SharePoint REST API as a
parallel extraction path alongside the existing Playwright + SSO extension approach?

Key sub-questions: (1) What concrete APIs exist for extracting SharePoint page content
programmatically? (2) What auth setup is required (IT dependency)? (3) How does API-based
extraction compare to Playwright on quality, speed, and architecture fit? (4) Is this
worth pursuing given that Playwright already works for SharePoint, Jira, and Confluence?

## 2. Sources Studied

| # | Source | URL / Location | Relevance |
|---|--------|----------------|-----------|
| 1 | Microsoft Graph SharePoint API overview | learn.microsoft.com/en-us/graph/api/resources/sharepoint | .90 |
| 2 | Graph API `sitePage` + `canvasLayout` | learn.microsoft.com/en-us/graph/api/sitepage-get?view=graph-rest-1.0 | .95 |
| 3 | Sites.Selected delegated auth announcement | devblogs.microsoft.com/microsoft365dev/sharepoint-now-supports-delegated-sites-selected-authentication/ | .85 |
| 4 | Office365-REST-Python-Client (vgrem) | pypi.org/project/Office365-REST-Python-Client/ | .80 |
| 5 | MSAL Python docs | msal-python.readthedocs.io/en/latest/ | .80 |
| 6 | CDP spike results | .owlbear/research/cdp-spike-results.md | .95 |
| 7 | #751 pipeline research | .owlbear/research/751-authenticated-content-pipeline.md | .90 |
| 8 | Existing ContentFetcher protocol | serve/knowledge/src/owlbear_knowledge/protocol.py | 1.0 |
| 9 | Existing BrowserContentFetcher | serve/browser/src/owlbear_browser/fetcher.py | .95 |
| 10 | Brief architect voice (Phase 4 risk) | .owlbear/briefs/draft-browser-knowledge-extraction/voices/architect.md | .85 |

## 3. Analysis

### 3.1 Graph API Content Extraction Capability

Microsoft Graph v1.0 provides structured page access:

```
GET /sites/{site-id}/pages/{page-id}/microsoft.graph.sitePage?$expand=canvasLayout
```

Returns JSON with `canvasLayout.horizontalSections[].columns[].webparts[]` where
text web parts contain `innerHtml`. Key advantage: **structured content, no boilerplate**.
No nav bars, no suite chrome, no dynamic timestamps — just the authored content per
web part. The entire `strip_noise()` / trafilatura pipeline is unnecessary for this path.

Discovery endpoint: `GET /sites/{site-id}/pages` lists all pages in a site. The API
also supports `$filter`, `$select`, and `$orderby` for efficient enumeration.

**Limitation:** Graph sitePage API covers modern SharePoint pages only. Classic wiki
pages, list views, and web-part pages are not fully supported. Document library files
require the separate `/drives/{drive-id}/items` endpoint.

### 3.2 SharePoint REST API (Legacy)

The traditional `/_api/` REST API provides broader SharePoint coverage but returns
CSOM-style JSON/XML rather than structured page content. Extracting rendered page
content requires either `/_api/SitePages/Pages({id})` (limited fields) or client-side
rendering. Less useful for content extraction than Graph API.

### 3.3 Authentication Requirements

| Auth Pattern | IT Dependency | Scope | Fit for OwlBear |
|-------------|---------------|-------|-----------------|
| Delegated + MSAL interactive | Azure AD app registration + admin consent for `Sites.Read.All` | All sites user can access | Best fit — user-present model |
| Delegated + Sites.Selected | Azure AD app reg + admin grants per-site access | Specific sites only | Good — granular, least privilege |
| Application (client credentials) | Azure AD app reg + admin consent + client secret/cert | Tenant-wide or Sites.Selected | Over-privileged — daemon model, no user context |

**All paths require IT involvement.** An Azure AD (Entra ID) app registration must be
created, and a tenant admin must grant API permission consent. Timeline for this at
the current organization is unknown but historically slow (weeks to months).

MSAL Python (`msal>=1.20`) provides the auth library. Device-code flow (already used
for Copilot OAuth in `serve/orchestrator/`) or interactive browser flow for token
acquisition. Tokens can be cached and refreshed.

### 3.4 Architecture Fit — ContentFetcher Protocol

The existing `ContentFetcher` protocol (`async def fetch(url: str) -> str`) is compatible.
A `GraphContentFetcher` would:

1. Accept a pre-authenticated `httpx.AsyncClient` (or `msgraph` SDK client) at init
2. Parse the SharePoint URL to extract site hostname + page path
3. Resolve site-id via `GET /sites/{hostname}:/{path}`
4. Fetch page content via `GET /sites/{site-id}/pages/{page-id}?$expand=canvasLayout`
5. Concatenate `innerHtml` from all text web parts → simple HTML → markdownify → return

The `RefreshOrchestrator` already dispatches by `SourceType`. A new `SourceType.SHAREPOINT_API`
(or reuse `AUTHENTICATED_WEB` with a config flag) would route to a handler using
`GraphContentFetcher` instead of `BrowserContentFetcher`.

### 3.5 Trade-off Matrix: Playwright vs Graph API for SharePoint

| Criterion | Playwright + SSO Extension | Graph API | Weight |
|-----------|---------------------------|-----------|--------|
| IT dependency | None (works today) | Azure AD app reg + admin consent | High |
| Content quality | Raw HTML → cleaner pipeline | Structured JSON (clean by design) | Medium |
| Speed per page | ~2-5s (browser render + extract) | ~200-500ms (REST call) | Low |
| Parallelism | Sequential (single browser) | Fully parallelizable | Low |
| Hash stability | Requires normalization pipeline | Trivially stable (no dynamic HTML) | Medium |
| Site coverage | Any authenticated site (SP, Jira, Confluence, tools) | SharePoint Online modern pages only | High |
| Discovery | Link-following (browser nav) | API enumeration (list all pages) | Medium |
| Dep footprint | playwright + trafilatura + lxml (~15) | msal + httpx (2-4 new deps) | Low |
| Maintenance | Cleaner patterns must track Fluent UI changes | API is versioned, stable | Medium |

### 3.6 Dependency Analysis

| Option | New Dependencies | Transitive | KISS Score |
|--------|-----------------|------------|------------|
| A: httpx + MSAL only | msal (already have httpx) | ~5 (cryptography, requests, etc.) | .80 |
| B: msgraph-sdk-python | msgraph-sdk, msgraph-core, kiota-* | ~15-20 | .40 |
| C: Office365-REST-Python-Client | Office365-REST-Python-Client | ~8-10 | .55 |

**Option A** (raw httpx + MSAL) is KISS-aligned: thin wrapper, no SDK abstractions,
full control over the 3 HTTP calls needed (resolve site → list pages → get page content).

### 3.7 Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| IT approval takes months | High (.70) | Blocks entire feature | Start approval process early; Playwright path works meanwhile |
| Conditional Access blocks MSAL device-code flow | Medium (.40) | Blocks auth | Test with IT before investing in implementation |
| Graph API doesn't cover classic SP pages | Medium (.50) | Partial coverage gap | Playwright fallback for non-modern pages |
| API rate limits on bulk extraction | Low (.20) | Slows bulk refresh | Batch requests + retry with backoff |

## 4. Recommendation (confidence: .72)

**Defer implementation. Pursue IT approval as a non-blocking parallel track.**

The Graph API path has clear advantages for SharePoint-specific content (cleaner output,
faster, parallelizable, stable hashing), but its value is gated by an external dependency
(IT app registration approval) that OwlBear cannot control. The Playwright approach
already works for SharePoint and covers Jira/Confluence/internal tools — sites that
Graph API cannot reach.

**Recommended sequence:**
1. Continue with Playwright as the primary extraction path (Phases 1-3)
2. Submit Azure AD app registration request to IT (no code investment needed)
3. When/if IT approval arrives, implement `GraphContentFetcher` (~100-150 LOC) using
   httpx + MSAL (Option A) behind the existing `ContentFetcher` protocol
4. Add `SourceType.SHAREPOINT_API` to route Graph API sources through the new fetcher
5. Sources can be configured per-type: Playwright for Jira/Confluence, Graph for SharePoint

**Not recommended:** Building the Graph API integration before IT approval is confirmed.
The implementation is straightforward (~1-2 days of code) but worthless without OAuth
credentials.

**Tier: T2 — Advisory.** Trade-offs exist but no T3 triggers: no new architecture
(reuses ContentFetcher protocol), no security policy change, no breaking change.
The decision is about timing and IT coordination, not technical design.

Challenge: FALLBACK — challenger subagent not in available agent list.

## 5. Follow-up Tasks

1. **Submit Azure AD app registration request to IT** — non-code task, requires
   documenting requested permissions (Sites.Read.All delegated or Sites.Selected),
   justification, and contact. Prerequisite for any Graph API work.
2. **Implement GraphContentFetcher** — blocked on IT approval. ~100-150 LOC: MSAL
   token acquisition, site resolution, page content extraction, innerHtml concatenation.
   Depends on follow-up #1 completion.
