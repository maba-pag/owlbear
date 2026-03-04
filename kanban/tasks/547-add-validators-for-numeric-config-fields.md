---
id: 547
title: Add validators for numeric config fields
status: ideation
priority: nice-to-have
created: 2026-03-04T07:38:50.6863315+01:00
updated: 2026-03-04T07:38:50.6863315+01:00
tags:
    - audit
    - config
class: standard
---

F-14: temporal_decay_rate, temporal_recency_weight, embedding_idle_timeout, approval_timeout have no validators. Negative or zero values cause subtle bugs. Add @field_validator for non-negative constraints. AC: invalid values rejected at config load. See docs/config-dependency-audit.md.
