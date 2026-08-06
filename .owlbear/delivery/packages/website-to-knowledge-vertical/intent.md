# Website-to-Knowledge Vertical

> **Status:** Roadmap only; never approve or admit this umbrella.
> **Research:** `.owlbear/research/website-to-knowledge-opportunity-assessment.md`

## Umbrella Governance

This Design session preserves the overall product promise, evidence, dependencies, and extraction order. It is not an independently deliverable change. Never derive, validate, approve, admit, plan, or orchestrate `website-to-knowledge-vertical`.

Implementation proceeds only through separate focused Design sessions from the ordered extraction queue in the linked research. “Next” means the first queue item without an active or completed focused child. Create or resume that exact child, copy only its bounded scope and relevant evidence, and leave this umbrella unchanged.

Use:

```text
/design website-to-knowledge-vertical
Extract the next unfinished focused change from the ordered queue in the linked research.
Create or resume that child as a separate Design session and work only on its stated scope.
Do not revise, derive, approve, admit, plan, or orchestrate the umbrella change.
Stop at the child change's normal Design approval gate.
```

## Problem

OwlBear exposes Knowledge ingestion, registered source refresh, Browser acquisition, enrichment, and search as separate capabilities, but the normal website-to-Knowledge workflow has never completed successfully in this workspace. The local Knowledge store currently contains no sources or content. Users cannot reliably turn a public or rendered website into a refreshable, searchable source, understand why ingestion failed, or manage the result in Cockpit.

## Actors

- A developer who wants durable project or global knowledge from a website.
- An operator diagnosing Knowledge, Browser, model, storage, or configuration failures.
- An agent ingesting and refreshing curated sources without inventing tool contracts.

## Product Promise

A user can provide a website, validate the acquired content, register it as a durable source, ingest and search it, refresh it later, and inspect source health from one coherent OwlBear workflow. Failures identify the responsible stage and a safe retry condition.

## Normal Workflow

1. The user supplies a public static URL.
2. OwlBear acquires and previews cleaned content without ingesting raw HTML or an ambiguous page.
3. The user or ingestion agent registers a valid refreshable source through the documented schema.
4. OwlBear refreshes the source, chunks and indexes its content, and proves it searchable.
5. Cockpit shows the source, health, refresh result, and search results.
6. A later phase extends the same contract to rendered or authenticated pages without weakening Browser safety boundaries.

## In Scope

- Correct source-management authority and documentation for the ingestion agent.
- One authoritative source identity and delta/refresh contract.
- Cleaned Markdown acquisition for public static pages.
- A deterministic end-to-end fixture proving register -> refresh -> chunk -> search.
- Actionable startup and stage diagnostics.
- A Cockpit Knowledge workspace after the backend vertical is proven.
- A separately gated rendered/authenticated acquisition extension.

## Accepted Exclusions For The First Slice

- Multi-page crawling and sitemap traversal.
- Scheduled refresh.
- Knowledge graph visualization.
- Automatic authentication or credential handling.
- Assembly-stage Delivery work.
- Cross-project workspace switching.

These exclusions defer breadth; they must not reduce the single-page public website promise.

## Preserved Behavior

- Browser remains deny-by-default and rejects ambiguous final pages unless the caller supplies an adequate content boundary.
- Source content remains untrusted data.
- Existing Delivery, Memory, Ideas, and completed-history behavior remains unchanged.
- Knowledge package boundaries remain explicit and mechanically enforced.

## Verified Current Evidence

- Focused Knowledge and Browser suite: 103 tests passed.
- Memory recall suite: 20 tests passed; recall is not missing.
- HTTP acquisition of `https://example.com` succeeds, but the Knowledge HTTP fetcher returns raw response text.
- Production Browser selection in mcp-knowledge raises `RuntimeError: browser fetcher selected but no browser session is wired`.
- Structured Browser acquisition of `https://example.com` returns `ambiguous_final_page` with `content_boundary_missing`; this is a deliberate safety boundary, not by itself a defect.
- Source registration examples omit required nested `config.kind` and fail current validation.
- The Knowledge ingestion agent lacks source register/delete tools.
- `knowledge_ingest` uses one inline, non-refreshable source despite broader documented source identity behavior.
- Browser and Memory MCP entries currently target a different checkout from Kanban and Knowledge in this development workspace.
- The local Knowledge database has zero sources, documents, chunks, entities, or edges.

## Success

- Every queue item is delivered through its own approved and admitted focused change.
- A local deterministic fixture proves a static website can be registered, refreshed, chunked, searched, refreshed unchanged, and diagnosed on failure.
- The public tool schemas, agent authority, handbook, and runtime behavior agree.
- Cockpit can list, inspect, refresh, and search proven sources.
- Rendered/authenticated support is admitted only after its acquisition ownership and proof boundary are explicit.
- The umbrella itself remains unadmitted.

## Technically Done But Wrong

- Admitting or orchestrating this umbrella instead of extracting a focused child.
- Combining multiple queue rows into one child merely to reduce tracking work.
- A polished Cockpit screen over an empty or non-refreshable backend.
- A crawler or scheduler built before one-page ingestion works.
- Weakening ambiguous-page rejection to make a demo pass.
- Mock-only tests that never exercise production composition.
- Treating the browser placeholder as a working integration because adapter unit tests are green.

## Open Material Decisions

These are delegated to the focused child that owns them; they do not make the umbrella admissible.

- Which package owns HTML-to-Markdown extraction for static HTTP sources.
- Whether rendered refresh composes Browser in-process, through an explicit service boundary, or through a different authoritative ingestion workflow.
- Whether the Cockpit child should include registration or initially expose only proven source operations.
