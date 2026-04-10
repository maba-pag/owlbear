# Research Notes — Authenticated Content Pipeline

## v1 Browser Implementation

12 files, ~1200 LOC. Edge CDP lifecycle: launcher finds Edge → probes CDP port 9222 → launches/attaches → Playwright connects.

- **BrowserManager**: async context manager, two modes (launch new / attach via CDP with isolated context)
- **Launcher**: searches standard Edge install paths, probes CDP readiness
- **BrowserToolset**: PydanticAI FunctionToolset subclass, 6 tools (navigate, click, type, select, read_text, screenshot)
- **Content extraction**: injected JavaScript, DOM parsing via accessibility tree (AXNodeInfo)
- **URL safety**: regex blocklist/allowlist via HookRegistry.PRE_TOOL_USE
- **Crawler**: BFS async deque-based, ~180 LOC, max_depth/max_pages limits, robots.txt, rate limiting

v1 was never taken into production before v2 rewrite.

## v2 Pipeline Gaps

- Only URL_LIST and FILE_GLOB source types exist
- RefreshOrchestrator does plain intake.read_url() for URL_LIST
- No browser integration, no subpage discovery
- Entity model is code-centric (file/function/class_/decision/pattern/concept)
- InterDocGraphBuilder exists but only handles code entities

## Community MCP Ecosystem

- browser-use v0.12.0: CDP support but brings own agent loop (conflicts with PydanticAI)
- crawl4ai v0.8.0: crawler-focused, good for scale but lacks interactive tools
- Stagehand: cloud-only, not viable for corporate laptop
- playwright-mcp: experimental, no current integration

Recommendation: port v1 BrowserToolset as custom integration.

## SharePoint/Corporate SSO Approaches

| Approach | Pros | Cons |
|----------|------|------|
| Browser CDP | No OAuth setup, works with policy-locked Edge, handles SSO natively | Slower, hard to parallelize |
| SharePoint REST API | Fast, structured metadata | Requires IT-approved OAuth, enterprise licenses |
| Microsoft Graph API | Rich discovery, parallelizable | Wrong tenant scope on Copilot token, requires separate OAuth |

Browser-based wins for corporate environment: no admin needed, no IT approval, reuses existing auth.

## Entity Model Extensions Needed

**New EntityTypes:** REQUIREMENT, SOLUTION, PROCEDURE, POLICY, STANDARD
**New RelationTypes:** GOVERNS, SUPERSEDES_VERSION (IMPLEMENTS already exists)

## Recommended Phasing

- Phase 1: BrowserToolset integration + AUTHENTICATED_WEB SourceType + corporate EntityTypes
- Phase 2: Subpage discovery + InterDocGraphBuilder extension for corporate types
- Phase 3: SharePoint REST API as optional parallel extraction path for scale
