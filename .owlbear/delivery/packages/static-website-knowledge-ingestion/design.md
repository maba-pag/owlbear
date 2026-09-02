# Static Website Knowledge Ingestion Design

> Status: candidate architecture; challenge and validation pending

## Ownership And Flow

Current flow is `URL_LIST -> CompositeSourceFetcher -> intake.read_url -> raw text -> FetchedDocument -> IngestCoordinator -> ContentStore -> knowledge_search`. Browser currently owns pure extraction beside Playwright.

Create `serve/web-content` as distribution `owlbear-web-content` and module `owlbear_web_content`. It depends on lxml and trafilatura and imports neither Browser nor Knowledge. Browser and Knowledge declare workspace dependencies on it; Knowledge includes it in the existing intake/full optional capability rather than forcing extraction dependencies on graph-only consumers. Move `extractor.py` extraction and `cleaner.py` normalization there. Browser retains compatibility adapters for `owlbear_browser.extractor.extract`, `owlbear_browser.extractor.extract_content`, `owlbear_browser.cleaner.strip_noise`, `owlbear_browser.cleaner.html_to_markdown`, and `owlbear_browser.cleaner.clean`. Browser retains its direct lxml dependency for `contract.py` diagnostic HTML sanitization, but no longer owns trafilatura or extraction policy.

The maintained ingestion interface remains:

```text
ConfiguredSourceRecord
  -> SourceFetcher.fetch_source
  -> FetchResult
  -> IngestRequest
  -> IngestResult
  -> RefreshResult
```

Do not widen the generic `ContentFetcher.fetch(url) -> str` contract used by Browser. Add an HTTP-specific `HttpResponse` value and `HttpResponseFetcher.fetch_response(url) -> HttpResponse` protocol. `HttpxContentFetcher` implements both protocols and accepts explicit keyword-only `transport: httpx.AsyncBaseTransport | None = None` and `resolver: HostResolver = system_host_resolver` dependencies. It calls `check_url_allowed(url, resolver=resolver)` inside `fetch_response` before constructing or using the HTTP client; production uses the zero-argument defaults. `CompositeSourceFetcher` receives a distinct `http_response_fetcher_factory: Callable[[], HttpResponseFetcher]`; Knowledge MCP production composition supplies `HttpxContentFetcher`, and `_fetch_url_list` passes that instance to `intake.read_url`. `intake.read_url` owns response classification, invokes `owlbear_web_content`, and adds `media_type` to `IntakeResult`; `FetchedDocument.text` receives already converted content and needs no media carrier. The existing `content_fetcher_factory` remains for authenticated-web acquisition and is not treated as the URL-list seam. Minimal downstream changes are canonical URL/external identity where proof requires it and structured failures. No ACL, cursor, pagination, attachment, or combined-onboarding fields are added.

## Content Behavior

`text/html` and `application/xhtml+xml` are extracted. `text/plain`, `text/markdown`, and `text/x-markdown` are normalized. Missing or other media type returns extraction `unsupported_media_type`. Meaningless HTML returns extraction `content_boundary_missing`. Both persist no new document and leave source state retryable. Normalized Markdown is hashed so presentation-only HTML changes do not replace equivalent meaning.

## Failure Carriers

Add `KnowledgeFailure`, `KnowledgeFailureStage`, stable code literals, and internal `KnowledgeOperationError` in `serve/knowledge/src/owlbear_knowledge/protocols/failures.py`, re-exporting the public carrier types through `owlbear_knowledge.protocols.__init__`. The internal exception holds one redacted `KnowledgeFailure` and is the only exception translated into a typed operational result at coordinator/MCP boundaries. `FetchError` and `RefreshError` carry `KnowledgeFailure` with source ID, safe URI, and timestamp. Add structured document failures to `IngestResult`; replace `_process_document` logging-and-`None` behavior so caught operational faults contribute a typed failure while existing health failure counts remain accurate.

Attribution is owned where the external operation is still distinguishable. Extend `SSRFProtectionError` with a typed reason rather than parsing its message: invalid scheme/hostname/port or blocked address maps to `url_rejected`; resolver failure or a resolver result containing no IPv4/IPv6 address must fail closed and map to `dns_failure`. `HttpxContentFetcher` maps HTTP status, timeout, transport, and size failures; `intake.read_url` owns extraction codes. `ContentStore.ingest` maps SQLite/store transaction faults to `persistence_failed`, embedding-provider faults to `embedding_failed`, and vector upsert faults to `vector_write_failed`, then raises `KnowledgeOperationError`. `ContentStore.search` maps query-embedding faults to `query_embedding_failed` and `search_similar` faults to `vector_query_failed`. It does not infer codes from exception strings. Coordinator and MCP layers propagate the typed carrier without reclassifying it.

