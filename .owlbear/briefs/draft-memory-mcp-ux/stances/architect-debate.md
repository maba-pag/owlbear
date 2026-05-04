# Architect Debate Log — Memory MCP Tool UX Refactor

**Cycles:** 2  
**Final confidence:** 0.78 (initial 0.82 draft → 0.72 after Cycle 1 → 0.78 stabilized after Cycle 2)

---

## Cycle 1

### Draft Position

Core claim: design is structurally sound, 7-tool surface correctly maps 3 actors with clean schema separation. Defended all five critic findings. Additionally identified `recall_memory` wildcard as a flaw, endorsed hidden body limit as correct, accepted missing `modified_by` on YAGNI grounds.

### Critic Challenges (severity: critical ×2, moderate ×3)

**C1 (critical): Deletion semantics contradiction.** Synthesis says "no hard-delete via MCP" (C7). D19 says "pending = hard-delete." The artifacts are inconsistent. Position claimed the design is settled when the packet itself isn't internally stable.

**Response:** Accepted. D19 supersedes synthesis C7 (synthesis was written before D19). The contradiction is real in the artifacts but resolved in the decision record. Added: "synthesis needs reconciliation" to the final stance. The design IS settled — the documentation is not.

**C2 (critical): Hidden body limit contradicts stated problem.** Context §3 says the anti-pattern is "constraints enforced but not exposed in tool descriptions." D22 reintroduces exactly this. Position endorsed the reintroduction.

**Response:** Accepted. Genuine blind spot — defended a design choice that violates the brief's own minimum-acceptable-outcome. Revised: flagged as design consistency gap. Recommended stating the limit in the description as a quality signal rather than hiding it.

**C3 (moderate): Wildcard contradicts core assessment.** Position claimed "clean schema separation" while simultaneously identifying a multiplexing flaw in the same tool. Inconsistent framing.

**Response:** Accepted. Revised core assessment to acknowledge the flaw explicitly. Elevated from side note to one of three structural issues.

**C4 (moderate): modified_by reasoning under-evidenced.** Data stance considers it architecturally correct but blocked by identity loss.

**Response:** Rebutted. After D10, `modified_by` would be self-reported and constant ("memory-curator" on every mutation). Zero information content. This isn't YAGNI — it's "field carries no signal in this system." Strengthened the argument with the zero-information reasoning.

**C5 (moderate): Unconditional downgrade cost claim unsupported.** System is dormant — "one re-approval" is speculative.

**Response:** Partially accepted. Acknowledged this is a bet. Maintained position: (a) alternative adds guaranteed complexity, (b) both options speculative in dormant system, (c) simpler option preferred when evidence absent.

**Blind spots identified:**
- Activation safety (evaluating steady-state only)
- Implementation delta (current code ≠ target design)
- Source-of-truth drift across artifacts

**Response:** Incorporated activation safety. Implementation delta acknowledged as expected (redesign). Artifact drift flagged for mediator.

### Post-Cycle-1 Confidence: 0.72

---

## Cycle 2

### Revised Position

Clarified identity model as self-declared routing metadata. Added tool-visibility specificity concern. Acknowledged kill-switch limitation. Took position on recall_memory body-only payload.

### Critic Challenges (severity: critical ×2, moderate ×1)

**C1 (critical): Self-declared identity undermines wildcard removal.** Removing "*" doesn't prevent one agent from querying as another. Pattern validation only constrains syntax, not honesty.

**Response:** Accepted characterization, maintained recommendation. D10 frames this as "accident prevention." Removing "*" prevents accidental unscoped queries (agent finds wildcard in docs and uses it). Doesn't prevent deliberate lying — nothing can. Fix is consistent with D10's threat model. Clarified in identity model section.

**C2 (critical): `ob-memory/*` exposes entire server surface.** Tool-visibility shorthand in the brief breaks the separation model at the registration layer. General agents wired with `ob-memory/*` see curator tools.

**Response:** Accepted. Strongest new finding. The fix is trivial (enumerate specific tools in tools: arrays) but the brief MUST state it explicitly. Elevated to structural issue #1.

**C3 (moderate): Kill-switch is shutdown, not rollback.** Removing tools disables MCP memory without restoring vscode/memory.

**Response:** Accepted characterization. Maintained acceptability: memory is enhancement, not dependency. Agents functioned without it. "Dead zone" (no memory) is bounded in duration and non-critical. Recommended staged activation even without formal gate.

**Blind spots identified:**
- Read-payload asymmetry (D27 body-only vs structured write)
- source_agent as routing metadata, not provenance
- User actor mediated through agent layer

**Response:** All incorporated. D27 body-only correct for pre-flight injection. source_agent reframed as routing metadata. "3 actors" reframed as "3 tool-design audiences with visibility-enforced boundaries."

### Post-Cycle-2 Confidence: 0.78

---

## Exit Condition

Position solid after 2 cycles. Core structural issues identified and resolved. Remaining uncertainty is activation sequencing — real but bounded because memory is non-critical.

---

## Items Flagged for Mediator

1. D22 body-limit hiding conflicts with brief's minimum-acceptable-outcome — needs decision.
2. Synthesis.md stale on D19, D16, D24 — reconcile before brief drafting.
3. `ob-memory/*` shorthand must become explicit tool enumeration in implementation spec.
4. Staged activation recommended despite D26 "no formal gate" — advisory.
