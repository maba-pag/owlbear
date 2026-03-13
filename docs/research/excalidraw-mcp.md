# Excalidraw MCP App Server — Research

> **Owning task:** #594 — Research: excalidraw/excalidraw-mcp
> **Date:** 2026-03-06 **Status:** Complete

## 1. Context and Question

OwlBear already integrates external MCP servers via `MCPServerRegistry` (stdio/SSE/StreamableHTTP). This research analyzes the excalidraw-mcp repository to determine whether the **MCP Apps** extension (interactive HTML UIs served inline via MCP tools) offers patterns or capabilities applicable to OwlBear's agent workflows — specifically visual feedback, diagram generation, or interactive approval UIs.

## 2. Sources Studied

| # | Source | URL | Relevance |
|---|--------|-----|-----------|
| 1 | excalidraw/excalidraw-mcp | <https://github.com/excalidraw/excalidraw-mcp> | .90 — Primary subject |
| 2 | MCP Apps spec (ext-apps) | <https://modelcontextprotocol.io/docs/extensions/apps> | .85 — Official extension spec |
| 3 | ext-apps SDK repo | <https://github.com/modelcontextprotocol/ext-apps> | .80 — SDK + examples |

## 3. Architecture Analysis

### 3.1 Server Structure

The excalidraw-mcp server is a TypeScript/Node.js MCP server exposing **5 tools** and **1 resource**:

| Tool | Visibility | Purpose |
|------|-----------|---------|
| `read_me` | Model | Returns a cheat-sheet prompt with element format, palettes, examples |
| `create_view` | Model + UI | Accepts JSON elements, renders SVG via Excalidraw, saves checkpoint |
| `export_to_excalidraw` | App-only | Uploads diagram to excalidraw.com (called by widget, not model) |
| `save_checkpoint` | App-only | Persists user edits from fullscreen mode |
| `read_checkpoint` | App-only | Reads checkpoint for restore |

**Key pattern:** Tool visibility scoping (`_meta.ui.visibility: ["app"]`) hides internal tools from the LLM while making them callable by the embedded widget. This is an MCP Apps extension, not core MCP.

### 3.2 Reusable Patterns

| Pattern | Description | OwlBear Relevance |
|---------|-------------|-------------------|
| **Cheat-sheet tool** | `read_me` pre-loads domain knowledge into model context before the main tool call | High — applicable to any complex tool that needs format/schema guidance |
| **Checkpoint/restore** | Server-side state store with UUID keys; widget syncs edits back via private tools | Medium — could inform session state persistence patterns |
| **`registerAppTool` / `registerAppResource`** | SDK helpers that wire tool → HTML resource via `_meta.ui.resourceUri` | Low — TypeScript/Node SDK only; OwlBear is Python |
| **Dual transport** | Factory pattern: `createServer()` returns fresh `McpServer` per request (stateless HTTP) or single instance (stdio) | Medium — matches OwlBear's existing registry pattern |
| **Input validation** | `MAX_INPUT_BYTES` (5MB) check, alphanumeric checkpoint ID validation, path-traversal guard on file store | High — good security practices to adopt |
| **CSP policy** | `_meta.ui.csp.resourceDomains` allows font loading from esm.sh | N/A — OwlBear doesn't serve HTML UIs |

### 3.3 MCP Apps Extension Assessment

| Criterion | Assessment |
|-----------|-----------|
| **Theoretical validity** | MCP Apps are sound — official extension supported by Claude, VS Code Copilot, ChatGPT, Goose. The iframe sandbox + postMessage architecture is secure. |
| **Prior art** | 20+ examples in ext-apps repo (maps, 3D, PDFs, dashboards). Excalidraw is the flagship demo. |
| **Technical feasibility** | Python SDK support exists (`@modelcontextprotocol/ext-apps/server` has a Python `say-server` and `qr-server` example using `uv run`). However, OwlBear's agents run server-side via PydanticAI — MCP Apps require a host (Claude, VS Code) to render the iframe. OwlBear itself is NOT an MCP host; it is an MCP client/consumer. |
| **Architecture fit** | **Low.** OwlBear consumes MCP tools via `MCPServerRegistry` + PydanticAI. It does not render HTML iframes. MCP Apps are designed for chat UIs (Claude Desktop, VS Code chat). OwlBear's channels (CLI, Slack) cannot render interactive HTML. |
| **KISS/YAGNI** | Adding MCP Apps rendering to OwlBear would require building an iframe host — significant complexity for unclear benefit. The existing `VisualFeedbackToolset` (screenshots) and `ScreenshotService` handle visual feedback adequately. |

## 4. Recommendation (.70 confidence)

**Do not adopt MCP Apps rendering in OwlBear.** The architecture mismatch is fundamental: MCP Apps need an HTML-capable host (browser-based chat UI), and OwlBear's channels (CLI, Slack) cannot render sandboxed iframes.

**One adoptable pattern (.85 confidence):** The **cheat-sheet tool** pattern (`read_me`) is directly applicable. Complex OwlBear tools (e.g., `create_view` for kanban, knowledge ingestion) could benefit from a lightweight "read format first" companion tool that pre-loads domain context into the model. This is essentially what `RECALL_CHEAT_SHEET` does — it's a tool that returns a structured prompt.

**One security pattern (.80 confidence):** The checkpoint store's `validateCheckpointId()` function (alphanumeric + length check + resolve-then-startswith guard) is a clean pattern for any file-keyed persistence. OwlBear's `ErrorJournal` and session stores could adopt similar validation.

## 5. Follow-up Tasks

```
kanban\kanban-md.exe create "Evaluate cheat-sheet tool pattern for complex toolsets" --priority nice-to-have --status ideation --tags "research,tooling,scope:core" --body "Investigate adding read_me-style companion tools to complex OwlBear toolsets (KnowledgeToolset, KanbanToolset) that pre-load format/schema context before the main tool call. Inspired by excalidraw-mcp read_me pattern. See docs/research/excalidraw-mcp.md §3.2."
```

No other follow-up tasks warranted — MCP Apps rendering is out of scope (YAGNI), and the checkpoint/security patterns are minor observations, not actionable tasks.
