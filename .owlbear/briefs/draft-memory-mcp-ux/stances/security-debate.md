# Security Debate Log — Memory MCP Tool UX Refactor (Full Design)

## Cycle 1

### Initial Position (pre-Critic)

1. **Access Control (D10):** ACCEPTABLE. tools: array wiring is coherent for threat model. Blast radius of spoofing = wrong source_agent on pending entry, caught by curation.
2. **Identity Coherence:** NOT a contradiction. source_agent is provenance/routing, not authorization. Honor system with curation oversight.
3. **Deletion Safety:** ACCEPTABLE. Hard-delete of pending = garbage collection of unreviewed input. Soft-delete of curated/approved preserves audit trail.
4. **Scope as Routing:** CORRECT framing. Worst-case bypass = agent sees irrelevant entries. Explicitly not access control.
5. **Hidden 1KB Limit:** ACCEPTABLE anti-gaming measure. Poor failure UX but not security-through-obscurity.
6. **Big-Bang Transition:** HIGHEST RISK. Simultaneous activation + fallback removal. Recommend staged rollout.
7. **Data Provenance:** ADEQUATE. source_agent + auto-state logic + timestamps = reconstructable history.
8. **Auto-Downgrade:** STRONG security property. Code-enforced invariant prevents stale approvals.
9. **Wildcard Wiring:** REAL CONCERN. ob-memory/* exposes all tools to any wired agent.

### Critic Challenges (Cycle 1)

**Challenge 1 — Cross-scope blast radius understated (severity: critical)**
Scope filtering IS enforced in code, not just routing. Any memory-enabled agent can call recall_memory with any agent name. Blast radius is broader than "wrong source_agent" — it includes cross-scope recall by any memory-enabled agent.

**Challenge 2 — Self-reported source_agent trust (severity: critical)**
source_agent serves curation routing AND audit trail AND provenance. Spoofed source_agent distorts the only actor-like field. Downstream agents can't challenge it (recall strips metadata).

**Challenge 3 — D19 vs C7 inconsistency on hard-delete (severity: moderate)**
Synthesis C7 says "No hard-delete via MCP" but D19 says pending entries are hard-deleted.

**Challenge 4 — Hidden 1KB contradicts problem statement (severity: moderate)**
Context §3 identifies hidden constraints as THE problem. D22 deliberately creates a new hidden constraint. This is incoherent.

**Challenge 5 — Big-bang risk understated (severity: critical)**
Curator can't even call MCP tools. The lifecycle has never executed. This isn't "remove fallback after validation" — it's "remove the only working system on faith."

**Challenge 6 — Audit trail overclaimed (severity: critical)**
Auto-downgrade isn't shipped. modified_by is dropped. "State machine IS the audit trail" is stronger than what exists.

**Challenge 7 — Wildcard wiring is a contradiction not just a concern (severity: critical)**
C1 claims audience separation. Current wiring uses ob-memory/* which exposes everything. The claim is architecturally unfounded.

### Blind Spots Identified

- Cross-scope recall surface: any agent can pass any name to recall_memory
- Curator not MCP-capable means lifecycle proof is impossible today
- Recall payload strips metadata — consumers cannot verify provenance post-recall
- Shipped code vs design intent not separated — several cited controls don't exist yet
- D19/C7 deletion semantics not fully reconciled in brief artifacts

### Response and Refinement

**Challenge 1 (cross-scope):** PARTIALLY ACCEPTED. Blast radius IS broader than initially stated — any agent with ob-memory/* can read any scoped entry by passing a different agent name. But the THREAT MODEL explicitly says this is accident prevention, not adversarial access control. Worst outcome = "agent gets irrelevant entries." Adjusting to acknowledge full read surface while maintaining ACCEPTABLE for threat model.

**Challenge 2 (source_agent trust):** PARTIALLY ACCEPTED. source_agent is more load-bearing than just routing. But: (a) recall strips metadata, so consumers never SEE source_agent — can't be misled, (b) only curator sees it and evaluates content regardless, (c) in single-user system, spoofing requires prompt injection, at which point source_agent is the least dangerous action. Maintaining ACCEPTABLE with explicit trust assumption documented.

**Challenge 3 (D19 vs C7):** ACCEPTED. Real inconsistency in brief artifacts. D19 is authoritative (decisions override synthesis). Adding explicit note that D19 governs; C7 describes curated/approved behavior only.

**Challenge 4 (hidden 1KB):** ACCEPTED. Genuine philosophical contradiction. Brief's purpose = eliminate "cryptic validation errors from hidden constraints." D22 creates one. Upgrading from "acceptable but poor UX" to "incoherent design choice."

**Challenge 5 (big-bang):** ACCEPTED. Significantly strengthened. Not just "if recall_memory has a bug" but "entire lifecycle mechanism never proven AND executor not wired." This is highest-priority recommendation.

**Challenge 6 (audit overclaim):** ACCEPTED. Separated design intent from shipped reality throughout. Auto-downgrade IS strong — as a design property, not as current code.

**Challenge 7 (wildcard contradiction):** ACCEPTED. Upgraded from "real concern" to "structural contradiction." The design claims a property (audience separation) that its own activation mechanism (ob-memory/*) defeats.

### Refinements Applied

1. Separated "cross-scope recall" as its own risk item (R3), distinct from access control adequacy
2. Wildcard wiring elevated to R1 (CRITICAL) — structural contradiction, not just concern
3. Big-bang elevated with explicit failure chain: curator not wired → lifecycle unproven → fallback removed
4. Hidden limit marked as design contradiction, not just poor UX
5. Added shipped-vs-designed caveat to auto-downgrade (R7)
6. Maintained ACCEPTABLE rating for identity model and deletion semantics — Critic challenges were valid observations but don't change the threat-model-appropriate conclusion

### Position After Cycle 1

Confidence: 0.82 (up from initial ~0.70 — the Critic forced sharper framing on the three critical items, making the stance more defensible by being more precise about what's a concern vs. what's acceptable)

Exit rationale: Position is now precise about the three structural issues (wildcard wiring, big-bang, hidden limit) and explicit about why other items are acceptable for the threat model. Further Critic cycles would refine phrasing but not change the assessment.
