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

## D11 — 2026-05-04 (revised 2026-05-05) — MCP Tool Surface

**Chosen:** Single MCP server, 8 active tools + 4 deferred scope interfaces.

Cut from original 17 by eliminating: list_entities (vague browser), bookmark_source/list_bookmarks/update_bookmark_tags (premature), consolidate_knowledge (replaced by get_consolidation_candidates), get_enrichment_status (folded into get_stats).

**Active tools (8):**

| Tool | Consumer | Purpose |
|------|----------|--------|
| `search_knowledge` | Pipeline agents, user | Semantic search + graph-augmented results |
| `list_sources` | Pipeline agents, user, ingestor | What's indexed |
| `get_stats` | Ingestor, enricher | Health check + enrichment/consolidation progress |
| `ingest_document` | Ingestor | Add content (local files, URLs, browser-fetched) |
| `refresh_source` | Ingestor | Re-ingest stale source |
| `get_next_batch` | Enricher | Pull unprocessed chunks for Phase 1 entity extraction |
| `get_consolidation_candidates` | Enricher | Pull unreviewed cross-source entity pairs for Phase 2 consolidation |
| `store_enrichment` | Enricher | Write entities + edges (Phase 1) or cross-source edges/dismissals (Phase 2) |

**Deferred scope interfaces (4):** import_scope, export_scope, sync_from_global, sync_to_global — stubs until second consumer project.

**Design invariant:** `store_enrichment` serves both phases. Empty edges = "reviewed, no match" — candidate is consumed from queue.

## D12 — 2026-05-04 — Scope Machinery

**Chosen:** Include interfaces, defer implementation. Scope tools exist as stubs/interfaces in the MCP server but actual sync logic not implemented until second consumer project exists.

## D13 — 2026-05-04 — Entity Type Schema

**Chosen:** Phase 2 research question. Current types (FUNCTION, CLASS, FILE, CONCEPT, REQUIREMENT, SOLUTION, PROCEDURE, POLICY, STANDARD) may need extension (TICKET, COMPLIANCE_CONTROL, etc.) for cross-source mapping use case.

## D14 — 2026-05-05 — Consolidation Design (Phase 2 Enrichment)

**Decision:** Consolidation is Phase 2 of enrichment, not a separate concept.

**Mechanism:**
- `get_consolidation_candidates` runs deterministic SQL: finds entity names appearing in multiple sources without cross-source edges
- Returns entity name + relevant chunks from both sources inline (agent has full context)
- Agent decides: same entity? → `store_enrichment(edges=[...])`. Not a match? → `store_enrichment(edges=[])` (marks pair as reviewed)
- Review unit is the **source-pair per entity name** — new sources generate new candidate pairs; old dismissals are preserved
- No rejected candidates accumulate; no matches lost when new sources are added

**Rejected:**
- Separate `dismiss_candidate` tool — unnecessary when empty edges already signal dismissal
- Entity-level "done" marking — would lose matches when new sources are added

## D15 — 2026-05-05 — Agent Model

**Decision:** 2 functional agent roles for the knowledge system:

| Agent | Job | Triggered by |
|-------|-----|-------------|
| `knowledge-ingestor` | Ingest, refresh, dispatch enrichment | User via prompt |
| `knowledge-enricher` | Phase 1 entity extraction + Phase 2 consolidation | Ingestor dispatch or user directly |

Whether these are 1 or 2 `.agent.md` files is an architect decision.

**Consumer matrix:**

| Tool | Pipeline agents | Ingestor | Enricher | User |
|------|:-:|:-:|:-:|:-:|
| `search_knowledge` | ✓ | | | ✓ |
| `list_sources` | ✓ | ✓ | | ✓ |
| `get_stats` | | ✓ | ✓ | |
| `ingest_document` | | ✓ | | |
| `refresh_source` | | ✓ | | |
| `get_next_batch` | | | ✓ | |
| `get_consolidation_candidates` | | | ✓ | |
| `store_enrichment` | | | ✓ | |

**Rejected:**
- `knowledge-curator` naming — too close to `memory-curator` which does refinement. "Ingestor" is more accurate for bringing content in.
- Single combined agent — the enricher worker loop is a distinct behavioral mode better served by its own prompt/agent.

## D16 — 2026-05-04 — Scope Tool Inclusion (Panel OQ1)

**Status quo:** D12 defers scope implementation. Architect panel says import_scope/export_scope are fully implemented and useful for backup/restore.
**Decision to make:** Active or deferred?

**Options considered:**

- A: Defer all scope tools (D12 stands, register as stubs)
- B: Keep import/export active, defer only sync_* tools

**Chosen:** A — Defer all. D12 already decided this. Backup/restore is nice-to-have, not activation-critical.

**Rejected:**

- B because narrower active surface reduces exposure (security) and D12 already made this call.

**Source inputs:** Architect stance §MCP Tool Surface, Security stance §7 Least-Privilege

## D17 — 2026-05-04 — Edge Uniqueness Constraint (Panel OQ2)

**Status quo:** Enrichment writes entity edges. Need a uniqueness constraint.
**Decision to make:** Coarse or provenance-aware?

**Options considered:**

- A: UNIQUE(source_entity, target_entity, relation) — simpler, loses per-document evidence chain
- B: UNIQUE(source_entity, target_entity, relation, document_id) — preserves which document established each edge

**Chosen:** B — Provenance-aware. Cross-source relationship mapping is the core value. Edges must be traceable to their source document.

**Rejected:**

- A because losing provenance undermines the graph's trustworthiness for the cross-source mapping use case.

**Source inputs:** Data stance §4, Architect stance §6

## D18 — 2026-05-04 — get_stats Output Depth (Panel OQ3)

**Status quo:** get_stats needs a response contract.
**Decision to make:** How much detail?

**Options considered:**

- A: Minimal (total sources, chunks, entities)
- B: Include enrichment progress (chunks processed / total)
- C: Full per-source health (enrichment coverage, per-source chunk count, enrichment state)

**Chosen:** B — Enrichment progress included. Workers need this to know when they're done. Defer per-source breakdown to post-activation.

**Rejected:**

- A because enrichment workers need progress visibility.
- C because per-source health is post-activation polish.

**Source inputs:** Enduser stance B2, R2

## D19 — 2026-05-04 — delete_source Tool (Panel OQ4)

**Status quo:** No delete tool exists. Manual path: edit sources.yaml + re-ingest.
**Decision to make:** Include in this brief or defer?

**Chosen:** Defer. Manual ingest means manual lifecycle. Document the manual path. Add tool when operator feels the pain.

**Rejected:**

- Include because it's meaningful new work and manual lifecycle is acceptable at current scale.

**Source inputs:** Enduser stance R4

## D20 — 2026-05-04 — Content Guard Timing (Critic Finding)

**Status quo:** Security says scan at ingest AND before enrichment. Critic flagged synthesis for citing the stronger claim but adopting only ingest-time scanning.
**Decision to make:** Ingest only, or also pre-enrichment?

**Chosen:** Ingest only. Pre-guard chunks are a one-time legacy issue. All new ingestion goes through the guard.

**Rejected:**

- Both ingest and enrichment because the risk is limited to pre-guard legacy chunks, and scanning at enrichment time adds per-batch overhead for a one-time edge case.

**Source inputs:** Security stance §2, §8; Critic Pass 1 T6; Critic Pass 2 #8
