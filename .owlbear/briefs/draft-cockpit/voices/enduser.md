# End User Stance — Cockpit v1

**Panelist:** End User (UX practitioner)
**Tier:** Shared | **Critic cycles:** 5

---

## 1. Cockpit Layout for v1

**Concrete layout (1440×900 reference viewport):**

| Region | Position | v1 Content | Reserved For |
|--------|----------|------------|-------------|
| **Status bar** | Top, full width, thin (~36px) | Connection traffic light (green/yellow/red) + compact activity summary: "3 running · 1 stuck · 2 free" + "Last sync: 3 s ago" | Per-service health indicators, notification badges |
| **Primary nav** | Left sidebar, narrow (~56px icon rail) | Icon rail: Board (active), Activity, future surface icons grayed/hidden. Tooltip on hover. | Project list, filter tree, search |
| **Workspace** | Center, fills remaining space | Kanban board — horizontal columns by status, cards stacked vertically by priority | Any future surface (decision queue, knowledge search, etc.) |
| **Sidecar** | Right panel, ~360px, slides in on demand | Two tabs: **Detail** (task body + YAML fields) and **Activity** (agent-centric running/stuck/free list) | Decision detail, memory viewer, etc. |

**Why this layout:** Converges with Linear, Vibe Kanban, and Mission Control's nav | canvas | detail pattern. The sidecar absorbs both task detail and activity panel as tabs, avoiding the bottom-panel invention that conflicts with the user's explicit layout sketch (sidecar right). Activity gets proper panel real estate (full sidecar height) without competing for board space.

**What's populated in v1:** Status bar (fully), icon rail (Board + Activity icons), workspace (kanban board), sidecar (detail tab + activity tab).

**What's reserved:** Icon rail slots for future surfaces, sidecar tab slots for future panels, contextual-nav area below icon rail.

---

## 2. Kanban Surface UX

### Card Density

High density. Each card: **~48–56px tall**. Shows:
- **Title** (single line, truncated with ellipsis)
- **Priority** — color-coded left border (P0 red, P1 orange, P2 blue, P3 muted)
- **Block badge** — red "blocked" chip, visually distinct from priority
- **Running indicator** — pulsing dot (claimed + valid claim) or warning icon (stuck = expired claim)
- **Agent name** — small text below title when claimed

No body preview on cards. Body lives in the detail sidecar. At 200+ tasks, every pixel of card height costs a scroll.

### Drag-to-Move + Context Menu (Both)

**Drag:** Between columns for status transitions. On drag start, valid target columns highlight (subtle glow or border change); invalid columns dim to ~40% opacity. This teaches the transition rules visually. Drag works for adjacent or nearby columns.

**Context menu** (right-click or kebab icon): All six mutations available. Status submenu shows only valid transitions. This handles long-distance moves across scrolled columns where dragging is awkward.

**Justification:** Linear and GitHub Projects ship both. Drag is fast for the common case; menu is discoverable and covers everything.

### Detail Pane: Right Sidecar

NOT a modal. NOT inline card expansion (breaks column layout density). The right sidecar panel keeps the board visible while editing. The card's position in the board provides spatial context for what you're editing.

Reference convergence: all four Part C projects use a right-side detail pane over modals for primary editing.

---

## 3. Activity Surface UX

### Location

Right sidecar, second tab (alongside task Detail tab). Toggle between them. The status bar's compact summary ("3 running · 1 stuck · 2 free") provides at-a-glance activity without opening the panel.

### Content

Sorted list, grouped by state: **Stuck** (top, most actionable), **Running**, **Free** (collapsed by default — idle agents are low-signal).

Each entry:
- **Agent name** (e.g., "builder")
- **Task link** (clickable — switches sidecar to Detail tab for that task, highlights card on board)
- **State badge:** Running (green pulse), Stuck (amber warning icon), Free (muted)
- **Claim age** (human-readable: "12 min ago", "2 h ago")
- **Unclaim button** — visible only for Stuck items. Prominent, single-click. Confirms: "Release builder's claim on TASK-42?"

### Zero-Agent State

"All agents idle" — calm informational text, not an error. This is normal between pipeline runs.

---

## 4. Six-Mutation Discoverability

| Mutation | Where | Interaction | Confirm? | Rationale |
|----------|-------|-------------|----------|-----------|
| **Move** (status) | Board drag + context menu + detail pane dropdown | Drag between lit-up valid columns; menu shows valid transitions; detail pane has status dropdown | Backward moves only | Forward = expected flow. Backward = opposing flow, needs awareness. Engine enforces valid_transitions regardless. |
| **Reprioritise** | Context menu + detail pane | Menu → priority submenu; detail pane priority selector | No | Reversible, low-risk, common action. |
| **Block** | Card badge click + context menu + detail pane | Clicking block affordance opens inline reason input (required). Block reason stored. | Implicit (reason input is the gate) | Reason input prevents accidental blocks and documents intent. |
| **Unblock** | Card badge click + context menu + detail pane | Shows current block reason, then "Unblock?" | Yes — must see the reason | Critic catch: user must see WHY it was blocked before removing the block. Minimal friction. |
| **Unclaim** | Activity panel button + detail pane header + context menu | Direct button (activity panel), link in detail header, menu item | Yes — "Release [agent]'s claim on [task]?" | Opposes expected flow (agent is working). User must be aware. |
| **Edit body** | Detail pane only | Click "Edit" → rendered markdown replaced with monospace textarea + Save/Cancel | No | Explicit mode switch is the friction. Save is an intentional action. |
| **Edit YAML fields** | Detail pane only | Structured form controls: dropdowns, tag chips, text inputs. Read-only fields (id, timestamps, claim fields) have no interactive affordance — rendered as plain text. | No | Individual field edits are reversible. Read-only fields impossible to touch in UI (not just rejected by engine). |

