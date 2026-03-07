---
id: 507
title: Reuse httpx.AsyncClient in GitHubToolset
status: backlog
priority: important
created: 2026-03-04T07:38:19.232432+01:00
updated: 2026-03-06T23:49:06.4553242+01:00
started: 2026-03-06T23:40:08.9526803+01:00
tags:
    - audit
    - performance
    - tools
class: standard
---

F-08: Each of create_pr, list_prs, list_issues, get_issue creates own httpx.AsyncClient. 4 separate TCP+TLS negotiations in sequence. Create client in __init__, reuse, add close() method. AC: single client instance, connection reuse.

Research complete  see docs/httpx-client-reuse-research.md. Recommendation (.90): eager client in __init__ + aclose() + bootstrap cleanup registration. ~18 LOC change.
