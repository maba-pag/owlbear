# ddgs MCP Server Integration — Implementation Research

> **Owning task:** #686 — Add ddgs MCP server to VS Code config and agent tool allowlists
> **Date:** 2026-04-09 **Status:** Complete

## 1. Context and Question

Task #681 researched web search options and recommended ddgs built-in MCP server (confidence .85). This task (#686) implements the integration. This research validates the specific implementation approach: dependency placement, MCP config format, agent tool names, and compatibility with the existing workspace.

## 2. Sources Studied

| Source | URL | Relevance | What |
|--------|-----|-----------|------|
| ddgs v9.13 README | github.com/deedy5/ddgs | .95 | MCP server docs: `ddgs mcp` command, 6 tools, client config JSON example |
| ddgs PyPI v9.13 | pypi.org/project/ddgs/ | .90 | Install: `pip install ddgs[mcp]`, released Apr 6 2026 |
| #681 research doc | .owlbear/research/web-search-mcp-options.md | .95 | Comparative analysis of 4 options, ddgs recommended |
| seed/.vscode/mcp.json | seed/.vscode/mcp.json | .90 | Template: `uv --project {{path}} run python -m <pkg>` pattern |
| researcher.agent.md | share/agents/researcher.agent.md | .90 | Tool format: `'server-name/tool_name'`, current tools list |
| ideator.agent.md | share/agents/ideator.agent.md | .85 | Tool format, no web search tools currently |
| serve/mcp-*/pyproject.toml | serve/mcp-kanban/ etc | .80 | All pin `mcp[cli]>=1.26` — compatibility baseline |

## 3. Analysis

### 3.1 Dependency Placement

| Approach | Pros | Cons | KISS Score |
|----------|------|------|------------|
| `dev` group in root pyproject.toml | Simple, auto-included by `uv sync/run`, consistent | Semantic mixing with test tools | **High** |
| Separate `search` dep group | Cleaner categorization | Requires `--group search` in MCP config args; same lockfile resolution — no isolation benefit | Medium |
| `uv tool install ddgs[mcp]` | Full venv isolation | Not in lockfile, requires setup step, different pattern | Low |

**Recommendation:** `dev` group (.80 confidence). Semantic mixing is minor — dev already has pytest, ruff, pyyaml (heterogeneous). Separate group adds complexity without real isolation since uv resolves all groups in a single lockfile.

**Version pin:** `ddgs[mcp]>=9.13,<10` — protects against MCP tool signature changes in hypothetical v10 while allowing patch updates.

### 3.2 MCP Config Format

The seed template uses `uv --project {{owlbear_path}} run python -m <package>`. For ddgs:

```json
"ddgs": {
  "type": "stdio",
  "command": "uv",
  "args": ["--project", "{{owlbear_path}}", "run", "ddgs", "mcp"]
}
```

Follows existing pattern. `uv run ddgs mcp` resolves `ddgs` from the dev group and starts the stdio MCP server. Note: `seed/.vscode/mcp.json` is Copilot-ignored — builder must use terminal-based editing.

### 3.3 Agent Tool Selection

ddgs MCP server exposes 6 tools. Per YAGNI, restrict to needed subset:

| Agent | Tools | Rationale |
|-------|-------|-----------|
| researcher | `ddgs/search_text`, `ddgs/extract_content` | Search discovers URLs, extract fetches content |
| ideator | `ddgs/search_text` | Competitive analysis, feature research |

Remaining 4 tools (search_images, search_news, search_videos, search_books) omitted. Can add later if needed.

### 3.4 Compatibility Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| mcp SDK version conflict | Low | High | ddgs v9.13 likely pins mcp>=1.0. Verify with `uv add --dry-run` before locking |
| ddgs scraping breaks | Medium | Medium | 9-backend auto-fallback. Agents degrade to `fetch_webpage` for known URLs |
| Startup latency | Low | Low | Measure during smoke test (AC5). Expect <2s based on lightweight stdio server |
| Tool signature change | Low | Medium | Version pin `<10` limits blast radius |

### 3.5 Existing Install Migration

`seed/.vscode/mcp.json` updates only affect new installations. Existing users must manually add the ddgs entry. Document update steps in setup-guide.md.

## 4. Recommendation (.82 confidence)

Proceed with ddgs MCP server integration using the `dev` dependency group approach. Pin `ddgs[mcp]>=9.13,<10`. Use `uv --project ... run ddgs mcp` in the MCP config to match existing server patterns.

**Tier classification: T3 (new capability)** — adds web search to agent pipeline. Requires blocking DR via scribe before implementation.

**Challenge:** RECONSIDER at .75 — challenger identified missing T3 DR, dependency group concern, version pinning gap. Addressed: adopted narrow version pin, validated dependency group tradeoffs, creating T3 DR as part of this research deliverable. Revised confidence from .85 to .82 (slightly lower due to unverified mcp version compatibility).

## 5. Follow-up Actions

1. **T3 Decision Request** — blocking DR for new capability (web search in agent pipeline)
2. **Verify mcp compatibility** — run `uv add --dry-run ddgs[mcp]>=9.13,<10` before implementation
3. Implementation per existing ACs (AC1–AC5 on task #686)
