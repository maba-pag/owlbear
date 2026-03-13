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

F-08: trafilatura>=2.0.0 in both crawl and search extras. bookmark_pipeline also needs it but doesnt declare. Consider shared web extra or document which extra provides it. See docs/config-dependency-audit.md.

Research complete -- see docs/research/consolidate-trafilatura-extras.md. Finding: duplication is intentional (1 line, follows httpx/pydantic idiom). After #537 (centralize trafilatura calls), bookmark_pipeline will no longer import trafilatura directly. No structural changes to extras needed. One follow-up task: add clarifying comments to pyproject.toml and update import guard message.

## AC

- [x] Research doc at docs/research/consolidate-trafilatura-extras.md
- [x] Finding: duplication intentional, no structural changes needed
- [x] Follow-up task created (clarifying comments + import guard)
