## Why

OwlBear needs to ingest company-internal pages that require authentication, but its current DDGS extraction path is a short-timeout HTTP request with no browser session, JavaScript rendering, or authenticated profile. OwlBear already has a proven Playwright path for corporate SharePoint, Jira, and Confluence, so content acquisition should use that browser capability instead of depending on an extraction tool that cannot satisfy the workflow.

## Product Promise

Given a known company-internal root URL, OwlBear will ultimately let the user acquire the authenticated rendered page, inspect and approve linked pages, register the approved source, and refresh it into the knowledge system without handing corporate credentials to an agent. This change completes the load-bearing first part of that promise: reliable, structured, single-page browser acquisition that the subsequent knowledge-integration change can compose directly.

The completed acquisition capability is worth using because it returns meaningful Markdown rather than an application shell, reuses a persistent authenticated browser session, identifies when the user must authenticate, exposes redirects and failure diagnostics, and discovers links without navigating them or silently expanding scope.

## Normal Workflow

1. An agent invokes the browser acquisition tool with a user-supplied HTTP(S) root URL and, when needed, an optional content selector or readiness selector.
2. OwlBear opens the page in its persistent browser profile, follows and records web redirects, and lets the user complete login, consent, trust, or MFA interaction in the visible browser when required.
3. OwlBear waits for the selected content or stable meaningful rendered content within explicit deadlines.
4. On success, the tool returns a structured result containing the requested and canonical URLs, redirect chain, title, cleaned Markdown, inert discovered links, content hash, fetch timestamp, and useful diagnostics.
5. On authentication, readiness, access, selector, download, or navigation failure, the tool returns a specific non-success result and does not represent an empty shell, login page, consent page, or access-denied page as acquired content.

## What Changes

- Add a reusable browser-library acquisition API for rendered and authenticated single-page content.
- Add a thin browser MCP tool that exposes the same structured acquisition contract to agents.
- Support persistent, session-assisted authentication without accepting, storing, or automating passwords, MFA codes, or other corporate credentials.
- Add meaningful-content readiness, optional readiness and content selectors, redirect diagnostics, canonical URL reporting, Markdown extraction, link discovery, content hashing, and explicit failure states.
- Treat a caller-supplied valid HTTP(S) root URL as user authorization to visit that page and its web redirects; do not require static host allowlists or reject intranet/private addresses solely because they are private.
- Keep discovered links inert and keep acquisition separate from browser action tools; reject caller-supplied JavaScript, non-web schemes, and downloads.
- Make platform support capability-based: retain the proven Windows Microsoft SSO extension path while allowing ordinary persistent-session authentication on macOS and other supported Playwright hosts.
- **BREAKING** Remove DDGS completely from dependencies, MCP registration, agent grants, setup templates, and research guidance. OwlBear will no longer provide open-ended DDGS web search; known public URLs use built-in web access, while rendered or authenticated URLs use browser acquisition.
- Preserve linked-page approval, source registration, refresh, and knowledge ingestion as a required, separately proposed integration that consumes this acquisition contract.

## Capabilities

### New Capabilities

- `browser-content-acquisition`: Acquire one user-authorized rendered or authenticated web page through a persistent browser session and return meaningful Markdown, discovered links, provenance, diagnostics, and explicit failure states.
- `web-content-tool-routing`: Route known-page acquisition through built-in public web access or OwlBear browser acquisition as appropriate, with DDGS and open-ended DDGS search fully retired.

### Modified Capabilities

None. The main OpenSpec catalog has no existing capability specifications.

## Boundaries

### In Scope

- One-page acquisition through both the reusable `serve/browser` API and a thin `serve/mcp-browser` tool.
- Persistent-session authentication, visible user intervention, readiness and content selection, structured Markdown-first results, inert link discovery, and failure diagnostics.
- User-authorized HTTP(S) navigation and transparent web redirects without a static origin list or blanket private-address denial.
- Complete DDGS retirement and replacement guidance for known public, rendered, and authenticated URLs.
- Unit, integration, and assembled-browser proof for the acquisition contract.

### Out of Scope

- Crawling or automatically following discovered links.
- Linked-page review and approval UI or workflow.
- Knowledge source registration, refresh scheduling, graph relationships, or changes that make `AuthenticatedWebConfig.auth_profile` and `page_limit` operational.
- Wiring `serve/mcp-knowledge` to the browser library or replacing its intentional unwired-browser failure.
- Password, MFA-code, credential, or login-form automation.
- General browser automation through the acquisition API, including arbitrary caller JavaScript.

### Preserved Remainder

