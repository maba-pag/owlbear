---
id: 575
title: Close minor test coverage gaps across modules
status: ideation
priority: someday
created: 2026-03-04T07:39:17.2171749+01:00
updated: 2026-03-04T07:39:17.2171749+01:00
tags:
    - audit
    - test
class: standard
---

Coverage gaps identified: bootstrap exception paths (19 lines), browser/config validators (4 lines), ask_user exhausted-retries (3 lines), github_api get_issue error (4 lines), filesystem _search_files truncation (3 lines), usage.py summary(None) (2 lines). Individually minor. AC: coverage >99% on these modules. See docs/test-quality-audit.md.
