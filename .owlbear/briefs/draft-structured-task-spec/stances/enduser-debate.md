# End-User Critic Debate Log

## Cycle 1 — Initial Position

### Draft Position Summary
- AC in YAML is readability regression for humans but win for agents; acceptable with block-style YAML
- String matching for remove_ac is fragile; proposed index-based removal as alternative
- Semantic AC prefixes (AC-lint:) superior to ordinal (AC1:)
- Proof bundle in show_task: just the string, agents know the taxonomy
- Forward-only migration acceptable with migration script encouraged
- AC in list_tasks is noise; proof_bundle in list_tasks is useful; ac_count meaningless
- Error messages must list existing entries on failure

### Critic Challenges (6 challenges, 4 blind spots)

**Critical:**
1. **Search regression.** Moving AC out of body makes AC text invisible to `list_tasks(search=...)` unless search semantics are extended. This is a blocking issue, not a nice-to-have.
2. **Migration blast radius.** proof_bundle controls test-writing scope, challenger dispatch, and reviewer depth. Inconsistent proof_bundle during transition causes different proof obligations — a correctness issue, not just visual inconsistency.

**Moderate:**
3. AC naming is not cosmetic — with list[str], the prefix IS the stable handle for review references and mutation targeting. Dismissing it as "out of scope" is weaker than the data shape allows.
4. Index-based removal is worse than string matching — reordering silently changes targets. Self-defeating given the anti-ordinal argument.
5. "Just the string" for proof_bundle assumes shared skill context; not all consumers load the same skills.
6. AC in list_tasks dismissal ignores the dispatch surface (DispatchEntry/pick_tasks).

**Blind spots:**
- Body predicates inspect body sections for status transitions — migration could break these
- Proof bundle modifier grammar (normalization, ordering, redundancy) not addressed
- Default for missing proof_bundle (None vs behavioral) has downstream consequences
- AC equivalence rule (exact, trimmed, case-folded) left undefined

### Refinements Applied
- **Retracted** index-based removal — Critic is right, it's worse
- **Added** search regression as blocking requirement
- **Strengthened** migration: proof_bundle migration must be non-optional
- **Softened** proof_bundle display slightly for non-agent consumers
- **Added** normalization contract for proof_bundle modifiers
- **Added** default semantics: None, not behavioral
- **Defined** AC equivalence: trimmed, case-preserved, exact after trim
- **Acknowledged** AC naming as behavioral contract risk, not just cosmetic

---

## Cycle 2 — Refined Position

### Critic Challenges (6 challenges, 2 blind spots)

**Critical:**
1. **Body-coupled gates proven in code.** Dispatch clarity gate requires bullet/numbered AC line in body. Status predicates are body-section based. Forward-only AC migration directly breaks these gates — not "must be verified" but "code proves breakage."

**Moderate:**
2. proof_bundle = None doesn't force anything — current skills tolerate absence and continue with normal flow. The stance treats a representation choice as enforcement when consuming workflows don't enforce.
3. Normalization scoped too narrowly to show_task — start_work, create_task responses, and mutation responses all return task-shaped payloads. Normalization must be model-level, not surface-level.
4. AC naming overreach — the data panelist rejects prefix-pattern enforcement, current review workflow consumes full lines not stable identifiers. Convention ≠ contract.
5. proof_bundle in DispatchEntry lacks consumer evidence — current orchestration is status-driven, workers get full context at start_work claim time.
6. Search broadening under-specified — changing a documented search contract from "title+body" to include frontmatter has implications for query semantics and result noise.

**Blind spots:**
- Malformed frontmatter written directly to disk could silently hide tasks from all list/pick/board views (Pydantic validation failure on load)
- Existing proof scope is a companion contract for the `existing` bundle value — moving proof_bundle alone doesn't fully resolve split authority

### Final Refinements Applied
- **Upgraded** body-gate breakage from "verify before migration" to blocking design requirement — gates must check frontmatter `ac` field, not just body
- **Softened** None semantics — it's better than silent default but won't enforce by itself; recommend skill updates to treat None as "must set before dispatch"
- **Broadened** normalization to model-level (Pydantic validator), not show_task-specific
- **Acknowledged** AC naming as convention recommendation, not contract requirement
- **Softened** DispatchEntry proof_bundle to "recommended, not blocking" given current start_work workflow
- **Added** graceful degradation for malformed frontmatter — invalid values should warn, not silently drop tasks
