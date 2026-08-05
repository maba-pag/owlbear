# Website-to-Knowledge Opportunity Assessment

> **Owning task:** Draft Design change `website-to-knowledge-vertical`
> **Date:** 2026-08-05
> **Question:** Which new functionality should OwlBear invest in next, and what enabling improvements
> are required before that investment can deliver reliable user value?

## 1. Context and Question

This assessment compared OwlBear's current product surfaces after the target Delivery lifecycle,
Cockpit Delivery workspace, lifecycle controls, and cross-session review skill were completed. The
goal was to find at least ten new-functionality opportunities and ten improvements, rank them by
value and feasibility, and independently test the hypothesis that Knowledge or Browser should be
next.

The investigation prioritized normal user workflows and executable boundaries over TODO comments,
package-local test counts, or historical claims. No implementation was performed. The resulting
initiative is preserved as the unadmitted Design session `website-to-knowledge-vertical`, package
`2c38985cfd425e3b0af900c64330bcae9c8660d58be16ea83d4ed373d748aa9b`.

## 2. Sources Studied

| Source | Relevant fact | Evidence limit |
|---|---|---|
| `README.md`, `README-consumer.md`, `pyproject.toml` | Delivery, Knowledge, Memory, Browser, Cockpit, setup, and agent ecosystem are current product surfaces | Product-level orientation only |
| `serve/knowledge/src/owlbear_knowledge/` | Owns source lifecycle, HTTP/file intake, ingestion, chunks, vectors, graph, and query | Direct current source |
| `serve/mcp-knowledge/src/owlbear_mcp_knowledge/` | Owns Knowledge MCP composition and tool contracts | Direct current source |
| `serve/browser/src/owlbear_browser/` | Owns rendered acquisition, extraction, validation, and diagnostics | Direct current source |
| `serve/mcp-browser/src/owlbear_mcp_browser/` | Owns Browser MCP lifespan, allowlist, and interactive tools | Direct current source |
| `share/agents/knowledge-ingestor.agent.md` | Ingestor can ingest and refresh but cannot register or delete sources | Current agent authority |
| `share/skills/h-knowledge-ops/SKILL.md` | Documents source lifecycle but contains invalid registration examples and contract drift | Current handbook |
| `.vscode/mcp.json`, `seed/.vscode/mcp.json` | Development MCP wiring mixes checkout identities and supplies no Browser allowlist | Local file is host-specific; seed is distributable authority |
| `serve/cockpit/` | Current UI covers Delivery, Memory, Ideas, completed history, recovery, and limited workspace health; no Knowledge workspace | Direct current source and tests |
| `share/skills/w-orchestration/SKILL.md` | Assembly is explicitly unsupported and recovered rather than dispatched | Current workflow authority |
| `.owlbear/research/751-authenticated-content-pipeline.md` | Prior authenticated-content architecture and trafilatura decision | Historical owners were later replaced |
| `.owlbear/research/765-pipeline-quality-hash-cleaned-content.md` | Prior cleaned-content hashing and replace-on-change reasoning | Describes retired ingestion modules |
| `.owlbear/research/775-phase1-browser-pipeline-schema.md` | Prior Browser/Knowledge package-boundary and phased-delivery reasoning | Its referenced boundary test is now absent |
| `.owlbear/research/browser-fetcher-wiring-1326.md` | Records the Browser placeholder as completed routing | Demonstrates why green adapter tests were insufficient |

No new external source materially affected this assessment, so `.owlbear/sources/overview.md` did
not require an attribution entry.

## 3. Verified Current Baseline

### 3.1 Executable Evidence

| Check | Result | Meaning |
|---|---|---|
| Focused Knowledge and Browser suite | `103 passed` | The subsystem is not generally unstable |
| Memory recall suite | `20 passed` | Recall is implemented; proposals claiming it is missing are stale |
| `HttpxContentFetcher().fetch("https://example.com")` | Success, 559 characters | Static HTTP transport works |
| `select_content_fetcher("browser").fetch(...)` | `RuntimeError: browser fetcher selected but no browser session is wired` | Production browser-backed Knowledge refresh cannot work |
| Direct structured Browser acquisition of example.com | `ambiguous_final_page`, signal `content_boundary_missing` | The default content-boundary guard works as designed; this result alone is not a Browser defect |
| Source-registration model checks | Only payloads with nested `config.kind` validate | Handbook examples are invalid |
| Local Knowledge SQLite inspection in read-only mode | 0 sources, documents, chunks, entities, and edges | No local ingestion workflow has established value yet |
| Final Git check | Clean tree at `333ef436eec40cd082365e5c9a6c66571cbc6268` | Research did not mutate product code |

