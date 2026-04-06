---
response: needs-info
decision: "user needs more information, see notes"
notes: "i need more depth on the risk: what is the cost of Qdrant cold-start migration on every restart, Qdrant cold-start latency on restart? How risky and how realistic is schema drift in a single-user local-laptop dev setting? how big is the effort actually? (caution, your time estimates are usually off by a factor of 12-24: you say 3 days but really it is 3-6 hours max.)"
task_id: 616
agent: researcher
created: 2026-04-05
urgency: blocking
decision_type: approach-selection
impact_tier: 3
correction_note: "Original response was needs-info, incorrectly resolved as approved by scribe. Corrected 2026-04-05. Risk-depth research was done but formal approval never obtained."
---

# Decision: Approve Option C for Project-Local Knowledge Architecture

## Context

Task #616 completed research on how to add project-local knowledge source support (`.owlbear/knowledge/`) to the mcp-knowledge server. The research document analyzes four architectural options, with Option C ("Scope-based tool parameters + import/export") rated at .80 confidence.

**Why this matters:** This is a T3 decision (adds new MCP tools, changes user-facing tool signatures). Approval of Option C unblocks two follow-up implementation tasks (#617: expose scope params; #618: build import/export tools). Rejection or deferral halts project-local knowledge scope for this phase.

**Key finding:** The original dual-stack approach (Options A/B) carries hidden costs: Qdrant cold-start re-indexing on every server restart, required rewrites across all 5 tool handlers (not just search), and risk of silent schema drift in target project repos. Option C avoids these by leveraging the existing scope-column infrastructure already implemented in #135.

## Options

### A: Scope-based tool parameters + import/export (Option C from research) — (rec:) recommended
- **Effort:** Low — exposes existing `scopes` param on `search_knowledge`, `scope` on `ingest_document` and `list_entities`. Adds ~100 LOC for `import_scope`/`export_scope` tools.
- **Trade-off:** Portability via export/import snapshots instead of live dual databases. Project knowledge must be explicitly imported into global DB under a project scope.
- **Risk:** Low. Reuses tested scope-column infrastructure. No Qdrant cold-start complexity.
- **Confidence:** .80 (validated by challenger; challenger confidence in original: .55 after challenge).

### B: Do not support project-local knowledge in this phase
- **Effort:** Zero.
- **Trade-off:** Defers project-local KB to later phase. Project repos remain centralized on `store/knowledge/`.
- **Risk:** Low immediate risk; blocks downstream work on #617/#618.
- **Confidence:** N/A (deferral).

### C: Pursue dual-stack facade (original Option A) or ATTACH DATABASE (original Option B)
- **Effort:** Medium-high — rewrites 5 tool handlers. Adds Qdrant cold-start migration on every restart.
- **Trade-off:** Live dual databases with potential silent schema drift in target repos.
- **Risk:** High. Qdrant cold-start latency on restart. Challenger raised valid concerns about handler rewrite cost and schema lifecycle risk. Confidence in this approach: .55 (revised down from initial .82).
- **Confidence:** .55 (challenger concern, researcher accepted).

## Recommendation
.80 confidence — **Option A: Scope-based tool parameters + import/export.** This approach leverages the existing scope-column infrastructure from #135, avoids Qdrant cold-start complexity, and requires minimal code change. The challenger's concerns about dual-stack maintainability pushed the confidence down from .82 to .55, making Option C the clear winner.

## Impact of Deferral
- **Blocks:** #617 and #618 cannot proceed to implementation without this approval.
- **Work pending:** Two tasks with complete acceptance criteria are ready for architecture review and TDD cycles once approved. Without approval this cycle, project-local knowledge support is deferred to a future phase.

## Supporting Evidence

Full research analysis: [.owlbear/research/project-local-knowledge-source.md](.owlbear/research/project-local-knowledge-source.md)

Option comparison table: Section 3.1 of research doc.

Codebase evidence: Scope infrastructure confirmed in `serve/mcp-knowledge/models.py`, `graph_store.py`, `query_service.py`, `ingest.py`. Tool handlers do NOT currently expose scope params, confirming the gap addressed by #617.
