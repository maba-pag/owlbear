---
id: 1271
title: 'P1-05: Implement file engine with MtimeScanCache'
status: todo
priority: needed
created: 2026-05-02T03:43:35.312728+00:00
updated: 2026-05-02T03:45:18.119048+00:00
tags:
- phase-1
- scope:mcp-memory
parent: 1266
depends_on:
- 1270
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

## Objective

Implement the file-based MemoryEngine: directory scanning, YAML frontmatter parsing, atomic writes, slug generation, and MtimeScanCache. Must pass all tests from #1270.

Brief: see parent #1266

## Scope

**In scope:**
- New file: `serve/mcp-memory/src/owlbear_mcp_memory/engine.py`
- `MemoryEngine` class with configurable `memory_dir` path (default: `.owlbear/memory/`)
- `load_all()` → list[MemoryEntry] — scan directory, parse all valid .md files
- `write_entry(entry: MemoryEntry)` → Path — serialize to frontmatter+body, atomic write (mkstemp → fsync → rename)
- `read_entry(path: Path)` → MemoryEntry | None — parse single file
- Slug generation: `slugify(title)` → kebab-case truncated + 6-char random alphanumeric suffix
- `MtimeScanCache`: store dir mtime, skip `load_all` re-parse when unchanged
- Create `.owlbear/memory/` on first write if missing
- YAML: `yaml.safe_load` / `yaml.safe_dump` only
- Add `pyyaml` to `pyproject.toml` dependencies if not already present
- Skip malformed files with logged warning (don't crash on bad YAML)

**Out of scope:**
- MCP tool definitions (handled by #1273)
- Access control logic (handled by #1273)
- State transition enforcement (handled by #1273)

## Acceptance Criteria

- [ ] All tests from #1270 pass GREEN
- [ ] Engine reads `.md` files with YAML frontmatter + markdown body
- [ ] Atomic writes use mkstemp → fsync → rename pattern
- [ ] Slug is deterministic for same title (excluding random suffix)
- [ ] MtimeScanCache avoids re-parse when directory mtime unchanged
- [ ] Malformed files logged and skipped without raising
- [ ] Directory auto-created on first write