---
id: 530
title: Parameterize observability metadata dict type
status: backlog
priority: nice-to-have
created: 2026-03-04T07:38:36.1891917+01:00
updated: 2026-03-07T00:27:15.6625355+01:00
started: 2026-03-07T00:26:11.1497454+01:00
tags:
    - audit
    - code-quality
    - scope:core
class: standard
---

F-13: observability.py metadata: dict = {} uses bare dict instead of dict[str, Any]. Prevents Pylance from catching type misuse. AC: metadata typed as dict[str, Any]. See docs/code-quality-audit.md.

Research: N/A - trivial type annotation, one-line change.
- L55 in src/owlbear/core/observability.py: change `metadata: dict = {}` to `metadata: dict[str, Any] = {}`
- Add `Any` to the `from typing import TYPE_CHECKING` import (becomes `from typing import Any, TYPE_CHECKING`)