The focused test command was:

```text
uv run pytest tests/test_source_fetcher.py tests/test_ingest_coordinator_fetch_error.py \
  tests/test_mcp_knowledge_server.py serve/browser/tests serve/mcp-browser/tests -q --tb=short
```

### 3.2 Root Findings

1. `serve/mcp-knowledge/src/owlbear_mcp_knowledge/_types.py` deliberately supplies a Browser
   placeholder that always raises; mocked adapter tests do not prove production composition.
2. `serve/knowledge/src/owlbear_knowledge/fetcher.py` returns raw HTTP response text. Registered
   URL refresh can therefore chunk and embed HTML rather than cleaned content.
3. `knowledge_ingest` in the Knowledge MCP server always uses one inline, non-refreshable source,
   contradicting the handbook's source-identity and refresh claims.
4. The ingestor agent lacks `register_knowledge_source` and `delete_knowledge_source`, so its
   normal authority cannot create a refreshable source.
5. Source configuration is a discriminated union requiring nested `config.kind`; current handbook
   examples omit it.
6. Browser defaults to deny all domains when `BROWSER_ALLOWED_DOMAINS` is absent. The development
   MCP file also points Browser and Memory at sibling `owlbear` while Kanban and Knowledge use
   `owlbear-dev`, making local cross-service evidence version-ambiguous.
7. Architecture instructions claim `tests/test_package_boundary.py` enforces cross-package
   dependencies, but that file is absent.
8. Cockpit already exposes completed history and claim/integration recovery. Proposals describing
   those as missing were rejected after current-source verification.
9. Memory recall is present in Builder authority and passes its focused suite. It is not a current
   product gap.
10. Prior Browser research classified the placeholder's routing behavior as complete. The current
    live probe shows that structural routing and usable functionality are different acceptance bars.

## 4. Ranked Opportunity Portfolio

Scores use five 1-5 dimensions: user value (`V`), reach/frequency (`R`), baseline testability (`T`),
confidence (`C`), and effort (`E`, where 1 is easy). The prioritization aid is
`score = 2V + R + T + C - E`; ordering also respects dependencies, so it is not false precision.

### 4.1 New Functionality

| # | Opportunity | V/R/T/C/E | Score | Dependency |
|---|---|---:|---:|---|
| 1 | Guided static URL -> preview -> registered source -> ingest -> verify workflow | 5/5/5/5/3 | 22 | Contract and extraction fixes |
| 2 | Cockpit Knowledge workspace: sources, health, refresh, search | 5/4/5/5/3 | 21 | Proven backend vertical |
| 3 | `owlbear doctor` for setup, MCP, model, Browser, and storage readiness | 4/5/5/5/2 | 21 | Stable diagnostic contracts |
| 4 | Scheduled refresh with stale-source alerts | 4/4/5/4/3 | 18 | Reliable manual refresh |
| 5 | Bounded sitemap/link crawler with domain and depth policy | 5/3/4/4/4 | 17 | Reliable one-page ingestion |
| 6 | Delivery attempt timeline linked to cross-session review | 4/4/4/4/3 | 17 | Current attempt/history projection |
| 7 | Cross-project Cockpit launcher and workspace registry | 3/3/5/4/2 | 16 | Multi-workspace configuration authority |
| 8 | Authenticated Browser profiles and guided login validation | 5/3/2/3/5 | 13 | Authoritative rendered bridge |
| 9 | Knowledge graph and provenance explorer | 3/2/4/4/3 | 13 | Populated, trusted corpus |
| 10 | Assembly worker and cross-task composition review | 4/2/3/3/5 | 11 | Explicit product demand and workflow redesign |

### 4.2 Improvements

