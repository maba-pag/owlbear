---
id: 672
title: Extract GraphEnricher from IngestPipeline to enrichment.py
status: archived
priority: needed
created: 2026-03-08T03:00:14.1413242+01:00
updated: 2026-03-09T00:41:17.0187701+01:00
started: 2026-03-08T05:29:57.4935231+01:00
completed: 2026-03-09T00:41:17.0187701+01:00
tags:
    - modularity
    - knowledge
depends_on:
    - 671
class: standard
---

Move graph enrichment scheduling from IngestPipeline to a new GraphEnricher class in src/owlbear/memory/knowledge/enrichment.py. See docs/ingest-complexity-reduction-research.md.

AC:
1. GraphEnricher class exists in enrichment.py with methods: schedule_graph_enrichment, schedule_inter_doc_enrichment (public), _enrich_graph, _enrich_graph_inner, _enrich_inter_doc_graph (private).
2. GraphEnricher owns the _background_tasks set and _bg_semaphore.
3. GraphEnricher.__init__ takes: conn (sqlite3.Connection), graph_store (GraphStore), graph_builder (IntraDocGraphBuilder | None), inter_doc_builder (InterDocGraphBuilder | None), document_store (DocumentStore), pipeline_name (str), bg_concurrency (int).
4. IngestPipeline.__init__ accepts an optional enricher: GraphEnricher | None = None parameter.
5. IngestPipeline delegates all enrichment calls to self._enricher (no-op when None).
6. bootstrap.py constructs GraphEnricher only when graph_builder is available and passes it to IngestPipeline; passes None otherwise.
7. ingest.py is under 400 lines (currently 513; removing ~120 lines of enrichment + init wiring achieves ~393).
8. All existing tests pass. Enrichment-related test fixtures (test_knowledge_ingest.py BgConcurrency tests, provenance tests, inter-doc integration tests) must instantiate GraphEnricher directly -- this is more than an import update.
9. Ruff clean.
10. No circular imports. enrichment.py imports: graph.py (GraphStore), graph_builder.py (IntraDocGraphBuilder), inter_doc_graph_builder.py (InterDocGraphBuilder), document_store.py (DocumentStore for set_status + conn); models.py and extractor.py under TYPE_CHECKING only.

[[2026-03-08]] Sun 23:57
Wave 4, agent: auditor

[[2026-03-09]] Mon 00:40
## Audit
### Report
| AC Line | Evidence | Confidence |
|---------|----------|------------|
| AC1: GraphEnricher class + 5 methods | enrichment.py L26,71,88,119,129,169 | .97 |
| AC2: owns _background_tasks + _bg_semaphore | enrichment.py L66-67 | .97 |
| AC3: __init__ signature | enrichment.py L52-63 all 7 params match | .97 |
| AC4: IngestPipeline enricher param | ingest.py L91 enricher: GraphEnricher or None = None | .97 |
| AC5: delegates to self._enricher | ingest.py L280-282 None check + calls | .97 |
| AC6: bootstrap conditional | bootstrap/knowledge.py L144-155 gates on inter_doc_builder | .95 |
| AC7: ingest.py under 400 lines | 323 lines | .97 |
| AC8: all tests pass | 91/91 knowledge ingest; 1271/1272 full suite (1 pre-existing Slack) | .95 |
| AC9: ruff clean | All checks passed | .97 |
| AC10: no circular imports | runtime: asyncio+logging only; domain under TYPE_CHECKING | .97 |

Confidence: .96
