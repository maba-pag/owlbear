# Website-to-Knowledge Vertical Design

> **Status:** Roadmap architecture only; never approve or admit this umbrella.
> **Research:** `.owlbear/research/website-to-knowledge-opportunity-assessment.md`

## Governance

`website-to-knowledge-vertical` is the stable roadmap and evidence container. It must never enter derivation, checkpoint, validation, approval, admission, Planning, Build, or Integration. The Designer uses it only to select and ground one separate focused Design session from the queue below.

Before extracting “next,” inspect current Design and Delivery state. Resume an existing queue child when present. Otherwise create the lowest-order child whose prerequisites are complete. Never skip a blocked prerequisite, combine queue rows, or revise this umbrella as part of child work.

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

## Ordered Focused Change Queue

| Order | Focused change ID | Bounded scope | Prerequisites |
|---:|---|---|---|
| 1 | `knowledge-source-contract-alignment` | Ingestor register/delete authority, valid handbook schemas, and contract tests | None |
| 2 | `knowledge-runtime-readiness` | Consistent MCP/setup wiring, explicit Browser policy, package-boundary enforcement, and readiness diagnostics | 1 |
| 3 | `static-website-knowledge-ingestion` | Static HTML extraction ownership, source identity/delta semantics, and register -> refresh -> search proof | 1, 2 |
| 4 | `guided-knowledge-ingestion-workflow` | User preview, validation, registration, ingestion, verification, and actionable failure flow | 3 |
| 5 | `cockpit-knowledge-workspace` | Source list, health, refresh, deletion confirmation, and search UI | 3, 4 |
| 6 | `rendered-knowledge-source-refresh` | Authoritative Browser bridge with rendered/authenticated fixture proof and preserved safety | 3, 4 |

A focused child must cite this umbrella and `.owlbear/research/website-to-knowledge-opportunity-assessment.md`, but owns its own Product Promise, decisions, architecture, contract, gates, approval, admission, and Delivery lifecycle.

## Child Extraction Procedure

1. Read this umbrella and the linked research without revising either.
2. Inspect current Design/Delivery state for the six exact child IDs.
3. Select the first child that is neither completed nor active and whose prerequisites are completed.
4. Create or resume that child using only its queue-row scope and relevant current evidence.
5. Resolve that child's material decisions and run its normal Design gates.
6. Stop at explicit approval for the child; never ask approval for the umbrella.
7. After the child completes, repeat the same command to select the next row.

## Proposed Product Outcomes

The queue collectively aims to deliver contract/runtime truth, a proven static website vertical, a guided ingestion workflow, a Knowledge operations surface, and a separately gated rendered/authenticated extension. These are roadmap outcomes, not one Delivery contract.

## Architecture Alternatives Delegated To Children

### Static HTML Extraction

The `static-website-knowledge-ingestion` child chooses among a lightweight Knowledge extractor, a shared extraction package, Browser-owned acquisition, or an existing conversion boundary such as MarkItDown. It must minimize duplicate logic and keep package dependencies explicit.

### Rendered Refresh Composition

The `rendered-knowledge-source-refresh` child chooses among an in-process Browser library dependency, an explicit browser-acquisition handoff followed by source-bound ingest, or an agent-mediated durable refresh recipe. The current placeholder is not an implementation.

## Shared Proof Expectations

- Contract tests for tool grants and handbook examples.
- Setup tests proving MCP entries resolve intended runtime authority and Browser policy is explicit.
- Golden HTML-to-Markdown fixtures.
- Local HTTP integration using deterministic embedding/vector doubles where appropriate.
- One assembled production-composition smoke for register -> refresh -> search.
- Cockpit backend, frontend, and Playwright tests only after backend proof is green.
- Rendered fixtures with explicit selectors and structured acquisition outcomes.

Each child adopts only the proof relevant to its bounded scope.

## Known Risks

- BGE-M3 model size and lazy startup can obscure failures unless diagnostics distinguish model readiness from acquisition and persistence.
- Moving extraction across package boundaries without a mechanical boundary test can create accidental coupling.
- Browser safety criteria can be weakened accidentally if convenience is optimized without preserving ambiguity checks.
- Prior research describes retired implementations; only current source and executable proof are authoritative.

## Outside The Queue

Crawler, scheduled refresh, graph exploration, Assembly, rollback, and cross-project management remain deferred. They require new evidence and separate Design sessions after their prerequisites are complete.

## Admission State

**Permanently not admissible.** This umbrella intentionally has no Delivery contract. Do not call `derive_delivery_contract`, `publish_design_checkpoint`, `validate_delivery_contract`, or `admit_delivery_change` for `website-to-knowledge-vertical`. Only focused child changes may pass those gates.
