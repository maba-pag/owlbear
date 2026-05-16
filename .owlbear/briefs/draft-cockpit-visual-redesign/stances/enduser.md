# End-User Stance — Cockpit Visual Redesign

## User Experience Stance

The cockpit's visual failure is a *foundation* failure, not a component failure. The most impactful batch is installing the PDS foundation and fixing board scroll together — these are co-equal Tier 1 because foundation enables correct rendering of every existing PDS component, and board scroll restores the kanban spatial metaphor. Everything else builds on this.

After Tier 1, the highest UX returns come from two parallel tracks: **(a)** card visual treatment — the metadata is already present but lacks visual hierarchy, and **(b)** detail-surface data formatting — ISO timestamps, raw booleans, and empty fields make the sidecar hostile to read. These are not cosmetic — they directly affect task comprehension speed and editing confidence.

The sidecar is an action surface, not a passive reader. Its information architecture must lead with orientation (what task? what state?) then immediately surface actions and content. Metadata is supporting context, not the primary view. Decision-request workflow must have explicit placement — it is a core sidecar function today.

Transient success feedback is the critical gap. Error paths exist; success paths are silent. This creates mutation anxiety: did the move work? Did the edit save? Users will double-act or lose trust in the tool.

## Usability Reasoning

### 1. Batch priority (highest impact first)

**Batch 1 — Foundation + Board Scroll (co-equal, same batch):**
- PDS foundation install (fonts, variables, normalize) is root-cause — every existing PDS component starts rendering correctly. Research estimates significant visual improvement with zero other changes.
- Board horizontal scroll (`overflow-x: auto` on board container) restores kanban left-to-right metaphor. Without it, users cannot scan pipeline progression.
- These are the minimum viable win from the context. Ship together, human review before proceeding.

**Batch 2 — Card visual treatment + Detail-surface data formatting (parallel):**
- Cards already render ID, priority, age, tags, blocked/claimed/dependency-blocked/decision-pending signals. The problem is *visual differentiation*, not absence. Priority needs color/weight distinction, not just text. Blocked/decision-pending need icon indicators scannable at a glance. Tags need chip/badge treatment.
- Detail surface (sidecar) needs: human-readable timestamps ("2 hours ago" or "May 14, 2026"), hide-if-empty for blank fields, boolean-to-semantic text ("Claimed" label with agent name or hidden if unclaimed, never "false").

**Batch 3 — Sidecar structure + Component migration:**
- Restructure sidecar sections (see §4 below).
- Replace raw HTML with PDS React components (buttons, modals, lists, headings).
- Replace custom modals with PModal overlays.

**Batch 4 — Feedback + Filter panel + Polish:**
- Add success toasts for mutations.
- Filter panel: horizontal bar above board or collapsible sidebar — never push-down.
- Dark mode border contrast, context menu hover/focus states, ConflictBanner diff formatting.

### 2. Findings that affect task comprehension (from 73+)

**Comprehension-critical (blocks understanding or action):**
- Board wrapping — can't see pipeline progression
- Missing PDS foundation — fonts, normalize, variable inheritance all broken
- ISO timestamps in detail view — cognitive load on every read
- Empty fields displayed — noise obscuring real data
- Raw booleans — "Claimed: false" is implementer text, not user text
- Card visual hierarchy — metadata exists but blends together without differentiation
- Sidecar zero padding — cramped, unreadable

**Workflow-critical (blocks confident action):**
- No success confirmation for moves/edits
- ConflictBanner as plain stacked text — merge conflicts are high-stakes; display must be clear
- Decision-request workflow visibility — embedded in sidecar but may lack visual prominence

**Secondary (real but polish-tier):**
- Context menu hover/focus states
- Filter panel push-down layout
- Activity tab session row layout
- Dark mode border contrast (partially self-resolves with PDS foundation)

### 3. Card information density

Cards currently show adequate density: task ID, title, priority, age, tag preview, blocked/claimed/dependency-blocked/decision-pending signals. **Do not add more.** The redesign task for cards is *visual treatment*, not information addition.

What cards need:
- **Priority**: Color or weight differentiation (not just text label) — scannable at board level
- **Blocked/decision-pending**: Icon indicator (lock, clock) visible without reading text
- **Tags**: Chip/badge treatment, max 3 visible with "+N" overflow
- **Age**: Relative time ("2h ago") not absolute
- **Clear card boundaries**: Shadow or border to distinguish cards from column background

What cards should NOT gain:
- Description preview (that's the sidecar's job)
- Full timestamp
- Dependency list
- Action buttons on the card face (actions live in sidecar or context menu)

### 4. Sidecar inspector: sections and order

The sidecar serves three jobs: *orient* (what am I looking at?), *act* (edit, move, decide), and *investigate* (history, metadata). Order by job frequency:

