# Synthesis — Memory MCP Tool UX Refactor (Panel 2)

**Mode:** converge | **Active stances:** architect, data, enduser, security  
**Panel run:** 2 (post-design-expansion; D14–D30 locked)  
**Date:** 2026-05-04

---

## Summary

With 30 decisions now locked, the design is substantially complete. The four panelists converge strongly on the expanded model: 7-tool surface (2 general, 4 curator, 1 user), auto-state logic on `curate_memory`, state-dependent deletion, scope-as-curation-gate, and atomic consumer update. Three user-locked decisions (D22 hidden body limit, D27 body-only recall, D26 no formal cutover gate) draw explicit opposition from 3–4 panelists each — these are flagged as tensions but remain locked per user authority.

The panel surfaced two critical implementation under-specifications (scope gate atomicity and auto-downgrade comparison domain) that require resolution in the implementation contract before coding begins.

---

## Convergences

### C1 — 7-tool surface with 3 audiences (4/4)

All stances accept the final tool set: `save_memory` + `recall_memory` (general), `list_memories` + `read_memory` + `curate_memory` + `delete_memory` (curator), `approve_memory` (user). Schema-enforced audience separation via `tools:` arrays.

**Sources:** architect §structural-reasoning, data §schema, enduser §1, security §R1

### C2 — Per-tool wiring, NOT server wildcard (4/4)

All four stances explicitly flag `ob-memory/*` as dangerous. General agents MUST list `ob-memory/save_memory, ob-memory/recall_memory`. Curator lists the full set. Wildcard wiring collapses audience separation entirely.

**Sources:** architect §1 (structural issue), enduser §4, security §R1 (CRITICAL), data (implicit via schema separation)

### C3 — `curate_memory` auto-state logic (4/4)

All accept D29: `curate_memory` always results in `curated` state. pending→curated (promote), curated→curated (stay), approved→curated (downgrade). No agent-controlled state parameter.

**Sources:** architect §state-machine, data §transitions, enduser §5, security §R7

### C4 — Scope gate: `pending→curated` rejects if `scope_agents=[]` (4/4)

All accept D18's validation gate. Unscoped entries cannot leave pending state. This is the critical data-integrity invariant.

**Sources:** architect §1 (conditional required param), data §critical-gap (D18/D29/D30 resolution), enduser §implicit, security §least-privilege-4

### C5 — State-dependent deletion (4/4)

All accept D19: pending → hard-delete (file removed, never committed), curated/approved → soft-delete (state=deleted, file retained, terminal). No recovery from deleted state.

**Sources:** architect §deletion-semantics, data §deletion-model, enduser §implicit, security §R6

### C6 — `modified_by` correctly dropped (3/4)

Architect, data, and security agree: post-D10, `modified_by` would be self-reported and constant ("memory-curator"). Zero information content. Only one curator exists.

**Sources:** architect §modified_by-omission, data §schema (dropped per D21), security §R4

### C7 — `source_agent` required + immutable (4/4)

All agree on D21's `source_agent` as creation-time provenance. Serves curation routing and audit trail. Self-reported is acceptable for single-user threat model.

**Sources:** architect §identity-model, data §field-set, enduser §6, security §R4

### C8 — Guidance hints on mutations (3/4)

Architect, enduser, and data support actionable return messages from mutating operations. Enduser provides a full 7-operation hint table. Pattern already proven in kanban MCP.

**Sources:** enduser §7, architect §implicit, data §implicit (actionable error messages)

### C9 — Activation must sequence curator BEFORE general agents (3/4)

Enduser, security, and architect agree: wiring general agents to `save_memory` before the curator is functional creates a pending-entry backlog with no review path. Curator wiring + verification must precede general agent activation.

**Sources:** enduser §8, security §R2, architect §warning-2

### C10 — Consumer instruction update must be atomic with tool rename (3/4)

Enduser, architect, and security flag that 7 consumer artifacts reference the old tool names. If instructions still say `store_learning(scope_agents=[...])`, agents fail regardless of schema quality.

**Sources:** enduser §6 (expanded), architect §warning-1 (artifact drift), security §warning-4

### C11 — D18/D29/D30 scope gate requires spec clarification (3/4)

Architect, data, and security identify that the three decisions create an ambiguous contract for pending entries. Resolution: `scope_agents` is a conditional-required parameter — required when target is `pending`, optional (partial-update) when target is already `curated` or `approved`.

**Sources:** architect §1 (conditional required param), data §critical-gap, security §least-privilege-4

### C12 — Auto-downgrade needs normalization rules (2/4, strong signal)

Data provides explicit normalization spec (sort sets, trim whitespace, exact float equality). Architect agrees unconditional downgrade is simpler (skip comparison entirely). These are two valid implementation paths — either must be specified, not left ambiguous.

**Sources:** data §critical-gap-2, architect §trade-offs (unconditional)

---

## Tensions with User-Locked Decisions

### T1 — D22: Hidden 1KB body limit (3/4 oppose user choice)

