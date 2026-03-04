---
id: 550
title: Trim knowledge __init__.py to 15 or fewer exports
status: ideation
priority: nice-to-have
created: 2026-03-04T07:38:53.2483718+01:00
updated: 2026-03-04T07:38:53.2483718+01:00
tags:
    - audit
    - architecture
    - knowledge
class: standard
---

INT-11: knowledge/__init__.py exports 35+ symbols including init_db, compute_content_hash, IngestPipeline. Too many internals exposed. Target <=15 public re-exports. AC: clean public API surface. See docs/integration-audit.md.
