# Static Website Knowledge Ingestion

> Status: admitted revision 2 (2026-10-10). D1, D2, D4, and D5 accepted. Revision 2 adds corrective
> OUT-006 for finalization review findings G10 and G11 and converts commitment provenance to
> decision blocks; challenge, baseline, checkpoint, validation, and approval restart.

## Revision Basis

This package predates the Delivery redesign. Its original four outcomes are observed on `dev` and
form the preserved baseline; they are not re-contracted:

- `serve/web-content` (`owlbear_web_content`) owns extraction; Browser `extractor`/`cleaner` and
  Knowledge `intake.read_url` import it (observed).
- `HttpxContentFetcher.fetch_response` with injectable `transport`/`resolver`, production
  `check_url_allowed` before transport, empty DNS fails closed, 30 s timeout and 5 MB size limit
  (observed, `serve/knowledge/src/owlbear_knowledge/fetcher.py`).
- Media classification for HTML/XHTML/plain/Markdown, `unsupported_media_type`,
  `content_boundary_missing` (observed, `intake.py`).
- `KnowledgeFailure`/`KnowledgeOperationError` carriers, additive refresh counts, typed
  `knowledge_search` failure union (observed, `protocols/failures.py`, Knowledge MCP `server.py`).
- `build_app_context` + `KnowledgeRuntimeFactories` composition root, assembled MCP proof
  (`tests/test_mcp_knowledge_static_refresh.py`), opt-in `model` BGE-M3/Qdrant smoke (observed;
  delivered by commits through ddfd7e393 and 33c31eb3f).

`dev` advanced from 48f263325 to 4990469c1 with no commits under `serve/knowledge`,
`serve/knowledge-mcp`, `serve/browser`, `serve/browser-mcp`, `serve/web-content`, or `tests/`
(observed 2026-10-07); the observations below remain current.

## Confirmed User Directives (2026-10-06)

- Keep `register_knowledge_source`, `refresh_knowledge_source`, `serve/web-content`, and Browser
  structured acquisition with the URL redaction from PR #399.
- Design the missing end-to-end path: register a public static site, refresh it, see it in search,
  re-refresh honestly with change detection.