1. **Orientation header** (sticky): Task ID + title (prominent), current status badge, priority indicator, blocked/decision-pending markers
2. **Actions toolbar**: Move, edit, archive buttons — always visible, not buried in tabs
3. **Description / Acceptance Criteria**: The content body — editable, with section dividers
4. **Decision Request** (conditional): If a pending DR exists, surface it prominently — this is why someone opened this task
5. **Tags + Dependencies**: Chips for tags, linked task IDs for dependencies
6. **Metadata**: Human-readable timestamps (created, updated), hide-if-empty for optional fields
7. **History / Activity** (collapsed by default): Session log with date grouping, not a flat list

Key principles:
- Lead with orientation, then action affordances — users open the sidecar to *do something*
- Decision-request workflow gets explicit, prominent placement — not buried in a tab
- Metadata is supporting context, not primary content
- Empty sections are hidden, not shown with blank values
- Per-task history and global activity are distinct surfaces — don't conflate them

### 5. Transient feedback patterns

The existing UI handles errors (banners, validation messages, retry). The gap is **success acknowledgment**:

- **Move**: Toast "Task #{id} → {column}" — auto-dismiss 3s. PDS `PToast` or inline `PBanner` with `state="success"`.
- **Edit save**: Brief field highlight (green flash or checkmark) on the saved field — confirms which field was written.
- **Archive**: Toast with context "Task #{id} archived" — no undo needed if archive is a kanban status move, but confirmation language matters ("archived" not "deleted").
- **Conflict resolution**: When ConflictBanner resolves, toast confirming which version was kept.

Why this matters: error-only feedback creates anxiety. When the user clicks "move" and nothing visually confirms success, they either (a) double-click causing duplicate mutations, (b) manually scan columns to verify, or (c) lose trust that the tool is responsive. A 3-second toast eliminates all three.

### 6. Anti-patterns that survive the redesign unchanged

These are not fixed by PDS foundation install or component migration and need explicit attention:

- **Filter panel as page-push**: The filter panel currently pushes the board down. PDS components make it prettier but don't fix the layout pattern. Filters should be a horizontal bar above the board (always visible, low height) or a collapsible sidebar. Push-down means the board jumps vertically every time you toggle filters — spatial instability.

- **Data formatting is a code concern, not a style concern**: ISO timestamps, raw booleans, empty-field display — these are formatting logic, not CSS. PDS gives you `PText` but doesn't auto-format your date strings. Every timestamp needs a `formatRelativeTime()` call. Every optional field needs a `if (value) show` guard. This is mechanical but easily overlooked in a "visual redesign" framing.

- **Activity tab structural weakness**: Even with PDS styling, a flat chronological session list doesn't scale. Sessions need date grouping ("Today", "Yesterday", "May 14") and within-session structure. This is information architecture, not styling.

- **ConflictBanner diff legibility**: Stacked plain text for showing "server version vs. your version" is inadequate for the stakes. Conflict resolution is the highest-anxiety moment in the edit flow. Needs side-by-side or inline-diff treatment with clear "keep mine / keep server" affordances.

## Key Trade-offs

| Trade-off | Position | Rationale |
|-----------|----------|-----------|
| Foundation first vs. component migration first | Foundation first | Root-cause fix; components inherit correct rendering; validates how much self-resolves |
| Card density: more info vs. scan speed | Keep current density, improve visual treatment | Metadata already present; adding more increases scan fatigue; improve *hierarchy* not *volume* |
| Sidecar: browse-first vs. action-first | Action-first after brief orientation | Users open sidecar to act, not read. Orientation header → actions → content |
| Feedback: toasts vs. inline indicators | Both, scoped by action type | Moves = toast (board-level confirmation); edits = inline (field-level confirmation) |
| Tailwind: adopt vs. plain CSS | Adopt per D4 | PDS recommends it; questioning PDS recommendations is the documented failure mode |
| Batch size: big batches vs. small with review | Small with human visual review | Builder agents write CSS without seeing results; human checkpoint after each batch is the risk mitigation |

## Warnings

1. **Data formatting will be forgotten.** A "visual redesign" framing naturally biases toward CSS and components. But the worst comprehension failures (ISO timestamps, raw booleans, empty fields) are JavaScript formatting logic. Explicit tasks for data formatting must be in the brief, not treated as "obvious cleanup."

2. **The sidecar is more complex than it looks.** It contains editing, conflict handling, decision workflow, history, and actions. Treating it as "add padding and section dividers" will produce a pretty but dysfunctional action surface. Information architecture must be designed before styling.

3. **Post-foundation re-audit is essential.** Many of the 73 findings may self-resolve when PDS variables cascade correctly. Committing to all 73 as tasks before seeing the foundation result will create wasted work. The batch structure must include a re-audit checkpoint.

4. **Success feedback is the quiet UX gap.** It won't show up in a visual audit because it's temporal, not spatial. But it's the difference between "this tool is responsive" and "did that work?" Flag it now or it will be deprioritized into never.

## Confidence

**0.82** — Position is well-grounded after Critic correction on card metadata (retracted stale claim), sidecar action model (promoted from browse-first), and feedback coverage (revised from "zero" to "no success path"). Remaining uncertainty: card visual treatment specifics depend on post-foundation state; sidecar section ordering is a reasoned proposal that needs user validation.
