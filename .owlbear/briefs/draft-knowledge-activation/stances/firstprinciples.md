# First-Principles Stance — Knowledge Engine Activation

## Irreducible Claims

What is actually necessary for "pipeline agents can search curated domain knowledge"?

1. **Embedded content must be searchable by semantic similarity.** A vector store with an embedding model. Period.
2. **Content must get into that store.** A pipeline that fetches → chunks → embeds → writes.
3. **The MCP server must start.** It's stdio; it must not block on auth or LLM init.
4. **Authenticated sources need browser automation.** Edge SSO is the only viable path for corporate content.

Everything beyond these four claims is structure inherited from LightRAG, from the existing vibe-coded implementation, or from ambitions that haven't been validated.

## Challenged Assumptions

### A1: "Entity extraction is necessary for useful retrieval"

**Inherited from:** LightRAG's graph-augmented RAG pattern.

**Challenge:** The primary use case is "agent searches domain knowledge." Pure vector search over well-chunked content with metadata filtering already serves this. Entity extraction + graph retrieval adds value only when:
- Queries require multi-hop reasoning across documents
- The relationship structure is richer than what metadata/tags provide
- Retrieval recall is poor without graph expansion

None of these have been demonstrated as actual pain points. The 548 sources in `sources.yaml` are research docs, skills, and instructions — mostly structured markdown that embeds well. Graph enrichment is expensive (context window, agent time, maintenance) and its marginal value over vector+metadata is **unproven for this corpus.**

**Irreducible version:** Vector search is necessary. Graph enrichment is speculative investment that should be deferred until vector-only retrieval demonstrably fails.

### A2: "The agent IS the LLM for extraction"

**Inherited from:** The no-API-key constraint + desire to reuse the Copilot model.

**Challenge:** This conflates two things:
1. "No external API keys" (hard constraint, real)
2. "Therefore the interactive VS Code agent must do extraction inline" (one possible solution, not the only one)

Hidden costs of agent-as-extractor:
- **Context window:** Each extraction call consumes agent context. For 548 sources × N chunks, this is thousands of extraction rounds. An agent session has finite context.
- **No parallelism:** Agent generates serially. LLMExtractor can batch. Agent cannot.
- **Session coupling:** Extraction only happens when a user has an active VS Code chat session. Rebuilding the DB on a new machine requires the user to sit through it.
- **Structured output fidelity:** The Copilot chat model doesn't guarantee JSON schema compliance the way OpenAI's structured output mode does. Parsing failures will be common.
- **Rate limiting:** VS Code Copilot has per-minute token limits. 548 × N extractions could take hours of wall time.

**Irreducible version:** If extraction is needed at all (see A1), the Copilot device-flow CLI auth (interactive terminal, not MCP lifespan) against the Copilot API endpoint is a better path — it's the same model but accessed programmatically with proper structured output. The existing `copilot_auth.py` already implements this; it just needs to be invoked interactively, not at MCP startup.

### A3: "35 modules are necessary"

**Inherited from:** The existing implementation.

**Challenge:** For the irreducible claims (embed, store, search, ingest), you need:
- Embedding model management (1 module)
- Vector store client (1 module)
- Chunking (1 module)
- Fetcher/loader (2–3 modules for file/http/browser)
- Source registry (1 module)
- Query service (1 module)
- MCP tool handlers (1 module)

That's ~8–10 modules. The remaining 25 modules serve graph construction, entity extraction, consolidation, scope transfer, bookmarks, inter-document graphs, evaluation, benchmarking, content safety, refresh orchestration. Most of these serve Outcome 3/4 (enrichment + graph retrieval) which depends on assumption A1 holding.

**Irreducible version:** Phase 1 activates ~10 modules. The other 25 are dead weight until graph enrichment proves its value.

### A4: "Single-DB architecture (DR #616) is load-bearing"

**Inherited from:** DR #616 (approved).

**Challenge:** DR #616 decided single-DB with scope column over dual-stack. But scope transfer, import/export, and portable snapshots add complexity. The actual use case right now is: one user, one machine, one knowledge base. The scope machinery solves a problem that doesn't exist yet (multi-project knowledge isolation).

**Irreducible version:** One SQLite DB, no scope column, no import/export. Add scoping when a second project needs isolation. DR #616 solved a future problem; honor the direction but don't implement the full mechanism in Phase 1.

### A5: "LightRAG evaluation is a Phase 2 research question"

**Inherited from:** The framing assumes the custom engine is the default and LightRAG is the challenger.

**Challenge:** Invert the question. LightRAG is a maintained, tested library that does exactly what the 35-module engine attempts. The custom engine is untested, never-activated code. The burden of proof should be: "what does our custom engine do that LightRAG cannot?" not "should we maybe switch to LightRAG?"

If the answer to A1 is "graph enrichment is speculative," then the custom engine's primary differentiator (its graph pipeline) is the speculative part. What remains (vector search + ingest) is commodity functionality that LightRAG, ChromaDB, or even raw Qdrant handles.

**Irreducible version:** Evaluate LightRAG first, not last. If it covers the irreducible claims, wrap it. The custom engine is 35 modules of technical debt until proven otherwise.

### A6: "14 MCP tools are the right surface"

**Inherited from:** The existing implementation.

**Challenge:** Pipeline agents need exactly two operations: `search_knowledge(query, filters)` and maybe `get_document(id)`. The remaining 12 tools (ingest, bookmark, consolidate, refresh, etc.) are operator/curation tools, not agent consumption tools. Mixing curation and consumption in one MCP server conflates two audiences with different reliability requirements.

**Irreducible version:** Agent-facing surface is 2–3 read-only tools. Curation is either a separate MCP server or a CLI. Don't make agents depend on a server that also does writes.

## Risks

| # | Risk | Severity | Trigger |
|---|------|----------|---------|
| R1 | Agent-as-LLM extraction is impractical at scale | High | Attempting to enrich 548 sources through chat |
| R2 | Graph enrichment adds complexity without measurable retrieval improvement | Medium | Building the full pipeline before validating vector-only |
| R3 | 35-module engine has unknown bugs that surface only at activation | High | Never tested end-to-end |
| R4 | Scope/transfer machinery adds surface area for a single-user system | Low | Implementing DR #616 fully in Phase 1 |
| R5 | LightRAG evaluation deferred too long, sunk cost locks in custom engine | Medium | "Phase 2" never happens because Phase 1 is complex enough |

## Recommendations

1. **Start with vector-only retrieval.** Get the MCP server starting, embedding working, and search returning results. Skip graph entirely in Phase 1. Measure retrieval quality. Only add graph if vector-only demonstrably fails.

2. **Evaluate LightRAG before building more custom code.** The custom engine is unproven. LightRAG is proven. Invert the burden of proof.

3. **Use Copilot device-flow CLI for extraction, not agent-inline.** If extraction is needed, `copilot_auth.py` + a CLI tool that calls the Copilot API with structured output is sound. Agent-inline extraction is a UX and scalability dead end.

4. **Separate read surface from write surface.** Agents get 2–3 read-only MCP tools. Curation gets a CLI or separate server.

5. **Defer scope machinery.** One DB, no scope column, until multi-project is a real need.

## Confidence

**0.82** — High confidence that graph enrichment and agent-as-LLM are inherited structure rather than irreducible needs. Moderate uncertainty about whether the existing 35-module engine has salvageable value vs. starting from LightRAG.