| # | Improvement | V/R/T/C/E | Score | Dependency |
|---|---|---:|---:|---|
| 1 | Give the ingestor source registration/deletion authority and correct schemas | 5/5/5/5/1 | 24 | None |
| 2 | Align MCP checkout paths and configure Browser policy explicitly | 5/4/5/5/1 | 23 | None |
| 3 | Make `knowledge_ingest` honor source identity and delta/refresh semantics | 5/5/5/5/3 | 22 | One source contract decision |
| 4 | Convert static HTTP HTML into clean Markdown before chunking | 5/4/5/5/2 | 22 | Extraction ownership decision |
| 5 | Add register -> refresh -> chunk -> search assembled fixture proof | 5/4/5/5/2 | 22 | Deterministic embedding/vector boundary |
| 6 | Add startup diagnostics for BGE-M3, Qdrant, Playwright, and storage | 4/4/5/5/2 | 20 | Stable error taxonomy |
| 7 | Improve selector discovery, preview, and acquisition diagnostics | 4/4/5/4/2 | 19 | Preserve ambiguity guard |
| 8 | Expose source and trust filters through Knowledge search | 4/3/5/4/2 | 18 | Populated corpus |
| 9 | Replace the Browser refresh placeholder with an authoritative bridge | 5/3/4/5/4 | 18 | Rendered composition decision |
| 10 | Restore the package-boundary test promised by architecture rules | 3/3/5/5/2 | 17 | Current dependency map |

## 5. Analysis and Sequencing

### 5.1 Why Knowledge Is First

Delivery and Cockpit received most recent investment and now have strong runtime and UI proof.
Knowledge exposes substantial capabilities but has an empty local corpus and a broken normal source
workflow. Closing that vertical creates direct user value and exercises Browser, setup, agents,
Cockpit, model readiness, storage, and diagnostics together.

### 5.2 Why Static HTTP Precedes Browser/Auth

Static HTTP transport already succeeds and is highly testable with a local server. It isolates
source identity, extraction, ingest, vector, and search semantics without browser profiles, SSO,
allowlists, or corporate environment policy. Rendered/authenticated support should extend a proven
contract rather than define the contract under harder-to-reproduce conditions.

### 5.3 Correct Sequence

1. Correct agent authority, handbook schemas, setup wiring, and package-boundary enforcement.
2. Add a failing deterministic register -> refresh -> chunk -> search fixture.
3. Decide the authoritative static extraction owner and make the fixture pass.
4. Deliver the guided static website workflow.
5. Add Knowledge source health and management to Cockpit.
6. Decide and prove the rendered/browser composition boundary.
7. Consider crawler and scheduler only after one-page refresh is reliable.

### 5.4 Attractive Work That Should Wait

- A Cockpit-only implementation would present an empty or misleading backend.
- Crawling multiplies extraction, policy, deduplication, progress, and cancellation problems before
  one-page ingestion is reliable.
- Scheduling automates failure until refresh semantics and diagnostics are stable.
- Graph visualization has little value before a corpus exists and provenance is trustworthy.
- Assembly is explicitly unsupported by current workflow and lacks demonstrated user demand.
- Rollback is high-risk Git/runtime work and is less valuable than making an unused core product
  surface functional.

## 6. Recommendation, Confidence, and Limits

**Recommendation:** Proceed with a source-grounded `website-to-knowledge-vertical`, starting with a
public static page and ending with a usable Cockpit Knowledge workspace. Treat rendered and
authenticated acquisition as a separately gated extension.

**Confidence:** High (`0.88`) that Knowledge is the highest-value next product investment; medium
(`0.70`) on the final extraction and Browser composition ownership until Design resolves those
boundaries.

**Independent challenge:** `revise`, then proceed. The challenger agreed with the investment but
required three corrections adopted here: fix mixed checkout authority before interpreting Browser
evidence, preserve the ambiguous-page guard, and decide acquisition/extraction ownership before
implementation rather than assuming the Browser failure is merely extraction quality.

**Limits:** This was a broad current-source assessment, not a full production acceptance run. It did
not download or load BGE-M3, ingest external content into the persistent store, execute corporate
authentication, or run the entire repository suite. Those are Design baseline and delivery proof
concerns, not evidence that the current normal workflow works.