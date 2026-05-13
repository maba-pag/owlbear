# Security Debate Log

## Round 1

### Draft Position (Pre-Critic)

**Position 1: proof_bundle is a privilege-determining field (HIGH RISK)**
proof_bundle controls verification depth — determines test count (w-tdd-red), challenger invocation, and review depth. A wrong value (e.g., "skip" when "critical" is needed) silently reduces verification rigor. Framed as an integrity-critical authorization signal.

Recommended strict Pydantic Literal validation, modifier validation against a closed set, and immutability after task leaves "todo."

**Position 2: AC is a verification trust anchor (MEDIUM RISK)**
AC drives test creation and review verification. Post-start modifications could weaken the verification contract. Recommended "at minimum visible in task history" and append-only semantics during active work.

**Position 3: File-system bypass is bounded but real (MEDIUM RISK)**
Agents can write .md files directly, bypassing engine validation. Claimed "next engine read fails loudly" as sufficient detection. Recommended accepting as inherent to architecture.

**Position 4: YAML injection via AC strings (LOW RISK)**
Pydantic model_dump() → ruamel.yaml dump handles special characters. No string concatenation path. Recommended max-length/max-items as defense-in-depth.

**Position 5: Migration integrity (MEDIUM RISK)**
Forward-only migration risks AC loss if body section is accidentally removed. Recommended upgrading migration script from "optional" to "recommended."

**Position 6: DoS via large AC (LOW RISK)**
Single-user, agents as producers. Recommended reasonable caps on items and string length.

**Overall confidence: 0.82**

### Critic Challenges

**Challenge 1 (CRITICAL): Dual authority / split-brain**
Downstream agents (w-tdd-green, w-code-review, w-arch-review, w-task-decomposition) currently read proof_bundle and AC from body text, not frontmatter. Adding frontmatter creates a second authority. Body-based consumers will continue acting on stale body values while frontmatter may say something different. The dispatch clarity gate (dispatch.py:145) also checks body AC. The stance treats frontmatter as the authority, but it isn't one until all consumers switch.

**Challenge 2 (MODERATE): "Authorization signal" is overstated**
No actor or role enforcement exists. Engine edit accepts mutations from any caller with only a free-form source label. Cockpit edit permits body changes. proof_bundle is workflow-routing metadata with weak enforcement, not a technical authorization boundary.

**Challenge 3 (CRITICAL): Activity log cannot provide field-level visibility**
Current edit events are hardcoded as "task edited" with generic detail text. Activity schema carries only timestamp, task_id, action, source, and detail. The recommended "visible in task history" control doesn't exist and would require separate implementation.

**Challenge 4 (CRITICAL): Engine doesn't "fail loudly" on invalid fields**
Engine pre-screens corruption and continues (engine.py:670, 692, 706). Invalid-status tasks are silently excluded (engine.py:715). An invalid typed frontmatter field would make a task disappear from ordinary views and dispatch — not "fail loudly." The stance's core detection assumption is wrong.

**Challenge 5 (MODERATE): Shadow keys survive via extra='allow'**
Task model extra='allow' preserves unknown YAML keys through round-trips. A typo like `proof_bundel` would be stored as an extra while the canonical field uses its default. Ambiguous state survives even when the typed field has strict validation.

**Challenge 6 (BLIND SPOT): Migration risk is split-brain, not just AC loss**
The larger omission is divergent execution paths: body-based consumers act on stale body data while frontmatter consumers see updated values. This is a consistency risk, not just a data-loss risk.

**Critic confidence in draft: 0.41 (high pressure)**

### Response to Challenges

**Challenge 1 — Accepted.** This is the strongest finding. Split-brain is the primary integrity risk, not field bypass or YAML injection. The transition period where body and frontmatter coexist as competing authorities is the real attack surface. Revised to make this the top-level concern.

**Challenge 2 — Partially accepted.** "Authorization signal" overstates the mechanism. Revised to "integrity-relevant routing metadata." However, the functional impact is the same: wrong value → reduced verification rigor. The risk level stays, the framing changes.

**Challenge 3 — Accepted.** Revised recommendation to what the current schema actually supports: include changed-field names in the edit event detail string. This is achievable within the existing model without schema changes. Field-level audit is a separate feature.

**Challenge 4 — Accepted and elevated.** This is a design-level concern. The stance's "detection via loud failure" assumption was wrong. Revised to: invalid proof_bundle causes silent task exclusion, which is worse than a validation error because it's invisible. Recommended: engine should surface validation warnings distinctly from corruption, or the Brief should specify that proof_bundle validation happens at write time (in edit_task), not just at read time.

**Challenge 5 — Accepted as low-severity note.** Shadow keys are a code quality concern, not a security one. Worth documenting but doesn't change the risk profile materially.

**Challenge 6 — Accepted and merged with Challenge 1.** Split-brain is now the top-level finding.

### Position Status After Round 1

- Position 1: Revised framing (routing metadata, not authorization). Risk level maintained. Added write-time validation recommendation.
- Position 2: Revised recommendation to realistic scope (detail text, not field-level audit).
- Position 3: **Reversed.** Silent exclusion is worse than loud failure. Elevated to HIGH concern.
- Position 4: Unchanged. YAML injection remains low risk.
- Position 5: **Expanded.** Migration risk upgraded from "AC loss" to "split-brain consistency."
- Position 6: Unchanged.
- **New top-level finding: Split-brain during transition is the primary integrity risk.**

Revised confidence: 0.78
