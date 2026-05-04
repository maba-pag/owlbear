# Architect Stance — Memory MCP Tool UX Refactor

**Panelist:** ideation-architect  
**Mode:** stance (full design evaluation)  
**Critic cycles:** 2  
**Confidence:** 0.78

---

## Architectural Stance

The design is structurally sound at the domain-model level. The 7-tool surface correctly separates three tool-design audiences (general agent, curator, user) with different schemas per audience. The state machine (pending → curated → approved, plus state-dependent deletion) is deliberately minimal — 4 states, 5 transitions, no recovery from deleted, no reject path. This minimalism is a feature.

However, the design has **three structural issues** that must be resolved before implementation:

1. **Tool-visibility specificity.** The brief says "all pipeline agents get `ob-memory/*`" — but `ob-memory/*` exposes the entire MCP server surface including curator tools. General agents MUST list specific tools: `ob-memory/save_memory`, `ob-memory/recall_memory`. The curator lists `ob-memory/list_memories`, `ob-memory/read_memory`, `ob-memory/curate_memory`, `ob-memory/delete_memory`. This is how the 2-tool/4-tool separation is actually enforced. The brief's shorthand must become explicit in implementation.

2. **`recall_memory` wildcard `"*"` violates C9.** The design establishes schema-enforced separation as a core principle (convergence C9) then breaks it by embedding a privileged path (`"*"` = unscoped query) inside the general-agent read tool. The curator already has `list_memories` + `read_memory` for full unscoped access. Remove `"*"` from `recall_memory` — the tool should validate that the `agent` parameter matches a specific agent-name pattern and reject wildcards.

3. **Body limit hiding contradicts the problem statement.** D22 says the 1KB limit is "NOT stated in tool description — only in validation error." The brief's problem statement #3 explicitly identifies hidden constraints as the anti-pattern being fixed. D22 reintroduces it. Recommend: state the constraint in the tool description as a quality signal ("Content: concise single-topic note, max 1KB") rather than hiding it.

---

## Structural Reasoning

### State Machine Completeness

The five critic findings are resolved as follows:

| # | Finding | Resolution | Reasoning |
|---|---------|-----------|-----------|
| 1 | Scope gate vs auto-state | Atomic rejection | `curate_memory` on pending entry WITHOUT `scope_agents` → entire call fails. Error: "Pending entry requires scope_agents for promotion to curated." Both invariants (auto-state always→curated, scope gate rejects unscoped promotion) are preserved because the call never executes. |
| 2 | Atomicity | All-or-nothing | Validate all provided fields first, apply atomically. Standard write semantics. Partial state on failure is unacceptable. |
| 3 | Auto-downgrade trigger | Unconditional | Any `curate_memory` call on approved entry → curated. No equality check. Simpler implementation, bounded cost (one re-approval), curator shouldn't call without intent. |
| 4 | Stale ID after hard-delete | "Entry not found" | Clean absence. No tombstone for entries that were never committed. |
| 5 | Admin vs substantive edit | Both trigger downgrade | Code cannot judge semantic significance. Bounded cost. Guidance hint explains to user. |

The scope-gate atomic rejection is the critical one: it means `curate_memory` has a **conditional required parameter** — `scope_agents` is required when the target entry is in `pending` state. This is unusual but principled. The error message makes it actionable.

### Identity Model

After D10 deleted runtime identity mechanisms, all identity in this system is **self-declared routing metadata**, not verified provenance. This applies to:
- `source_agent` on save — the storing agent self-reports its name
- `agent` on recall — the querying agent self-reports its identity
- `modified_by` (dropped) — would be constant "memory-curator"

D10's threat model is explicit: "accident prevention, not true access control — sufficient for single-user laptop deployment." The schema separation enforces which tools an agent CAN call (via `tools:` lists). It cannot verify WHO is calling — and doesn't try to.

This means "3 actors with schema separation" is more precisely: **3 tool-design audiences with visibility-enforced boundaries**. The user actor is further mediated — `approve_memory` is called by an agent on the user's behalf during the guided prompt workflow, not by the user directly.

### Read Payload (D27 body-only)

D27's decision to return body-only from `recall_memory` is **architecturally correct**. The tool serves pre-flight context injection: agents need the KNOWLEDGE content, not curation metadata. Categories, confidence, scope, timestamps are curation machinery that would pollute agent context without aiding their primary task. The curator's `read_memory` returns full metadata — that's where structured inspection belongs.

### Deletion Semantics

D19 supersedes synthesis C7 on deletion. The final model:
- `pending` → hard-delete (file removed from disk, never committed, no trace)
- `curated`/`approved` → soft-delete (state=deleted, file retained, terminal)

This is sound: pending entries are uncommitted scratch that never entered the quality pipeline. Removing them permanently is appropriate — there's no audit value in preserving rejected drafts. Curated/approved entries have been through review and carry institutional knowledge; soft-delete preserves the audit trail.

Note: the synthesis artifact has not been updated to reflect D19. **Decisions.md is authoritative.** The mediator should reconcile synthesis before brief drafting.

### `modified_by` Omission

Correct. After D10, this field would be self-reported and constant ("memory-curator" on every mutation). Zero information content. `source_agent` is meaningful because different agents create entries. `modified_by` is not meaningful because one agent curates all entries. Add it if/when a second curator exists.

---

## Key Trade-offs

| Decision | Trades | For | Acceptable Because |
|----------|--------|-----|-------------------|
| Unconditional downgrade | Precision | Simplicity | Cost = one re-approval. Equality checking on YAML+markdown is non-trivial. |
| Atomic scope rejection | Curator UX friction | Invariant safety | One extra parameter when editing pending entries. Clear error message. |
| Remove "*" wildcard | Curator convenience | Structural consistency | Curator has dedicated tools for unscoped access. |
| No modified_by | Audit depth | Schema minimalism | Single curator = constant value = zero information. |
| Body limit in description | Behavioral shaping | Discoverability | D22's hiding contradicts the brief's core problem statement. |
| Tool-specific visibility | Shorthand convenience | Actual separation | `ob-memory/*` breaks the model. Must enumerate. |

---

## Warnings

1. **Artifact drift.** Synthesis.md is stale on deletion semantics (pre-D19), curator tool shape (pre-D16), and category names (pre-D24). Reconcile before implementation to prevent confusion.

2. **Activation is shutdown, not rollback.** D12 (big-bang replacement) + D26 (no formal gate) means removing `ob-memory/*` tools disables memory entirely — it doesn't restore the old `vscode/memory` system. This is acceptable because memory is an enhancement, not a dependency (agents function without it), but the brief should acknowledge the dead zone explicitly. Recommendation: staged activation (curator first, verify, then pipeline agents) even without a formal gate.

3. **Self-declared identity is the ceiling.** No design decision in this system can achieve stronger-than-self-reported identity guarantees without a new identity mechanism. Accept this limitation explicitly — don't pretend `source_agent` or tool-visibility provides true access control.

4. **D22 body-limit hiding is a design inconsistency.** It directly contradicts the brief's minimum-acceptable-outcome. Flag for mediator decision.

---

## Confidence: 0.78

The core model (7 tools, 3 audiences, minimal state machine, scope-as-curation-gate) is well-reasoned. The structural issues (#1 tool visibility, #2 wildcard, #3 body limit) are individually low-effort fixes. The activation safety gap (Warning #2) is real but bounded because memory is non-critical infrastructure. The primary risk is artifact drift creating implementation confusion.
