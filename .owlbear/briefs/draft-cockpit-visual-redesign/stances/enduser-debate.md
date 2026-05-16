# End-User Debate Log — Cockpit Visual Redesign

## Cycle 1

### Draft Position

**Priority ranking:** Board scroll > Card density > Sidecar structure > Mutation feedback > Data formatting.

Board wrapping into multi-row grid is the #1 usability killer — destroys kanban spatial metaphor. Cards show only title with no ID, priority, tags, blocked state — can't scan the board. Sidecar has zero padding, ordered as browse-first (header → status → content → metadata → activity). Zero mutation feedback currently. Anti-patterns surviving redesign: filter page-push, raw data formatting, no loading/stale states, flat activity list.

Card density rule: show what you need to decide which card to click. No claimed status on card. Sidecar: never lead with metadata.

Confidence: 0.80.

### Critic Challenges (7 challenges, 4 blind spots — pressure: high)

1. **Priority ranking is symptom-first.** Board wrapping is a symptom; PDS foundation is the root cause. Ranking scroll above foundation contradicts the research that says foundation install self-resolves many issues. Severity: critical.

2. **Card metadata sparsity claim is stale.** Current `Card.tsx` already renders task ID, priority, updated age, tag preview, blocked/claimed/dependency-blocked/decision-pending signals. The claim that users "can't scan the board" is materially overstated against the actual code. Severity: critical.

3. **Card signals include actionability, not just selection.** Blocked, claimed, dependency-blocked, and decision-pending are first-class card signals. Saying "no claimed status on card" ignores actionability scanning — the user needs to know if a task is claimable, blocked, or waiting on a decision *from the board view*. Severity: critical.

4. **Sidecar is an action surface, not a reader.** The current sidecar contains editing, task actions, conflict handling, history, and pending decision-request workflow. A browse-first ordering model is ungrounded — users open the sidecar to *act*, not just read. Severity: critical.

5. **"Claimed-by" is legacy/forbidden in the backend.** Including it as standard sidecar metadata is an unverified assumption. Severity: moderate.

6. **"Zero feedback" and "no loading states" are overstated.** The UI already has mutation-error banners, validation messages, fetch retry, scan retry, connection health indicators, board loading, decision loading, activity empty/error states, and explicit stale tracking. The gap is *success acknowledgment*, not absence. Severity: moderate.

7. **Detail-surface comprehension costs under-ranked.** Raw timestamps, raw booleans, raw dependency status in the detail view are real comprehension costs ranked last. No evidence that board-level pain dominates detail-level pain. Severity: moderate.

**Blind spots:**
- No user segmentation or usage-frequency evidence
- Pending decision-request workflow missing from sidecar information architecture
- Activity = both global tab and per-task history (treated as one thing)
- Mobile-sheet vs desktop-sidecar branches exist despite desktop-only scope

### Refinements

**Challenge 1 — Accepted.** Foundation and board scroll are co-equal Tier 1. Foundation is root-cause (enables everything), board scroll is highest-visibility user impact. They should be the same batch, not sequenced. Revised framing: "Foundation + board scroll = Batch 1. Everything else follows."

**Challenge 2 — Accepted.** Card metadata claim retracted. Cards already show meaningful density. The real UX issue is *visual hierarchy and scannability* of existing metadata, not absence. The card signals exist but may lack visual differentiation (priority as text vs. color, tags as text vs. chips, blocked as text vs. icon). Revised: card density is adequate; card *visual treatment* needs PDS component migration.

**Challenge 3 — Accepted.** Actionability signals (blocked, dependency-blocked, decision-pending) belong on the card face. These tell the user "can I act on this?" which is the board-scan question. Claimed status stays because it tells the user "is someone working on this?" — relevant for a pipeline tool. Retracted the "no claimed status" position.

**Challenge 4 — Partially accepted.** The sidecar is indeed an action surface. However, the browse-first ordering still has merit for the *initial view* — you need orientation (what task? what state?) before you can act. The refinement: sidecar has an orientation zone (header + status) at top, then actions/content as the primary surface, then metadata. The action model is promoted from "occasional" to "primary." Decision-request workflow gets explicit placement.

**Challenge 5 — Accepted.** Dropped "claimed-by" from sidecar spec. If it appears in existing UI, treat it as data-present (show if populated, hide if not) rather than a designed section.

**Challenge 6 — Accepted.** Revised from "zero feedback" to "no success acknowledgment." Error paths are covered; the gap is positive confirmation — "your move/edit worked." This is still a real problem because error-only feedback creates anxiety: silence means "maybe it worked, maybe it failed silently."

**Challenge 7 — Accepted.** Data formatting (timestamps, booleans, empty fields) promoted from last to co-equal with card visual treatment. Detail-surface comprehension is where users spend time *after* scanning the board. Ranking it last was board-scanning bias.

**Revised confidence: 0.82** (up from 0.80 — the position is stronger after correction, not weaker).
