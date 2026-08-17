---
description: "Architecture standards for serve/ packages — topology, dependency rules, and domain boundaries"
applyTo: "serve/**"
---

## Architecture Overview

OwlBear v2 has no custom Python agent runtime. Agents are `.agent.md` files executed by VS Code and GitHub Copilot. Tools are provided by MCP servers (`serve/*-mcp/`) or VS Code built-in tools.

```text
agents/*.agent.md             (agent definitions — pure markdown, no Python)
    use tools from
serve/delivery-mcp/           (MCP server: Delivery operations)
    import from
serve/delivery-github/        (provider adapter: GitHub publication)
    import from
serve/delivery/                (core library: Change lifecycle and target Delivery)

serve/cockpit/                 (HTTP application: read-oriented operator UI)
    import from delivery, delivery-github, memory
serve/tools/                   (repository tools and migration utilities)
    import from delivery

serve/memory-mcp/              (MCP server: persistent agent memory)
    import from
serve/memory/                   (core library: memory state and storage)

serve/knowledge-mcp/            (MCP server: knowledge base operations)
    import from
serve/knowledge/                (core library: graph, vector, ingest, query)

serve/browser-mcp/              (MCP server: authenticated content acquisition)
    import from
serve/browser/                   (core library: browser acquisition)
```

Each MCP server is a standalone MCPServer application. Core libraries, the Delivery provider
adapter, Cockpit, and repository tools are separate packages. Cross-package imports are enforced by
`tests/test_package_boundary.py`, which scans runtime and `TYPE_CHECKING` imports.

## Dependency Rules

Cross-namespace imports are enforced by `tests/test_package_boundary.py`. The `ALLOWED_IMPORTS`
constant in that file maps each package namespace to its permitted owlbear-namespace imports.

**Rules:**

- When adding a new package, update `ALLOWED_IMPORTS` — the manifest guard will fail otherwise.
- Core libraries do not import applications, MCP servers, provider adapters, or repository tools.
- The Delivery GitHub provider adapter may import only the Delivery core.
- Cockpit may import Delivery, the Delivery GitHub provider adapter, and Memory for its read API.
- Each MCP server may import its corresponding core package and any provider adapter required by
  its public operations, but MCP servers must not import other MCP servers.
- Repository tools may import Delivery, but product packages must not import repository tools.
- Relative imports remain within the owning package; the boundary test reports only external
  `owlbear_*` namespaces.

## Domain Scope Map

Each task targets exactly one domain. Multi-domain work must be split into separate tasks.

| Domain | Scope |
| --- | --- |
| delivery | `serve/delivery/` (Change lifecycle, target contract, workspaces, publication state) |
| delivery-github | `serve/delivery-github/` (fixed-operation GitHub publication provider) |
| delivery-mcp | `serve/delivery-mcp/` (Delivery MCP tools and target-facing server) |
| cockpit | `serve/cockpit/` (FastAPI read API and Cockpit frontend) |
| knowledge | `serve/knowledge/` (graph, vector, ingest, query, embeddings) |
| knowledge-mcp | `serve/knowledge-mcp/` |
| memory | `serve/memory/` (memory state, scoring, and storage) |
| memory-mcp | `serve/memory-mcp/` |
| browser | `serve/browser/` |
| browser-mcp | `serve/browser-mcp/` |
| tools | `serve/tools/` (repository utilities, migration, quality, and indexing commands) |
| agent-config | `share/agents/`, `share/skills/`, `share/instructions/`, `.github/copilot-instructions.md` |
| test-infra | shared conftest, fixtures, factories (not individual test files) |
| docs | `docs/`, `README.md`, `SECURITY.md` |

**Edge case:** Adding a `config.py` field as part of a core feature is NOT a domain violation — domain = primary concern.
