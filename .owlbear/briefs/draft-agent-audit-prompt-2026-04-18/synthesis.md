# Synthesis — Agent-Audit Prompt Rewrite

**Pragmatist synthesis | Inputs:** context.md, stance-architect.md, stance-enduser.md
**Confidence:** 0.90

---

## Convergences

Both panelists agree on the following — these form the backbone of the recommendation.

1. **Rewrite, not patch.** Both panelists reject in-place patching. Architect: "gaps touch every section." End-User: the two conflicting output formats must be eliminated, not merged. *(Architect, End-User)*

2. **7 audit dimensions (6 existing + Memory Governance).** Both treat memory as a first-class dimension, not folded into Content Placement. Architect cites unique governance rules; End-User specifies a distinct evidence shape for memory entries. *(Architect, End-User)*

3. **Continuous one-finding-at-a-time loop.** Scan → present finding → askQuestions → fix → verify → next. Both explicitly discard the batch FINDINGS/REMEDIATION PLAN format. *(Architect, End-User)*

4. **askQuestions on every user-facing turn.** Non-negotiable behavioral rule. Both panelists state this unconditionally. *(Architect, End-User)*

5. **Scan-first, then present.** Read all files before presenting any finding. Build prioritized queue, then work it. Architect: "can't prioritize without the full picture." End-User: "Do not present any finding until all files are read and the full queue is formed." *(Architect, End-User)*

6. **Three discovery surfaces (File, Memory, MCP).** Both agree on file-based + memory-file + MCP as distinct surfaces with graceful degradation when MCP is unavailable. *(Architect, End-User)*

7. **Severity-first ordering (HIGH → MED → LOW).** End-User defines it explicitly for fatigue mitigation; Architect's "prioritized findings queue" implies the same. *(Architect, End-User)*

8. **Dual-direction auditing (top-down + bottom-up).** Architect embeds negative-space probes per dimension. End-User's evidence shape for "Missing content" (governing rule + searched files + "not found") is the UX realization of the same idea. *(Architect, End-User)*

9. **Queue invalidation after structural fixes.** Both require re-evaluation of remaining findings when a fix resolves downstream issues. *(Architect, End-User)*

10. **"Run from the top again?" at queue exhaustion.** Both define a re-scan cycle. On re-run, fully fresh evaluation — no suppression. *(Architect, End-User)*

11. **Carry forward proven content.** Pipeline Integrity routing tables, dynamic file discovery, standards-first loading. Both respect the working baseline. *(Architect, End-User)*

12. **End-of-cycle holistic verification.** Both require pipeline traces, rejection-routing verification, and SNR spot-checks before the "run again?" prompt. *(Architect, End-User)*

---

## Disagreements

### D1: Finding Presentation Detail — Card Template vs. Structural Spec

- **End-User** prescribes a precise 5-section "card" (Header with progress indicator, Evidence, Options, Recommendation with confidence score, Approval via askQuestions) with explicit ceremony-scaling rules (Options section conditional on ambiguity, approval options scale with severity).
- **Architect** specifies "facts → options → recommendation → approval" carried forward from the current prompt but does not define a card template, progress indicators, severity rubric, or ceremony scaling.

**Nature:** Not a conflict — a gap. Architect's process section is structurally compatible with End-User's card. The card is a refinement of the Architect's protocol.

### D2: Acknowledged Deviations Persistence

- **End-User** introduces `.owlbear/audit/deviations.md` — a persistent file tracking intentional deviations with staleness re-evaluation on future runs.
- **Architect** has no equivalent mechanism. Findings are either fixed, skipped, or invalidated — all ephemeral.

**Nature:** Genuine addition. End-User argues this prevents re-litigating settled decisions across runs. Architect's model resurfaces everything on re-scan. Trade-off: durability vs. simplicity.

### D3: Phase Breaks Between Severity Tiers

- **End-User** specifies conditional phase breaks ("High-severity complete. 10 medium-severity findings next. Continue / Pause?") after each severity tier if the next tier has ≥3 findings.
- **Architect** has no equivalent — the loop runs continuously with per-finding askQuestions and a single end-of-cycle break.

**Nature:** UX detail absent from the architectural model. Adding phase breaks is additive and doesn't conflict with the Architect's control loop.

### D4: Instruction File Taxonomy — Stubs vs. Authority Files

- **Architect** identifies an explicit taxonomy gap: h-agent-structure defines "stubs" but not "authority instruction files." Proposes a pragmatic workaround (stubs get format checks; authority files get content checks; unclassified files get flagged).
- **End-User** does not address this distinction.

**Nature:** Architect-only concern. The audit prompt needs to encode this distinction or it will apply stub rules to authority files (false positives).

---

## Recommendation

**Write the prompt as a rewrite using the Architect's 5-section structure, populated with End-User's UX contracts.** Specifically:

| Section | Source |
|---------|--------|
| **Preamble** | Architect's role/stakes/behavioral contract + End-User's "rejection is safe" and "all evidence inline" trust signals |
| **Audit Surface & Standards** | Architect's three-surface model + loading order + instruction file taxonomy (stubs vs. authority) |
| **Audit Dimensions** | Architect's 7 dimensions with per-dimension negative-space probes + End-User's evidence-shape table for finding types |
| **Process** | Architect's scan→remediate→re-scan loop + End-User's card template, severity rubric, severity-first ordering, phase breaks, queue re-evaluation messaging, pause/bail UX, and acknowledged deviations |
| **Verification** | Architect's holistic checks + End-User's verification-surfaced-issue handling (address now / defer) and completion status table |

**Key implementation notes:**

- The End-User's card template (Header/Evidence/Options/Recommendation/Approval) is the canonical finding presentation format. It subsumes the Architect's "facts → options → recommendation → approval" with richer structure.
- End-User's severity rubric (HIGH/MED/LOW with criteria) is the ordering authority.
- End-User's ambiguity fixes (§6) are the executing-agent clarity layer — each one should be addressed in the relevant prompt section.
- Architect's memory governance heuristics (stale/contradictory/duplicated) need explicit inclusion since no authority defines thresholds.

---

## Open Questions

**Q1: Acknowledged Deviations — include or defer?** *(End-User)*
The `.owlbear/audit/deviations.md` mechanism adds cross-run memory for intentional deviations. It's useful but introduces a new persistent artifact and staleness logic. **Include in v1, or add later after the core loop is proven?** This is the only feature that creates a new file outside the prompt itself.

**Q2: Instruction file taxonomy — pragmatic workaround or fix the source?** *(Architect)*
The Architect identifies that h-agent-structure doesn't define "authority instruction files." The audit prompt can work around this (as the Architect proposes), but the workaround embeds knowledge that arguably belongs in h-agent-structure. **Encode the workaround in the prompt now, or first update h-agent-structure to close the gap?**

**Q3: Confidence scores on findings — keep or drop?** *(End-User proposes, Architect silent)*
End-User includes per-finding confidence (0.0–1.0, informational only). This adds ceremony to every finding but gives the user a trust signal. The End-User explicitly says it should NOT branch UX. **Worth the space, or noise?**
