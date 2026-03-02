---
id: 387
title: File glob source type — resolve workspace-relative globs
status: archived
priority: important
created: 2026-03-01T20:15:37.6655077+01:00
updated: 2026-03-02T01:53:46.6062352+01:00
started: 2026-03-01T20:23:07.2854931+01:00
completed: 2026-03-02T01:53:46.6062352+01:00
tags:
    - phase-9
    - knowledge-graph
class: standard
---

From #254 source-registry-research.md. Implement file_glob source type in RefreshOrchestrator: resolve workspace-relative globs via pathlib.Path.glob(), ingest(path) per matched file. AC: file_glob source type resolves patterns like 'docs/**/*.md' and ingests all matching files; respects delta detection. Depends on #254, #384.
