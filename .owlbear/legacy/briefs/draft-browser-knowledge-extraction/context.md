# Authenticated Content Pipeline — Context

## Problem Statement

OwlBear agents lack access to corporate knowledge that spans authenticated intranet sources. When agents perform knowledge-intensive work (security concepts, architecture docs, implementation planning), they can't reference corporate security requirements, solution blueprints, operating procedures, ticket history, or tool documentation — because that content lives behind SSO on SharePoint, Confluence, internal web tools, and GitHub repos, and no pipeline exists to bring it into the knowledge graph.

The existing ingestion pipeline works for unauthenticated content. The gap is a full source-to-graph pipeline for authenticated content: discovery of subpages from user-provided roots, user review of value, extraction through authenticated sessions, and ingestion with cross-source entity interconnection.

**Scale:** Dozens of SharePoint sites, multiple Confluence spaces (hundreds of pages each), internal tools, and GitHub repos. Manual extraction is impractical.

**Blocking:** Agent output quality is constrained because agents operate without corporate standards and context. Tasks requiring corporate knowledge compliance are blocked.

## Usage Pattern
- User provides root entry points (SharePoint home pages, Confluence spaces, tool URLs, GitHub repos)
- System discovers subpages from those roots
- User reviews/confirms what's valuable (or defines evaluation criteria upfront)
- Extracted content flows into knowledge graph with cross-source entity relationships
- Weekly refresh runs pick up changes to existing indexed content
- Discovery of new subpages happens incrementally

## Existing Tooling
- Confluence/Jira: MCP servers exist (varying maturity; Atlassian Cloud migration end of year)
- Office/PDF files: markitdown MCP server from Microsoft
- PowerPoint analysis: separate project (low priority, future MCP server candidate)
- Text pipeline: IngestPipeline, BookmarkPipeline, intake.read_url/read_file/read_text all operational
- IngestPipeline already handles: chunking → entity extraction → graph storage → delta detection
- BookmarkPipeline already handles: dedup → content evaluation → conditional ingestion
- RefreshOrchestrator already handles: source refresh with content-hash skipping

## Outcomes

1. **Agents search the existing KB for corporate content.** No workflow change for pipeline agents — the KB just has richer, corporate-context content. Success: agent working on a security concept queries KB and gets security requirements, solution blueprints, and operating procedures from across SharePoint/Confluence with source attribution.

1. **Authenticated web content can be extracted programmatically.** The system retrieves HTML/text from SSO-protected corporate pages (SharePoint, internal web tools) through the user's authenticated Edge browser session. Success: given a URL to an SSO-protected page, the system returns the page's text content without manual copy-paste.

2. **A source management agent interactively onboards new sources.** User provides a root URL. Agent discovers linked/child pages, discusses scope and depth with the user, and feeds confirmed pages into the ingestion pipeline. Different source types (SharePoint sites, Confluence spaces, standalone web tools) have type-appropriate discovery strategies. Success: user provides a SharePoint site URL → agent discovers site pages → user reviews list → confirmed pages are ingested.

3. **Ingested corporate content is queryable by pipeline agents.** Pipeline agents search the KB and receive corporate content results with source attribution (URL, source system, last refresh). No agent workflow changes. Success: `search_knowledge("security requirements for cloud services")` returns relevant results from ingested corporate content with source URL in metadata.

4. **Cross-source concepts are linked in the knowledge graph.** The entity extraction pipeline recognizes corporate knowledge types and creates cross-source edges when entities from different sources refer to the same concept. Success: a "data classification" concept from a SharePoint security policy links to "data classification" from a Confluence implementation guide.

5. **Content freshness is maintained through scheduled refresh.** Each source has a configurable refresh interval (weekly default). Refresh re-fetches via authenticated extraction, uses delta detection to skip unchanged content, and discovers newly added pages. Success: updated intranet page appears in KB within one refresh cycle.

6. **Source removal cleans up completely.** Removing a source cascade-deletes all associated documents, entities, and edges. Allowed URL domains prevent accidental ingestion of unintended sites.

## Landscape Summary

**v1**: Playwright + Edge CDP. 12 files, ~1200 LOC. Launcher/Manager/Toolset/Crawler/ContentExtractor. Never reached production. BFS crawler with safety guards.

**v2 gaps**: Only url_list and file_glob source types. No authenticated extraction, no subpage discovery, code-centric entity model.

**Community**: No mature browser MCP fits. browser-use conflicts with PydanticAI agent loop; crawl4ai is crawl-only; Stagehand is cloud-only. Recommendation: port v1 BrowserToolset as custom integration.

**SharePoint extraction**: Browser CDP wins for corporate (no OAuth setup, works with locked-down Edge, handles SSO natively). API approaches require IT approval and separate OAuth flows.

**Entity model**: Needs corporate knowledge types (REQUIREMENT, SOLUTION, PROCEDURE, POLICY, STANDARD) and new relation types (GOVERNS, SUPERSEDES_VERSION).

**Phasing suggested**: Phase 1 (browser + source type + entity types) → Phase 2 (discovery + graph builder) → Phase 3 (API parallel path).
