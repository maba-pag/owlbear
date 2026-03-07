---
id: 566
title: Consider sub-packages for knowledge/ directory (22 files)
status: backlog
priority: someday
created: 2026-03-04T07:39:08.9251319+01:00
updated: 2026-03-07T04:28:06.9048401+01:00
started: 2026-03-07T04:28:06.9048401+01:00
tags:
    - audit
    - modularity
    - knowledge
class: standard
---

MOD-04: Decision documented in docs/knowledge-subpackages-research.md. **Decision: Keep flat (.80 confidence).** 22 files is below the split threshold. No circular imports, no navigation pain, PEP 20 flat-is-better. Revisit if package exceeds 30 files. AC: decision documented.
