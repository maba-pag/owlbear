---
id: 511
title: Validate IMPORTANCE_BY_TYPE keys match EntityType enum
status: ideation
priority: important
created: 2026-03-04T07:38:23.1624031+01:00
updated: 2026-03-04T07:38:23.1624031+01:00
tags:
    - audit
    - bugfix
    - knowledge
class: standard
---

F-21: IMPORTANCE_BY_TYPE dict keys (decision, pattern, concept, class_, function, file) may not match EntityType enum values. Mismatched keys silently return default 0.5. Import EntityType and use enum members as keys, or add validation test. AC: all EntityType members have entries, test validates. See docs/code-quality-audit.md.
