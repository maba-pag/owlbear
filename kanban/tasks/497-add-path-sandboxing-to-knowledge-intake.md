---
id: 497
title: Add path sandboxing to knowledge intake
status: backlog
priority: important
created: 2026-03-04T07:38:11.4324226+01:00
updated: 2026-03-06T23:39:30.40319+01:00
started: 2026-03-06T23:31:39.0730282+01:00
tags:
    - audit
    - security
    - knowledge
class: standard
---

SEC-11: intake.py read_file() reads any path without sandboxing. LLM-directed ingestion of /etc/passwd or ~/.ssh/id_rsa would ingest content into knowledge base. Add workspace-root validation. AC: PermissionError for paths outside workspace. See docs/security-audit.md.
