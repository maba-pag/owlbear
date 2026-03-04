---
id: 486
title: Fix or remove dead ks_refresh CLI command
status: ideation
priority: important
created: 2026-03-04T07:38:02.9004356+01:00
updated: 2026-03-04T07:38:02.9004356+01:00
tags:
    - audit
    - yagni
    - scope:cli
class: standard
---

YAGNI-05/F-11/INT-13: _make_refresh_orchestrator() always raises NotImplementedError. ks_refresh is dead at runtime. Either implement the factory or remove the command. Testing seams belong in test fixtures, not production. AC: command works or is removed. See docs/software-design-audit.md, docs/code-quality-audit.md, docs/integration-audit.md.
