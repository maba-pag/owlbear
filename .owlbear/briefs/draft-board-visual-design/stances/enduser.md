# End-User Stance — Board Visual Design

## User Experience Stance

The board's primary failure is invisibility — white on white, no surfaces, no boundaries. Solving that is the prerequisite for everything else discussed here. Every position below assumes the brief delivers visible surfaces, shadows, and text contrast first. The metadata and density questions optimize an already-visible board.

The target user is a single developer managing an AI agent pipeline. Their primary workflow: glance at the board to assess pipeline health, right-click to route tasks intentionally, and open the sidecar for detail. Design should serve that workflow directly while not foreclosing the shared visual baseline that future features (grouping, search, decisions tab) will inherit.

## Usability Reasoning

### 1. Variable Card Height — Correct, With Practical Bounds

Decision D7 (release height constraint) is the right call. A developer managing their own pipeline benefits more from reading actual task names and seeing tag context than from a uniform card grid. Board-level scanning happens at the column level (column fullness, color density); card-level reading is where titles and status matter.

**Tag display:** Show the first 3 tags as compact chips. Overflow as "+N" indicator. This bounds tag-driven height growth while preserving the categorical context the user wants. Full tag list lives in the sidecar — that's its purpose.

**Title risk:** Variable height means a task with a very long title creates an outlier card that breaks visual rhythm. This is acceptable now. If it proves disruptive in practice, a soft cap (4 lines with ellipsis) is a clean fallback — but start uncapped and let actual usage inform the threshold.

### 2. Empty States Should Be Quiet — Pushback on D9

Decision D9 chose PDS illustrated placeholders. I'm pushing back on the illustration weight.

Kanban columns empty as part of normal operations. "Done" empties after every archive cycle. "Review" clears when the pipeline is healthy. These are recurring operational states, not exceptional first-run events. Illustrated placeholders are designed for the latter — they signal "you haven't started yet," not "the pipeline is flowing."

Each time an illustration appears and disappears, it draws the eye to the least important column (the empty one) and away from columns with actionable tasks. For a "scan board status quickly" workflow, this is backwards.

**What "designed feel" actually requires:** A single line of subdued text using PDS typography tokens (appropriate font weight, muted color from PDS surface tokens) with generous whitespace. The clean column surface IS the design. An optional small muted icon (not illustration) is acceptable. The empty column's job is to recede.

### 3. Context Menu — Status Names, Count Optional

Show status transition targets with directional indicators: "→ in-progress", "→ review".

Adding the target column's task count ("→ in-progress (3)") is cheap information but genuinely redundant — column headers already display counts per Position 6. A single developer looking at their own board just saw the column counts before right-clicking. Include the count only if it costs nothing in implementation complexity; do not design around it.

The context menu itself needs PDS elevation treatment: `shadow-md` token, surface background, appropriate border-radius, keyboard navigation (arrow keys, Escape to close). This is where the "finished product" bar matters — the context menu is the primary action surface.

### 4. Theme Toggle — Status Bar, Right Side

The toggle should live in the status bar, right-aligned. The status bar already houses system-level operational controls (health indicators, cleanup, DR status). Theme is a system-level preference — it belongs with that family.

- Nav rail: wrong — theme isn't a navigation destination.
- Settings/preferences: wrong — buries a visual preference behind navigation for a control that may be toggled multiple times as lighting conditions change.
- Status bar right side: follows the convention of system-level controls in persistent chrome. Discoverable on first use, predictable on repeat use.

On mobile (≤767px), the toggle should remain accessible from whatever collapsed navigation surface exists.

### 5. Priority Border — 4px Left Border + Accessible Text Label

The 4px left-border color is the right primary indicator. It's spatially efficient, immediately scannable, and follows the established kanban card pattern.

**Accessibility requirement:** Color-only encoding fails for color-blind users. Supplement the border with a compact text label in the card's metadata line: "P1" / "crit" / "need" / "nice" using the corresponding PDS notification color as text color. This is a secondary cue — small, unobtrusive, but present. Text over icon because text is universally parseable by assistive technology without additional `aria-label` burden.

