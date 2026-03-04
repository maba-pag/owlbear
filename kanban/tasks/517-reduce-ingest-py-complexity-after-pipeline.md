---
id: 517
title: Reduce ingest.py complexity after pipeline refactor
status: ideation
priority: important
created: 2026-03-04T07:38:27.4728203+01:00
updated: 2026-03-04T07:38:27.4728203+01:00
tags:
    - audit
    - modularity
    - knowledge
class: standard
---

MOD-02: ingest.py is 849 lines. IngestPipeline handles intake, hashing, chunking, doc CRUD, embedding, extraction, graph enrichment, inter-doc, status tracking. After DRY-10 fix, extract intake to its own module (partially exists). Reduce IngestPipeline to orchestration only. AC: ingest.py <500 lines. See docs/software-design-audit.md.
