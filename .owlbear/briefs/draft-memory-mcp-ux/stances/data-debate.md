# Data Debate Log — Full Design Evaluation

## Cycle 1

### Initial Position (Modeler)

**State machine is well-formed but under-specified at two critical edges.** Schema is correct and minimal. Deletion model is sound. Scope semantics are clean. Two gaps require resolution:

1. Auto-downgrade trigger: D20 says "any field change" but never defines comparison domain. Without explicit mutable-field boundary and normalization rules, the trigger is ambiguous.
2. Pending curation atomicity: D18 requires scope for pending→curated. D29 says curate_memory always results in curated. D30 allows partial update. These three simultaneously holding for a pending entry without scope_agents is impossible.

Additional positions:
- approved_at clearing on downgrade is intentional (current-state truth, not data loss)
- All field changes on approved entries trigger downgrade (including scope_agents — audience change needs re-approval)
- No tombstone needed for pending hard-deletes (UUID, short lifecycle, fresh list)
- 1KB content cap is correct given D8's splitting philosophy (not a conflict with T5 — D22 supersedes)
- Scope model is internally sound but consumers cannot observe scope via recall_memory (intentional per D27)

### Critic Response

**Confidence in position: 0.44 | Pressure: high**

7 challenges raised:

1. **[Critical] Position 2 atomicity is not the necessary reading.** D18+D29+D30 is a genuine contract collision, not proof that zero-mutation rejection is required. Atomic rejection makes partial-update unusable for pending entries until scope is known. Where do "needs work" pending entries live under this model?

2. **[Critical] "Field change" has no stable comparison domain.** System-managed fields (updated_at, approved_at, state) are themselves modified during downgrade. Without explicit boundary between submitted mutable fields and system-managed fields, the rule is circular. Scope list ordering, markdown normalization, bookkeeping writes — all undefined.

3. **[Moderate] Position 1 attacks a straw man.** D30 gives read_memory as inspection path. Curator reads first, then curates. "Accidentally downgrade by inspecting" doesn't arise in the actual design.

4. **[Moderate] approved_at clearing discards historical evidence.** T4 questions whether source_agent + updated_at is enough for corruption diagnosis. The position declares the cost away without engaging the audit gap.

5. **[Moderate] Pending hard-delete creates observability collapse.** "Not found" merges deleted-after-list, wrong-id, and never-existed. Dismissed without evidence of acceptable risk.

6. **[Moderate] Content limit framing is wrong.** D22 is locked and later than T5. D8 values entry splitting. The "conflict" doesn't exist. Unit-of-knowledge assumption contradicts D8.

7. **[Moderate] Scope model overclaims.** Internal model ≠ observable system semantics. recall_memory consumers see no metadata about scope.

Blind spots: activation risk absent, no path for "needs work" pending entries, recall-side observability gap.

### Refinements Applied

**Challenge 1 — accepted, position revised.** The collision is real. Resolution: curate_memory on pending entries requires scope_agents as mandatory for THAT transition. Reconciles D29 (always curated), D18 (scope gate), and D30 (partial update on other fields). For curated→curated edits, scope_agents remains optional. "Needs work" path: curator deletes pending (hard) and agent re-stores, OR curator provides scope + content in one call.

**Challenge 2 — accepted, position sharpened.** Explicit mutable-field set defined: {title, content, categories, confidence, scope_agents}. System-managed fields excluded from comparison. Normalization rules specified: sorted sets for scope_agents and categories, trailing-whitespace trim for content, exact equality for confidence and title.

**Challenge 3 — partially accepted.** Inspection scenario is a straw man (read_memory exists). Underlying value-comparison principle retained for idempotent-safety: identical resubmission must not downgrade.

**Challenge 4 — partially accepted.** Clearing is semantically correct. Acknowledged audit gap. Mitigation: git batch commits (D25) preserve previous approved_at in history. Recoverable but not convenient. Noted as acceptable for launch with post-launch escape hatch (additive field).

**Challenge 5 — acknowledged, position softened.** Observability collapse is real in theory. Error response SHOULD distinguish "not found" from generic states where possible. For pending hard-deletes specifically, "not found" is the only possible response (no record to reference). Formal tombstones contradict D25 intent.

**Challenge 6 — accepted, position withdrawn.** D22 supersedes T5. D8 splitting philosophy makes 1KB correct. Reframed: validation error message must teach splitting, not just reject.

**Challenge 7 — accepted, position refined.** Separated internal correctness (maintained) from observable-system claim (withdrawn). Consumers operate in intentional ignorance of scope (D27 design choice). Curator has full metadata via read_memory.

### Post-Refinement Assessment

The two critical gaps remain critical — they are genuine under-specifications in the locked decisions, not merely my interpretation. The Critic confirmed them as real collisions rather than challenging the diagnosis. All moderate challenges improved precision without invalidating the core position.

**Confidence: 0.80** (up from initial ~0.65 after sharpening comparison domain and resolving the atomicity question)
