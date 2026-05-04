# Decisions — Knowledge Engine Activation

## D1 — 2026-05-04 — Project Type

**Status quo:** Knowledge service code exists but is not operationally active.
**Decision to make:** What kind of project is this?

**Options considered:**

- A: Net-new (design from scratch)
- B: Existing-feature/refactor (get existing code working, then improve)

**Chosen:** B — existing-feature/refactor. Substantial implementation exists (~35 modules, 14 MCP tools, architecture decisions already approved).

**Rejected:**

- A because the code already exists and has approved architecture decisions. This is activation + refinement, not greenfield.

## D2 — 2026-05-04 — Investment Tier

**Status quo:** Need to calibrate ideation depth.
**Decision to make:** What tier does this work fall into?

**Options considered:**

- Tool: Standard panel, faster cycle
- Shared: Full panel, research bridge required
- Production: Full panel + Critic at every moment

**Chosen:** Shared — multi-consumer artifact (all pipeline agents use it), external integration complexity, operational concerns (DB storage, model lifecycle), but not external-facing.

**Rejected:**

- Tool because the multi-consumer + external integration complexity warrants fuller rigour.
- Production because it's not end-user-facing; consumers are internal agents and the operator.

## D3 — 2026-05-04 — LLM Access Path

**Status quo:** No API keys possible (corporate policy). Only LLM access is GitHub Copilot subscription.
**Decision to make:** How does the system access an LLM for entity extraction?

**Options considered:**

- A: Agent-driven enrichment inside VS Code (Copilot model via subagent parallelization)
- B: OpenAI-compatible API key (Ollama, OpenAI, Azure)
- C: Copilot CLI device-flow in terminal
- D: Token passthrough from VS Code to MCP server

**Chosen:** A — agent-driven enrichment inside VS Code. Triggered by user via prompt. Parallelizable via subagents (8+ observed in practice). Pydantic for structured output. Session coupling is intentional (no invisible costs).

**Rejected:**

- B because corporate policy prohibits API keys. Hard constraint.
- C because it uses the same API/rate limits as VS Code with less visibility and more tech surface. No advantage over A.
- D because VS Code doesn't expose token passthrough today. Future dependency.

**User rationale:** "the arguments [against A] are bad. vs code CAN parallelize agents (8+ in parallel observed). Same API, same limits. Session coupling is intentional — why would I want invisible costs?"

## D4 — 2026-05-04 — Graph Enrichment: Required or Optional?

**Status quo:** Challengers argued graph is speculative value for this corpus size.
**Decision to make:** Is graph enrichment core to the deliverable?

**Chosen:** Core requirement — graph enrichment is non-optional.

**User rationale:** Use case is cross-source relationship mapping:
- SharePoint: requirements
- Jira: tickets needing implementation evidence
- Confluence: documentation standards, policies, tools, processes, manuals
- These sources are NOT mapped to each other
- User needs cross-source relationship awareness for compliant project documentation
- Vector search alone ≈ Confluence MCP search = "doesn't work, not even remotely, not even a little — too much information"
- Graph maps cross-source relationships that vector search cannot surface

## D5 — 2026-05-04 — LightRAG Evaluation Timing

**Status quo:** Custom 35-module engine exists but untested. LightRAG is proven (28.7k stars, MIT, .90 relevance).
**Decision to make:** When to evaluate LightRAG?

**Options considered:**

- Before P0 (don't invest in custom engine until evaluated)
- After P0 (fix crash first, then evaluate)
- Parallel (fix crash while spiking LightRAG)

**Chosen:** Before P0. Evaluate LightRAG first. Don't invest in fixing the custom engine until we know whether to keep it.

**Rationale:** LightRAG eval is research input to the Brief. If it wraps cleanly, 25+ custom modules become throwaway. Avoid sunk cost.

## D6 — 2026-05-04 — Deliverable Structure

**Status quo:** Challengers recommended P0→P1→P2 phasing.
**Decision to make:** One Brief or multiple?

**Chosen:** One Brief. LightRAG eval is prerequisite research, not a separate phase. "Fix the crash" is included in the deliverable if we keep the custom engine.

**User rationale:** "the lightrag evaluation is not a brief, its research for the brief. fixing the startup crash is not a brief either, if we change the logic. so there is nothing left but P2 with P0 included and P1 as a prerequisite."

## D7 — 2026-05-04 — Enrichment Worker Pattern

**Decision:** Pull-based worker agents (not orchestrator + per-chunk subagents).

Worker agent loop:
1. Call `get_next_batch(limit=20)` → 20 chunks with metadata
2. Process each chunk inline (LLM extraction)
3. Call `store_enrichment(results)` → persist
4. Repeat until done

Parallelism: 4-6 workers pulling from same pool. `get_next_batch` coordinates (marks in-progress). No orchestrator needed.

Ingest prompt can offer to start enrichment workers after ingestion.

New MCP tools: `get_next_batch`, `store_enrichment`, `get_enrichment_status`.

## D8 — 2026-05-04 — Model Selection for Extraction

**Chosen:** gpt-5.4 mini (0.33x cost, 400K context)
**Fallback chain:** gpt-5 mini (0x) → gpt-5.4 mini (0.33x) → Haiku 4.5 (0.33x)
**Rationale:** Entity extraction is narrow structured parsing. Cheap models with good instruction-following suffice. 400K context allows longer sessions.

## D9 — 2026-05-04 — Browser Detection for Authenticated URLs

**Chosen:** HTTP-first with user validation.
1. Agent tries HTTP fetch first (fast, no Playwright)
2. Shows user preview (title + first ~200 chars)
3. User confirms or rejects ("that's a login page")
4. If rejected → re-fetches via Browser with SSO
5. Saves correct `fetch_method` to sources.yaml manifest

**Rejected:**
- Domain allowlist (0.55) — config drift, maintenance burden
- Always ask (0.30) — annoying, slow
- Pure auto-detect without validation (0.25) — silent data corruption (login pages ingested as content)
- Both HTTP + browser comparison (overkill, Playwright cold start overhead)

## D10 — 2026-05-04 — Ingest/Enrich Separation

**Chosen:** Per-source `enrich: true/false` flag in sources.yaml. Ingest prompt asks user for new sources. Separate `/kb-enrich` prompt for bulk/catch-up.

## D11 — 2026-05-04 — MCP Tool Surface

**Chosen:** Single MCP server, 17 tools total:
- 4 agent-facing read-only: search_knowledge, list_sources, get_stats, list_entities
- 6 operator curation: ingest_document, bookmark_source, list_bookmarks, update_bookmark_tags, refresh_source, consolidate_knowledge
- 3 enrichment (NEW): get_next_batch, store_enrichment, get_enrichment_status
- 4 scope interfaces (deferred impl): import_scope, export_scope, sync_from_global, sync_to_global

## D12 — 2026-05-04 — Scope Machinery

**Chosen:** Include interfaces, defer implementation. Scope tools exist as stubs/interfaces in the MCP server but actual sync logic not implemented until second consumer project exists.

## D13 — 2026-05-04 — Entity Type Schema

**Chosen:** Phase 2 research question. Current types (FUNCTION, CLASS, FILE, CONCEPT, REQUIREMENT, SOLUTION, PROCEDURE, POLICY, STANDARD) may need extension (TICKET, COMPLIANCE_CONTROL, etc.) for cross-source mapping use case.
