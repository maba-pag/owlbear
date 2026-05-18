# End-User Debate Log — Cockpit Memory Tab

## Cycle 1 — Initial Position → Critic Challenges

### Draft Position Summary

1. Inline accordion for detail (≤1024 chars makes separate route wasteful)
2. State-priority sort, `updated_at` descending within state
3. Action buttons in list row (Approve + Delete as one-click row actions)
4. Deleted entries filterable but hidden by default
5. Nav-rail badge when pending > 0
6. Slide-over drawer for edit form
7. Confirmation only for hard-delete (soft-delete treated as "reversible")
8. Compact one-line rows with title, categories, confidence, state, actions (no scope_agents)
9. Instant text search, URL param filter persistence

### Critic Challenges (Cycle 1)

**Critical:**

1. **Soft-delete is not reversible.** The state machine says `deleted → nowhere (locked)`. The draft incorrectly assumed reversibility and used that to justify no confirmation for soft-delete. Both delete paths are terminal.

2. **Approve changes agent behavior.** The draft treated approve as "non-destructive" but approval changes the trust level of entries visible to agents. Risk model too focused on storage destruction, not behavior impact.

3. **Edit interaction incoherent.** Section 3 says edit opens accordion; Section 6 says slide-over drawer. Two contradictory interaction models for the same action. Cockpit has no established drawer pattern.

4. **scope_agents dropped from row.** The user's stated need includes "filter by agent" and "see what agents remember." Dropping scope from the row hides a primary dimension.

5. **1024-char cap not guaranteed on read path.** Cap enforced at MCP input boundary, not in persisted model. Cockpit reads files directly — the layout assumption could break.

**Moderate:**

6. **"Scan to act" asserted, not demonstrated.** User confirmed delete as primary; approve frequency is unestablished. Elevating both to row-level is unjustified.

7. **Detail pattern is a false binary.** Overlay patterns exist in the cockpit architecture — "accordion vs navigate-away" isn't the real choice space.

8. **`updated_at` descending ≠ existing engine behavior.** Engine uses `created_at` ascending. Continuity argument was false.

**Blind spots identified:** Live-update/stale behavior, global-scope entry handling, accessibility (icon-only buttons), context preservation beyond filters, contradictory data scale numbers.

### Revisions Applied

- Soft-delete now gets confirmation dialog (terminal state acknowledged)
- Approve moved to expanded detail (lower frequency, needs content context)
- Edit form: inline in accordion (no drawer, consistent with detail pattern)
- scope_agents added to row (first 2 chips + overflow)
- Accordion made defensive (max-height, scrollable for overlong content)
- Sort corrected to `created_at` ascending (matching engine)
- Approve risk re-evaluated: curated entries already visible to agents, approve is trust promotion only
- Added global-scope handling, accessibility requirements, freshness model

---

## Cycle 2 — Revised Position → Critic Challenges

### Critic Challenges (Cycle 2)

**Critical:**

1. **Approve semantics incorrect.** The stance loaded UX weight onto "approve makes entries visible to agents" but curated entries are already visible. Approve raises trust level only. The deliberation justification (putting approve behind expansion) was anchored to a false premise.

2. **Edit of approved entries is state-changing.** Edit on an approved entry auto-downgrades to curated and clears `approved_at`. The revised position still treated edit as a normal form operation without surfacing this consequence.

**Moderate:**

3. **Sort "matches existing engine" is wrong.** Engine uses `created_at` ascending (oldest first), not descending. Continuity claim was still false.

4. **Approve undo-toast model is heavier than acknowledged.** Undo requires reversing a state mutation (approved → curated) which changes timestamps. Not as lightweight as presented.

5. **Global-scope conflates wildcard and empty scope.** Wildcard (`*`) is valid for curated/approved. Empty scope is pending-only (hasn't been scoped). These are different states.

6. **Persistence story outruns #1638 contract.** Accordion/scroll persistence depends on tab lifecycle not yet landed.

7. **Deleted entries readable from disk but not via MCP tools.** Cockpit's direct-read path enables audit of deleted entries, but this is a cockpit-specific decision that should be explicit.

**Blind spots:** State-specific action visibility not precisely defined, post-mutation entry-moved behavior undefined, sort toggle + state grouping interaction unclear.

### Revisions Applied

- Approve: removed undo-toast complexity. Approve is low-risk (trust bump, already visible), no confirmation needed. Kept in expanded detail for workflow reasons (review content before endorsing).
- Edit downgrade: added inline warning text when editing approved entry ("Saving will downgrade to curated").
- Sort: corrected to ascending (oldest first), documented rationale.
- Global scope: distinguished wildcard (valid, "All agents" badge) from pending without scope.
- Persistence: scoped down to URL params only, explicitly noted accordion/scroll depends on #1638.
- State-action matrix: made precise (pending=delete only, curated=all three, approved=edit+delete, deleted=read-only).
- Deleted entries: explicitly noted cockpit reads from disk regardless of MCP restrictions.

---

## Final Assessment

Position hardened across two cycles. Key corrections: soft-delete terminal (both deletes get confirmation), approve is trust-only (no confirmation needed, but kept behind expand for deliberation flow), edit-downgrade surfaced explicitly, scope_agents visible in row, sort matches engine. Remaining uncertainty around #1638 tab lifecycle acknowledged without over-specifying.