Preserve recognizable success values. `refresh_knowledge_source` retains `source_id`, `sources_refreshed`, and `errors`, and additively returns aggregate `documents_created`, `documents_replaced`, `documents_unchanged`, `chunks_created`, and `chunks_replaced` from `RefreshResult.ingest_results`. Operational tool-level failure returns `KnowledgeFailure`. `knowledge_search` is annotated and documented as `list[SearchResult] | KnowledgeFailure`; invalid caller arguments may raise a safe `ToolError`. `share/agents/knowledge-ingestor.agent.md`, `serve/knowledge-mcp/README.md`, and `share/skills/h-knowledge-ops/SKILL.md` document the exact unions and refresh counts and stop instructing callers to parse free-form strings.

Stage/code ownership is:

- acquisition: `url_rejected`, `dns_failure`, `transport_failure`, `http_status`, `timeout`, `response_too_large`;
- extraction: `unsupported_media_type`, `content_boundary_missing`, `extraction_failed`;
- persistence: `persistence_failed`;
- indexing: `embedding_failed`, `vector_write_failed`;
- query: `query_embedding_failed`, `vector_query_failed`.

Partial URL lists retain successful documents and item failures; total failure reports no refresh success.

## Composition Root

Extract the inline service assembly in `serve/knowledge-mcp/src/owlbear_knowledge_mcp/server.py` into one private `build_app_context` composition root parameterized by a private `KnowledgeRuntimeFactories` record. Its fields are `http_response_fetcher_factory`, `embedding_provider_factory`, and `vector_store_factory`; the HTTP fetcher itself owns its resolver and transport dependencies. `app_lifespan` calls this root with production factories for `HttpxContentFetcher`, `BgeM3EmbeddingProvider`, and filesystem `QdrantVectorStore`. The root still constructs real SQLite stores, `ContentStore`, `QueryFacade`, `IngestCoordinator`, and schema tables.

Assembled tests call the same composition root with hand-written deterministic embedding and vector adapters plus `HttpxContentFetcher(transport=httpx.MockTransport(...), resolver=public_fixture_resolver)`. These adapters implement the production protocols and must not inherit from or be instances of `unittest.mock.Mock`, ensuring `ContentStore._upsert_vectors`, `_delete_vectors`, and search traverse normal `store_embedding`, `delete_embedding`, and `search_similar` methods. Configurable failing variants provide the operational failure proofs without patching the public tools.

## Topology And Distribution

The new shared package requires:

- `serve/web-content/pyproject.toml`, `serve/web-content/README.md`, `serve/web-content/src/owlbear_web_content/`, and focused package tests;
- root `uv.lock` and workspace resolution;
- Browser and Knowledge dependency declarations and `[tool.uv.sources]` entries;
- removal of Browser's direct trafilatura dependency while retaining lxml for diagnostic sanitization;
- `tests/test_package_boundary.py` entries for `owlbear_web_content`, Browser, and Knowledge;
- `.github/sync-manifest.json` new `web-content` scope and `tests/test_sync_manifest.py` serve-scope expectations;
- root `pyproject.toml` Ruff `src` entry;
- `.github/copilot-instructions.md` test-domain mapping plus `.owlbear/instructions/architecture.instructions.md` topology diagram and domain table;
- `serve/tools/src/owlbear_tools/testing.py` test-router mapping;
- consumer projection and setup proof that synced Browser and Knowledge resolve the shared distribution.

## Deterministic HTTP Proof Seam

Use source URL `https://fixture.example/article`. Keep production `check_url_allowed` active and add its resolver parameter as described above. The test's `public_fixture_resolver` returns only a synthetic public address for `fixture.example`; `HttpxContentFetcher` passes it to the real SSRF policy and uses deterministic `httpx.MockTransport` only after validation. Supply that fetcher through `KnowledgeRuntimeFactories.http_response_fetcher_factory` into `CompositeSourceFetcher`. Production lifespan supplies the zero-argument production `HttpxContentFetcher`. Do not bind a loopback server, allow private addresses, patch out `check_url_allowed`, parse SSRF messages, or claim that the existing authenticated-web `content_fetcher_factory` reaches URL lists. This is in addition to embedding/vector substitution at the same composition root.

## Migration And Security