**Governing principle:** Confirm when the action **opposes expected flow direction** (backward move, unclaim, unblock). No confirm for forward/neutral actions.

---

## 5. Empty / Error / Loading States

### Empty Board (no tasks)

Centered illustration + text: **"Waiting for tasks. Start your pipeline in the terminal to see work appear here."** Columns are visible (establishes the board structure) but each shows a muted "No tasks" placeholder. The centered message spans the workspace.

Critical: The cockpit cannot create tasks. The empty state must explain this without making the user feel stuck.

### Empty Column

Muted placeholder text inside the column: "No [status] tasks." Not blank whitespace — blank columns feel broken.

### Loading (Initial Cold Load)

Skeleton cards in each column — animated shimmer placeholders. Status bar shows yellow "Connecting…" indicator. This is the first frame a demo audience sees. It must feel designed, not default.

### Loading (Polling Refresh)

**Invisible.** No spinners, no flash of content. Optimistic UI + revision polling means refreshes are seamless. The status bar's "Last sync: 3 s ago" timestamp is the only refresh indicator.

### Error: Engine Unreachable

Status bar turns **red**. Top-of-workspace banner: **"Connection lost — changes won't save."** Board stays visible with last-known state. All mutation affordances disabled (drag disabled, buttons grayed, context menu items grayed). "Retry" button in banner. Board does NOT white-screen.

### Error: Mutation Failed

Inline toast anchored near the affected card. Optimistic state rolls back with a brief animation (card slides back to original column). Toast shows the error reason. Dismisses after 5 s or on click. No modals for errors.

### Error: Stale View

Status bar turns **yellow**. Subtle banner: "View may be outdated — refreshing…" Auto-recovers on next successful poll. If stale for >15 s, banner adds "Reconnect" button.

---

## 6. Demo-Readiness

**The one thing: animated card transitions.**

When a card moves between columns — whether from a user drag or from a poll update reflecting an agent action — it visibly animates from source column to destination column. A smooth ~300ms slide with a subtle scale pulse on arrival.

This is the hero moment for shoulder-surfers. Cards flying across the board as agents work = immediate comprehension that the system is alive and doing things. No explanation needed.

**Supporting proof-of-life for static moments:** The status bar's green traffic light and "Last sync: 3 s ago" timestamp prove the system is connected and polling even when no cards move. Without this, a static board during a demo looks frozen.

---

## 7. Single Highest-Risk UX Assumption

**The sidecar-open board remains usable at 1440×900 with 200+ tasks.**

At 1440 width: ~56px nav rail + ~360px sidecar = ~1024px for the board. With 8–10 status columns, each column gets ~100–128px. Card titles may truncate aggressively. Horizontal scroll is permitted (per O1) but if every column requires scrolling, the "at a glance" outcome fails.

### Validation (Before Committing to Layout)

Build a **static HTML mockup** at 1440×900 with:
- 200 task cards distributed across 8 columns
- Sidecar open (360px)
- Realistic title lengths (task titles from the actual board)

Test: Can you answer "What's in review?" and "What's blocked?" without scrolling? Can you read card titles in every visible column?

**If it fails:** The sidecar must overlay the board (sheet/drawer pattern) rather than shrink it. This changes the interaction model (you lose board context while editing) but preserves board readability. This is testable in under a day with zero code.

---

## Warnings

1. **Keyboard shortcuts are absent from v1.** For a power-user tool, this is a debt. Tab order and arrow-key navigation through cards should be in the base implementation even if hotkeys are deferred.
2. **Body editor is raw markdown textarea.** Acceptable for v1 but the view→edit context switch is jarring. Split-pane or live-preview is a fast-follow.
3. **Activity panel shares sidecar with Detail.** You can't see activity AND edit a task simultaneously. If this proves frustrating, the activity summary in the status bar is the relief valve — but monitor for complaints.
4. **No undo.** Optimistic rollback on error is not the same as user-initiated undo. Confirm dialogs are the v1 substitute, but undo would be strictly better.

---

## Confidence

**0.82** — High confidence in layout, mutation model, and error states. Moderate uncertainty on sidecar width viability at 1440×900 (flagged as top risk with concrete validation plan). The reference-project convergence on right-panel detail is strong signal. Activity-as-sidecar-tab is my weakest position — it's a pragmatic compression that could frustrate if users constantly switch between detail and activity.
