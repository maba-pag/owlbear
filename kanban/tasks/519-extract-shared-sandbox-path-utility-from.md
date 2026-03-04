---
id: 519
title: Extract shared sandbox_path utility from duplicated _safe_path
status: ideation
priority: nice-to-have
created: 2026-03-04T07:38:28.7733322+01:00
updated: 2026-03-04T07:38:28.7733322+01:00
tags:
    - audit
    - dry
    - refactor
    - tools
class: standard
---

ARC-11/DRY-03: Identical _safe_path logic in FileToolset and KnowledgeToolset. Same null-byte check, same resolve+boundary check, same error message. Extract to owlbear.tools._path_utils.sandbox_path(). AC: single implementation, both toolsets use it. See docs/architecture-audit.md, docs/software-design-audit.md.
