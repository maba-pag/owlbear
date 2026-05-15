---
id: 1576
title: Classify inactive knowledge surfaces
status: research
priority: important
created: 2026-05-14T18:47:54.230692+00:00
updated: 2026-05-15T04:22:41.949182+00:00
tags:
  - scope:knowledge
  - type:cleanup
  - maintainability
parent:
depends_on:
  - 1556
  - 1557
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
Context:
Knowledge module audit found that the active MCP surface is intentionally narrow, but the codebase still contains several older or inactive knowledge paths: bookmark workflows, legacy consolidation, scope transfer implementation/stubs, duplicate inter-doc builder concepts, inactive plain functions that used to be tools, Copilot token utilities, and docs/handbook text that may describe outdated result shapes or operational defaults.

This is not a runtime blocker. It should run after the core source identity and manual enrichment persistence repairs so cleanup does not destabilize activation work.

Objective:
Classify inactive knowledge code and docs as keep, expose, retire, or document-as-stub, then make the smallest cleanup/doc changes needed to reduce future confusion.

Acceptance Criteria:
- [ ] Inventory inactive or deferred knowledge surfaces and classify each as keep, expose, retire, or document-as-stub.
- [ ] Preserve intentionally deferred scope stubs unless a new decision supersedes them.
- [ ] Remove or clearly label dead legacy paths that are not part of the active architecture.
- [ ] Update user-facing knowledge docs/handbooks where they describe outdated tool outputs, defaults, or workflows.
- [ ] Do not change the intentional manual VS Code-agent enrichment model.

Out of scope:
- Source identity repair (#1556).
- Manual enrichment graph persistence repair (#1557).
- New source lifecycle design (#1558).
- Full KB ingestion.
2026-05-15T03:51:01+00:00


Audit refinement — inactive surfaces must be checked before re-exposure:
Several plain async functions remain in `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py` but are not active MCP tools. Some of them still use `asyncio.to_thread(...)` around SQLite-backed stores or connection work (`list_entities`, bookmark helpers, scope sync/import/export paths). They should not be re-exposed as tools until thread ownership and return contracts are reviewed.

Required follow-up before cleanup completion:
- For each inactive function, classify whether it is intentionally internal, a candidate active tool, or dead legacy code.
- If a function is kept as a future tool, check for SQLite same-thread usage, stale return shapes, and docs/handbook alignment before exposure.
- Prefer deleting or clearly marking legacy paths over leaving callable-looking functions that are absent from the active MCP surface.
2026-05-15T04:19:38+00:00


Audit refinement — scope transfer is lossy and should be retire-by-default:
`scope_transfer.py` copies only `documents`, `document_status`, `chunks`, `entities`, and `edges`, and its import helpers omit current schema fields such as `documents.source_id`, `entities.importance`, `edges.document_id`, chunk enrichment/consolidation fields, and status `error`. It also omits source/bookmark/source-page/consolidation tables entirely. Export opens an existing SQLite output path without clearing it first, so stale rows or duplicate primary keys can produce mixed or failed snapshots.

Required follow-up before cleanup completion:
- Classify scope transfer/import-export as retire-by-default unless a current portability contract is explicitly approved.
- If retained, redesign it against the current schema, including source identity, enrichment state, reviewed pairs, and vector re-embedding/import semantics.
- Do not re-expose inactive MCP scope transfer tools until this classification is complete.
2026-05-15T04:22:41+00:00


Audit refinement — bookmark and legacy consolidation surfaces are retire-or-redesign:
Bookmark code remains present but inactive; `bookmarks.content_hash` exists in schema/model while the current bookmark pipeline/store do not populate or use it, leaving dedup URL-only. Legacy consolidation is also inactive, but MCP lifespan wires `ConsolidationService(conn, make_text_completion_fn())` with a completion function that returns an empty string; if `consolidate_knowledge` were re-exposed as-is, it could mark chunks consolidated while storing empty insights.

Required follow-up before cleanup completion:
- Classify bookmark tools as retire, redesign, or explicitly inactive; do not re-expose without a current dedup/content identity contract.
- Classify legacy consolidation as retire or redesign; do not re-expose with the current no-op completion wiring.
- User-facing docs/handbooks should not imply these inactive paths are operational MCP tools.