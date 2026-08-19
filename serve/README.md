# OwlBear Packages

Use this page when you know what you want to add, run, or understand, but not which package
owns it. Start with the job, then open the package guide for commands and configuration.

[Project README](../README.md) · [Setup authority](../setup/setup-guide.md)

## Choose by job

| I want to... | Start here | What it provides |
| --- | --- | --- |
| Turn an idea into reviewed work | [Delivery MCP](delivery-mcp/README.md) | The VS Code tool boundary for Design, Planning, Build, publication, and acceptance |
| Understand or extend the Delivery lifecycle | [Delivery core](delivery/README.md) | Change authority, workspaces, commits, publication state, and recovery |
| Publish Delivery pull requests | [GitHub adapter](delivery-github/README.md) | The fixed GitHub operations used by Delivery |
| See current work and answer requests | [Cockpit](cockpit/README.md) | The browser UI for work items, requests, attention, recovery, and completed history |
| Give agents durable institutional memory | [Memory MCP](memory-mcp/README.md) | The VS Code tool boundary for scoped, curated memory |
| Change memory storage or lifecycle rules | [Memory core](memory/README.md) | File-backed entries, states, scoring, and engine primitives |
| Search documents and knowledge graphs | [Knowledge MCP](knowledge-mcp/README.md) | Ingestion, search, sources, graph lookup, and enrichment tools |
| Extend the knowledge engine | [Knowledge core](knowledge/README.md) | Documents, chunks, vectors, graph data, and query services |
| Fetch authenticated web content | [Browser MCP](browser-mcp/README.md) | Allowlisted browser actions and Markdown accessibility snapshots |
| Extend browser acquisition | [Browser core](browser/README.md) | Playwright-backed page acquisition and content extraction |
| Maintain indexes and workspace tooling | [Tools](tools/README.md) | Documentation, Python, and TypeScript indexes plus repository utilities |

## How the packages fit

Core packages hold reusable behavior. MCP packages expose that behavior to VS Code agents through
Model Context Protocol, the tool interface used by the five seeded servers. Cockpit is the human
operator surface; the GitHub adapter is Delivery's publication provider; Tools support the repository
rather than the product runtime.

```text
VS Code agents
    -> MCP packages -> core packages
    -> Cockpit -> Delivery, GitHub adapter, Memory
    -> Tools -> Delivery
```

The package guides are the next level of detail. The project README covers the current checkout and
the consumer README covers installation into another project when both are present; on `main`, the
consumer README becomes the project README. The [setup guide](../setup/setup-guide.md) owns exact
installation commands and [Operating OwlBear](../setup/operating-owlbear.md) owns daily operation
and recovery.

## Package groups

| Group | Packages |
| --- | --- |
| Delivery | `delivery`, `delivery-mcp`, `delivery-github` |
| Human operation | `cockpit` |
| Agent memory | `memory`, `memory-mcp` |
| Knowledge | `knowledge`, `knowledge-mcp` |
| Browser | `browser`, `browser-mcp` |
| Repository maintenance | `tools` |

All packages use the workspace's Python environment. Cockpit's `web/` directory is the only Node.js
surface and is needed for frontend development and tests; consumers use its prebuilt `dist/` bundle.
