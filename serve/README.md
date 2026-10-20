# OwlBear Packages

Use this page when you know what you want to add, run, or understand, but not which package
owns it. Start with the job, then open the package guide for commands and configuration.

[Project README](../README.md) · [Setup authority](../setup/setup-guide.md)

## Choose by job

| I want to... | Start here | What it provides |
| --- | --- | --- |
| Turn an idea into reviewed work | [Delivery engine](delivery-next/) | The machine host, its pages, the `owlbear` command, and the chat server; run it as [Operating OwlBear](../setup/operating-owlbear.md#running-owlbear) describes |
| Give agents durable institutional memory | [Memory MCP](memory-mcp/README.md) | The VS Code tool boundary for scoped, curated memory |
| Change memory storage or lifecycle rules | [Memory core](memory/README.md) | File-backed entries, states, scoring, and engine primitives |
| Record, validate, or migrate decisions | [Decisions core](decisions/README.md) | One file per decision, the validator, and the record's migration preview |
| Search documents and knowledge graphs | [Knowledge MCP](knowledge-mcp/README.md) | Ingestion, search, sources, graph lookup, and enrichment tools |
| Extend the knowledge engine | [Knowledge core](knowledge/README.md) | Documents, chunks, vectors, graph data, and query services |
| Fetch authenticated web content | [Browser MCP](browser-mcp/README.md) | Allowlisted browser actions and Markdown accessibility snapshots |
| Extend browser acquisition | [Browser core](browser/README.md) | Playwright-backed page acquisition and content extraction |
| Convert HTML to Markdown | [Web content](web-content/README.md) | Shared HTML extraction and Markdown normalization for Browser and Knowledge |
| Maintain indexes and workspace tooling | [Tools](tools/README.md) | Documentation, Python, and TypeScript indexes plus repository utilities |

## How the packages fit

Core packages hold reusable behavior. MCP packages expose that behavior to VS Code agents through
Model Context Protocol, the tool interface used by the four seeded servers. The Delivery engine runs
once per Mac, serves every registered project on its pages, and publishes Changes to GitHub; it
uses the Memory core for agent memory, and its Memory page is where people review memory. Tools
support the repository rather than the product runtime.

```text
owlbear command -> Delivery engine -> pages, agent sessions, GitHub
                                   -> Memory core
VS Code agents  -> MCP packages    -> core packages
                -> Delivery chat server
Tools
```

The package guides are the next level of detail. The project README covers the current checkout and
the consumer README covers installing OwlBear on a Mac. The [setup guide](../setup/setup-guide.md) owns exact
installation commands and [Operating OwlBear](../setup/operating-owlbear.md) owns daily operation
and recovery.

## Package groups

| Group | Packages |
| --- | --- |
| Delivery | `delivery-next` |
| Agent memory | `memory`, `memory-mcp` |
| Decisions | `decisions` |
| Knowledge | `knowledge`, `knowledge-mcp` |
| Browser | `browser`, `browser-mcp`, `web-content` |
| Repository maintenance | `tools` |

All packages use the workspace's Python environment. The Delivery engine's pages are its only web
frontend; they are plain HTML, CSS and JavaScript served from the package, with no build step.
