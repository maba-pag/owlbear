# Critic Debate Log — Data Quality Stance

## Cycle 1

### Draft Position

Simple `str.replace("\\n", "\n")` without escape convention. Key claims:
- Idempotency is more valuable than escape convention precision
- Near-zero false-positive frequency
- LLMs can't triple-escape, so the escape convention is unusable
- Skip the escape convention; document that literal `\n` is normalized
- Also normalize `\\r\\n` → newline

### Critic Challenges

1. **Critical: Overturns locked D4 without new evidence.** D4 explicitly chose normalize-and-notify and rejected naive replace. The stance drops both the notification-based recovery model and the escape path without empirical justification.

2. **Critical: "Near-zero false positive frequency" is unvalidated.** The 16.5% stat measures corruption prevalence, not intentional-literal prevalence. The archive is mixed — both corrupted and intentional literal content exists. Treating an unclassified dataset as proof of rarity is unsound.

3. **Critical: `create_dr` silent-destruction hole.** The guidance channel doesn't exist for `create_dr`, so dropping the escape convention reintroduces exactly the silent false-positive behavior D4 rejected.

4. **Moderate: Round-trip and idempotency don't discriminate.** Simple replace also guarantees loss of intentional literals on re-edit. Idempotency is only helper-level within mutations that are themselves non-idempotent.

5. **Moderate: Code fences don't protect payload meaning.** Archive contains output format strings like `"Relevant knowledge:\\n\\n- title: content"` where converting `\n` to newlines changes the described string, not just formatting.

6. **Moderate: CRLF precedent is weaker than claimed.** Existing parser normalizes semantically equivalent newline encodings. This proposal converts visible characters into control characters in an ambiguous case.

### Stance Adjustments

- **Retracted** the recommendation to drop the escape convention. D4 is locked; work within it.
- **Retracted** the "near-zero" false-positive frequency claim. Acknowledged as unquantified.
- **Adopted** three-step escape-protected normalization as the implementation.
- **Flagged** `create_dr` as a contract contradiction requiring brief-level decision.
- **Acknowledged** non-idempotency as structural (per-content-lifecycle), not contained (per-invocation).

## Cycle 2

### Revised Position

Three-step escape processing (protect `\\n`, normalize `\n`, restore). Escape convention via `\\\\n` in JSON. Non-idempotency constrained to single-application. `create_dr` options presented. `\r\n` included in normalization scope. Confidence 0.80.

### Critic Challenges

1. **Critical: `create_dr` contract is locked by D13.** Adding `guidance` to the dict response breaks a prior decision and existing test assertions. Skipping normalization contradicts the locked outcome "all body fields normalize." This is an unresolvable tension, not a pick-one choice.

2. **Moderate: Non-idempotency is structural, not contained.** "Exactly one point" per invocation is true, but content lifecycle is multi-invocation. `show_task` returns full bodies; `edit_task` accepts full replacements. Preserved literals degrade on re-edit.

3. **Moderate: `\r\n` normalization adds a new false-positive class.** No corresponding escape convention defined for intentional literal `\r\n`. The existing CRLF→LF precedent in `body_parser.py` normalizes actual CRLF, not literal escape text.

4. **Moderate: Placeholder safety is asserted, not established.** The pipeline has no null-byte input validation. JSON transport makes collisions extremely unlikely, not impossible.

5. **Moderate: 0.80 confidence is high** given unquantified false-positive frequency and unresolved `create_dr` tension.

### Stance Adjustments

- **Removed** `\r\n` from normalization scope. Context confirms the problem is `\n`-specific; adding `\r\n` expands scope without evidence or escape path.
- **Reframed** `create_dr` as an unresolvable contract contradiction needing brief-level decision, with options table.
- **Acknowledged** non-idempotency as structural across content lifecycle, limiting escape convention to first-write fidelity.
- **Weakened** placeholder safety claim from "impossible" to "extremely low risk."
- **Lowered** confidence to 0.75.

## Final Assessment

The hardened position respects D4, specifies the three-step mechanism precisely, and surfaces the unresolvable `create_dr` tension for escalation. The main residual risk is proportionality: the escape convention complexity may exceed the frequency of intentional-literal cases it protects. This is an honest uncertainty reflected in the confidence score.