| Stance | Position |
|--------|----------|
| **architect** | OPPOSE. "Contradicts the brief's problem statement. State the constraint in the tool description." |
| **data** | ACCEPT with caveat. "Validation error must teach splitting (D8 philosophy), not just reject." |
| **enduser** | STRONG OPPOSE. "Recreates the EXACT defect the brief identifies. Fix agent verbosity in instructions, not by hiding tool constraints." |
| **security** | OPPOSE. "Design-hostility — the exact pattern the brief set out to eliminate. Incoherent design." |

**User decision (locked):** 1KB limit NOT in tool description. Only in validation error.

**Nature of tension:** The brief's problem statement §3 explicitly identifies hidden Pydantic constraints as the anti-pattern being fixed. D22 reintroduces a hidden constraint. 3/4 panelists call this philosophically incoherent. The user rationale — prevent "fill the budget" behavior — is an instruction-level concern per enduser's analysis.

**Recommended position:** Expose the limit. One line in the tool description: `"content: concise single-topic note, max 1000 characters"`. This costs nothing and eliminates a guaranteed first-call failure for agents with thorough lessons. The anti-gaming goal is better served by pipeline instructions ("be concise, focus on atomic lessons") than by hiding a tool constraint.

**Confidence: 0.82** — Strong panel consensus, strong logical argument. But user has already weighed this and chosen to keep hidden. Respect the lock.

### T2 — D27: `recall_memory` returns body only (2/4 oppose, 1 conditional)

| Stance | Position |
|--------|----------|
| **architect** | ACCEPT. "Architecturally correct. Agents need knowledge, not curation metadata." |
| **data** | ACCEPT. "Scope serves the curator's routing function, not the consumer's self-awareness." |
| **enduser** | CONDITIONAL ACCEPT → opposes on confidence. "Stripping confidence removes the ONLY tiebreaker when entries contradict." |
| **security** | ACCEPT. "Consumers don't need provenance — they need the knowledge." |

**User decision (locked):** Body only. No metadata, no confidence.

**Nature of tension:** Enduser makes a specific functional argument: when `recall_memory` returns multiple entries and two contradict, the consuming agent has no basis to prefer one over another without confidence scores. This is an information-theoretic argument, not a metadata-management one.

**Recommended position:** Include confidence in the recall format (as title annotation: `## Entry Title (confidence: 0.85)`). This is one field, zero schema complexity, and solves the contradiction-tiebreaker problem without exposing management metadata. Categories, state, timestamps, and IDs remain excluded.

**Confidence: 0.65** — Only enduser opposes, and the architect's counter ("agents need knowledge not metadata") is legitimate. The tiebreaker scenario may be rare in practice. Respect the lock.

### T3 — D26: No formal cutover gate (2/4 flag risk)

| Stance | Position |
|--------|----------|
| **architect** | ACCEPT with caveat. "Staged activation (curator first, verify, then pipeline agents) even without a formal gate." |
| **data** | Not addressed directly. |
| **enduser** | FLAGS RISK. "If general agents start calling save_memory before the curator is wired, pending entries accumulate with no review path." |
| **security** | STRONG OPPOSE. "Removes a working system before the replacement is proven. Prove it works with 2-3 agents first." |

**User decision (locked):** No formal gate. User controls big-bang timing.

**Nature of tension:** Security's argument is strongest: D12 (big-bang replacement) + D26 (no gate) means removing the ONLY working memory system without evidence the replacement executes end-to-end. The curator agent currently CANNOT call MCP memory tools (research F2). If activation proceeds before the curator is functional, pending entries pile up with no review path.

**Recommended position:** Accept D26 (no formal gate document) but sequence activation per C9: curator wiring + lifecycle proof → 2-3 pilot agents → full pipeline rollout. This gives the user informal validation without bureaucratic gate artifacts. The KEY requirement: do not wire general agents before the curator's curate lifecycle has executed at least once.

**Confidence: 0.78** — The sequencing recommendation is compatible with D26 (no formal gate ≠ no sequencing). Security's 4-condition checklist can be an implementation task's AC without being a separate gate document.

---

## New Design Clarifications from Panel

### NC1 — Scope Gate Atomicity (architect + data)

`curate_memory` on a pending entry WITHOUT `scope_agents` → entire call fails atomically. Error: "Pending entry requires scope_agents for promotion to curated." The call never partially executes. This reconciles D18 (scope gate), D29 (always→curated), and D30 (partial-update) without contradiction.

For curated/approved entries, `scope_agents` follows D30's partial-update semantics (None = no change).

**Implementation contract:** Validate all fields before applying any. Standard all-or-nothing write semantics.

### NC2 — Auto-Downgrade: Two Valid Paths (architect vs. data)

| Approach | Advocate | Trade-off |
|----------|----------|-----------|
| **Unconditional** | architect | Any `curate_memory` call on approved entry → curated. No equality check. Simpler. Cost = one re-approval if no-op edit. |
| **Normalized comparison** | data | Compare mutable field set after normalization. Identical resubmission = no state change (idempotent). Complex but precise. |

