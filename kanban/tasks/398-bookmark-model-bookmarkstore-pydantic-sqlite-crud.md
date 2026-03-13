---
id: 398
title: Bookmark model + BookmarkStore (Pydantic + SQLite CRUD)
status: archived
priority: needed
created: 2026-03-01T20:17:23.7804382+01:00
updated: 2026-03-03T13:42:39.5612417+01:00
started: 2026-03-01T20:23:24.0751337+01:00
completed: 2026-03-03T13:42:39.5612417+01:00
tags:
    - phase-13
    - knowledge-graph
    - model
class: standard
---

From #304 source-discovery-bookmarking.md. Pydantic Bookmark model (id, url, title, description, tags, relevance_score, reason, scope, document_id, content_hash, created_at, updated_at). BookmarkStore with SQLite CRUD: create, get_by_url, list, update_tags, delete. Schema v5 migration for bookmarks table with indexes on url+scope and scope. AC: Bookmark model validates; store CRUD works; dedup by URL+scope; schema migration idempotent. Depends on #304.