- GitHub issue #235 (vertical browser-to-knowledge acceptance coverage) is the acceptance proof.
- Authenticated sources (#227) and managed-Mac authentication (#228) are out of scope.
- Bring the Browser and Knowledge docs touched by this Change in line with supported code (part of
  #237).

Interpretation (inferred, shown for approval): a doc file this Change edits is reconciled for its
Browser and Knowledge contract claims as a whole, not only the edited lines. The touched files are
`serve/browser/README.md`, `serve/browser-mcp/README.md`, `serve/knowledge-mcp/README.md`,
`share/skills/h-knowledge-ops/SKILL.md`, `share/agents/knowledge-ingestor.agent.md`, and the Browser
to Knowledge section of `setup/setup-guide.md`. Other `setup-guide` sections, stale preflight test
docstrings, and the remainder of #237 stay with #237.

## Problem

The static HTTP leg works and is proven at the assembled MCP boundary, but the user-facing journey
is not honest end to end:

- G1 (observed): when every item of a refresh fails acquisition, `IngestCoordinator.refresh`
  continues before `ingest`, so source health, `last_checked_at`, and `last_error` keep the previous
  successful state.
- G2 (observed): `_process_document` returns `None` for untyped `RuntimeError`/`ValueError`/
  `LookupError`/`TypeError`/`AttributeError`/`KeyError`; if every document fails that way, refresh
  reports `sources_refreshed=1`, zero counts, and `errors: []` (false success).
- G3 (observed): `url_list` dispatch ignores `fetch_method`; registering `url_list` with
  `fetch_method="browser"` is accepted and silently refreshes over HTTP. No registration validator
  checks kind/transport compatibility.
- G4 (observed, no change needed): documents for URLs removed from a `url_list` would persist, but
  no MCP tool changes a registered source's URLs; delete-and-re-register purges them.
- G5 (observed, #229): `knowledge_ingest` writes to a shared `mcp-inline-{scope}` source, takes no
  `source_id`, returns an `Ingested: ...` string even with structured failures, returns raw exception
  text on error, and lets untitled URL-less captures collide on the default title.
- G6 (observed, #231): Browser acquisition classifies HTTP 404/500 pages containing a content region
  as `success`; only 401/403 are failures.
- G7 (observed, #235): no test crosses Browser acquisition and Knowledge ingestion/search; search
  results expose neither the document URI nor capture provenance.
- G8 (observed 2026-10-07): `IngestCoordinator.ingest` derives health only from the documents it
  receives; `refresh` reports fetch errors in `RefreshResult.errors` but never counts them in health,
  so a refresh where one URL fails acquisition and another succeeds records `ok` health and no
  `last_error`.
- G9 (observed 2026-10-07): `list_knowledge_sources` rows (`SourceInfo`) expose `last_checked_at`
  and `last_error` but not `health` or the registered URLs, so the user cannot see
  `ok`/`degraded`/`failed` and a resumed agent cannot discover which URLs a capture round must cover.
- G10 (observed 2026-10-10, finalization review of `00ad5c405`): Knowledge MCP
  `_redact_capture_url` removes only query names matching its own credential tokens, so values of
  `code`, `jwt`, `assertion`, `SAMLResponse`, `nonce`, and other names that Browser `redact_url`
  redacts or marks as correlation survive into stored capture provenance and `knowledge_search`
  `source.provenance`, contrary to COM-001.
- G11 (observed 2026-10-10, same review): `BrowserContentFetcher.acquire` reports `http_error` only
  when the main-document response origin equals the requested origin (added by OUT-002-T01 commit
  `2ac1358c4` without recorded rationale), so a redirect ending on a different-origin 4xx/5xx main
  document bypasses `http_error`, contrary to COM-006.
- G12 (observed 2026-10-10, design challenge of revision 2): `serve/knowledge-mcp/README.md` states
  that a successful no-op refresh reports all document counts as `0`, but `refresh_knowledge_source`
  reports unchanged documents in `documents_unchanged` (asserted in
  `tests/test_mcp_knowledge_static_refresh.py`), contrary to COM-007.

## Operating Context (inferred)

- Actors and trust: the user (trusted); Copilot agents such as `knowledge-ingestor` (trusted but
  fallible); public web servers and their content (untrusted).
- Exposure: fetched HTTP responses and rendered pages, DNS results, page-supplied URLs and links.
- Stakes: local, reversible Knowledge state; a false success or an error page replacing good content
  misleads later agent work; secrets in URLs must not reach results.
- Guarded: SSRF to private/loopback targets, URL credential/token leakage on the surfaces this Change
  adds or changes, false success summaries, error pages replacing last good content, silent
  transport substitution, scope leakage, an agent capture round that omits or invents registered
  URLs, an agent passing an unredacted provenance URL.
- Not guarded: DNS rebinding and private redirects beyond the accepted current policy (documented
  limit); authenticated or managed-browser sources (excluded by directive); adversarial prompt
  content beyond existing untrusted-content handling; an agent that fabricates capture text for a
  registered URL (agents are trusted but fallible, not adversarial); restoring a previous document
  after a processing fault that follows a committed replacement (reported, not rolled back);
  pre-existing raw exception text in Browser MCP DNS-failure and Knowledge MCP purge messages.

## Product Promise

- A user registers public pages as one Knowledge source and chooses its acquisition: `http`
  (programmatic `refresh_knowledge_source`) or `browser` (agent-mediated capture).
- HTTP sources refresh in one call; browser sources refresh by the agent reading the registered URLs
  from `list_knowledge_sources`, acquiring each through Browser MCP `acquire`, and submitting one
  capture round, a captured document or a typed failure for each registered URL, to
  `knowledge_ingest` bound to that source.
- Both paths land content in the source's scope, visible through `knowledge_search` with the source
  ID, document URI, and capture provenance.
- Re-refresh is truthful: unchanged is a no-op, changed content replaces stale chunks and
  enrichment/graph evidence, failed reacquisition (including HTTP error pages) preserves the last
  good document, and no failure is reported as success.
- Source health is computed the same way for both transports over one refresh or capture round,
  counting acquisition and document failures: no failure -> `ok`; some fail -> `degraded`; none
  succeed -> `failed`; `last_checked_at` and a redacted `last_error` reflect that round, and
  `list_knowledge_sources` shows the health.
- A transport the system cannot honor is refused with a typed reason rather than silently
  substituted.
- Anonymous inline `knowledge_ingest` remains available, documented as non-refreshable, and reports
  the same typed outcomes.
- #235's vertical test proves this across Browser MCP and Knowledge MCP public tools with synthetic
  pages, no credentials, no external network, and no real vector service; the test plays the agent
  and never makes one MCP server call another.
- The Browser and Knowledge docs touched by this Change describe only supported behavior.

Accepted exclusions and the value they remove: authenticated sources (#227) and managed-Mac
authentication (#228) remove capture of signed-in pages, so #235's "authenticated-looking page"
becomes a public synthetic page and its "not a login page" check is proven through Browser's
existing 401/403 classification and the new `http_error`; login-wall heuristics stay with #231. No
programmatic browser refresh (D1) means a browser source needs an agent to refresh.

Technically done but wrong: a browser source that refreshes over HTTP; a capture round that drops a
failing URL and reports `ok`; a 404 page replacing the last good document; health that stays `ok`
after a failed round; a vertical test that mocks either MCP server or the SSRF policy away; cleanup
assertions that pass vacuously because enrichment was disabled.

## Out Of Scope And Preserved Remainder

Authenticated sources (#227), managed Edge/macOS SSO (#228), interactive browser tools (#233), the
remainder of #231 (readiness, authentication ordering, pending pages, redirect policy, region
selection, keyword heuristics), a programmatic Browser transport inside Knowledge MCP, crawling or
link following, attachments, scheduling, source-config editing, Cockpit, approved private
destinations, and redaction of pre-existing Browser MCP DNS-failure and Knowledge MCP purge error
messages are excluded. The delivered baseline above, existing SSRF policies including exact-host
trusted-internal approval, Browser credential/script/action input prohibitions, #399 redaction,
package import boundaries, and file-glob behavior are preserved.

## Material Decisions

- D1 (accepted 2026-10-06, user): Browser-acquired content reaches Knowledge through agent-mediated
  capture bound to a registered source. GitHub issue #229 belongs in this Change. Programmatic
  Browser refresh inside Knowledge MCP is rejected for this Change (it would add a second browser
  lifecycle owner, a Playwright dependency in Knowledge MCP, and overlap #227).
- D2 (accepted 2026-10-06, user): this Change adds only Browser HTTP-status classification from
  #231: a main-document status of 400 or above other than 401/403 yields a typed `http_error`
  acquisition failure. The rest of #231 stays separate.
- D4 (accepted 2026-10-07, user; option B of A per-capture report / B whole round / C not
  recorded): a bound `knowledge_ingest` accepts one complete capture round for a browser source,
  one entry per registered URL, each either captured content or a typed capture failure. Health is
  aggregated over the round exactly as for an HTTP refresh. Consequence: the shared aggregation must
  count acquisition failures, which also repairs G1 and G8 for HTTP sources.
- D5 (accepted 2026-10-10, user): repair G10 and G11 through one corrective outcome (OUT-006):
  Knowledge capture provenance redaction covers every query name Browser `redact_url` redacts or
  marks as correlation, and `http_error` applies to any main-document status of 400 or above other
  than 401/403 regardless of response origin. Completed outcomes keep their bindings.

```yaml target-contract
kind: decision
id: DEC-001
origin: decided
basis: "user directives 2026-10-06 (Confirmed User Directives section)"
statement: "Keep register_knowledge_source, refresh_knowledge_source, serve/web-content, and Browser structured acquisition with the PR #399 URL redaction; design the end-to-end static-site path; GitHub issue #235 is the acceptance proof; authenticated sources (#227) and managed-Mac authentication (#228) are out of scope; bring the touched Browser and Knowledge docs in line with supported code (#237 part)."
```

```yaml target-contract
kind: decision
id: DEC-002
origin: decided
basis: "D1, user 2026-10-06"
statement: "Browser-acquired content reaches Knowledge through agent-mediated capture bound to a registered source; #229 belongs in this Change; programmatic Browser refresh inside Knowledge MCP is rejected."
```

```yaml target-contract
kind: decision
id: DEC-003
origin: decided
basis: "D2, user 2026-10-06"
statement: "This Change adds only Browser HTTP-status classification from #231: a main-document status of 400 or above other than 401/403 yields a typed http_error acquisition failure."
```

```yaml target-contract
kind: decision
id: DEC-004
origin: decided
basis: "D4, user 2026-10-07, option B"
statement: "A bound knowledge_ingest accepts one complete capture round, one entry per registered URL, and health is aggregated over the round exactly as for an HTTP refresh, counting acquisition failures."
```

```yaml target-contract
kind: decision
id: DEC-005
origin: approved
basis: "designer proposal (G3) in the package approved for admission"
statement: "Transport honesty is enforced at registration and refresh, with no compatibility path for the old knowledge_ingest string result."
```

```yaml target-contract
kind: decision
id: DEC-006
origin: approved
basis: "designer proposal in the package approved for admission"
statement: "Internal names beyond the public acceptance fields, the Browser MCP resolver seam form, retryability per capture status, and test fixture layout are builder discretion."
```

```yaml target-contract
kind: decision
id: DEC-007
origin: decided
basis: "askQuestions 2026-10-10 'Finalization review found two real defects in completed tasks. How should I proceed?' -> Start Design revision for P1+P2"
statement: "Repair finalization findings G10 and G11 in one corrective outcome: Knowledge capture provenance redaction covers every query name Browser redact_url redacts or marks as correlation, and http_error applies to any main-document status of 400 or above other than 401/403 regardless of response origin."
```

```yaml target-contract
kind: decision
id: DEC-008
origin: autonomous
basis: "designer, revision 2 design challenge finding G12"
statement: "The corrective outcome also corrects the Knowledge MCP README no-op refresh sentence so it reports unchanged documents in documents_unchanged, keeping the touched docs within COM-007."
```

## Pending Decisions

None.

## Delivery Commitments

```yaml target-contract
kind: commitment
id: COM-001
class: dealbreaker
decisions: [DEC-001, DEC-007]
statement: "Keep register_knowledge_source, refresh_knowledge_source, serve/web-content, and Browser structured acquisition with the #399 URL redaction; the surfaces this Change adds or changes (capture-round and inline knowledge_ingest results and errors, refresh errors, health last_error, stored capture provenance, search provenance, and Browser http_error results) carry no URL credentials, tokens, raw exception text, or session material."
```

```yaml target-contract
kind: commitment
id: COM-002
class: dealbreaker
decisions: [DEC-001, DEC-002]
statement: "Authenticated sources (#227), managed-Mac authentication (#228), and a programmatic Browser transport inside Knowledge MCP are out of scope; MCP servers do not import or call each other, existing package import boundaries hold, and the Browser SSRF allowlist policy is unchanged."
```

```yaml target-contract
kind: commitment
id: COM-003
class: protected-request
decisions: [DEC-001]
statement: "A new vertical test under tests/ is the acceptance proof: it plays the agent across Browser MCP and Knowledge MCP public tools with synthetic pages in headless Chromium, production SSRF checks against synthetic resolvers, and deterministic embedding/vector adapters, using no credentials, external network, or real vector service, and it is repeatable with isolated temporary state."
```

```yaml target-contract
kind: commitment
id: COM-004
class: important-reviewed
decisions: [DEC-004]
statement: "Source health is aggregated over one refresh or capture round, identically for http and browser transports, counting acquisition and document failures; a round with any failure never reports ok and a round with zero successes reports failed; acquisition failures never touch existing documents, while document-processing failures are reported as typed errors without a rollback guarantee."
```

```yaml target-contract
kind: commitment
id: COM-005
class: important-reviewed
decisions: [DEC-002, DEC-004]
statement: "knowledge_ingest bound by source_id accepts one capture round for an active url_list+browser source with one entry per registered URL, refuses the whole round on a missing, unregistered, or duplicate URL, uses the registered URL as document identity, and returns a typed result; list_knowledge_sources exposes the registered URLs so an agent can build the round; unbound inline ingestion stays available, non-refreshable, typed, and collision-free."
```

```yaml target-contract
kind: commitment
id: COM-006
class: important-reviewed
decisions: [DEC-003, DEC-007]
statement: "Browser acquisition reports http_error for a main-document status of 400 or above other than 401/403; 401/403 keep their existing classification order (authentication_required for a detected login form, otherwise access_denied); no other #231 behavior changes."
```

```yaml target-contract
kind: commitment
id: COM-007
class: protected-request
decisions: [DEC-001, DEC-008]
statement: "The Browser and Knowledge docs touched by this Change describe only behavior the code supports, cross-checked against source and tests, without claiming managed SSO, authenticated sources, or programmatic browser refresh."
```

```yaml target-contract
kind: commitment
id: COM-008
class: agreed-path
decisions: [DEC-005]
statement: "Transport honesty is enforced at registration (kind/transport compatibility) and at refresh (browser sources return agent_capture_required); no compatibility path preserves the old knowledge_ingest string result."
```

```yaml target-contract
kind: commitment
id: COM-009
class: implementation-discretion
decisions: [DEC-006]
statement: "Internal model and field names beyond the public fields named in acceptance, the Browser MCP resolver seam form, retryability per capture status, and test fixture layout are builder discretion provided the public tool contracts and acceptance hold."
```
