---
id: 485
title: Wire or remove MemoryConsolidator
status: ideation
priority: important
created: 2026-03-04T07:38:01.9660025+01:00
updated: 2026-03-04T07:38:01.9660025+01:00
tags:
    - audit
    - yagni
    - scope:core
class: standard
---

YAGNI-04/INT-03: MemoryConsolidator has model='test' default (scaffolding artifact). Never imported or wired in bootstrap/daemon. Tests exist but feature unreachable in production. Wire into session lifecycle or remove. AC: no dead production code. See docs/software-design-audit.md, docs/integration-audit.md.
