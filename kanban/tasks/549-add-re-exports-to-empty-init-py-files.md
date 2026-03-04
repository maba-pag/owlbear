---
id: 549
title: Add re-exports to empty __init__.py files
status: ideation
priority: nice-to-have
created: 2026-03-04T07:38:52.389879+01:00
updated: 2026-03-04T07:38:52.389879+01:00
tags:
    - audit
    - architecture
    - scope:core
class: standard
---

INT-10: auth, planning, projects, providers, safety, tools, tools/browser have empty __init__.py. No public API surface defined. Add re-exports for key public types. AC: public API discoverable via package imports. See docs/integration-audit.md.
