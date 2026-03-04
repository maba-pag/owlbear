---
id: 507
title: Reuse httpx.AsyncClient in GitHubToolset
status: ideation
priority: important
created: 2026-03-04T07:38:19.232432+01:00
updated: 2026-03-04T07:38:19.232432+01:00
tags:
    - audit
    - performance
    - tools
class: standard
---

F-08: Each of create_pr, list_prs, list_issues, get_issue creates own httpx.AsyncClient. 4 separate TCP+TLS negotiations in sequence. Create client in __init__, reuse, add close() method. AC: single client instance, connection reuse. See docs/code-quality-audit.md.
