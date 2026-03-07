---
id: 569
title: Consolidate trafilatura across extras groups
status: backlog
priority: someday
created: 2026-03-04T07:39:11.5014884+01:00
updated: 2026-03-07T04:34:58.0499359+01:00
started: 2026-03-07T04:34:58.0499359+01:00
tags:
    - audit
    - config
    - deps
class: standard
---

F-08: trafilatura>=2.0.0 in both crawl and search extras. bookmark_pipeline also needs it but doesnt declare. Consider shared web extra or document which extra provides it. AC: clear guidance on extra dependencies. See docs/config-dependency-audit.md.

Research complete -- see docs/consolidate-trafilatura-extras-research.md. Finding: duplication is intentional (1 line, follows httpx/pydantic idiom). After #537 (centralize trafilatura calls), bookmark_pipeline will no longer import trafilatura directly. No structural changes to extras needed. One follow-up task: add clarifying comments to pyproject.toml and update import guard message.