Existing URL-list registrations remain valid, but prior raw-HTML documents may be replaced once. File and inline behavior remains unchanged. Browser behavior remains observable while implementation ownership moves. Existing refresh-error consumers migrate from free-form strings to typed fields with a derived human message. Additive refresh count fields and the search failure union are documented public-schema changes.

Preserve HTTP(S)-only SSRF protection, untrusted-source treatment, no credentials/headers/cookies/scripts/actions, no link following, and redaction of secrets, bodies, inappropriate local paths, and exception internals. `HttpxContentFetcher` must enforce finite request timeout and maximum response-byte limits so `timeout` and `response_too_large` are real fail-closed outcomes; exact values are implementation discretion, named constants, and covered by boundary tests. Extraction resource limits remain implementation discretion unless evidence makes a threshold product-significant.

## Proof

- Golden shared-core fixtures prove hierarchy, links, lists, tables, normalization, and noise exclusion.
- Classification and empty-content tests prove fail-closed behavior and retryable source health.
- Browser compatibility tests cover the five existing extraction/cleaner callables named above.
- SourceFetcher and coordinator tests prove partial success, identity, unchanged, replacement, stale-evidence invalidation, additive refresh counts, and structured errors.
- Hand-written failing embedding/vector adapters prove `ContentStore.ingest` and `ContentStore.search` assign stage/code at the operation boundary, preserve retryable state, and propagate redacted carriers through MCP tools.
- An assembled Knowledge MCP test uses `build_app_context` with real registration, refresh, SSRF policy, SQLite persistence, `ContentStore`, `QueryFacade`, and tools; explicit resolver/transport plus deterministic non-Mock embedding/vector adapters produce a positive search result through normal adapter methods.
- Add pytest marker `model`; rewrite default marker selection to `not e2e and not model`; increase `session_timeout` above the model command budget; run the opt-in real-runtime smoke with `-m model --timeout=600`. The smoke loads BGE-M3 and filesystem Qdrant, ingests a bounded fixture, observes persisted vectors, and returns a positive query result.
- Package-boundary, sync-manifest, dependency-lock, Ruff, consumer-projection, and routed package tests cover `web-content`.

## Known Limits

Static HTTP cannot observe JavaScript-postloaded content. Extraction fails closed where no meaningful boundary exists. Moving Browser extraction changes package topology. The current URL-list path, `_ssrf.check_url_allowed`, and MCP lifespan lack the response-fetcher, resolver, and runtime-factory seams described above; current SSRF validation also permits resolver results with no IPv4/IPv6 address, so Delivery must add a fail-closed branch. Current `HttpxContentFetcher` lacks finite response-size and explicit timeout enforcement. Current `ContentStore._upsert_vectors` and `_delete_vectors` have special `unittest.mock.Mock` branches, so proof adapters must be hand-written and exercise normal `store_embedding`, `delete_embedding`, and `search_similar` methods. Existing source-deletion retry leakage remains. Read-only challenge cannot independently verify Delivery's composite package/digest identity; checkpoint and contract validation remain required. Old umbrella files may remain physically present but do not govern this Change.

```yaml target-contract
kind: outcome
id: OUT-001
title: Shared structural web content
promise: Browser and Knowledge use one distributed pure converter that emits normalized structural Markdown without Playwright coupling in Knowledge.
acceptance:
  - "Given representative HTML containing article headings, lists, links, tables, navigation, scripts, and cookie chrome, calling the shared converter returns Markdown containing the article heading, list, link, and table while excluding the fixture navigation, script, and cookie strings."
  - "Given the representative HTML fixture, the compatibility callables owlbear_browser.extractor.extract, owlbear_browser.extractor.extract_content, owlbear_browser.cleaner.strip_noise, owlbear_browser.cleaner.html_to_markdown, and owlbear_browser.cleaner.clean return the same values and raise the same documented input errors as before relocation."
  - "Given serve/web-content and its dependency declarations, running dependency sync, tests/test_package_boundary.py, tests/test_sync_manifest.py, Ruff against owlbear_web_content, consumer projection checks, and serve/tools/src/owlbear_tools/testing.py routed shared-package tests reports no unresolved dependency, boundary violation, sync-owner gap, lint error, projection omission, or test failure."
commitments: [COM-001, COM-005]
dependencies: []
```

