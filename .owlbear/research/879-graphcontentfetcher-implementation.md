# GraphContentFetcher Implementation — Validation & Implementation Plan

> **Owning task:** #879 — Implement GraphContentFetcher for SharePoint API extraction
> **Date:** 2026-04-14  **Status:** Complete

## 1. Context and Question

Task #879 was created as a follow-up from #773 (SharePoint REST API parallel path research).
The parent research recommended deferring implementation until IT approval of Azure AD app
registration (#878). This research validates the #773 findings against current codebase state
and API surface, then documents the implementation plan in enough detail for TDD decomposition.

Key question: Is the implementation approach from #773 still sound, and what specific
decisions are needed for the builder when the external blocker clears?

## 2. Sources Studied

| # | Source | URL / Location | Relevance |
|---|--------|----------------|-----------|
| 1 | #773 research doc | .owlbear/research/773-sharepoint-rest-api-parallel-path.md | 1.0 |
| 2 | canvasLayout v1.0 API reference | learn.microsoft.com/en-us/graph/api/resources/canvaslayout?view=graph-rest-1.0 | .90 |
| 3 | SE: retrieve modern SP page content | sharepoint.stackexchange.com/questions/307632 | .85 |
| 4 | MS Q&A: parse sharepoint aspx file | learn.microsoft.com/en-za/answers/questions/1838381 | .80 |
| 5 | msgraph-sdk-python README (v1.55.0) | github.com/microsoftgraph/msgraph-sdk-python | .75 |
| 6 | MSAL Python docs (v1.35.x) | msal-python.readthedocs.io | .80 |
| 7 | azure-identity vs msal comparison | datalineo.com/post/power-bi-rest-api-with-python-part-iii-azure-identity | .70 |
| 8 | ContentFetcher protocol | serve/knowledge/src/owlbear_knowledge/protocol.py | 1.0 |
| 9 | RefreshOrchestrator dispatch | serve/knowledge/src/owlbear_knowledge/refresh.py | 1.0 |
| 10 | SourceType enum | serve/knowledge/src/owlbear_knowledge/models.py | 1.0 |
| 11 | BrowserContentFetcher pattern | serve/browser/src/owlbear_browser/fetcher.py | .95 |

## 3. Analysis

### 3.1 Validation of #773 Findings

All #773 findings confirmed current as of 2026-04-14:

| Claim | Status | Evidence |
|-------|--------|----------|
| canvasLayout API in v1.0 GA | Confirmed | MS Learn updated 2024-07-23, community confirms v1.0 works |
| ContentFetcher protocol compatible | Confirmed | protocol.py `async def fetch(url: str) -> str` unchanged |
| SourceType extensible | Confirmed | models.py StrEnum with 3 members, trivial to add |
| RefreshOrchestrator dispatches by type | Confirmed | refresh.py if/elif chain, adding branch is trivial |
| Option A (httpx+msal) is KISS-optimal | Confirmed | msgraph-sdk v1.55.0 depends on kiota-*, azure-core, 15+ transitive deps |

### 3.2 New Finding: azure-identity vs raw MSAL

The msgraph-sdk-python ecosystem now recommends `azure-identity` (wraps MSAL) over
raw MSAL for `DeviceCodeCredential`. Trade-off:

| Criterion | raw msal | azure-identity | Weight |
|-----------|----------|----------------|--------|
| Transitive deps | ~5 (cryptography, requests, PyJWT) | ~10+ (azure-core, msal, typing-extensions) | High |
| Token caching | Manual (serialize/deserialize) | Built-in with `TokenCachePersistenceOptions` | Medium |
| API ergonomics | Manual device-code flow loop | One-liner `DeviceCodeCredential(client_id, tenant_id)` | Low |
| KISS alignment | Better — fewer deps, full control | Worse — adds azure-core layer | High |

**Verdict:** Stick with raw MSAL (Option A). The 3 HTTP calls in GraphContentFetcher
don't justify adding azure-core's abstraction layer. Token cache can be a simple JSON
file (~10 LOC with msal's `SerializableTokenCache`).

### 3.3 API Call Sequence (Implementation Detail)

```
1. Parse SharePoint URL → extract hostname + site-relative-path
   e.g. "https://contoso.sharepoint.com/sites/Engineering/SitePages/Overview.aspx"
   → hostname="contoso.sharepoint.com", path="/sites/Engineering"

2. Resolve site-id:
   GET https://graph.microsoft.com/v1.0/sites/{hostname}:/{path}
   → response.id = "contoso.sharepoint.com,guid1,guid2"

3. Find page by name:
   GET https://graph.microsoft.com/v1.0/sites/{site-id}/pages
       ?$filter=name eq 'Overview.aspx'
       &$select=id,name,title
   → page_id

4. Fetch page content:
   GET https://graph.microsoft.com/v1.0/sites/{site-id}/pages/{page-id}/
       microsoft.graph.sitePage?$expand=canvasLayout
   → canvasLayout.horizontalSections[].columns[].webparts[]

5. Extract innerHtml from text web parts → markdownify → return
```

### 3.4 Known Limitations

- **Modern pages only.** Classic wiki pages, list views, web-part pages unsupported.
- **CanvasContent1 null for complex pages via REST API** — but `$expand=canvasLayout`
  via Graph API returns structured content (confirmed by community sources #3, #4).
- **Non-text web parts** (images, embeds, Power BI) return config JSON, not content.
  Initial implementation should extract text web parts only.

### 3.5 External Blocker Status

Task #878 (IT app registration) is in `research` status, not yet submitted.
Task #879's `depends_on` field is empty but should include #878. The architect
review on #773 flagged this gap — cannot be fixed via available kanban tools
(no `update_task` available).

## 4. Recommendation (confidence: .82)

**No changes to the #773 recommendation.** Defer implementation until #878 clears.
The implementation plan is ready for TDD decomposition when elevated.

Specific implementation decisions resolved by this research:
1. **Auth:** raw msal + httpx (Option A) — not azure-identity
2. **Token cache:** msal `SerializableTokenCache` to JSON file in store/
3. **HTML→markdown:** markdownify (already in `serve/browser` dep tree via trafilatura)
4. **URL parsing:** regex or urllib.parse — extract hostname + site-path + page-name
5. **SourceType:** Add `SHAREPOINT_API = "sharepoint_api"` member
6. **Orchestrator wiring:** New `_handle_sharepoint_api()` method + dispatch branch

**Tier: T1 — Autonomous.** Implementation follows established ContentFetcher protocol
pattern. No architectural changes. Dependency addition (msal) is standard.

Challenge: FALLBACK — challenger subagent not in available agent list.

## 5. Follow-up Tasks

No new follow-up tasks needed. Task #879 itself is the implementation task (to be
decomposed by planner when elevated). Task #878 (IT prerequisite) already exists.

Action item: Set `depends_on: [878]` on task #879 when update_task tool is available.
