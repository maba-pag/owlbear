---
id: 568
title: Tighten genai-prices version specifier
status: backlog
priority: someday
created: 2026-03-04T07:39:10.6285864+01:00
updated: 2026-03-07T04:53:03.4906214+01:00
started: 2026-03-07T04:53:03.4906214+01:00
tags:
    - audit
    - config
    - deps
class: standard
---

F-01: genai-prices >=0.0.1 accepts every version ever published. Pre-1.0, breaking change in 0.1->0.2 silently enters. See docs/config-dependency-audit.md.

## AC

- [ ] genai-prices version specifier tightened (e.g. >=0.0.1,<1.0)
- [ ] uv lock resolves successfully
