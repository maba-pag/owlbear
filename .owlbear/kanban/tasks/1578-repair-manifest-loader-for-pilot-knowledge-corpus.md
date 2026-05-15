---
id: 1578
title: Repair manifest loader for pilot knowledge corpus
status: backlog
priority: important
created: 2026-05-15T01:23:46.788046+00:00
updated: 2026-05-15T04:03:30.338706+00:00
tags:
  - scope:knowledge
  - type:build
  - pilot
  - loader
parent:
depends_on:
  - 1556
  - 1557
  - 1579
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
Context:
Knowledge module audit found that the manifest loader path is not ready even for a tiny pilot corpus. The checked-in default manifest points at paths that do not match the current repo layout, and `load_manifest_file(...)` registers source rows but calls `pipeline.ingest(...)` without forwarding the created `source_id`. The CLI pipeline is also constructed without a `KnowledgeSourceStore`, so loader-ingested documents can become orphaned from their source records.

Intent:
This is a deferred pilot-readiness task, not a full knowledge-base bootstrap. It should run only after the core source/document/vector/enrichment contracts are repaired.

Scope:
- In scope: make the manifest loader suitable for a small manually chosen pilot corpus; align manifest paths with current repo layout; ensure loader-created documents are linked to their source records and scopes; prove search/enrichment can trace pilot docs back to sources.
- Out of scope: full OwlBear corpus ingestion, automatic scheduled ingestion, authenticated/browser source lifecycle design, Cockpit visibility, and broad loader redesign beyond pilot readiness.

Functional acceptance note:
Acceptance is based on observed loader output and persisted state. Passing or failing tests alone is not functional proof.

Acceptance Criteria:
AC-1: Given a tiny pilot manifest with one `file_glob` source matching at least one current workspace file, running the loader creates one source row and ingests matching documents whose `documents.source_id` points to that source row and whose scope matches the manifest entry.
AC-2: Given the default `store/knowledge/general/sources.yaml`, the configured paths either match the current repo layout or are explicitly replaced by a documented pilot manifest; stale paths such as `docs/research/*.md`, `skills/*/SKILL.md`, and `instructions/*.md` must not be presented as working defaults for this repo.
AC-3: Given a loader-ingested pilot document, `search_knowledge` can return the document and include resolvable source metadata after the core ingest/vector fixes are present.
AC-4: Given the pilot source has `enrich=false`, `get_next_batch` does not return its chunks; given `enrich=true`, source-linked chunks are eligible only after #1557 provenance rules are satisfied.
AC-5: Proof must inspect the relevant persisted rows (`knowledge_sources`, `documents`, `chunks`) and demonstrate the source linkage, not only report loader counters.

Dependencies:
This task depends on the core source/document/vector cleanup work, manual enrichment provenance repair, and blocked-content persistence repair.
2026-05-15T01:58:03+00:00


Dependency update:
Blocked-content repair task #1577 was archived as deprecated after the user chose policy task #1579 to remove the ingestion safety guards. Pilot loader readiness now depends on #1579 instead of #1577.
2026-05-15T02:17:08+00:00


Audit refinement — loader vectors must persist in the MCP-visible backend:
The MCP server uses a persistent Qdrant location from `OWLBEAR_QDRANT_PATH` or `.owlbear/knowledge/vectors`, but the standalone loader CLI currently constructs `QdrantVectorStore()` with the default in-memory location. That can persist documents in SQLite while losing embeddings when the loader process exits.

Required follow-up before review:
- The pilot loader must write embeddings to the same configured vector backend that `search_knowledge` uses.
- Proof must run across the loader/search boundary or otherwise demonstrate that embeddings survive process exit and are visible to MCP query wiring.
- Mocked or in-memory-only vector proof is insufficient for pilot readiness.
2026-05-15T03:28:27+00:00


Audit refinement — pilot search proof must return matched evidence, not only document starts:
`search_knowledge` currently searches chunk embeddings but returns `doc.content[:500]` as the snippet. For long documents, the snippet may not include the matched chunk, making a correct hit look irrelevant.

Required follow-up before review:
- Pilot search proof should show that a loader-ingested document returns a snippet from the matched chunk or a nearby evidence window.
- The result must still include document/source/scope metadata.
- If the matched-snippet behavior is deferred, the pilot task must explicitly record that search is functionally present but evidence display remains incomplete.
2026-05-15T03:57:30+00:00


Audit refinement — URL-list manifest support is inconsistent and deferred for pilot:
`RefreshOrchestrator._handle_url_list(...)` expects `source.config["urls"]` to be a list, but the manifest loader schema currently accepts only string config values via `sy.MapPattern(sy.Str(), sy.Str())`. A manifest cannot naturally express a working multi-URL source even though `type: url_list` is accepted.

Required follow-up before review:
- Keep the pilot loader proof file-first unless the user explicitly expands scope to URL sources.
- Do not present manifest `url_list` support as complete until the schema/config format can represent the list shape refresh expects.
- If URL-list support is deferred, document that clearly in the pilot loader outcome.
2026-05-15T04:03:30+00:00


Audit refinement — pilot proof must not rely on global enrichment ratio:
`get_stats` currently computes `chunks_enriched_ratio` as enriched chunks divided by all chunks, regardless of source `enrich` eligibility. A pilot that uses `enrich=false` sources can make this ratio look incomplete even if every eligible chunk is handled.

Required follow-up before review:
- Pilot proof should inspect eligible chunks directly rather than relying only on `chunks_enriched_ratio`.
- If `get_stats` is used as pilot evidence, either make the metric eligibility-aware or explicitly document its limitation.
- Final source-health metric design can be handled by #1558.