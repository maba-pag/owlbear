# Browser Package and Knowledge Integration Audit

> **Owning task:** User-requested browser audit, 2026-09-05; no Delivery task admitted.
> **Date:** 2026-09-05
> **Question:** What prevents reliable acquisition of trusted company-internal websites,
> including macOS SSO, and their ingestion into maintainable, correctly scoped knowledge?
> **Source baseline:** `5ba3d49aeb91f7b3fd8ddc4a9efaebb07596e8c9` on `dev`.
> **Status:** Research complete; implementation and corporate-site acceptance not performed.

## 1. Context and Question

The intended use is curated company-internal content, including authenticated SharePoint,
Confluence, and other enterprise web applications. The user accepts the documented DNS-rebinding
and private-address redirect limitations. This audit does **not** propose closing those gaps,
restoring removed knowledge-ingestion guards, or treating internal addresses as inherently hostile.
Credential handling, truthful results, content quality, and scope correctness remain relevant.

**Conclusion:** this is a useful alpha acquisition foundation, not a finished Edge/SSO-to-knowledge
workflow. Adding a macOS extension search path alone will not achieve the intended outcome.
The largest problems are browser/authentication selection, inconsistent intranet access policy,
false acquisition successes, incomplete authentication recovery, and broken knowledge handoff semantics.

### Scope and Method

- Inspected all implementation files and package manifests in Browser and Browser MCP, their
  maintained tests and READMEs, and the shared extraction implementation they actually call.
- Followed the knowledge interface through agent guidance, MCP ingestion and composition,
  transport selection, source fetching, coordinator requests, and content identity/storage.
- Reviewed setup seeding and readiness documentation. Knowledge internals were examined where
  they affect browser content; this is not a complete independent knowledge-engine audit.
- Ran focused maintained tests, synthetic Chromium acquisitions, and dependency-isolated probes.
  No production knowledge writes, corporate-site visits, credential collection, browser-profile
  inspection, browser installation, or user-browser attachment occurred.
- Local browser probes used fresh headless Chromium contexts. Requests to synthetic hosts were
  intercepted. Maintained acquisition tests used loopback fixtures, except for one external redirect;
  their authentication-retry test uses the launcher's home-directory persistent profile. These are
  synthetic tests, not company authentication evidence.
- Existing unrelated workspace research was left untouched. Runtime code was not modified.

### Prior Research Reconciled

[Authenticated pipeline research](751-authenticated-content-pipeline.md) describes Edge/CDP and
an injected fetcher as intended architecture, not proof that current production wiring exists.
[The macOS verification](browser-macos-degradation-903.md) explicitly deferred functionality and
accepted startup-only graceful degradation. Its historical paths and runtime descriptions are not
current implementation evidence. It does not establish working macOS authentication.

## 2. Sources Studied

