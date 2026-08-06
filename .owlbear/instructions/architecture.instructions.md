---
description: "Architecture standards for serve/ packages — topology, dependency rules, and domain boundaries"
applyTo: "serve/**"
---

## Architecture Overview

OwlBear v2 has no custom Python agent runtime. Agents are `.agent.md` files executed by VS Code and GitHub Copilot. Tools are provided by MCP servers (`serve/*-mcp/`) or VS Code built-in tools.

```
agents/*.agent.md            (agent definitions — pure markdown, no Python)
    use tools from
serve/delivery-mcp/          (MCP server: Delivery operations)
serve/knowledge-mcp/         (MCP server: knowledge base operations)
serve/memory-mcp/            (MCP server: persistent agent memory)
    import from
serve/knowledge/             (core library: graph, vector, ingest, query)
```

Each MCP server is a standalone MCPServer application. Core libraries live in separate packages. Cross-package imports are enforced by `tests/test_package_boundary.py`.

## Dependency Rules

Cross-namespace imports are enforced by `tests/test_package_boundary.py`. The `ALLOWED_IMPORTS` constant in that file maps each package namespace to its permitted owlbear-namespace imports.

**Rules:**

- When adding a new package, update `ALLOWED_IMPORTS` — the manifest guard will fail otherwise.
- TYPE_CHECKING import policy is documented in the test module docstring.
- MCP servers may import from their corresponding core library (e.g., `knowledge-mcp` imports from `knowledge`) but not from other MCP servers.

## Domain Scope Map

Each task targets exactly one domain. Multi-domain work must be split into separate tasks.

| Domain | Scope |
|--------|-------|
| knowledge | `serve/knowledge/` (graph, vector, ingest, query, embeddings) |
| delivery-mcp | `serve/delivery-mcp/` |
| knowledge-mcp | `serve/knowledge-mcp/` |
| memory-mcp | `serve/memory-mcp/` |
| browser | `serve/browser/` |
| browser-mcp | `serve/browser-mcp/` |
| agent-config | `share/agents/`, `share/skills/`, `share/instructions/`, `.github/copilot-instructions.md` |
| test-infra | shared conftest, fixtures, factories (not individual test files) |
| docs | `docs/`, `README.md`, `SECURITY.md` |

**Edge case:** Adding a `config.py` field as part of a core feature is NOT a domain violation — domain = primary concern.
