---
id: 517
title: Reduce ingest.py complexity after pipeline refactor
status: backlog
priority: important
created: 2026-03-04T07:38:27.4728203+01:00
updated: 2026-03-07T00:05:24.4194363+01:00
started: 2026-03-06T23:58:22.1903475+01:00
tags:
    - audit
    - modularity
    - knowledge
class: standard
---

MOD-02: ingest.py is 799 lines. IngestPipeline handles intake, hashing, chunking, doc CRUD, embedding, extraction, graph enrichment, inter-doc, status tracking. AC: ingest.py <500 lines. See docs/software-design-audit.md.

## Research Findings

See docs/ingest-complexity-reduction-research.md for full analysis.

**Recommendation (.85 confidence):** Extract 2 new modules:
1. **document_store.py** (~280 lines) - DocumentStore class with all document CRUD, status tracking, and storage writes
2. **enrichment.py** (~150 lines) - GraphEnricher class with background graph enrichment scheduling
3. **ingest.py** shrinks to ~350 lines - pure orchestration only

**Sources:** LlamaIndex IngestionPipeline (separate docstore), Haystack Pipelines (component-based), Python Composition over Inheritance pattern. Zero circular deps confirmed.

## Research Checklist
- [x] Theoretical validity - SRP extraction is textbook decomposition
- [x] Prior art - LlamaIndex + Haystack confirm orchestrator-only pipelines
- [x] Technical feasibility - Zero circular imports; all extracted modules depend on leaf modules only
- [x] Architecture fit - Follows existing intake.py precedent; complements #566, enables #516
- [x] Implementation approach - Composition; IngestPipeline takes DocumentStore + GraphEnricher in __init__
