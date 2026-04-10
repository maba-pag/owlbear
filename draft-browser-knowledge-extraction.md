# Context — Authenticated Browser Content Extraction

## Problem

Corporate intranet content (Confluence, SharePoint, internal docs, SSO-protected pages) is valuable knowledge that should flow into the OwlBear knowledge graph. However, headless HTTP clients can't access these pages because they lack the user's browser authentication (SSO, certificates, cookies).

The user's desktop browser (Edge/Chrome) is already authenticated to corporate systems. v1 solved this with Chrome DevTools Protocol (CDP) — attaching to the running browser to extract content from authenticated pages. v2 has no equivalent.

## Desired Outcomes

1. Agents can trigger ingestion of URLs from authenticated corporate intranet pages
2. Content extraction happens through the user's authenticated browser session
3. Extracted content flows into the knowledge graph via the existing ingestion pipeline
4. User maintains control over which pages are accessed (consent model)
5. The solution works on a corporate Windows laptop with Edge as the primary browser

## Tier

Medium complexity — involves browser process management, content extraction, security considerations.

## Landscape

**v1 approach:** Playwright + Edge CDP. 1200 LOC, 12 files, 60+ kanban tasks. Managed browser lifecycle, injected JavaScript for content extraction, had URL safety guards.

**Ecosystem:** Community Playwright MCP servers exist. Chrome extensions for content extraction exist. CDP is a stable protocol.

**Constraints:** VS Code Copilot Chat agents can't directly manage browser processes. Solution must work as either an MCP server, a standalone tool, or an extension.
