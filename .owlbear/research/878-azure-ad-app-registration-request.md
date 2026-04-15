# Azure AD App Registration Request — Graph API SharePoint Access

> **Owning task:** #878 — Submit Azure AD app registration request to IT for Graph API SharePoint access
> **Date:** 2026-04-14  **Status:** Complete

## 1. Context and Question

OwlBear's knowledge pipeline needs read-only access to SharePoint Online page
content via Microsoft Graph API. This requires an Azure AD (Entra ID) app
registration with delegated permissions and tenant admin consent. What exact
configuration should be requested, and what risks exist?

Parent research: .owlbear/research/773-sharepoint-rest-api-parallel-path.md

## 2. Sources Studied

| # | Source | URL / Location | Relevance |
|---|--------|----------------|-----------|
| 1 | Graph API `sitePage.Get` permissions | learn.microsoft.com/en-us/graph/api/sitepage-get | .95 |
| 2 | Entra ID app registration quickstart | learn.microsoft.com/en-us/entra/identity-platform/quickstart-register-app | .90 |
| 3 | OAuth 2.0 device authorization grant | learn.microsoft.com/en-us/entra/identity-platform/v2-oauth2-device-code | .90 |
| 4 | Parent research §3.3 auth requirements | .owlbear/research/773-sharepoint-rest-api-parallel-path.md | 1.0 |
| 5 | Existing Copilot OAuth device-code flow | .owlbear/research/copilot-auth.md | .80 |

## 3. Analysis

### 3.1 Permission Options

| Permission | Type | Scope | Admin Consent | IT Friction |
|------------|------|-------|---------------|-------------|
| `Sites.Read.All` | Delegated | All sites user can access | Required | Medium — broad but read-only |
| `Sites.Selected` | Delegated | Admin-granted per-site | Required + per-site setup | High — per-site overhead |
| `Sites.ReadWrite.All` | Delegated | All sites, read+write | Required | High — over-privileged |

**Recommendation: `Sites.Read.All` (delegated).** This is the least privileged
permission listed by Microsoft for the `sitePage.Get` API. `Sites.Selected` is
more granular but adds per-site admin overhead disproportionate to the use case
(a single developer's local knowledge tool). Write permissions are unnecessary.

### 3.2 Auth Flow Options

| Flow | Fit | Conditional Access Risk |
|------|-----|------------------------|
| Device-code (`/devicecode` endpoint) | Best — OwlBear already uses this pattern for Copilot OAuth | Medium (.40) — CA policies may block |
| Interactive browser (authorization code + PKCE) | Fallback — works with MFA/CA but needs redirect URI | Low — most compatible |
| Client credentials (app-only) | Poor — daemon model, over-privileged, no user context | N/A |

### 3.3 App Registration Specification

| Field | Value |
|-------|-------|
| **Application name** | OwlBear Knowledge Extractor |
| **Supported account types** | Accounts in this organizational directory only |
| **Platform** | Mobile and desktop applications |
| **Redirect URI** | `https://login.microsoftonline.com/common/oauth2/nativeclient` |
| **Client type** | Public client (allow public client flows = Yes) |
| **API permissions** | Microsoft Graph → `Sites.Read.All` (Delegated) |
| **Additional scopes** | `openid`, `offline_access` (for token refresh) |
| **Client secret** | None (public client — device-code flow) |
| **Admin consent** | Required — tenant admin must grant `Sites.Read.All` |

### 3.4 Justification Template

> **Purpose:** Read-only extraction of authored content from SharePoint Online
> modern pages for a local developer knowledge base tool. The application runs
> on a single developer laptop, uses delegated permissions (user-present model),
> and accesses only pages the authenticated user already has read access to.
> No data is stored externally or shared. No write operations are performed.
>
> **Requested permission:** `Sites.Read.All` (Delegated) — least privileged
> permission for the Microsoft Graph `sitePage.Get` API per Microsoft docs.
>
> **Auth flow:** OAuth 2.0 device authorization grant (RFC 8628). User
> authenticates via browser; the application polls for the token. Tokens are
> cached locally and refreshed via `offline_access` scope.

### 3.5 Questions for IT Consultation

1. Does Conditional Access policy block the device-code flow? If so, is
   interactive browser flow (authorization code + PKCE) permitted?
2. What is the intake process for Azure AD app registrations — ServiceNow,
   email, Entra admin center self-service, or other?
3. Is `Sites.Read.All` acceptable, or does IT require `Sites.Selected` with
   per-site grants?
4. What is the expected approval timeline?

### 3.6 Risk Assessment

| Risk | Likelihood | Mitigation |
|------|-----------|------------|
| IT rejects `Sites.Read.All` as too broad | Medium (.40) | Fall back to `Sites.Selected`; accept per-site overhead |
| Conditional Access blocks device-code | Medium (.40) | Use interactive browser flow (auth code + PKCE) |
| Approval takes months | High (.70) | Playwright path works today; this is non-blocking |
| IT requires app review / security assessment | Medium (.30) | Justification template above covers common questions |

## 4. Recommendation (confidence: .85)

**Request `Sites.Read.All` delegated permission with device-code flow.** This is
the least privileged permission for the required API, uses the same auth pattern
OwlBear already implements for Copilot, and requires no client secrets.

The specification in §3.3 and justification in §3.4 are ready for submission.
User action required: identify the IT intake process, submit the request, and
record the tracking ID in the task body.

**Tier: T1 — Autonomous.** Documentation/preparation task. No code, no
architecture change, no security policy change. Findings are non-controversial.

Challenge: FALLBACK — challenger subagent not in available agent list.

## 5. Follow-up Tasks

No additional follow-up tasks needed. Sibling task #879 (GraphContentFetcher
implementation) already exists and is blocked on this task's completion. The
user performs AC #3 (submit request) and AC #4 (track approval) manually.
