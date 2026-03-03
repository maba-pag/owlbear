---
id: 401
title: BookmarkToolset — bookmark_source + list_bookmarks agent tools
status: in-progress
priority: important
created: 2026-03-01T20:17:51.3799582+01:00
updated: 2026-03-03T12:28:40.8894303+01:00
started: 2026-03-01T20:23:45.5568854+01:00
tags:
    - phase-13
    - knowledge-graph
    - agent
    - tooling
class: standard
---

From #304 source-discovery-bookmarking-research.md. FunctionToolset with bookmark_source(url, reason) and list_bookmarks(tag?, min_score?) agent tools. Follow FunctionToolset pattern. Wire in bootstrap.py. AC: Agent can call bookmark_source to evaluate+save a URL; list_bookmarks filters by tag and min_score; wired in bootstrap. Depends on #304, #400.
