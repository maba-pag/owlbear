---
id: 566
title: Consider sub-packages for knowledge/ directory (22 files)
status: ideation
priority: someday
created: 2026-03-04T07:39:08.9251319+01:00
updated: 2026-03-04T07:39:08.9251319+01:00
tags:
    - audit
    - modularity
    - knowledge
class: standard
---

MOD-04: knowledge/ flat namespace mixes schema, storage, pipeline, retrieval, toolsets. 22 .py files. Consider knowledge/storage/, knowledge/pipeline/, knowledge/retrieval/. Low priority -- current layout works. AC: decision documented. See docs/software-design-audit.md.
