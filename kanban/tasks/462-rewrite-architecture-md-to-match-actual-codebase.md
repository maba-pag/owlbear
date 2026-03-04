---
id: 462
title: Rewrite architecture.md to match actual codebase
status: ideation
priority: critical
created: 2026-03-04T07:37:43.1678897+01:00
updated: 2026-03-04T07:37:43.1678897+01:00
tags:
    - audit
    - docs
    - architecture
class: standard
---

DOC-F-01: architecture.md (v0.2) is severely outdated. Wrong agent names (lists 5, reality 7), missing 4 entire subpackages (planning, projects, safety, bootstrap), knowledge file count wrong (says 14, reality 22), assembly gap section stale (bootstrap.py now exists). AC: sections 3,4.3,4.4,6,7 rewritten, all packages/modules/agents listed correctly. See docs/documentation-audit.md.
