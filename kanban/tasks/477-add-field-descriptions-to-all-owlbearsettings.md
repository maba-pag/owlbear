---
id: 477
title: Add Field descriptions to all OwlBearSettings config fields
status: ideation
priority: needed
created: 2026-03-04T07:37:55.648052+01:00
updated: 2026-03-04T07:37:55.648052+01:00
tags:
    - audit
    - docs
    - config
class: standard
---

DOC-F-02: 30+ config fields have no Field(description=...) and no inline comments. Users cant discover valid values, units, or implications. Examples: embedding_idle_timeout (units?), temporal_decay_rate (range?), approval_policy (schema?). AC: every field has description with units/ranges/behavior. See docs/documentation-audit.md.