**Against background tint:** Tinting the entire card background competes with the surface/shadow hierarchy the brief is trying to establish. The border keeps priority information spatially contained.

### 6. Column Header — Name + Count + Blocked Count (When Non-Zero)

Column headers show: status name, total task count, and blocked count when any tasks in the column are blocked.

Example: "in-progress (5)" or "in-progress (5 · 2 blocked)"

**Rationale:** If blocked is the most actionable card-level signal ("why isn't this moving?"), a board-level summary of that signal directly serves the "scan board status quickly" workflow. The user sees pipeline health without reading every card. When no tasks are blocked, the indicator doesn't appear — zero visual noise in the healthy state.

The blocked count should use a PDS notification color (warning or error) to visually separate it from the neutral task count.

### 7. Card Content — Title + Priority + Blocked + Tags + Claimed

Cards display:
- **Title** — full, no truncation (variable height allows this)
- **Priority** — 4px left-border color + accessible text label
- **Blocked** — visible indicator (icon or text) when blocked
- **Tags** — first 3 as compact chips, "+N" overflow for more
- **Claimed** — subtle indicator when an AI agent is actively working the task

**Claimed vs. Assignee distinction:** "Claimed" is a real-time operational signal — it tells the user "an agent is working this right now," which is directly actionable in a pipeline management workflow. "Assignee" is a static ownership field that is meaningless for a single user (it's always you). Claimed earns card real estate; assignee does not. Future multi-user scenarios can add assignee trivially — the card layout accommodates it.

**Age excluded:** Task age is not reliably communicated by a card-level indicator. If staleness matters, it's a filtering/sorting feature, not a visual cue.

## Key Trade-offs

| Decision | Trade-off | Position |
|----------|-----------|----------|
| Card height (D7) | Visual rhythm vs. content visibility | Content visibility; soft cap as future fallback |
| Empty state (D9) | User's illustration preference vs. recurring-state quietness | Quiet text; pushback on illustrations |
| Context menu | Action-time info vs. header redundancy | Status names primary; count optional |
| Theme toggle (D6) | Discoverability vs. intrusiveness | Status bar right side |
| Priority indicator | Simplicity vs. accessibility | Border + text label for color-blind access |
| Column header | Minimal vs. pipeline health scanning | Name + count + blocked (conditional) |
| Card density | Per-card info vs. board scanning | Title + priority + blocked + tags(3) + claimed |

## Warnings

1. **Empty state illustrations will become visual noise.** The user requested them, but the kanban workflow guarantees frequent empty columns. If implemented as illustrated placeholders, expect the user to want them removed within weeks of real use.

2. **Unbounded title height is a known gamble.** The stance accepts it because the alternative (truncation) defeats the purpose. Monitor for outlier cards and have the 4-line soft cap ready as a quick CSS change.

3. **Priority border alone is not WCAG-compliant.** The text label is not optional polish — it's an accessibility requirement. Ship it with the border, not as a follow-up.

4. **Context menu must feel native.** The context menu is the primary intentional action surface. If it lacks proper elevation, background, and keyboard support, the "finished product" quality bar fails at the most important interaction point.

5. **Visibility and density are coupled.** Adding tags, blocked indicators, and claimed state to cards while simultaneously removing height constraints creates denser, taller cards. The brief should test the combined effect, not each element in isolation.

## Confidence

**0.79 overall**

| Position | Confidence | Note |
|----------|------------|------|
| Variable height + bounded tags | 0.78 | Right call, but title outlier risk is real |
| Empty state pushback | 0.82 | Recurring-state UX pattern is well-established |
| Context menu | 0.80 | Elevation and keyboard support are critical |
| Theme toggle placement | 0.75 | Defensible; responsive collapse needs verification |
| Priority border + text | 0.76 | Border is right; text label implementation needs design exploration |
| Column header with blocked | 0.80 | Directly serves scanning workflow |
| Card content model | 0.78 | Claimed vs. assignee distinction is sound; tag overflow needs testing |
