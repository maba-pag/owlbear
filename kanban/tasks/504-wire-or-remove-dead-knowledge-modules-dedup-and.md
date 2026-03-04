---
id: 504
title: Wire or remove dead knowledge modules dedup and reranker
status: ideation
priority: important
created: 2026-03-04T07:38:16.8793979+01:00
updated: 2026-03-04T07:38:16.8793979+01:00
tags:
    - audit
    - yagni
    - knowledge
class: standard
---

INT-14: knowledge/dedup.py and knowledge/reranker.py are never imported anywhere except their own test files. Wire into ingest/retrieval pipeline or delete. Dead code with tests is still dead code. AC: modules used in production or removed. See docs/integration-audit.md.
