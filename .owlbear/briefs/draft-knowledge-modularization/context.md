# Context — Knowledge Module Modularization

## Problem

The knowledge subsystem (~7700 LOC, 32 modules) has never been used end-to-end. Most existing code is speculative implementation from multiple architectural pivots (PydanticAI → GitHub CLI → VS Code Copilot agents), never validated by real consumer demand. Every audit reveals cascading findings (wrong implementations, dead code, wrong logic, missing connections, technically impossible features) requiring multi-day rework. After 5+ audit-fix cycles without convergence, the cost of continuing without stable module definitions is unacceptable.

**Root cause:** No authoritative top-down interface specification exists. Module boundaries were grown bottom-up and shift with each audit. There is no contract to audit against, and no way to track interface changes intentionally.

**What's not broken:** Core algorithms (chunking, embedding, hybrid search), tech choices (BGE-M3, Qdrant, SQLite), layered import structure (no circular deps). These are validated and locked.

**What's unvalidated:** Most pipeline features (entity extraction, cross-source consolidation, graph augmentation, refresh orchestration, enrichment state machine) have never served a real consumer agent. Their interfaces may be speculative.

## Project Type

existing-feature/refactor

## Actors

| Actor | Role | Key Constraint |
|-------|------|----------------|
| **Consumer agent** | Queries knowledge + relationships | Must get precise text with provenance and cross-source context |
| **Consumer agent** (secondary) | Registers a wish for missing data | Cannot block; writes request to register |
| **Ingestor agent** | Fetches + processes sources with AI | Human-triggered; needs auth; involves AI model |
| **Enricher agent** | Cross-source consolidation, entity resolution | Human-triggered; depends on ingested data |
| **Human user** | Triggers agents, authenticates, approves | Gate for corporate auth |
| **Cockpit** | Displays source status, graph visualization | Read-only window |

## Consumer Demand Signal (anchoring scenarios)

1. "For ISMS control 2.4.5 regarding IAM, what is the documented standard procedure in AWS standards tools approved by information security?" — crosses SharePoint ISMS → Confluence standards → InfoSec approvals
2. "What access right in what tool do I need to apply for to use service X?" — crosses service catalog → access management → tool registry
3. "In PDS 4.1 what color options does the PTag have that is in line with corporate CI?" — crosses Porsche Design System docs → corporate CI guidelines

**Common requirements from scenarios:** Multi-source retrieval, exact text preservation (control numbers, procedure names, color codes), cross-source entity relationships, provenance attribution.

## Expectation Signal

**What we're trying to give the user:** A top-down design specification that defines the knowledge system's submodules from user needs. Each module has: defined users, intents, inputs/outputs, timing, and interface contracts. The spec is authoritative — code conforms to it.

**What would make it feel worth using:** Pick up any submodule, implement against its contract, test against its AC independently, compose with confidence. Changes to interfaces are intentional and tracked, not discovered during audits. End-to-end user stories are thought through even when later layers (cockpit UI) aren't built yet.

**What can arrive first (First Useful Step):** The engine layer needs to be split into practical parts (not delivered as one monolith). The natural cuts likely exceed 3 (browser/auth is distinct from content transformation). Each part should be independently buildable. After engine parts: MCP → agents → cockpit API → cockpit UI. The spec covers all layers; implementation is incremental.

**What would be technically done but still wrong:** A monolithic spec that mixes concerns. A spec that doesn't trace scenarios end-to-end. Bottom-up description of existing code. A spec that exists but doesn't enable independent module testing or localize cascade failures to named interfaces. A spec with modular form but no independently executable AC per module.

**What the user knowingly gave up:** Database choice (SQLite locked). Embedding model (BGE-M3 locked). Detailed cockpit visual design (only information requirements).

## Key Tensions from Early Challenge

1. **"Engine first" = the monolith renamed.** The engine IS what needs decomposition. 3 cuts may be too coarse; natural boundaries exist at tech transitions (browser ↔ content processing, processing ↔ persistence, etc.)
2. **Domain maturity.** System has never been used by real consumers. Interfaces will evolve. The goal is not preventing change but making change trackable and intentional.
3. **Spec vs. goal.** The goal is a working knowledge database. The spec is means, not end. It must prove that cascade failures are localized to named interfaces, not just look modular on paper.
4. **Reuse is optional.** No sunk cost attachment. Existing code can be reference material, not sacred.

## Reference Architecture

The kanban module demonstrates the target layering:
- `serve/kanban/` — transport-free engine (pure domain logic, defined public API)
- `serve/mcp-kanban/` — MCP interface on top
- Cockpit routes read from engine directly

## Existing Assets

- Architectural audit: `.owlbear/research/knowledge-package-audit.md`
- Prior briefs: `draft-knowledge-activation/`, `draft-knowledge-source-lifecycle/`, `draft-browser-knowledge-extraction/`
- Research corpus: 20+ research docs covering pipeline, graph, scoping, ingestion, toolset, integration
- Working code: intake, ingest, refresh, query, graph store, vector store, MCP tools
- Sources config: `store/knowledge/general/sources.yaml`

## Status

Phase 1 — M2 complete, early challenge lane complete, research bridge next
