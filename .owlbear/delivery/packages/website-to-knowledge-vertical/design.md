# Website-to-Knowledge Vertical Design

> **Status:** Draft architecture; unresolved decisions remain.
> **Research:** `.owlbear/research/website-to-knowledge-opportunity-assessment.md`

## Current Ownership

- `serve/knowledge/`: source registry, HTTP/file intake, ingestion, chunks, vectors, graph, refresh orchestration.
- `serve/mcp-knowledge/`: Knowledge MCP lifecycle and tools; currently selects a browser placeholder for browser transport.
- `serve/browser/`: rendered acquisition, content extraction, safety validation, and diagnostics.
- `serve/mcp-browser/`: Browser MCP lifecycle, allowlist, and interactive tools.
- `share/agents/knowledge-ingestor.agent.md` and `share/skills/h-knowledge-ops/SKILL.md`: agent authority and operator contract.
- `serve/cockpit/`: human operating surface; currently has no Knowledge workspace.
- `setup/` and seeded `.vscode/mcp.json`: consumer runtime composition.

## Root Findings

1. **Authority gap:** the source registration tool exists but the ingestion agent cannot call it, and the handbook's registration examples are invalid.
2. **Semantic gap:** direct ingestion and documented source identity/refresh behavior disagree.
3. **Content gap:** static HTTP refresh passes raw HTML into ingestion.
4. **Composition gap:** browser-backed refresh is deliberately unwired in mcp-knowledge.
5. **Configuration gap:** Browser defaults deny all domains and the development MCP file mixes checkout identities.
6. **Proof gap:** adapter and unit tests are green, but no production-composition test proves register -> refresh -> search.
7. **Operations gap:** Cockpit cannot expose Knowledge health or sources, but UI work must follow backend proof.

## Proposed Delivery Shape

### Outcome 1: Contract And Runtime Truth

Align tool grants, handbook schemas, source identity semantics, MCP checkout/configuration, and startup diagnostics. Restore or replace the missing package-boundary enforcement promised by architecture instructions.

### Outcome 2: Static Website Vertical

Write a failing deterministic local-server proof first. Choose one explicit extraction owner, then make a public static URL produce cleaned Markdown, a refreshable registered source, chunks, vectors, and searchable results. Prove unchanged refresh and structured failure behavior.

### Outcome 3: Knowledge Operations Surface

Add Cockpit backend routes and a Knowledge workspace for source listing, registration, refresh, health, deletion confirmation, and search. Reuse current workspace health conventions and keep destructive operations explicit.

### Outcome 4: Rendered And Authenticated Extension

Choose and implement one authoritative Browser-to-Knowledge composition boundary. Preserve allowlist, SSRF, authentication, content-boundary, diagnostic-redaction, and untrusted-content constraints. Prove it with a controlled rendered fixture before any corporate-site-specific automation.

## Sequencing

1. Contract truth and consistent runtime wiring.
2. Failing end-to-end static fixture.
3. Extraction ownership decision and static implementation.
4. Agent-facing workflow proof.
5. Cockpit Knowledge workspace.
6. Rendered/authenticated bridge.
7. Only then consider crawler, scheduler, graph explorer, or advanced automation.

## Architecture Alternatives Still Open

### Static HTML Extraction

- Put a lightweight extractor in Knowledge.
- Extract a shared package from Browser and Knowledge.
- Route all website acquisition through Browser.
- Use an existing conversion boundary such as MarkItDown when its contract fits.

The decision must minimize duplicate extraction logic while keeping package dependencies explicit.

### Rendered Refresh Composition

- In-process Browser library dependency owned by mcp-knowledge.
- Explicit inter-service/browser acquisition handoff followed by source-bound Knowledge ingest.
- Agent-mediated acquisition and ingest with a durable refresh recipe.

The current placeholder is not an implementation. The selected option must preserve source refreshability and test production composition.

## Proof Strategy

- Contract tests for tool grants and handbook examples.
- Setup tests proving all MCP entries resolve the intended OwlBear checkout and Browser policy is explicit.
- Golden HTML-to-Markdown fixtures.
- Local HTTP server integration test using deterministic embedding/vector doubles where appropriate.
- One assembled production-composition smoke for register -> refresh -> search.
- Cockpit backend, frontend, and Playwright tests after the backend proof is green.
- Rendered fixture tests with explicit selectors and structured acquisition outcomes.

## Known Risks

- BGE-M3's model size and lazy startup can obscure ingestion failures unless diagnostics separate model readiness from acquisition and persistence.
- Moving extraction across package boundaries without a mechanical boundary test can create accidental coupling.
- Browser safety criteria can be weakened accidentally if ordinary-page convenience is optimized without preserving ambiguity checks.
- Prior research describes retired implementations; only current source and executable proof are authoritative.

## Deferred Opportunities

After the vertical is stable: bounded crawler, scheduled refresh and stale alerts, source-specific extraction profiles, provenance/graph exploration, and cross-project Knowledge management.

## Admission State

Not ready. Product scope is directionally stable, but extraction ownership, rendered composition, and first-change boundary require explicit decisions, architecture challenge, baseline, derived contract, validation, and user approval.
