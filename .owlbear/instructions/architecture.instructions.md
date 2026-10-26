---
description: "Architecture standards for serve/ packages — topology, dependency rules, and domain boundaries"
applyTo: "serve/**"
---

## Architecture Overview

OwlBear's runtime is the Delivery engine, `serve/delivery-next/`. It runs its workers on the GitHub Copilot SDK
(`github-copilot-sdk`): `runtimes/sdk_adapter.py` opens one bounded session on the installed Copilot CLI per step.
The workers' agents and skills ship inside the package, in `owlbear_delivery_next/agents/*.agent.md` and
`owlbear_delivery_next/skills/`; `local_system/preload.py` gives each role its agent file, tools, memory and
skills. The engine also serves the pages, the `owlbear` command and the `owlbear-delivery` MCP server, and
publishes Changes to GitHub.

VS Code chats use the agents and skills under `share/` and the MCP servers in `.mcp.json`. Each of those servers
runs through `python -m owlbear_delivery_next serve <name>` (memory, knowledge, browser) or `... mcp` (delivery).
`commands/mcp_launch.py` runs the named server module; Delivery does not import it.

```text
serve/delivery-next/   Delivery engine: SDK workers, packaged agents and skills, pages, MCP server, GitHub
    imports decisions, memory
serve/decisions/       core: decision files, validator, record migration
serve/memory/          core: memory state, scoring, storage
serve/memory-mcp/      MCP server for agent memory; imports memory
serve/knowledge/       core: graph, vector, ingest, query; imports web-content
serve/knowledge-mcp/   MCP server for the knowledge base; imports knowledge
serve/browser/         core: browser acquisition; imports web-content
serve/browser-mcp/     MCP server for authenticated content; imports browser
serve/web-content/     core: HTML extraction and Markdown normalisation
serve/tools/           repository tools: quality, tests, indexes
```

## Dependency Rules

`tests/test_package_boundary.py` enforces them. Its `ALLOWED_IMPORTS` maps each `owlbear_*` package to the
`owlbear_*` packages it may import, in runtime and `TYPE_CHECKING` imports. Each package's `pyproject.toml`
declares the same workspace dependencies.

- A new package needs an `ALLOWED_IMPORTS` entry; the test fails on any package without one.
- Core packages (`decisions`, `memory`, `knowledge`, `browser`, `web-content`) import no MCP server, no Delivery
  and no tools. `knowledge` and `browser` may import `web-content`; the others import no OwlBear package.
- An MCP server imports only its own core package, never another MCP server.
- Delivery imports only `decisions` and `memory`. It names the MCP servers it launches; it does not import them.
- `tools` imports no OwlBear package, and no product package imports `tools`.
- Relative imports stay within their package; the test checks only absolute `owlbear_*` imports.

## Domain Scope Map

Each task targets exactly one domain. Multi-domain work must be split into separate tasks.

| Domain | Scope |
| --- | --- |
| delivery | `serve/delivery-next/` (engine, packaged agents and skills, pages, MCP server, GitHub publication) |
| decisions | `serve/decisions/` (decision files, validator, and record migration preview) |
| knowledge | `serve/knowledge/` (graph, vector, ingest, query, embeddings) |
| knowledge-mcp | `serve/knowledge-mcp/` |
| memory | `serve/memory/` (memory state, scoring, and storage) |
| memory-mcp | `serve/memory-mcp/` |
| browser | `serve/browser/` |
| browser-mcp | `serve/browser-mcp/` |
| web-content | `serve/web-content/` (shared HTML extraction and Markdown normalisation) |
| tools | `serve/tools/` (repository utilities, quality, and indexing commands) |
| agent-config | `share/agents/`, `share/skills/`, `share/instructions/`, `.github/copilot-instructions.md` |
| test-infra | shared conftest, fixtures, factories (not individual test files) |
| docs | `README.md`, `SECURITY.md`, `setup/`, package `README.md` files |

**Edge case:** Adding a `config.py` field as part of a core feature is NOT a domain violation — domain = primary concern.
