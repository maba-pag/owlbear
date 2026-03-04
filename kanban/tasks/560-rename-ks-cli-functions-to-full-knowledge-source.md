---
id: 560
title: Rename ks_ CLI functions to full knowledge_source_ prefix
status: ideation
priority: someday
created: 2026-03-04T07:39:03.1672553+01:00
updated: 2026-03-04T07:39:03.1672553+01:00
tags:
    - audit
    - naming
    - scope:cli
class: standard
---

F-17: ks_add, ks_list, ks_show, ks_remove use abbreviated prefix. All other commands use full words (project_create, slack_auth). Inconsistent. AC: consistent naming or documented exception. See docs/code-quality-audit.md.
