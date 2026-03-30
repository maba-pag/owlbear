---
id: 161
title: Knowledge package README and installability verification
status: ideation
priority: needed
created: 2026-03-29T19:37:41.2084335+02:00
updated: 2026-03-29T19:37:41.2084335+02:00
tags:
    - phase-1
    - scope:knowledge
    - type:docs
depends_on:
    - 160
class: standard
---

## Objective
Create README.md for packages/knowledge/ and verify package installability and cross-module imports.

## Acceptance Criteria
- [ ] README.md exists in packages/knowledge/ with: package purpose, module overview, Qdrant setup (memory/file/remote), BGE-M3 model download instructions (~2.3 GB cache), optional deps install command, quick usage example
- [ ] uv pip install -e packages/knowledge/ succeeds cleanly
- [ ] All cross-module imports verified (import each public module, run basic smoke test)
- [ ] __init__.py re-exports include retrieval and query_service public types

## Context
Split from #34 per docs/research/knowledge-package-integration-hybrid-search.md. Final verification task for knowledge package completeness.
