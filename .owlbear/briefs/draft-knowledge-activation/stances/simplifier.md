# Simplifier Stance — Knowledge Engine Activation

## Summary

Seven outcomes bundled under one "activation" label. This is three projects wearing a trenchcoat. The core ask is narrow — "agents can search curated knowledge" — but the proposed scope balloons to include auth debugging, multi-source ingestion pipelines, browser automation, LLM enrichment plumbing, graph retrieval, tool-surface review, and a build-vs-buy evaluation. That's not a task; that's a roadmap quarter.

## Challenges

### Challenge 1: Outcome 1 is the only blocker — everything else is optional polish

The user wants pipeline agents to search domain knowledge. That requires: (a) server starts, (b) vector search returns results for pre-ingested content. That's Outcome 1. Outcomes 2–6 are enhancement work that only matters after the server is proven useful. Outcome 7 (LightRAG eval) actively questions whether Outcomes 2–6 are worth doing at all — so why scope them in the same work?

### Challenge 2: "Ingest pipeline works end-to-end" hides enormous complexity

Outcome 2 bundles three very different capabilities: local file ingest (probably works already), public URL fetch (moderate), and authenticated page scraping via Playwright + Edge SSO (complex, fragile, interactive-only). The third item alone is a full feature with its own failure modes, maintenance burden, and environment constraints. It shouldn't live in the same deliverable as "fix the startup crash."

### Challenge 3: Enrichment via VS Code prompt is an unsolved integration pattern

"Agent-driven entity extraction using the Copilot model already in chat" is a novel wiring problem. No existing OwlBear feature does this. It requires the knowledge engine to call back into the agent context for LLM completion — that's a new architectural seam. Scoping this alongside a startup fix is mixing R&D with maintenance work.

### Challenge 4: Outcome 7 undermines Outcomes 2–6

If the LightRAG evaluation concludes "wrap LightRAG directly," then any work invested in polishing the custom ingest pipeline, enrichment chain, or graph retrieval is throwaway. Doing the evaluation last maximises waste. Doing it first invalidates half the scope.

### Challenge 5: 35 modules + 14 tools is high surface area to "activate" in one pass

The framing implies turning on a dormant system. But a system that crashes on startup and has never run end-to-end isn't dormant — it's unvalidated. "Activation" is really "integration testing + bug fixing across 49 components." That's not a single task shape.

## Recommendations

### Decompose into three sequential phases with hard gates

| Phase | Scope | Gate |
|-------|-------|------|
| **P0: Startup + basic search** | Fix the auth crash. Validate vector search works against a manually-ingested test corpus. Ship 3–5 tools (search, ingest-file, status). | Agents can search and get results. |
| **P1: LightRAG evaluation** | Now that P0 proves the use case works, evaluate whether the 35-module engine or LightRAG is the right long-term path. | Decision recorded: keep custom engine OR adopt LightRAG. |
| **P2: Full pipeline** (conditional on P1=keep) | Ingest pipeline, enrichment, graph retrieval, browser sources. Scope depends on P1 findings. | End-to-end ingest from sources.yaml works. |

### Cut the tool-surface review from this work

14 tools is a review task, not a build task. It can happen asynchronously after P0 ships. Don't block activation on tool-surface opinions.

### Defer browser/SSO ingestion to P2 or later

Playwright + Edge SSO is interactive-only, environment-specific, and fragile. It's the highest-complexity, lowest-frequency ingest path. It should not gate "knowledge search works."

### Move the LightRAG evaluation before any pipeline investment

If you might throw away the custom engine, find out before polishing it. P1 before P2, not after.

## Confidence

0.85 — High confidence the scope is inflated and should be phased. The P0/P1/P2 decomposition is nearly forced by the logical dependency: you can't evaluate build-vs-buy without a working baseline (P0), and you shouldn't invest in pipeline polish before the build-vs-buy decision (P1→P2).
