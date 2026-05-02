---
id: 1270
title: 'P1-04: Test — File engine read/write/parse and MtimeScanCache'
status: todo
priority: needed
created: 2026-05-02T03:43:31.733852+00:00
updated: 2026-05-02T03:45:18.115612+00:00
tags:
- phase-1
- scope:mcp-memory
- tests
parent: 1266
depends_on:
- 1269
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

## Objective

Write failing tests that define the file engine contract: reading .md files with YAML frontmatter, writing with atomic ops, slug generation, directory scanning, and MtimeScanCache behavior.

Brief: see parent #1266

## Scope

**In scope:**
- Test file: `tests/test_memory_engine.py` (workspace root tests/)
- Parse `.md` file with YAML frontmatter into MemoryEntry
- Serialize MemoryEntry back to frontmatter+body .md format
- Slug generation from title (kebab-case, truncated, 6-char suffix)
- Load all entries from a temp directory
- Atomic write (file appears fully-formed or not at all)
- MtimeScanCache: skip re-parse when dir mtime unchanged
- MtimeScanCache: re-parse when dir mtime changes (file added/removed/modified)
- Handle empty directory (no entries)
- Handle malformed files gracefully (skip with warning, don't crash)

**Out of scope:**
- MCP tool behavior (tested in #1272)
- Access control / mutation rules (tested in #1272)
- Model validation itself (tested in #1268)

## Acceptance Criteria

- [ ] Tests import MemoryEngine from `owlbear_mcp_memory.engine`
- [ ] Tests FAIL (RED) — engine module does not yet exist
- [ ] Round-trip test: write entry → read entry → fields match
- [ ] Slug test: title "Ruff Import Sorting Pitfall" → slug starts with "ruff-import-sorting-pitfall-" + 6 alphanum
- [ ] Cache hit test: two consecutive loads without file change → second skips parse
- [ ] Cache miss test: add file between loads → second re-parses
- [ ] Malformed file test: invalid YAML → entry skipped, no exception raised
- [ ] Empty dir test: returns empty list