A required next OpenSpec change will connect the browser result to linked-page approval, source registration, refresh, and knowledge ingestion. Splitting that integration is an accepted sequencing decision, not a reduction of the promised end state; acquisition alone does not complete authenticated knowledge ingestion.

## Success and Completion

- A normal MCP invocation against a rendered public page returns non-empty meaningful Markdown and complete structured provenance.
- A session-assisted authenticated page can be acquired after automatic session reuse or visible user authentication, without credentials crossing the tool boundary.
- Login, consent, trust, access-denied, empty-shell, readiness-timeout, and selector-miss outcomes are explicit non-successes.
- Redirects are observable, discovered links remain inert, and invalid schemes, downloads, and caller JavaScript are rejected.
- The reusable library and MCP adapter share one acquisition contract, and the adapter contains no independent extraction or authentication policy.
- DDGS is absent from runtime dependencies, MCP configurations, agent tool grants, setup templates, and active research guidance.
- Assembled validation covers a public rendered page and an authenticated persistent-session page; the proven Windows Microsoft SSO route remains operational.
- The change does not claim to complete source ingestion, crawling, approval, or refresh.

## Technically Done but Wrong

- The tool returns HTTP-delivered HTML or a client-rendered shell before meaningful content appears.
- A login, consent, trust, or access-denied page is converted to plausible Markdown and reported as success.
- Authentication works only by asking the agent for passwords or MFA codes.
- The MCP tool works, but its behavior is reimplemented separately from the reusable browser API needed by future knowledge integration.
- Static allowlists or private-IP rejection prevent explicitly requested intranet pages or real SSO redirect flows.
- Link discovery automatically navigates or ingests pages the user has not approved.
- DDGS is removed from the package but remains in agent grants, workspace templates, documentation, or setup behavior.
- Acquisition is declared complete while linked-page approval and knowledge ingestion disappear from the owned product promise.

## Impact

- Browser core: acquisition contracts, Playwright lifecycle, authentication/readiness detection, extraction, link discovery, diagnostics, and platform capability reporting under `serve/browser`.
- Browser MCP: a structured acquisition tool and composition of the browser core under `serve/mcp-browser`.
- Tool topology: workspace and seed MCP configuration, Python dependencies, setup initialization, agent grants, and research/system guidance.
- Validation: browser package tests, MCP contract tests, configuration regressions, and assembled Playwright checks.
- Follow-on integration: `serve/knowledge` and `serve/mcp-knowledge` remain unchanged by this change but become consumers of the new core acquisition contract in the required next proposal.

## Decision Register

| Type | Statement | Basis | Status |
|---|---|---|---|
| User decision | OwlBear always receives a known root URL and does not need open-ended web search. | Confirmed during idea refinement. | Active |
| Accepted exclusion | Retire DDGS completely, accepting the loss of DDGS open-web search. | The user does not need search, and DDGS cannot render or authenticate the required pages. | Active |
| User decision | Complete single-page browser acquisition in this change; make knowledge ingestion and linked-page approval a required separate proposal. | The user chose a smaller implementation boundary while preserving the full end state. | Active |
| User decision | Expose both a reusable browser API and a thin MCP tool. | Agents need direct invocation now; future knowledge integration must compose the core library rather than call MCP-to-MCP. | Active |
| User decision | Use session-assisted authentication and never accept or automate corporate credentials. | Security and usability boundary confirmed during refinement. | Active |
| User decision | Treat the supplied HTTP(S) root as authorization; record redirects, but do not impose static origin lists or blanket private-address rejection. | Intranet access and unpredictable enterprise SSO redirects make those policies incompatible with the intended single-user workflow. | Active |
| User decision | Return Markdown as canonical content; expose raw or sanitized HTML only through explicit diagnostics. | The knowledge consumer needs normalized content while browser evidence remains available for debugging. | Active |
| Evidence conclusion | Retain the Python Playwright, lxml, and trafilatura stack instead of adding Cheerio or NodeHtmlMarkdown. | Existing repository implementation already provides the required extraction primitives; no demonstrated capability requires a second runtime. | Active |
| Evidence conclusion | Do not use CDP as the authentication foundation. | The corporate environment sets `RemoteDebuggingAllowed=0`; the proven route is Playwright Chromium with the Microsoft SSO extension and persistent profile. | Active |
| Assumption | Persistent-session manual authentication can support non-Windows hosts, while managed-macOS Microsoft SSO remains unverified. | Existing evidence proves Windows corporate SSO only; the design must report capability rather than block unrelated sites. | Open validation |
