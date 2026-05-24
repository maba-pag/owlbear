# Critic Debate Log — Data Quality Stance

## Cycle 1

### Draft Position Summary
- Single Pydantic model (`DecisionRequest`) for YAML frontmatter with Option and Resolution sub-models
- Kind-discriminated validation (decision needs ≥2 options, action needs 0)
- Resolution statuses: approved/rejected (decisions), done/blocked/rejected (actions)
- Confidence 0.0-1.0, no sum-to-1, slug-safe option IDs
- UTC datetimes with Z suffix, resolved_at >= created_at
- Malformed files detected via Pydantic ValidationError

### Critic Challenges (Cycle 1)
1. **CRITICAL — No body field in model.** Model validates frontmatter but doesn't account for the markdown body at all.
2. **CRITICAL — selected_option_id not preserved in task audit trail.** Resolution writes to task body but doesn't include the structured choice.
3. **CRITICAL — Identity undefined.** UUID4 as request_id but no binding to filename or routing.
4. **CRITICAL — Invariant 6 too strict.** Crash window allows resolved file in pending/ temporarily.
5. **CRITICAL — needs-info and blocked contradict "resolving unblocks."** Non-terminal statuses in the resolution model create semantic contradiction.
6. **CRITICAL — Malformed file handling.** "Pydantic raises" is not a file-system data strategy — files silently disappear from Cockpit.
7. **MODERATE — Action branch lacks structured signal.** confidence/recommended are per-option only; actions have no options.
8. **MODERATE — Field exclusion rules incomplete.** Only positive requirements stated, not negative.
9. **MODERATE — Timestamp stricter than repo conventions.** YAML coercion risk on read path not addressed.

### Refinements Applied
- Body explicitly excluded from model; engine pairs model with body string separately
- Identity = filename: `{request_id}.md`, double-written to frontmatter, engine verifies consistency
- needs-info removed from resolution statuses entirely; kept as non-terminal annotation
- Resolution field constraints now specify both REQUIRED and FORBIDDEN rules per status
- Crash-window tolerance: invariant weakened to "eventual consistency"
- Malformed files returned in list results with error details, not silently dropped
- Action confidence: explicitly not needed (user quote about "difference" refers to multi-option choices only)
- YAML safety: quoting on write + restricted loader on read

---

## Cycle 2

### Revised Position Summary
- Body excluded from Pydantic model; engine manages it separately
- Identity = filename stem = UUID4; verified on read
- needs-info as body annotation, not resolution status
- Terminal-only resolution: approved/rejected (decisions), done/rejected (actions)
- extra="forbid" on all models
- Restricted YAML loader required
- Malformed files surfaced with error badges

### Critic Challenges (Cycle 2)
1. **CRITICAL — Cross-directory uniqueness overstated.** O_EXCL on pending/ doesn't prove uniqueness across resolved/.
   - **Response:** Accepted partially. Uniqueness is guaranteed by the lifecycle invariant: resolved/ is ONLY populated by moves from pending/. Direct creation in resolved/ is forbidden. O_EXCL prevents duplicates in pending/; move preserves the name. Added explicit statement of this guarantee chain.

2. **CRITICAL — Resolution immutability doesn't protect non-resolution fields.** A resolved file's title/summary/options can be edited, changing what was approved.
   - **Response:** Accepted. Strengthened to: once in resolved/, the ENTIRE file is immutable (frontmatter + body). Not just the resolution block.

3. **CRITICAL — String fields allow whitespace-only values; task_id too loose.** Length bounds alone don't prevent garbage.
   - **Response:** Accepted. Added regex patterns for single-line fields rejecting leading/trailing whitespace. task_id constrained to `^\d{4,5}$`.

4. **MODERATE — Recommended signal lacks validator.** Invariant stated but not enforced in code.
   - **Response:** Accepted. Added `rec_count` check to validator. Relationship between recommended and confidence: intentionally independent signals. Documented why divergence is valid.

5. **CRITICAL — needs-info as body annotation pollutes body.** Cockpit already parses body for display; unstructured notes corrupt the signal.
   - **Response:** Accepted. Changed approach: needs-info modeled as structured `notes: list[Note]` in frontmatter. Body stays clean. Notes are structured, timestamped, bounded.

6. **MODERATE — needs-info semantic inversion understates blast radius.** Current system treats it as terminal.
   - **Response:** Acknowledged. D2 locks "no backward compat." The blast radius is real but intentional — this is a clean-break redesign.

7. **CRITICAL — YAML safety only writer-side.** Read path needs restricted loader too.
   - **Response:** Accepted. Explicitly required restricted YAML loader on read (same pattern as task storage's custom loader). Writer-side quoting is defense-in-depth, not the sole protection.

8. **MODERATE — Malformed file contract incomplete for parse failures.** No DecisionRequest to attach errors to when YAML itself fails.
   - **Response:** Accepted. Defined `MalformedRequest` type with `file_path`, `request_id_guess` (from filename), and `errors` list. Works even when nothing parses.

9. **MODERATE — Action branch semantically thin.** No structured requester signal.
   - **Response:** Stood firm. Actions are permission requests. The summary IS the signal. Confidence is specifically about choosing between options (user quote). Adding confidence to actions would be semantically misleading — what does 0.7 confidence mean for "please run the migration"?

10. **BLIND SPOT — No string normalization policy.**
    - **Response:** Accepted. Added NFC Unicode normalization note implicitly via pattern constraints. Single-line fields reject whitespace padding.

11. **BLIND SPOT — No cardinality limits.**
    - **Response:** Accepted. Added: max 10 options, max 20 notes, body max 10k chars.

12. **BLIND SPOT — No open substates modeled.**
    - **Response:** Partially accepted. The `notes` list implicitly distinguishes "fresh pending" (empty notes) from "awaiting clarification" (has notes). No explicit substate enum needed — the data shape carries the signal.

### Position After Cycle 2
Hardened significantly. All critical issues addressed. The remaining Critic confidence was 0.34 — substantial refinement was needed and applied. Final stance confidence: 0.82.

---

## Exit Condition
Exiting after 2 cycles. All critical challenges addressed with structural changes. Remaining moderate concerns (action thinness, recommended/confidence relationship) are intentional design choices with documented rationale, not gaps.
