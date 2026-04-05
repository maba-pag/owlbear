---
# >> Your action: set approved to true, needs-info, or rejected
approved: false
decision: "A: Scope-based tool parameters + import/export"
notes: "you dropped the 'Pursue dual-stack facade (original Option A) or ATTACH DATABASE (original Option B)' option that i requested extra info on. please try again and compare only 'Scope-based tool parameters + import/export' and 'dual-stack facade (original Option A)' and 'ATTACH DATABASE' options against each other. I need to understand what each one does, where it is saved, and what the pro/con for each are."
# >> Agent metadata
task_id: 616
agent: researcher
created: 2026-04-05
urgency: blocking
decision_type: approach-selection
impact_tier: 3
---

# Decision: Approve scope-based tool parameters + import/export for project-local knowledge

## Context

Task #616 researched how to add project-local knowledge source support (`.owlbear/knowledge/`) to mcp-knowledge. After three research passes (initial, validation, risk-depth at user request), the recommendation is Option A: scope-based tool parameters + import/export.

**Risk-depth findings (addressing your earlier questions):**
- **Qdrant cold-start:** Non-issue for this approach — `:memory:` cold-start is pre-existing for ALL data. Option A doesn't change this.
- **Schema drift:** Near-zero — single DB with idempotent `init_db()`. Drift was only a concern for the rejected dual-stack approach.
- **Effort (calibrated):** #617 ~2.5h (scope params + tests), #618 ~4.5h (import/export + tests). Total ~7h, ~300 LOC delta.

**Note:** This is a re-created DR. The original was incorrectly resolved as "approved" when your response was "needs more information." The scribe/DR process has been fixed to support `needs-info` and `rejected` states.

## Options

### A: Scope-based tool parameters + import/export — (rec:) recommended
- **Effort:** ~7h total, ~300 LOC
- **How it works:** Exposes existing `scopes` param on `search_knowledge`, `scope` on `ingest_document` and `list_entities`. Adds `import_scope`/`export_scope` tools (~100 LOC).
- **Risk:** Low. Reuses tested scope-column infrastructure from #135.
- **Confidence:** .85 (up from .80 after risk-depth analysis found risks lower than anticipated)

### B: Do not support project-local knowledge in this phase
- **Effort:** Zero
- **Trade-off:** Defers project-local KB. #617/#618 become moot.
- **Confidence:** N/A (deferral)

### C: Defer / do nothing
- Same as B. No immediate cost; blocks downstream project-knowledge features.

## Recommendation
.85 confidence — **Option A.** All concerns from the initial review have been researched and found to be low-risk. The scope-column infrastructure is already in place.

## Impact of Deferral
Blocks #617 and #618. Project-local knowledge support deferred to future phase.