Both are valid. The unconditional approach is simpler to implement and audit. The comparison approach prevents spurious re-approval cycles. **Pick one and specify it** — do not leave ambiguous.

Data's normalization rules if comparison path is chosen: sort sets for scope/categories, trim trailing whitespace for content, exact float equality for confidence, exact string for title.

### NC3 — Wildcard `"*"` on `recall_memory` (architect + security)

Architect: remove `"*"` entirely from `recall_memory` — the tool should validate that `agent` matches a specific agent-name pattern and reject wildcards. The curator already has `list_memories` + `read_memory` for unscoped access.

Security: if `"*"` stays, document it as CURATOR-ONLY in the parameter's JSON Schema description, not just in external docs.

**Panel position:** Block `"*"` at the code level. The curator has dedicated unscoped tools — a scope-bypass parameter on the ONE tool all agents see is a design contradiction (architect) and a structural inconsistency in the access model (security).

### NC4 — Activation Sequence (enduser + security)

Required order:
1. Wire curator agent with 4 curator tools → verify curate lifecycle executes end-to-end
2. Create `memory-review.prompt.md` → verify user approval flow
3. Wire 2-3 pilot agents with `save_memory` + `recall_memory` → verify entries flow through full lifecycle
4. Wire remaining pipeline agents + update consumer instructions atomically

Step 3 MUST NOT precede step 1. This is compatible with D26 (no formal gate) — it's sequencing, not a gate document.

### NC5 — Validation Error Must Teach (data + enduser)

When `save_memory` rejects for body exceeding 1KB, the error message must guide the agent to split by category (per D8 philosophy), not just reject with a size number. Example: "Content exceeds 1KB limit. Split into separate entries per category — if content spans multiple categories, each deserves its own entry."

### NC6 — Self-Declared Identity is the Ceiling (architect)

No design decision in this system achieves stronger-than-self-reported identity. `source_agent`, `agent` parameter on recall, and tool-visibility are all convention enforcement — not verified provenance. This is explicitly acceptable for the single-user threat model (D10). Document this as a known architectural boundary, not a bug.

### NC7 — Artifact Drift Warning (architect)

The existing synthesis (this document, pre-update) was stale on: deletion semantics (pre-D19), curator tool shape (pre-D16), category names (pre-D24), and body-limit scope (pre-D22). Decisions.md is always authoritative. Implementation must reference decisions.md directly, not intermediate synthesis artifacts.

---

## Resolved Open Questions (from Panel 1)

| # | Question | Resolution |
|---|----------|-----------|
| Q1 | Curator tool surface shape | **D16:** 4 MCP tools (list, read, curate, delete). Resolved. |
| Q2 | Category enum names | **D24:** 3 renamed (tool-usage, domain-knowledge, env-context). Resolved. |
| Q3 | Return payload from recall | **D27:** Body only (with title as heading). Locked. |
| Q4 | Cutover readiness gate | **D26:** No formal gate. Locked. (Panel recommends informal sequencing per NC4.) |
| Q5 | `intended_for` storage | **D18:** `intended_for` omitted entirely. Scope is curator-only. Resolved. |

---

## Remaining Open Questions

### Q1 — Auto-downgrade: unconditional vs. normalized comparison?

NC2 identifies two valid implementation paths. Unconditional is simpler (architect recommends). Normalized comparison is more precise (data recommends). Both work. Pick one.

**Recommendation:** Unconditional. Bounded cost (one extra re-approval for no-op edits). The curator shouldn't call `curate_memory` on approved entries without intent. Equality checking on YAML+markdown content is non-trivial to get right and adds a normalization surface for bugs.

### Q2 — `"*"` wildcard: code-block or document-only?

NC3 panel position is "code-block." If user prefers to keep the backdoor for curator convenience, document in schema description. Either way, specify.

**Recommendation:** Code-block. Curator has `list_memories` + `read_memory` — no functional gap from removing `"*"`.

### Q3 — Soft-delete accumulation / garbage collection

Data flags that soft-deleted entries accumulate on disk without defined pruning. Low priority (zero data, single-user), but should be a backlog item.

**Recommendation:** Backlog task. No launch blocker.

---

## Recommendation

**Confidence: 0.82**

The design is implementation-ready. The 30 locked decisions define a complete, principled system with strong panel consensus on structure. The three user-locked tensions (D22, D27, D26) are acknowledged as intentional trade-offs — panelists disagree but the design functions either way.

**Before implementation begins, resolve:**
1. Auto-downgrade path (Q1) — recommend unconditional
2. Wildcard handling (Q2) — recommend code-block
3. Specify NC1 (scope gate atomicity) in the implementation task's AC

**Ship with confidence on:** Tool surface, naming, state machine, deletion model, scope semantics, consumer update plan, activation sequence. These have full or near-full convergence and clear implementation contracts.
