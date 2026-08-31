# Static Website Knowledge Ingestion

> Status: candidate authority; admission gates pending

## Problem And Product Promise

OwlBear can register URL-list sources, but static HTTP currently supplies raw response text and no assembled production path proves clean, durable, searchable Knowledge. A user must be able to register a public HTTP(S) URL, refresh it, preserve meaningful structure as normalized Markdown, search it, skip unchanged content, and replace changed content under stable provenance. Operational failures must expose a stable workflow stage, code, retryability, and redacted message.

This Change is the static foundation, not a claim that server HTML covers modern websites. A separate rendered Browser Change will execute JavaScript and feed rendered DOM through the same converter and Knowledge boundary.

## Normal Workflow

1. Call `register_knowledge_source` with a URL-list source and HTTP transport; registration persists before network work.
2. Call `refresh_knowledge_source`.
3. Acquire under existing SSRF protection and classify the declared media type.
4. Extract HTML/XHTML or normalize plain text/Markdown into structural Markdown.
5. Hash, chunk, persist, index, and expose the content through `knowledge_search`.
6. Repeated clean content reports unchanged without duplicate chunks; changed clean content replaces stale chunks and invalidates stale enrichment and graph evidence.

## In Scope

- Public static HTTP(S), including independently processed URL-list items.
- Explicit register then refresh; no combined onboarding operation.
- Declared `text/html` and `application/xhtml+xml` extraction; declared `text/plain`, `text/markdown`, and `text/x-markdown` normalization.
- Fail-closed `unsupported_media_type` for missing, binary, or unsupported types.
- Fail-closed `content_boundary_missing` when supported HTML has no meaningful content.
- A pure shared web-content core used by Browser and Knowledge, with Playwright remaining Browser-only.
- Stable source/document identity and publicly observable created, unchanged, and replaced behavior.
- Structured operational failures across `acquisition`, `extraction`, `persistence`, `indexing`, and `query`.
- Deterministic assembled MCP proof plus separate positive real BGE-M3/Qdrant smoke.

## Out Of Scope And Preserved Remainder

JavaScript rendering, authentication, managed Edge, CDP, SSO, crawling, scheduling, attachments, Jira, Confluence, private-content authorization, Cockpit, a network Knowledge service, and a universal connector framework are excluded. Rendered acquisition remains assigned to a later Change using this converter and ingest boundary. Existing SSRF protection, untrusted-content handling, file/inline behavior, replacement ownership, Browser ambiguity checks, and Browser credential/session-input prohibitions remain intact.

## Confirmed Decisions

- This independent package supersedes old umbrella prerequisite assumptions for this scope; old umbrella files are non-governing historical material.
- Registration then refresh remains explicit so a failed first refresh leaves inspectable source state.
- Pure extraction moves from Browser into `serve/web-content`, distribution `owlbear-web-content`, module `owlbear_web_content`; Browser and Knowledge depend on it, not each other.
- Output is normalized Markdown preserving headings, paragraphs, lists, links, and tables while removing navigation, scripts, styles, cookie notices, and known page chrome.
- Declared response types use the literal set named in scope; content sniffing and document conversion are excluded.
- Empty or ambiguous extraction fails closed and persists no new document.
- `intake.read_url` owns response classification and shared conversion. `HttpxContentFetcher.fetch_response` supplies body and media type; `IntakeResult.media_type` records the declaration; `FetchedDocument.text` receives converted content and needs no media field.
- Operational failures use `{stage, code, retryable, message}` with contextual source, safe URI, and timestamp where applicable.
- Existing success values remain recognizable. `refresh_knowledge_source` keeps `source_id`, `sources_refreshed`, and `errors` and additively exposes document/chunk outcome counts. `knowledge_search` keeps its result list on success. Either operation returns a typed `KnowledgeFailure` value for operational tool-level failure; invalid arguments may still raise a redacted `ToolError`.
- Deterministic assembled proof may replace remote HTTP transport, DNS resolution, embedding, and vector implementations below the public MCP boundary while preserving the production SSRF policy and production composition. Real BGE-M3/Qdrant support requires a separate positive ingest-and-query smoke.

## Failure Codes

Codes exercised by this Change are:

- acquisition: `url_rejected`, `dns_failure`, `transport_failure`, `http_status`, `timeout`, `response_too_large`;
- extraction: `unsupported_media_type`, `content_boundary_missing`, `extraction_failed`;
- persistence: `persistence_failed`;
- indexing: `embedding_failed`, `vector_write_failed`;
- query: `query_embedding_failed`, `vector_query_failed`.

## Success

A deterministic public-host fixture crosses Knowledge MCP registration, refresh, persistence, indexing, and search while the real SSRF policy runs. Searchable Markdown retains article hierarchy and excludes noise. Plain-text/Markdown fixtures work without HTML extraction. Unsupported and empty responses persist no document and return structured failures. The refresh tool reports unchanged and replaced counts additively. Unchanged refresh creates no records; changed refresh replaces content and search no longer returns removed text. Existing Browser extraction callables preserve observable output through the shared core. Injected operational failures identify their stage without leaking internals. Distribution, lint, dependency, package-boundary, and test-routing metadata include the shared package.

## Technically Done But Wrong

Raw or page-shell HTML is indexed; hierarchy is flattened; JavaScript support is claimed from server HTML; tests bypass assembled MCP composition; tests disable the SSRF policy to reach localhost; Browser is imported into Knowledge; the cleaner is copied; searchability is claimed from SQLite alone; real runtime support is claimed from imports; refresh hides content outcomes; or exception text is returned without structured attribution.

## Evidence And Limits

Observed source confirms the existing `FetchedDocument -> IngestDocument -> IngestCoordinator` boundary, internal created/replaced/unchanged outcomes, free-form current errors, Browser's pure trafilatura/lxml cleaner, Browser's separate lxml diagnostic sanitizer, exact package-boundary coverage, optional BGE-M3/Qdrant dependencies, Knowledge's loopback/private-address block, and explicit sync/lint/test-routing topology. Generic extraction cannot cover every site and therefore fails closed. Existing deletion retry leakage is not repaired. The real-runtime smoke may require model preparation; failure blocks that support claim, not deterministic interface proof.

```yaml target-contract
kind: commitment
id: COM-001
class: dealbreaker
provenance: user-confirmed Product Promise
statement: Static URL refresh stores normalized structural content rather than raw HTML or ambiguous page shells.
```

```yaml target-contract
kind: commitment
id: COM-002
class: protected-request
provenance: user-confirmed workflow
statement: Unchanged clean content creates no duplicate document or chunks, while changed clean content replaces stale evidence under stable source identity and exposes its outcome through refresh.
```

```yaml target-contract
kind: commitment
id: COM-003
class: dealbreaker
provenance: user-confirmed safety decision
statement: Unsupported media and missing meaningful content fail closed without persisting a new document.
```

```yaml target-contract
kind: commitment
id: COM-004
class: protected-request
provenance: user-confirmed diagnostics decision
statement: The assembled workflow exposes typed redacted operational failures for acquisition, extraction, persistence, indexing, and query while preserving recognizable success values.
```

```yaml target-contract
kind: commitment
id: COM-005
class: agreed-path
provenance: user-confirmed architecture decision
statement: Browser and Knowledge consume one pure distributed web-content core without importing each other, and Playwright remains Browser-only.
```

```yaml target-contract
kind: commitment
id: COM-006
class: important-reviewed
provenance: source-grounded proof decision
statement: Deterministic assembled proof and real BGE-M3/Qdrant runtime proof remain distinct support claims.
```
