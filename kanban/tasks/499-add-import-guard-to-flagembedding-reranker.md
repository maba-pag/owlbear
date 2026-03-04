---
id: 499
title: Add import guard to FlagEmbedding reranker
status: ideation
priority: important
created: 2026-03-04T07:38:12.8421182+01:00
updated: 2026-03-04T07:38:12.8421182+01:00
tags:
    - audit
    - config
    - knowledge
class: standard
---

F-06: reranker.py does bare FlagEmbedding import without try/except. If knowledge extra not installed, raises raw ModuleNotFoundError instead of actionable message. Follow embeddings.py pattern. AC: ImportError handled with install instructions. See docs/config-dependency-audit.md.