```yaml target-contract
kind: outcome
id: OUT-002
title: Durable static source refresh
promise: Registered static textual URLs create searchable source-bound content and expose unchanged and changed refresh semantics.
acceptance:
  - "Given assembled Knowledge MCP tools built through KnowledgeRuntimeFactories, source https://fixture.example/article, production SSRF validation with a synthetic public resolver, an HttpxContentFetcher configured with deterministic httpx.MockTransport, and hand-written deterministic embedding and vector adapters, refresh_knowledge_source reports one created document and knowledge_search returns its unique article phrase."
  - "Given a source refreshed once and a second deterministic response with equivalent normalized content, refresh_knowledge_source reports one unchanged document and leaves document and chunk counts unchanged."
  - "Given a source refreshed once and a second deterministic response with a changed article phrase, refresh_knowledge_source reports one replaced document and knowledge_search returns the new phrase without returning the removed phrase."
  - "Given a deterministic response declaring text/plain, text/markdown, or text/x-markdown, refresh_knowledge_source normalizes and persists the text without HTML extraction."
  - "Given an HTTP response, HttpxContentFetcher.fetch_response retains its declared media type, runs production SSRF validation with its resolver before transport, and intake.read_url exposes that value through IntakeResult.media_type without changing ContentFetcher.fetch."
commitments: [COM-001, COM-002, COM-003]
dependencies: [OUT-001]
```

```yaml target-contract
kind: outcome
id: OUT-003
title: Structured workflow failures
promise: Static ingestion and search operational failures identify their responsible stage through typed redacted fields without false success.
acceptance:
  - "Given an invalid HTTP scheme, malformed authority, or resolved blocked address, refresh_knowledge_source returns acquisition-stage url_rejected with retryability and a redacted message and does not increment sources_refreshed."
  - "Given resolver failure or no resolved addresses for an otherwise valid public HTTP URL, refresh_knowledge_source returns acquisition-stage dns_failure with retryability and a redacted message and does not increment sources_refreshed."
  - "Given an injected transport, HTTP status, timeout, or response-size failure, refresh_knowledge_source returns acquisition-stage transport_failure, http_status, timeout, or response_too_large respectively without incrementing sources_refreshed."
  - "Given unsupported media or meaningful-content absence, refresh_knowledge_source returns extraction failure with unsupported_media_type or content_boundary_missing and persists no new document."
  - "Given a failing persistence operation, ContentStore.ingest raises KnowledgeOperationError carrying persistence_failed and refresh_knowledge_source returns that failure without incrementing created, replaced, or unchanged document counts."
  - "Given hand-written embedding and vector adapters configured to fail independently, ContentStore.ingest attributes embedding_failed or vector_write_failed at the operation boundary and refresh_knowledge_source does not report successful indexing."
  - "Given hand-written embedding and vector adapters configured to fail independently during search, ContentStore.search attributes query_embedding_failed or vector_query_failed and knowledge_search returns that query-stage KnowledgeFailure rather than a result list or unrestricted exception text."
  - "Given a URL-list source with one successful item and one failed item, refresh_knowledge_source retains the successful ingest result and returns the failed item's structured error."
  - "Given the failure carrier implementation, KnowledgeFailure, KnowledgeFailureStage, and code literals are owned and re-exported by owlbear_knowledge.protocols, and FetchError, IngestResult, RefreshError, refresh_knowledge_source, and knowledge_search expose that carrier without free-form parsing."
  - "Given the typed failure and additive refresh-count contract, share/agents/knowledge-ingestor.agent.md, serve/knowledge-mcp/README.md, and share/skills/h-knowledge-ops/SKILL.md describe the same success and KnowledgeFailure shapes and contain no instruction to parse free-form operational error strings."
commitments: [COM-003, COM-004]
dependencies: [OUT-001, OUT-002]
```

```yaml target-contract
kind: outcome
id: OUT-004
title: Proven searchable lifecycle
promise: The maintained Knowledge MCP workflow proves registration, refresh, persistence, indexing, search, and runtime-support boundaries through positive observations.
acceptance:
  - "Given assembled Knowledge MCP tools built through the production composition root with deterministic resolver, HTTP transport, embedding, and vector factories, registration followed by refresh and search returns a positive result from persisted fixture content while real SQLite, SSRF, ContentStore, QueryFacade, and normal store_embedding, delete_embedding, and search_similar adapter methods execute."
  - "Given pyproject.toml excludes model tests by default and sets session_timeout above 600 seconds, installed BGE-M3 and filesystem Qdrant prerequisites, and an opt-in model-marked smoke run with a 600-second per-test timeout, the smoke ingests a bounded fixture, observes persisted vector state, and returns a positive search result before that runtime is described as supported."
commitments: [COM-002, COM-004, COM-006]
dependencies: [OUT-002, OUT-003]
```