| ID | Source | What It Establishes / Evidence Limit |
| --- | --- | --- |
| L1 | [Launcher](../../serve/browser/src/owlbear_browser/playwright_launcher.py#L29) | Discovery, persistent Chromium launch, capabilities, ownership and cleanup |
| L2 | [Acquisition](../../serve/browser/src/owlbear_browser/fetcher.py#L54) | Actual readiness, authentication, classification, extraction and retained-page decisions |
| L3 | [Contract](../../serve/browser/src/owlbear_browser/contract.py#L35) | Inputs, results, normalization, link handling and diagnostic redaction |
| L4 | [MCP server](../../serve/browser-mcp/src/owlbear_browser_mcp/server.py#L36), [allowlist](../../serve/browser-mcp/src/owlbear_browser_mcp/allowlist.py#L18) | Public tools, preflight policy, lifecycle and serialization |
| L5 | [Browser README](../../serve/browser/README.md), [MCP README](../../serve/browser-mcp/README.md) | Advertised capability and configuration; claims checked against code |
| L6 | [Browser manifest](../../serve/browser/pyproject.toml), [MCP manifest](../../serve/browser-mcp/pyproject.toml), [workspace test configuration](../../pyproject.toml) | Dependency and test boundaries |
| L7 | [Shared extractor](../../serve/web-content/src/owlbear_web_content/extractor.py#L16), [cleaner](../../serve/web-content/src/owlbear_web_content/cleaner.py#L1) | Actual extraction owner; Browser cleaner/extractor modules are compatibility exports |
| L8 | [Knowledge factory](../../serve/knowledge-mcp/src/owlbear_knowledge_mcp/_helpers.py#L37), [placeholder](../../serve/knowledge-mcp/src/owlbear_knowledge_mcp/_types.py#L110), [composition](../../serve/knowledge-mcp/src/owlbear_knowledge_mcp/server.py#L336) | Registered browser refresh has no live acquisition implementation |
| L9 | [Source fetcher](../../serve/knowledge/src/owlbear_knowledge/source_fetcher.py#L43), [source schema](../../serve/knowledge/src/owlbear_knowledge/protocols/sources.py#L85) | Connector routing and persisted browser configuration |
| L10 | [Manual ingestion](../../serve/knowledge-mcp/src/owlbear_knowledge_mcp/server.py#L755), [coordinator](../../serve/knowledge/src/owlbear_knowledge/ingest_coordinator.py#L239), [content request](../../serve/knowledge/src/owlbear_knowledge/protocols/content.py#L45), [content store](../../serve/knowledge/src/owlbear_knowledge/stores/content.py#L140) | Source identity, scope, persistence and reporting |
| L11 | [Ingestor agent](../../share/agents/knowledge-ingestor.agent.md), [knowledge handbook](../../share/skills/h-knowledge-ops/SKILL.md) | Agent-mediated workflow, validation duties, accepted policy and documented contracts |
| L12 | [Seeded MCP configuration](../../seed/.vscode/mcp.json), [setup readiness](../../setup/setup-guide.md#L107) | Wildcard seed, independent processes, browser installation and public-site smoke check |
| L13 | [Package architecture rules](../instructions/architecture.instructions.md), [boundary test](../../tests/test_package_boundary.py) | Separate domain ownership; no MCP-server-to-MCP-server imports |
| E1 | [Microsoft Enterprise SSO for Apple](https://learn.microsoft.com/en-us/entra/identity-platform/apple-sso-plugin) | MDM/Company Portal prerequisites and browser-specific integration; not proof of this Mac's configuration |
| E2 | [Playwright browser types](https://playwright.dev/python/docs/api/class-browsertype) | `msedge` channel, persistent profile constraints and lower-fidelity CDP attachment |
| E3 | [Playwright extension support](https://playwright.dev/python/docs/chrome-extensions) | Persistent Chromium extension loading; branded Chrome/Edge removed sideload flags |
| E4 | [Microsoft Edge DevTools Protocol](https://learn.microsoft.com/en-us/microsoft-edge/devtools/protocol/) | Edge exposes CDP when configured for debugging; Windows examples are not a macOS setup recipe |

External sources were retrieved on the audit date and logged in [source attribution](../sources/overview.md).
The initially attempted Microsoft URL under `/entra/identity/devices/apple-sso-plugin` returned
not found; E1 is the successfully retrieved source. Rolling Playwright docs may describe APIs newer
than a deployed checkout; validate against the installed and locked version before implementation.

## 3. Analysis

### 3.1 Current Control Paths

```text
Browser MCP startup
  -> PlaywrightLauncher
  -> bundled Chromium + dedicated persistent profile
     -> optional extension path, not Edge selection or CDP attachment

acquire(url, selectors)
  -> MCP DNS/IP preflight + domain allowlist
  -> launcher.acquire -> BrowserContentFetcher.acquire
  -> success/failure envelope
  -> agent validates and manually calls knowledge_ingest(text, metadata, source_url)
  -> scope-named INLINE source -> IngestCoordinator -> ContentStore -> enrichment queue

refresh_knowledge_source(authenticated_web source)
  -> IngestCoordinator -> CompositeSourceFetcher
  -> select_content_fetcher("browser")
  -> placeholder.fetch -> transport_failure; no browser acquired
```

Manual text ingestion and registered refresh are distinct paths. The lack of automatic inter-server
communication does not itself make manual ingestion impossible, nor require inventing a new service.

### 3.2 Finding Index

Priority describes impact on the intended workflow, not an externally scored vulnerability.
P1 is a blocker for the named capability; it does not imply that every browser operation fails.
P2 is a concrete reliability or integration defect with a workaround or narrower affected path.
P3 covers maintenance. Unchosen features are design questions, not defects merely because they are
absent. C = code-confirmed; R = probe-reproduced. Conditions below are part of the rating.

| ID | Priority | Finding | Evidence |
| --- | --- | --- | --- |
| B01 | P1 for macOS SSO | Advertised Edge/CDP SSO is not the implemented launcher; macOS discovery fails | C, R |
| B02 | P2; P1 for required private-IP sites | Private intranet targets are blocked even when explicitly allowlisted | C, existing tests |
| B03 | P1 for registered browser refresh | Registered browser refresh always selects a failing placeholder | C, R |
| B04 | P2 | Manual capture cannot bind ingestion to its registered browser source | C, R |
| B05 | P1 for project-scoped ingestion | Project source scope is lost before content persistence | C, R |
| B06 | P1 for trustworthy ingestion reporting | Knowledge ingestion reports an ingestion-shaped success despite structured failures | C, R |
| B07 | P2; release gate for affected SPAs | Readiness can accept a loading shell or prematurely reject delayed content | C, R |
| B08 | P2 | Target selectors bypass authentication classification and close login pages | C, R |
| B09 | P2; HTTP handling is P1 before automatic replacement | Error pages can succeed; legitimate documentation can be classified as login/denial | C, R |
| B10 | P2 | Retained authentication pages lack ownership, cancellation and concurrency bounds | C, R |
| B11 | P2 | Startup failures are hidden; cleanup is not exception-safe throughout | C, R |
| B12 | P2 for demonstrated extraction behavior | Hidden content and first-match extraction need an explicit fidelity contract | C, R; broader formats unverified |
| B13 | Conditional P2 / policy decision | Origin policy rejects cross-origin destinations, including potential approved aliases | C; intercepted redirect probe inconclusive |
| B14 | P2 | Diagnostics are incomplete; URL disclosure risk depends on captured values | C, R; no live credential leak established |
| B15 | P2 for exposed no-session behavior | Interactive tools can report success without a page; broader control scope is undecided | C, R for no-session navigation |
| B16 | P2 profile ownership; other items require decisions | Profile defaults disagree; limits and capture identity need scoped requirements | C |
| B17 | Verification gate, not a separate runtime defect | Maintained tests do not establish the cross-module or managed-SSO user journey | Test review and executions |
| B18 | P3 | Documentation and public configuration disagree with implementation | C |

### B01. Browser and Authentication Selection

[Discovery](../../serve/browser/src/owlbear_browser/playwright_launcher.py#L41) checks
`SSO_EXTENSION_PATH`, then only the Windows Chrome `Default/Extensions` location.
The explicit override uses `exists()`, not directory/manifest validation; version selection is the
first directory returned, not a deterministic supported version. No platform/browser/profile selection
exists. An invalid configured override is also caught and downgraded to extension-free launch.

[Launch](../../serve/browser/src/owlbear_browser/playwright_launcher.py#L131) calls
`chromium.launch_persistent_context` without `channel`, executable selection, or a CDP connection.
No `connect_over_cdp` call exists in the inspected product path. Installed Edge is not selected.
The `microsoft_sso` capability means only that an extension path was supplied/found, not that the
extension loaded, its native integration works, or the target tenant accepted authentication.
Capabilities are not exposed through an MCP readiness/status tool.

**Local reproduction:** macOS (`darwin`), Python `3.14.7`, Playwright `1.62.0`, Edge application present,
`LOCALAPPDATA=None`, no `SSO_EXTENSION_PATH`, and `SSOExtensionNotFoundError`.
This establishes discovery failure, not the absence of all possible manual-login functionality.

**Priority basis:** P1 for the requested macOS SSO outcome, not a claim that Chromium or manual
authentication is generally unusable. Edge/CDP advertising alone would be documentation drift;
the missing authentication path makes this material to the stated goal.

**Planning implication:** choose and prove an authentication mode before implementing discovery.
E1 documents Company Portal, MDM enablement and browser-specific integration for Enterprise SSO;
Edge profile sign-in participates in Microsoft SSO. E3 warns against assuming existing extension
sideload flags will work after merely switching to Edge. Do not equate finding a Chrome extension
directory on macOS with completing the Microsoft authentication integration.

### B02. Intranet Policy Contradiction

[MCP preflight](../../serve/browser-mcp/src/owlbear_browser_mcp/server.py#L52) rejects any private,
loopback, link-local, reserved or unspecified DNS result before checking the allowlist. Exact-host
approval and `*` cannot override this. The core request and fetcher accept private HTTP targets,
and their real browser tests rely on loopback access. Thus the public MCP interface blocks a
class of potential target sites that the core can acquire. Company-internal content can also be
hosted on public-address SaaS; the user's actual target DNS results were not inventoried.

**Priority basis:** P2 pending target selection, P1 for any required private-address site.
This is an intentional policy incompatible with that target, not a broken IP check. Reordering
the allowlist and preflight alone would not fix it: both checks currently have to pass.

The preflight also depends on local DNS before browser navigation. Names resolved only through
an enterprise proxy can fail before the browser gets a chance to use its network configuration.
That proxy scenario is a compatibility risk, not locally reproduced.

**Planning implication:** define one trusted-internal target policy shared by the user-facing
workflow, tests and docs. Decide explicitly how exact host approval, wildcard testing, loopback,
and private addresses interact. This is an access-enablement decision, not a proposal to harden
the accepted rebinding/redirect gaps. The current wildcard seed is documented, not a hidden bypass.

### B03. Registered Browser Refresh Is Not Wired

[The production factory](../../serve/knowledge-mcp/src/owlbear_knowledge_mcp/_helpers.py#L37)
returns [a placeholder](../../serve/knowledge-mcp/src/owlbear_knowledge_mcp/_types.py#L110) whose
`fetch()` always raises. Production composition uses that factory. The source-fetcher probe returned
zero documents and `acquisition / transport_failure / retryable=true` without navigating anywhere.
Retrying cannot repair missing implementation; the retryability is misleading for this condition.

The [authenticated connector](../../serve/knowledge/src/owlbear_knowledge/source_fetcher.py#L151)
expects `fetch(url) -> str`, not the structured acquisition contract. Simply injecting the existing
browser fetcher would select its legacy string path, bypassing the newer readiness/authentication/
identity classifications. `auth_profile` and `page_limit` are persisted but not consumed; only
`base_url` is fetched. No automatic traversal is implemented.

**Planning implication:** decide whether refresh is agent-mediated reacquisition or a bounded
programmatic acquisition adapter. Preserve failures and metadata explicitly. Do not wire the legacy
string method and declare the structured browser workflow integrated. Do not add cross-MCP imports.

**Priority basis:** P1 for the exposed registered-browser-refresh capability. A consciously manual
capture workflow can operate without it. The placeholder fails safely rather than ingesting a login
page; retaining that failure is preferable to silently substituting unauthenticated HTTP.

### B04. Manual Ingestion Does Not Attach to the Registered Source

[`knowledge_ingest`](../../serve/knowledge-mcp/src/owlbear_knowledge_mcp/server.py#L755) creates or
reuses `mcp-inline-{scope}` with `kind=inline`, `fetch_method=none`, and `refreshable=False`.
`source_url` becomes the document URI; it does not create/reuse a browser source. There is no
`source_id` input. Prior browser-source registration therefore does not establish custody of the
subsequent manual capture. Refresh/deletion of that registered source does not address the inline
document. Deleting the shared inline source can instead affect multiple captures in the same scope.

This directly contradicts the handbook's documented URL-linked refresh behavior. `metadata.url`
is not promoted to the URI in this implementation. With omitted `source_url` and title, different
documents use the same default title; the [store identity](../../serve/knowledge/src/owlbear_knowledge/stores/content.py#L479)
falls back from external ID to URI to title, creating a replacement/collision risk.

Markdown itself is valid text input: there is no requirement to strip Markdown before ingesting.
Arbitrary metadata can carry acquisition provenance, but no enforced mapping preserves requested URL,
final URL, redirect history, capture time, profile identity or extraction settings.

**Priority basis:** P2 for source lifecycle and API contract mismatch, not total ingestion failure.
Supplying a stable `source_url` still gives the inline document a stable identity for repeat ingestion.
Independent refresh/deletion of browser sources remains unimplemented. Persist only provenance needed
for identity, traceability and reacquisition; every available browser field need not become mandatory.

### B05. Scope Is Lost at the Coordinator Boundary

[The coordinator](../../serve/knowledge/src/owlbear_knowledge/ingest_coordinator.py#L239) builds
`ContentIngestRequest` without scope. [Its default](../../serve/knowledge/src/owlbear_knowledge/protocols/content.py#L45)
is `global`. The coordinator checks source existence but does not propagate the source's scope.
The content store uses request scope for persistence and vector writes.

**Reproduction:** a source with `scope=project:audit` produced a content-store request with
`scope=global`. This probe inspected the actual request before persistence, using fake storage;
no production database was written. The storage impact follows directly from the source path.

**Impact:** browser content intended for a project can enter global retrieval scope. Scope is not
assumed to be a full authorization boundary, but this breaks isolation and retrieval intent.
Resolve this before claiming correct scoped browser-to-knowledge ingestion.

### B06. Ingestion Can Look Successful When Persistence Failed

The same MCP function discards `IngestResult.errors`, created/replaced/unchanged counts and document
identifiers. It always formats `Ingested: documents_processed=..., chunks_created=...,
chunks_enqueued=...` after a returned coordinator result. A probe with a structured failure and no
created chunks returned `Ingested: documents_processed=1, chunks_created=0, chunks_enqueued=0`.
An exception instead becomes an unstructured `error: ingestion failed: {exc}` string.

This prevents callers from reliably distinguishing unchanged content from failed persistence.
It also disagrees with the agent/handbook expectation of structured outcomes and redacted failures.
The research recommendation is truthful typed projection, not merely changing the success wording.

**Priority basis:** P1 for trustworthy reporting in the intended agent-driven workflow. This is not
proof that failed persistence corrupts stored content. Manual spot-checking can mitigate the problem,
but human initiation does not make an error-suppressing result accurate.

### B07. Readiness Is a Short Text Plateau, Not Page Completion

[Readiness](../../serve/browser/src/owlbear_browser/fetcher.py#L92) checks content-selector count
immediately after DOMContentLoaded. A selector inserted later is rejected before its readiness budget
is used. Without that rejection, two unchanged observations at 50 ms intervals establish stability.
An initially static loading shell easily meets this condition before useful content arrives.

**Reproductions:** a selector inserted after 250 ms returned `selector_not_found`; `Loading...`
scheduled to change after 500 ms returned `success` with the placeholder Markdown. Both used a
1,000 ms readiness budget. Existing maintained delayed-content coverage uses an 80 ms update.

A readiness selector is also used as the text-stability target, not just a readiness predicate.
A static heading can stabilize while the selected article still changes. Locator operations have
their own Playwright waits; the deadline does not bound every await or form one overall time budget.

**Planning implication:** define site-appropriate readiness and one bounded acquisition deadline.
Use the existing selector inputs effectively; neither a fixed sleep nor network-idle alone proves
completion for enterprise SPAs.

**Priority basis:** P2 for a generic acquisition API; a release blocker for target sites exhibiting
these timing patterns. The synthetic cases prove possible false results, not their prevalence across
company sites. Stable simple pages and a well-chosen readiness predicate can work correctly.

### B08. Authentication Is Detected Too Late

Authentication classification follows selector and readiness checks. On a login page lacking the
target article selector, acquisition returns `selector_not_found`; with a missing readiness selector,
it returns `content_not_ready`. The `finally` block closes the page in both cases. Both reproduced.
This removes the visible page the user would need for manual authentication.

When detection does work, the retry reuses a retained tab but navigates to the new request URL again.
After a user finishes login, that can correctly reuse context cookies; it is not inherently a defect
and does not by itself require a new resume API. Before login finishes, an unrelated retry can disrupt
the pending interaction. The concrete P2 defect is losing the login tab on selector/readiness failure.
The maintained retry test goes from an unprotected synthetic login form to an independently
accessible protected-looking page; it does not establish cookie acquisition, session reuse, MFA,
Conditional Access, or actual authentication recovery.

### B09. Final-Page Classification Has False Positives and False Successes

[Classification](../../serve/browser/src/owlbear_browser/fetcher.py#L146) recognizes only 401/403
as HTTP failures. A 404 page containing `main` returned success with `Page not found`; a 500 page
returned success with `Temporary service failure`. Such captures could replace good knowledge content
if the agent accepts them or a future adapter trusts acquisition success. Registered browser refresh
currently stops at B03, so automated replacement through that path is not an observed incident.

**HTTP status handling:** P2 in the current preview-and-confirm workflow, P1 before automatic content
replacement relies on this result. Page preview is a meaningful mitigation, not a substitute for
reporting an unsuccessful HTTP response accurately.

A title containing `sign in` is sufficient for authentication failure regardless of page structure.
A legitimate `How to sign in` guide reproduced this false positive. Body text containing
`access denied` independently produces denial; a troubleshooting guide reproduced that failure.
The form condition also includes any form or dialog, not only an authentication form.
English keyword matching and first-4,000-character scanning leave locale/provider coverage uncertain.

**Authentication/denial heuristics:** P2. False positives impede legitimate retrieval; locale and
provider support should follow the selected sites rather than a speculative universal detector.

**Planning implication:** combine HTTP outcome, authentication evidence, expected target identity
and site structure. Preserve uncertain states for user validation. Keep failure fixtures adjacent
to legitimate articles using the same words.

### B10. Retained Pages and Concurrency

[The fetcher](../../serve/browser/src/owlbear_browser/fetcher.py#L62) owns one mutable pending-page
reference, with no lock, per-request identity, TTL, cancellation operation or effective page cap.
`max_pending_pages` is validated and stored by the launcher but never passed to or enforced by the
fetcher. Parallel authentication requests can overwrite each other's retained reference.

**Reproduction:** three simultaneous authentication acquisitions left three open pages. Calling
`fetcher.close()` closed only one, leaving two until context shutdown. A subsequent unrelated request
can also reuse the pending authentication tab. A user-closed pending page is not checked before reuse.
Each retry adds another download listener without removing the previous listener.

The tab leak is bounded by browser-context lifetime, not proven to survive normal launcher shutdown.
Sequential use without overlapping authentication avoids the demonstrated overwrite. P2 is appropriate;
the unused page-limit parameter is a real contract defect, but multi-session orchestration is not
automatically required.

**Planning implication:** choose serialized acquisition or explicit session/request ownership.
At minimum, enforce the selected concurrency limit, recover from user-closed tabs and clean up owned
pages. Add expiry or a richer session protocol only if the selected workflow needs it; creating fresh
pages alone does not make concurrent authentication safe.

### B11. Startup, Recovery and Cleanup

[MCP lifespan](../../serve/browser-mcp/src/owlbear_browser_mcp/server.py#L104) suppresses every
startup exception and drops the launcher reference. It exposes no reason distinguishing missing
browser binaries, profile locks, policy restrictions, extension problems or page creation failure.
No package logging preserves these events. `acquire` then reports only `Browser unavailable`.

**Reproduction:** a successful synthetic launch followed by `page()` failure left no retained launcher
and invoked `close()` zero times. Normal shutdown closes the page before the launcher without an
independent cleanup guard; a page-close exception can skip launcher shutdown. The launcher itself
closes fetcher/context/Playwright sequentially, so earlier cleanup failures can skip later resources.
It does correctly stop Playwright when `launch_persistent_context` itself raises.

After shutdown, capabilities are not reset and `_pw` is not cleared. Repeated launch/close and
disconnect recovery have no explicit state contract. Startup-only MCP health is not browser readiness.

These are confirmed P2 gaps in failure paths. Normal shutdown does contain cleanup and no process leak
was measured on a real failed startup. The presence of `finally` does not fix a dropped launcher
reference or guarantee that later cleanup runs after an earlier close fails.

### B12. Content Fidelity and Extraction Ownership

The implementation checks visible text for readiness but extracts `inner_html`, which includes
hidden content. A fixture with one visible paragraph and one `hidden` paragraph returned both.
Matching multiple content regions silently selects `.first`; two `main` regions with an explicit
`main` selector returned only the first. Without a selector, the presence of a semantic region is
checked, but extraction still uses the body rather than that region.

Those observations establish behavior, not universal content loss: a selector may intentionally name
one region, and collapsed/hidden document sections may be useful content. Decide whether the product
captures the visible view or the whole logical document. Blanket hidden-node removal is not justified.

The shared extractor falls back to its structural converter whenever trafilatura omits any link
target from the broader cleaned HTML. This preserves links but can reintroduce unrelated content.
Fallback conversion does not have explicit handling for fenced code, image alt content, table
row/column spans or escaped table pipes. Relative link targets remain relative in fallback Markdown,
while `discovered_links` are resolved through browser DOM properties. Whitespace normalization
collapses repeated spaces, including indentation whose meaning may matter in technical content.

These fallback limitations are source-grounded risks, not demonstrated failures on company documents.
Retaining links is a valid trade-off, and trafilatura may handle formats that the fallback does not.
Keep the P2 finding focused on extraction fidelity and prove each proposed format fix with a sample.

There is no explicit frame, shadow-root, pagination, lazy-scroll or attachment acquisition contract.
Downloads are deliberately rejected, and discovered links are not followed. These are scope decisions
to validate with representative documents, not an invitation to implement a general crawler now.
Extraction fixes belong primarily in the shared web-content owner, not duplicate Browser wrappers.

### B13. Redirect and Document Identity

[The origin check](../../serve/browser/src/owlbear_browser/fetcher.py#L169) compares raw
`(scheme, netloc)` and rejects a differing final origin whenever the response request chain is
nonempty. This also rejects legitimate HTTP-to-HTTPS upgrades, corporate aliases and cross-host
canonical destinations. It is a result-identity check after navigation, not private-network prevention.
Intermediate SSO redirects that return to the original origin are not inherently rejected.

**Priority basis:** a policy decision with conditional P2 compatibility impact. Rejecting unknown
cross-origin destinations is defensible target validation. Allowing approved upgrades/aliases may be
necessary, but automatically trusting every redirect or HTML canonical hint is not the implied fix.

`canonical_url` is the final page URL, not HTML canonical metadata. Redirect history is obtained from
the original `goto()` response chain, so later script navigation is not completely represented.
Fragments, tracking/auth query parameters, aliases and hash-router state have no deliberate document
identity policy. If a changed final URL is used as the knowledge URI, it may create a different
document rather than replace the intended one.

The intercepted cross-host redirect probe returned `navigation_failed`, so it did not establish a
runtime result for the origin branch. A maintained external unrelated-redirect rejection case passes,
but does not cover an approved alias or HTTP upgrade. A controlled two-host fixture should distinguish
accepted from rejected destinations before changing this policy.

### B14. Diagnostic and Failure Contracts

#### Diagnostic HTML and Typed Failures

`include_diagnostic_html` is accepted by the public request and MCP tool, but acquisition never
produces diagnostic HTML and MCP serialization never includes it. The opt-in probe returned null.
The sanitizer has unit tests, but those tests do not prove an end-to-end diagnostic feature.
This is an exposed no-op option, not evidence that raw HTML must be added. Implement or remove the
promise according to need. The missing HTML alone is lower priority than truthful failure reporting.

Navigation and readiness exceptions are mapped, but later title/body/DOM reads, extraction,
link evaluation and page close can raise outside the structured failure mapping. Close failures can
replace a result. Public malformed URLs can also fail during parsing/preflight before request-level
error conversion. There is no uniform typed timeout, disconnect or extraction-exception projection.

#### URL Disclosure Boundary

[Success serialization](../../serve/browser-mcp/src/owlbear_browser_mcp/server.py#L136) returns raw
requested/final URLs, redirect history, Markdown and discovered links. A synthetic success envelope
containing `?code=synthetic-code&state=synthetic-state` retained both values in its URL fields.
This directly proves serializer behavior, not that a live SSO callback passes acquisition validation
or exposes a redeemable credential. The requested URL was already supplied by the caller; newly
observed final URLs, redirects and links are the more consequential disclosure surfaces.

[Diagnostic query filtering](../../serve/browser/src/owlbear_browser/contract.py#L183) recognizes
selected names, not every OAuth/SAML value, fragment or userinfo combination. `state` is generally a
correlation/CSRF value, not automatically a bearer credential; authorization-code sensitivity depends
on flow protections and lifetime. Ordinary query parameters can also be essential document identity.
Blocked-IP errors echo the input URL, while diagnostic HTML's sanitizer is not a general confidentiality
guarantee. Useful redaction already exists; it simply does not cover every output surface.

**Priority basis:** P2 risk assessment and output-contract work for authenticated acquisition, not a
confirmed credential leak or a reason to erase every query string. Keep navigation URLs usable inside
the browser, define safe output/provenance handling for sensitive values, and test final/redirect/link
fields as well as diagnostics. Before enabling diagnostic HTML, assess input values and URL attributes.

### B15. Interactive Tools Are a Separate Product Surface

[`navigate`](../../serve/browser-mcp/src/owlbear_browser_mcp/server.py#L196) extracts after
DOMContentLoaded without structured acquisition validation. With no page, it returns the input URL
as a successful dry run; reproduced with an unavailable session. `read_text` and `snapshot` can
return empty/stale cached content. The custom `AuthenticationRequired` exception is caught here,
but current Playwright navigation does not raise that package exception on a login page.

`click`, `type` and `select` operate on one shared page without synchronization, ownership or a fresh
target-policy check. The page differs from the acquisition tabs, so these tools do not reliably resume
an `acquire` authentication session. Clicks can have destructive site effects despite
`destructive_hint=False`; `type` echoes entered text in its result. This matters for future tool grants
even though the inspected knowledge-ingestor agent grants only `acquire`.

**Priority basis:** keep P2 for misleading results from currently exposed no-session tools, with lower
urgency for the acquire-only agent. Intentional dry-run code does not tell callers that no navigation
occurred. Separate interactive and acquisition APIs are otherwise reasonable; parity between them is
not mandatory. Concurrent control, credential entry and wider grants require explicit scope, not an
assumption that this path is already used by the ingestor. Annotation limitations are not proof of a
destructive action having occurred.

**Planning implication:** explicitly retain and test interactive control, or narrow the exposed
product to acquisition. Do not assume annotations enforce read-only behavior. Credentials/MFA should
remain user-entered in the browser, not pass through agent tool arguments or transcripts.

### B16. Profile Ownership and Open Operational Decisions

#### Profile Ownership: P2

- The direct launcher defaults to `~/.owlbear/browser-profile`; MCP defaults to
  `~/.owlbear/chromium-profile`. Manual authentication through the example API does not necessarily
  prepare the server's profile. Multiple workspaces default to the same MCP profile, creating
  ownership/profile-lock concerns. E2 states that browsers cannot concurrently launch the same user
  data directory. Do not solve this by blindly attaching to or copying an everyday profile.

This is a concrete default/configuration mismatch and a plausible multi-workspace lock conflict,
not a measured concurrent-launch failure. A single documented profile with serialized ownership may
be sufficient; tenant orchestration is not a prerequisite for a one-user pilot.

#### Open Operational Decisions

- The launcher exposes no browser-distribution/attachment mode, proxy, tenant/profile identity or
  enterprise-policy diagnostic. Readiness selectors already exist per acquisition request; absence
  of launcher-level site configuration does not remove that capability. Whether existing networking
  suffices for the target company is unverified. Do not disable TLS validation as a shortcut.
- There are positive timeout inputs but no upper bounds, overall deadline, content-size/output limit,
  link count limit or effective concurrency cap. Large pages can produce large tool responses and
  model-mediated ingestion payloads. Quantify target sizes before choosing limits or transfer artifacts.
- `accept_downloads` is not explicitly disabled, so a rejected acquisition does not itself prove that
  no transfer began; Playwright documents automatic download acceptance as the context default.
  Define whether rejection means no ingestion or no download at all.
- Browser and Knowledge compute distinct hashes. Knowledge explicitly owns its persistence hash;
  differing digests do **not** by themselves prove duplicate ingestion. Its whitespace-collapsing hash
  can treat structurally different Markdown as unchanged, and unchanged content returns before
  updating document metadata. Define capture identity, document identity and content identity separately.

These are bounded design questions and evidence gaps, not a collective P2 finding that requires every
possible setting. Adopt limits based on actual content sizes and execution budgets, preserve meaningful
structure where samples require it, and distinguish no-ingestion from no-transfer download semantics.

### B17. Test Coverage and Evidence

| Executed Check | Result | What It Does Not Prove |
| --- | --- | --- |
| Browser contract/compatibility; Browser MCP acquisition/preflight; source fetcher; knowledge static refresh | 92 passed | Managed SSO, a live browser refresh adapter, manual ingestion correctness |
| Six selected Browser acquisition test functions, including parametrized unready-content cases | 7 passed | Real authentication, long-delay SPAs, cross-host redirects |
| Complete acquisition suite plus the same contract/MCP/source/static-refresh selection | 105 passed | Company SSO or the missing browser-to-knowledge production handoff; overlaps the preceding two rows |
| Shared web-content suite and package boundary suite | 17 passed | Representative company-document fidelity or production connection ownership |
| Isolated platform probe | macOS extension failure reproduced; Edge installed | MDM state, Edge account state, Conditional Access or successful SSO |
| Synthetic Chromium cases | B07-B10/B12/B14 reproduced as described | Production site behavior or a complete performance envelope |
| Dependency-isolated interface/lifecycle cases | B03-B06/B11/B15 reproduced as described | Real vector writes, live MCP transport and actual browser process leakage |
| Synthetic success-envelope serialization | Raw `code` and `state` values retained in URL fields | Reachability of a real SSO callback or credential exploitability |

**Maintained checks passed: a 116-test selected set and an overlapping 105-test complete-package
selection, with zero reported failures.** These are overlapping runs, not 221 distinct tests.
The complete selection includes the home-profile authentication-retry test and external `example.com`
redirect case. Neither exercises real company login. The local Python/Playwright versions are
observations, not the declared minimum versions. Passing fixtures are meaningful evidence of working
basic acquisition, extraction and policy behavior, but not an end-to-end readiness result.

The missing user-journey proof is a release gate rather than another runtime defect. Exercise the
chosen adapter or agent-mediated workflow across public contracts; this does not require MCP servers
to import one another. Fixture coverage should address the demonstrated gaps, not replace useful
existing tests with blanket suspicion of mocks.

Relevant maintained files:

- [Browser contract](../../serve/browser/tests/test_contract.py), [compatibility](../../serve/browser/tests/test_content_compatibility.py), [acquisition](../../serve/browser/tests/test_acquisition.py)
- [MCP acquisition](../../serve/browser-mcp/tests/test_acquire.py), [preflight](../../serve/browser-mcp/tests/test_ssrf_preflight.py)
- [Source fetching](../../tests/test_source_fetcher.py), [static refresh](../../tests/test_mcp_knowledge_static_refresh.py)
- [Shared extraction](../../serve/web-content/tests/test_web_content.py), [package boundary](../../tests/test_package_boundary.py)

Synthetic reproduction recipes are deliberately small: fulfill synthetic pages with `context.route`,
call `BrowserContentFetcher.acquire` in a fresh context, and inspect status/Markdown/open pages.
For B07 use a 1,000 ms readiness budget with 250 ms selector insertion and 500 ms content replacement.
For B08 use a stable login form plus absent article/readiness selectors. For B09 return 404/500 with
`main`, and successful articles titled `How to sign in` or mentioning `access denied`. For B10 gather
three concurrent login acquisitions and compare page counts before/after fetcher close. The interface
probes replace storage/launcher dependencies with mocks and inspect requests rather than write data.

### B18. Documentation and Configuration Drift

The package descriptions and READMEs advertise Edge/CDP although the implementation launches bundled
Chromium. Browser README says there are no environment variables despite `SSO_EXTENSION_PATH`, calls
discovery an Edge extension lookup, describes Markdown extraction as plain text, and advertises an
authentication exception that the structured path does not use. MCP docs list `type_input` while the
registered tool is `type`, and advertise a diagnostic-HTML feature that is not wired.

The setup guide correctly distinguishes server startup from Chromium readiness, but its public-site
smoke check does not establish internal routing, SSO or ingestion. Knowledge handbook promises
URL-linked refresh and structured direct-ingest outcomes that the implementation does not provide.
Some preflight test docstrings still describe RED behavior although the checks now pass.

These claims should be reconciled alongside behavior changes, not used as acceptance evidence.

## 4. Recommendation, Confidence, and Limits

### Recommended Direction

Keep the existing Playwright acquisition contract, standalone MCP boundaries, shared web-content
extraction, and Knowledge coordinator/store responsibilities. First prove one real managed-browser
path and one truthful source-linked ingestion path. A replacement browser automation framework is not
justified by the observed failures; most lie in product wiring and local state/classification logic.

The maintained strengths are worth preserving: structured acquisition outcomes, rejection of
credential/script/action inputs, dedicated-profile intent, inert link discovery, explicit domain
configuration, shared extraction ownership, typed Knowledge refresh failures, and functioning local
Chromium fixture tests.

The immediate blockers are the requested macOS SSO path, the exposed registered-browser-refresh
placeholder, lost project scope and suppressed ingestion failures. Manual capture remains viable and
source-linking is a P2 improvement to that path. Private-IP access becomes a blocker only for sites
that need it. Correct HTTP-status handling before automatic replacement; validate readiness and
authentication behavior against the actual SPA targets. Lower-priority scope decisions must not
expand this into a general crawler, multi-tenant browser service or universal page classifier.

### Authentication Options to Validate

| Option | Benefit | Cost / Risk | Assessment |
| --- | --- | --- | --- |
| Managed Edge through Playwright's `msedge` channel and a dedicated approved profile | Reuses a supported installed browser and native identity integration; simpler ownership than attachment | Enterprise policy, profile sign-in and device compliance still need proof; cannot reuse extension flags blindly | First candidate for the company macOS pilot, not yet approved architecture |
| Attach over CDP to an explicitly prepared Edge session | Can reuse that session's authenticated state | Debugging policy/port exposure, lower protocol fidelity, disconnect/tab ownership and user-session interference | Evaluate if controlled launch cannot satisfy company authentication |
| Bundled Chromium with manual login, optional validated integration | Existing implementation and predictable automation runtime | May fail device-bound Conditional Access; extension presence is insufficient evidence | Useful explicit fallback for permitted sites, not advertised Edge SSO |

For any mode, use approved company configuration. Do not extract cookies/tokens, weaken Conditional
Access, expose a general remote-debugging endpoint, or indiscriminately close the user's browser.
An attached context and an application-owned context need different shutdown contracts.

### Knowledge Handoff Options

| Option | Benefit | Cost / Risk | Assessment |
| --- | --- | --- | --- |
| Agent-mediated acquire, validate, then ingest against an explicit source ID | Reuses existing separate MCP tools and human authentication; minimum new runtime machinery | Needs typed ingest results, enforced metadata mapping and an honest manual-refresh workflow | Recommended first complete vertical workflow |
| Programmatic acquisition adapter under an explicitly selected lifecycle owner | Repeatable registered-source refresh without routing content through agent text | Requires ownership/cancellation/failure mapping and an allowed package interface; cannot use the placeholder or legacy string fetch unchanged | Evaluate after the acquisition contract and real-site path are proven |
| Site-specific API connector | Potentially stronger provenance and attachment/version access for a known system | Separate API permissions, authentication and connector scope | Later option if representative sites cannot be captured reliably as rendered pages |

### Inputs for Later Planning

These are sequencing recommendations and acceptance candidates, not admitted tasks or an approved plan.

| Sequence | Bounded Outcome | Findings | Acceptance Evidence |
| --- | --- | --- | --- |
| 1 | Agree supported browser/authentication mode, trusted-site policy and lifecycle owner | B01, B02, B10, B16 | Managed Mac accesses one intended intranet site with company policy intact; unavailable prerequisites have actionable diagnostics |
| 2 | Make one-page acquisition truthful and resumable | B07-B14 | Loading/error/login fixtures never produce valid article success; user can authenticate, retry/cancel and close without stranded tabs |
| 3 | Preserve source identity, scope and outcomes through ingestion | B03-B06, B16 | Acquired Markdown binds to the intended source; project scope survives to content/vectors; unchanged/change/failure results are distinct |
| 4 | Complete the chosen refresh workflow | B03, B04, B13 | Reacquire the same protected page, preserve provenance, replace changed content, and leave old good content intact on acquisition failure |
| 5 | Prove representative content and publish truthful support guidance | B12, B15-B18 | Site samples preserve required tables/code/links; interactive scope is explicit; docs/config/status match exercised behavior |

Minimum regression scenarios for those outcomes:

These scenarios apply to selected capabilities, not mandatory support for every authentication method,
document format or network topology.

1. macOS managed SSO, visible manual-auth fallback, expired session, MFA/consent, user cancellation,
   missing browser, invalid profile, profile-in-use, and successful restart/session persistence.
2. Exact-approved internal host, private DNS results, unresolved/proxy-only host, and accepted SSO
   redirect chain; keep the explicitly accepted rebinding/private-redirect policy unchanged unless
   the user later chooses otherwise.
3. Delayed selectors, slow-changing content, static readiness indicator with changing article,
   404/500/401/403, authentic login pages and legitimate login/access-denied documentation.
4. The selected concurrency policy, user-closed tabs, cancellation and failures in each cleanup
  step; either serialize/reject overlapping acquisitions or prove ownership, with no stranded owned
  resources and no closure of unowned user tabs.
5. Approved representative SharePoint/Confluence/internal pages with headings, nested lists, tables,
   code, relative links, hidden content and any required frames. Decide attachment/crawl scope explicitly.
6. One cross-module fixture: acquire -> validate -> source-linked ingest -> unchanged ingest -> changed
   replacement -> failed reacquisition preserves old content -> search in correct scope -> source deletion.
7. Typed persistence/indexing failures and partial outcomes remain visible to the agent; no successful
  summary from a failed capture or write. Sensitive values in final/redirect/link URLs and diagnostics
  follow the selected output policy without destroying legitimate document identity.

### Confidence and Unresolved Decisions

**High confidence** in the directly inspected and reproduced defects. **Medium confidence** in the
preferred authentication mode until validated against company device policy and target sites.
The restrictive redirect policy is source-confirmed; compatibility with approved aliases/upgrades
still needs a controlled fixture and target requirements. URL serializer behavior is confirmed, but
real credential disclosure and exploitability are not. No claims
are made about this Mac's MDM enrollment, identity broker health, Edge sign-in, proxy certificates,
tenant Conditional Access, live source permissions or real knowledge-search quality.

Before implementation, resolve: whether Edge is mandatory; controlled launch versus attachment;
whether manual authentication is acceptable; single profile versus explicit tenant/profile selection;
whether refresh must be programmatic; which private/loopback targets are intended; representative
content and size limits; and whether interactive controls, attachments or traversal are required.
These are product decisions, not uncertainties that a larger code audit can settle.

No Delivery records, plans, runtime code changes or corporate configuration changes were created.
