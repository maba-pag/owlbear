# Store

`store/` holds a reference-only knowledge corpus manifest and placeholder directories. It is not
runtime package code, agent memory, or the active Knowledge source registry.

## What lives here

- `knowledge/general/sources.yaml` records historical file-glob source definitions for the knowledge
  corpus, including research, shared skills, and shared instructions. Current Knowledge packages
  do not load this file.
- `knowledge/.gitkeep` preserves the tracked source root; `knowledge/general/.gitkeep` is a
  leftover placeholder beside the reference manifest.

The active source registry is managed through the `owlbear-knowledge` MCP tools and persisted in
`.owlbear/knowledge/local.db`. The files named by the reference manifest remain the source of
truth for their own content; do not use this directory as a substitute for registered sources.

## What belongs elsewhere

| Concern | Canonical location |
| --- | --- |
| Knowledge runtime state and registered sources | `.owlbear/knowledge/` |
| Durable agent memory entries | `.owlbear/memory/` |
| Delivery authority and change state | `.owlbear/delivery/` |
| Knowledge implementation and MCP tools | `serve/knowledge/` and `serve/knowledge-mcp/` |
| Cross-package regression tests | `tests/` |
| Portable consumer templates | `seed/` |

`store/` is not included by `.github/sync-manifest.json`, so it is not copied to the rolling
consumer `main` branch. Database files and other runtime artifacts are ignored by the repository
rules; do not add them here as a substitute for the managed runtime stores.
