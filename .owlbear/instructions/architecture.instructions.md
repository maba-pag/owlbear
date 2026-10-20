---
description: "Architecture standards for serve/ packages — topology, dependency rules, and domain boundaries"
applyTo: "serve/**"
---

## Architecture Overview

OwlBear v2 has no custom Python agent runtime. Agents are `.agent.md` files executed by VS Code and GitHub Copilot. Tools are provided by MCP servers (`serve/*-mcp/`) or VS Code built-in tools.

```text
agents/*.agent.md             (agent definitions — pure markdown, no Python)
    use tools from the MCP servers below

serve/delivery-next/           (Delivery engine: Change loop, MCP tools, GitHub publication, pages)
serve/cockpit/                 (HTTP application: read-oriented operator UI)
    import from memory
serve/tools/                   (repository tools: quality, testing, and indexing)

serve/memory-mcp/              (MCP server: persistent agent memory)
    import from
serve/memory/                   (core library: memory state and storage)

serve/knowledge-mcp/            (MCP server: knowledge base operations)
    import from
serve/knowledge/                (core library: graph, vector, ingest, query)

serve/browser-mcp/              (MCP server: authenticated content acquisition)
    import from
serve/browser/                   (core library: browser acquisition)

serve/web-content/               (core library: shared HTML extraction and Markdown normalization)
```

Each MCP server is a standalone MCPServer application. Core libraries, the Delivery engine,
Cockpit, and repository tools are separate packages. Cross-package imports are enforced by
`tests/test_package_boundary.py`, which scans runtime and `TYPE_CHECKING` imports.

## Dependency Rules

Cross-namespace imports are enforced by `tests/test_package_boundary.py`. The `ALLOWED_IMPORTS`
constant in that file maps each package namespace to its permitted owlbear-namespace imports.

**Rules:**

- When adding a new package, update `ALLOWED_IMPORTS` — the manifest guard will fail otherwise.
- Core libraries do not import applications, MCP servers, or repository tools.
- Cockpit may import Memory for its read API.
- Delivery Next (`serve/delivery-next/`) may import Memory for its Memory tab, and nothing else.
- Each MCP server may import its corresponding core package, but MCP servers must not import other
  MCP servers.
- Repository tools import no other OwlBear package, and product packages must not import repository tools.
- Relative imports remain within the owning package; the boundary test reports only external
  `owlbear_*` namespaces.
- Browser and Knowledge may import the shared web-content core; web-content imports neither.

## Domain Scope Map

Each task targets exactly one domain. Multi-domain work must be split into separate tasks.

| Domain | Scope |
| --- | --- |
| delivery | `serve/delivery-next/` (Delivery engine: Change loop, MCP tools, GitHub publication, pages) |
| cockpit | `serve/cockpit/` (FastAPI read API and Cockpit frontend) |
| knowledge | `serve/knowledge/` (graph, vector, ingest, query, embeddings) |
| knowledge-mcp | `serve/knowledge-mcp/` |
| memory | `serve/memory/` (memory state, scoring, and storage) |
| memory-mcp | `serve/memory-mcp/` |
| browser | `serve/browser/` |
| browser-mcp | `serve/browser-mcp/` |
| web-content | `serve/web-content/` (shared HTML extraction and Markdown normalization) |
| tools | `serve/tools/` (repository utilities, quality, and indexing commands) |
| agent-config | `share/agents/`, `share/skills/`, `share/instructions/`, `.github/copilot-instructions.md` |
| test-infra | shared conftest, fixtures, factories (not individual test files) |
| docs | `docs/`, `README.md`, `SECURITY.md` |

**Edge case:** Adding a `config.py` field as part of a core feature is NOT a domain violation — domain = primary concern.
