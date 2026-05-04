# Security Stance — Memory MCP Tool UX Refactor (Full Design)

## Security Stance

The design is coherent for its stated threat model (accident prevention, single-user laptop) but contains three structural contradictions that must be resolved before implementation: (1) audience separation is claimed but structurally unenforceable with current wildcard wiring, (2) the hidden body limit reproduces the exact problem the brief set out to fix, and (3) the big-bang cutover removes the only proven system without evidence the replacement works. The remaining design choices — self-reported identity, scope-as-routing, state-dependent deletion, auto-downgrade — are acceptable given the threat model, with explicit caveats documented below.

---

## Risk Assessment

### R1 — Wildcard Tool Wiring Defeats Audience Separation (CRITICAL)

The design claims schema-enforced audience separation (C1: "different tools, different schemas = impossible to accidentally query pending entries"). D5 gives general agents 2 tools; D16 gives curator 4 tools. This split is the core security property.

**The structural contradiction:** Both tool sets live on one MCP server (`ob-memory`). Existing agents use `ob-memory/*` wildcard wiring (confirmed: test-writer, test-curator). D12's activation model gives all pipeline agents `ob-memory/*`. This exposes ALL server tools — including `curate_memory`, `delete_memory` — to every wired agent. The audience separation exists in design documents but not in the enforcement mechanism.

**Blast radius:** A general agent with `ob-memory/*` can call `curate_memory` to promote its own entries, bypassing the curation quality gate. It can call `delete_memory` to remove entries it disagrees with. The state machine constraints still apply (auto-downgrade, soft-delete), but the AUTHORITY model is broken — anyone can curate.

**Required mitigation:** Per-tool allowlisting in `tools:` arrays (e.g., `ob-memory/save_memory`, `ob-memory/recall_memory` for general agents; full set for curator). Wildcard `ob-memory/*` MUST NOT be the activation pattern for general agents. If VS Code MCP wiring doesn't support per-tool granularity, a server-level split is required (two server instances with different tool registrations).

### Per-option risk profile

### R2 — Big-Bang Cutover Without Lifecycle Proof (CRITICAL)

D12 removes `vscode/memory` simultaneously with `ob-memory/*` activation. D26 specifies no formal readiness gate. Research findings establish:

- The MCP memory lifecycle has NEVER executed end-to-end (F1)
- Only 2/12 agents are wired (F1)
- The memory-curator agent CANNOT call MCP memory tools (F2) — it uses `vscode/memory` only
- The file-based path is the ONLY working system (F4)

The big-bang therefore removes a proven capture-curate-approve loop and replaces it with an untested one where the curator isn't even wired to execute. This is not "remove fallback after validating replacement" — it is "remove the only working system on faith."

**Blast radius:** If any tool in the new system has a bug (schema validation error, scope filtering regression, state machine defect), ALL 12+ pipeline agents lose memory capability simultaneously. The curator — already unable to call MCP tools — cannot recover the situation. Rollback requires re-adding `vscode/memory` to every agent's tools: array.

**Required mitigation:** Staged validation gate before big-bang:
1. Wire curator agent to `ob-memory/*` tools and prove the curate lifecycle executes (pending→curated→approved)
2. Activate 2-3 agents (e.g., test-writer, builder) and confirm entries flow through the full lifecycle
3. Validate recall_memory returns correct scoped results after curation
4. Only THEN remove `vscode/memory` from remaining agents

### R3 — Cross-Scope Recall (MODERATE)

D15 makes `agent` parameter required on `recall_memory`, but the value is caller-supplied. An agent calling `recall_memory(agent="curator")` sees curator-scoped entries. The `"*"` wildcard (documented only in curator instructions per D15) returns all entries regardless of scope.

