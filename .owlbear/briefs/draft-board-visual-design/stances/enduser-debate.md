# End-User Debate Log — Board Visual Design

## Cycle 1

### Draft Position (summarized)

1. Growing cards are right for single user; rhythm break is acceptable at current scale (~50-100 tasks).
2. Empty states should be quiet, not illustrated — "clearly wrong" for frequently-empty columns.
3. Context menu: status names only, no target column counts.
4. Theme toggle: status bar, right side — asserted as certain.
5. Priority border: 4px is sufficient, no additional indicators needed.
6. Column header: name + count only; blocked count "mixes levels."
7. Card content: title + priority + blocked + tags. Assignee irrelevant (single user). Age knowable from title.

### Critic Challenges (severity-tagged)

- **Critical: Overfitting to single user.** The brief is classified Shared (D2) because the visual baseline serves future features. Repeatedly arguing from "single developer" narrows the frame below what the brief requires.
- **Critical: Priority border accessibility.** "4px is enough" with no contrast or color-blind analysis, especially when the brief's core problem is *invisible* hierarchy.
- **Critical: Blocked count contradiction.** Position 7 calls blocked "the most actionable signal" but Position 6 refuses board-level summary of that signal.
- **Moderate: Invented scale.** "~50-100 tasks" and "column of 15 short-title cards" are not in the brief record.
- **Moderate: Scan vs. read conflation.** Board scanning and card reading are different behaviors; stance conflated them.
- **Moderate: Card height + tag inconsistency.** Tags are "fully visible" in Position 1 but "truncated if needed" in Position 7.
- **Moderate: Empty state — not engaging user preference.** Called illustrations "clearly wrong" without confronting D9's documented user preference.
- **Moderate: Context menu count vs. header count.** If count is the core scanning metric in headers, dismissing it in the menu needs more than "they just looked."
- **Moderate: Theme toggle — no usage evidence.** Placement argued with high certainty but no evidence about toggle frequency or bar semantics.
- **Moderate: Assignee vs. claimed inconsistency.** Both are ownership cues; rejecting one but keeping the other without distinction.
- **Moderate: "Age from title" is unsupported.** Titles don't encode age.

### Blind Spots Identified

- Minimal PDS grounding — arguments are generic kanban preference, not PDS-informed.
- Responsive behavior not considered for variable-height cards, chips, toggle.
- Accessibility absent across the board.
- Primary failure mode (invisible surfaces) understated relative to metadata composition.

**Critic confidence in position: 0.31 — high pressure.**

### Revisions Made

1. Reframed from "single user only" to "current user is single developer, visual baseline is shared."
2. Removed invented scale numbers.
3. Distinguished board-level scanning from card-level reading.
4. Resolved tag inconsistency: first 3 tags + "+N" overflow.
5. Engaged D9 user preference directly rather than dismissing it.
6. Conceded context menu count is useful at action time.
7. Added color-blind considerations; committed to text label for priority accessibility.
8. Reconciled blocked: card-level most actionable + board-level summary in header.
9. Articulated claimed vs. assignee distinction (real-time operational vs. static ownership).
10. Dropped "age from title" claim.

---

## Cycle 2

### Revised Position (summarized)

All 7 positions revised per above. Core premise reframed: visibility is the prerequisite; metadata positions optimize an already-visible board. Overall confidence 0.79.

### Critic Challenges (severity-tagged)

- **Critical: Unbounded title height.** Tags are bounded (3 + overflow) but title remains uncapped. "Bounds worst-case height" claim is only half true.
- **Critical: Theme toggle premises.** Status bar already houses health/cleanup/DR controls — argument runs ahead of toggle existence and bar semantics.
- **Moderate: Visibility/density coupling.** Core premise claims metadata is "secondary to surfaces," but Positions 3, 6, 7 all alter first-order scan surfaces (header counts, card metadata, menu counts).
- **Moderate: Empty state — doctrine over evidence.** Recurring-state argument is generic pattern, not evidenced from actual empty-column frequency.
- **Moderate: Context menu count redundancy.** Header already shows counts; menu count is genuinely redundant with Position 6.
- **Moderate: Priority accessibility fork unresolved.** Text vs. icon left open; they differ materially in space and semantics.
- **Moderate: Claimed vs. assignee inconsistency.** Distinction not yet articulated in stance.

### Blind Spots Identified

- No empirical grounding for variable-height acceptance or empty-state frequency.
- No discussion of how denser cards affect drag targets and focus flow.
- Compression accessibility (how "+N" is announced, hidden tags for assistive tech).
- Redundancy between always-visible card cues and existing filter infrastructure.

**Critic confidence in position: 0.45 — pressure reducing, position firming.**

### Revisions Made (final stance)

1. Title: acknowledged outlier risk, proposed 4-line soft cap as ready fallback.
2. Context menu count: softened to "optional, include only if zero implementation cost."
3. Priority accessibility: committed to text label (not icon). Text is universally parseable.
4. Claimed vs. assignee: articulated real-time operational vs. static ownership distinction.
5. Added warning about visibility/density coupling — brief should test combined effect.
6. Theme toggle: acknowledged bar's existing control population, argued theme belongs with that family.

---

## Exit Assessment

After two Critic cycles, the core positions are stable:
- Variable height with bounded tags: challenged on title outlier → acknowledged with fallback
- Quiet empty states: challenged on user preference → engaged directly, held position
- Priority accessibility: challenged on color-blind gap → added text label requirement
- Blocked in headers: challenged on contradiction → reconciled consistently
- Claimed vs. assignee: challenged on inconsistency → distinction articulated

Remaining gaps are empirical (title length distribution, empty column frequency, tag count distribution) and require actual usage data to resolve. The stance is as hardened as it can be without runtime evidence.
