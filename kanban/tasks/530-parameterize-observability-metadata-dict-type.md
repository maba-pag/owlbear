---
id: 530
title: Parameterize observability metadata dict type
status: ideation
priority: nice-to-have
created: 2026-03-04T07:38:36.1891917+01:00
updated: 2026-03-04T07:38:36.1891917+01:00
tags:
    - audit
    - code-quality
    - scope:core
class: standard
---

F-13: observability.py metadata: dict = {} uses bare dict instead of dict[str, Any]. Prevents Pylance from catching type misuse. AC: metadata typed as dict[str, Any]. See docs/code-quality-audit.md.