**Assessment:** This is routing, not security (D10's explicit framing). The threat model says adversarial access isn't in scope. The worst outcome of cross-scope recall is "agent gets irrelevant entries in context." For the stated threat model, this is ACCEPTABLE. The `"*"` wildcard documentation-gating is adequate — agents won't discover it without being instructed to use it.

**Residual risk:** If future agents are trained with the wildcard pattern (from reading the source code or h-mcp-memory skill), scope isolation degrades. Document the wildcard as CURATOR-ONLY in the tool schema's parameter description, not just in external docs.

### R4 — Self-Reported Identity Without Verification (LOW)

D10 removes server-side identity. D21 adds `source_agent` as required/immutable/self-reported. No mechanism verifies the claim.

**Assessment:** The system never gates access decisions on `source_agent`. It serves: (a) curation routing — curator sees who wrote it, (b) audit trail — reconstruct entry origin. A spoofed source_agent means the curator routes incorrectly and the audit trail is wrong. Both are recoverable at curation time (curator reads the content regardless).

**Why this is acceptable:** In a single-user laptop system where all agents run under the same user's control, "agent lies about its name" isn't a meaningful attack vector. The agents are code the user deployed. If one is compromised (prompt injection), `source_agent` spoofing is the least of the problems — the attacker already has tool access.

**Caveat:** D27's body-only recall payload strips metadata. Post-recall, no consumer can verify provenance. This is fine because consumers don't NEED provenance — they need the knowledge. Provenance matters only to the curator.

### R5 — Hidden Body Limit Contradiction (MODERATE)

D22 deliberately hides the 1KB limit from tool descriptions ("only in validation error message"). The stated goal: prevent "fill the budget" agent behavior.

**The contradiction:** The problem statement (context.md §3) identifies "valid categories, confidence range, state transitions, and default query behavior are enforced by Pydantic but not exposed in tool descriptions" as a core problem. "Agents fail on first call with cryptic validation errors." D22 then deliberately creates a new hidden constraint with a cryptic validation error.

**Assessment:** This is not security-through-obscurity (the limit serves UX, not security). But it IS design-hostility — the exact pattern the brief set out to eliminate. The anti-gaming argument is weak: agents that "fill the budget" would write bad entries regardless of knowing the limit, and the curation step catches them.

**Recommendation:** Either expose the limit in the tool description (honest constraint) or remove it entirely and let the curator reject oversized entries. A hidden limit that reproduces the problem you're fixing is incoherent design.

### R6 — Deletion Semantics Internal Inconsistency (LOW)

D19 chooses hard-delete for pending entries. Synthesis C7 says "No hard-delete via MCP; that's a manual filesystem operation." These statements conflict on the surface.

**Resolution:** D19 is the authoritative decision. C7 likely refers to curated/approved entries (soft-delete is the only option for those). The `delete_memory` tool's behavior is state-dependent: pending → physical removal, curated/approved → mark deleted. This is the correct design — uncommitted garbage should not persist.

**Residual risk:** Zero audit trail for hard-deleted pending entries. An entry created, deleted, never curated — leaves no trace. This is ACCEPTABLE: pending entries are unreviewed input that never entered git. Their absence is expected state.

### R7 — Auto-Downgrade: Design Intent vs. Shipped Reality (LOW)

D20 specifies code-enforced auto-downgrade (approved + edit → curated). D29 specifies curate_memory always results in `curated` state. These are strong security properties.

**Caveat:** These properties do not exist in shipped code today. The current implementation rejects approved-entry edits outright rather than downgrading. The auto-downgrade is design intent awaiting implementation. This stance evaluates the DESIGN, not current code — but implementation must be verified against these constraints before activation.

---

## Compliance Implications

No regulatory compliance applies (single-user laptop, no PII, no external data flows). The relevant compliance is internal architectural contracts:

- **D4 (lifecycle is load-bearing):** Enforceable only if mutation tools run all state transitions through code. Wildcard wiring (R1) threatens this.
- **D20 (auto-downgrade code-enforced):** Requires curate_memory to implement the downgrade logic. If curator bypasses MCP (via filesystem), this constraint is advisory.
- **D25 (git commits via curator batch):** Hard-deleted pending entries never enter git — this is correct. Soft-deleted entries remain on disk — git history reflects their lifecycle.

---

## Least-Privilege Recommendations

1. **Per-tool wiring, not server wildcard.** General agents: `ob-memory/save_memory`, `ob-memory/recall_memory`. Curator: full set. This is the minimum viable audience separation. If VS Code doesn't support per-tool MCP wiring, split into two server instances.

2. **Curator filesystem write access: REMOVE after MCP activation.** Once the curator has `ob-memory/*` for mutations, remove `vscode/memory` write capability for the memory data directory. The bypass must be absent, not merely unused.

3. **Wildcard `"*"` on recall_memory: document as curator-only in schema.** Add to the parameter description: "Use '*' only from curator workflows. General agents must pass their own agent name." This is convention enforcement, not code enforcement — acceptable for the threat model.

4. **curate_memory action bounds: constrain to lifecycle edges.** The tool must not accept arbitrary state-to-state transitions. Valid edges only: pending→curated, curated→curated, approved→curated (auto-downgrade). No pending→approved shortcut. No curated→pending regression.

5. **Big-bang gate: prove lifecycle before cutting over.** The 4-condition operational readiness gate is the minimum: curator wired, lifecycle executed end-to-end, scoped recall validated, docs updated.

---

## Warnings

1. **The audience separation claim is currently UNENFORCEABLE.** Until per-tool wiring or server split is implemented, `ob-memory/*` exposes all tools to all agents. Shipping with wildcard wiring defeats the design's core access model. This is not a future concern — it's the current wiring pattern for the only two agents already activated.

2. **The big-bang removes a working system before the replacement is proven.** No amount of design quality compensates for activating an untested system while simultaneously removing the fallback. Prove it works with 2-3 agents first.

3. **The hidden 1KB limit is philosophically incoherent with the brief's stated purpose.** Either own the constraint publicly or remove it.

4. **Design properties ≠ shipped properties.** Auto-downgrade, soft-delete, scope filtering, state machine constraints — these are DESIGN decisions. Implementation must be verified against each before activation. The current code does not implement all of them.

---

## Confidence

**0.82**

The design is sound for its threat model. The three structural issues (wildcard wiring, big-bang risk, hidden limit) are real but resolvable — they are implementation/rollout decisions, not architectural flaws. The identity model, deletion semantics, scope model, and auto-downgrade are all coherent choices for accident-prevention security on a single-user system. Refined through one Critic cycle that correctly identified the shipped-vs-designed distinction and the wildcard wiring contradiction.
