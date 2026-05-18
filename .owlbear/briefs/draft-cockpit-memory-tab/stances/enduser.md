# End-User Stance — Cockpit Memory Tab

## User Experience Position

The Memory tab serves one primary job: make the memory black box transparent and controllable. The design must optimize for **scanning** (103–500 entries), **targeted action** (delete, approve, edit), and **progressive disclosure** (detail on demand without losing list context). Every design choice below is evaluated against those three axes.

## Detail Pattern: Inline Accordion Expand

Inline expand via PAccordion. Content is ≤1024 chars (enforced at MCP input). The accordion should be defensive — scrollable content area with max-height — so edge-case overlong entries don't break the layout.

Overlay/modal/drawer/separate-route all add interaction chrome (close buttons, backdrops, transitions) that buys nothing for content this short. The user's workflow is serial review: expand, read, act, collapse, next. Inline expand keeps the list visible and enables this rhythm without navigation.

## List Row Design

Each row shows the minimum scannable set:

| Field | Treatment |
|-------|-----------|
| Title | Truncated ~60 chars |
| scope_agents | First 2 as chips, "+N" overflow badge |
| Categories | Top 2 chips, "+N" overflow |
| Confidence | Numeric (0.70–1.00) |
| State | Color-coded badge with text label |
| Actions | State-dependent (see §Actions) |

Scope_agents is in the row because agent-scoping is the primary lens the user cares about. The stated pain is "filter by agent" and "see what agents remember." Hiding scope in detail-only would undermine the tab's reason to exist.

Compact table-like density, not cards. At 100–500 entries, cards waste vertical space and force excessive scrolling.

## Sort Order

**Default:** State-priority grouping (pending → curated → approved). Within each state group, sort by `created_at` ascending (oldest first — process the queue from oldest pending forward).

**Deleted entries excluded from default view** (see §Deleted Entries).

**Sort toggle available:** switch within-state secondary sort between `created_at` and `updated_at`. State grouping always dominates — the list never flattens into a single chronology regardless of sort toggle.

## Action Placement and State-Specific Availability

### Row-Level Actions (One-Click)

- **Delete** (visible text-label button, not icon-only): shown for pending, curated, and approved entries.

### Expanded-Detail Actions

- **Approve**: shown only for curated entries.
- **Edit**: shown for curated and approved entries.

### State-Action Matrix

| State | Row Actions | Expanded Actions |
|-------|-------------|-----------------|
| Pending | Delete | — |
| Curated | Delete | Approve, Edit |
| Approved | Delete | Edit |
| Deleted | — (read-only) | — |

**Rationale:** Delete is the confirmed high-frequency action (user's stated need). Approve and Edit require more context (reading the content first) and have lower frequency. Placing them behind expansion creates natural deliberation without adding blocking dialogs.

## Confirmation Patterns

- **Hard-delete (pending):** Confirmation dialog. Irreversible — file removed from disk.
- **Soft-delete (curated/approved):** Confirmation dialog. Terminal state — the system provides no recovery from deleted. Treat as destructive.
- **Approve:** No confirmation. Curated entries are already visible to agents; approve is a trust-level promotion, not a visibility gate. Low-consequence, easily reversed via edit (which downgrades back to curated).
- **Edit of approved entry:** Inline warning text displayed when editing an approved entry: "Saving will downgrade this entry to curated." Not a blocking dialog, but visible feedback about the state consequence.
- **Edit of curated entry:** No extra confirmation beyond Save/Cancel.

## Edit Form: Inline in Accordion Expansion

Edit renders inside the expanded accordion, replacing the read view with editable fields:

- Title: text input
- Content: textarea (preserving markdown)
- Categories: PMultiSelect (9 enum options)
- Confidence: number input (0.7–1.0, step 0.01)
- scope_agents: PMultiSelect (populated from known agents)

Save/Cancel buttons at bottom of the form. On save: accordion collapses, row updates in-place, list refetches. On cancel: reverts to read view without collapse.

No drawer or modal — neither has an established pattern in this cockpit, and the content fits comfortably inline.

## Filtering

- **State filter:** PMultiSelect. Default selection: pending + curated + approved. "Deleted" available as opt-in.
- **Category filter:** PMultiSelect with all 9 enum values.
- **Agent filter:** PMultiSelect populated from known scope_agents values + "All agents" option (for wildcard-scoped entries).
- **Text search:** PInputSearch with instant keystroke filtering (no submit). Searches title and content.

All filters are AND-combined (state AND category AND agent AND text match).

### Deleted Entries

Available through the state filter but excluded from default. The cockpit reads files from disk directly — deleted entries exist as files with `state: deleted` and are readable regardless of MCP tool restrictions. Shown read-only (no actions available).

### Wildcard-Scope Entries

Entries with `scope_agents: ["*"]` display an "All agents" badge in the row. They appear when filtering for any specific agent (since they apply to all). They also appear under a dedicated "All agents" filter option.

## Filter Persistence

Active filter selections stored in URL search params. Navigating away and returning restores the filter state. Enables sharing filtered views via URL.

Expanded-row state and scroll position are not guaranteed across tab switches — this depends on #1638 tab lifecycle semantics which are not yet settled. Do not over-specify.

## Nav-Rail Badge

Show pending count badge only when pending > 0. Subtle styling (informational, not alarm). At typically 0–2 pending, a permanent badge would be noise. "Something appeared that needs attention" is the signal.

## Freshness Model

No SSE for V1. Mutations in this tab are user-initiated:
- After each action (approve/edit/delete), refetch the full entry list.
- If the mutated entry no longer exists or moved state, the accordion collapses and the list re-renders.
- Poll-on-focus (mtime check) catches entries created by background agent activity.

## Accessibility

- Delete and Approve use `PButton` with visible text labels (not icon-only).
- State badges use color + text (never color alone) for colorblind users.
- Accordion expand/collapse is keyboard-navigable (PAccordion provides this).
- Row actions have descriptive `aria-label` attributes: "Delete entry: {title}".
- Filter controls are labeled with visible `<label>` elements.

## Key Trade-offs

| Choice | Gains | Costs |
|--------|-------|-------|
| Inline accordion over overlay | Zero navigation friction, list always visible | Vertical space consumption when expanded |
| Delete in row, Approve/Edit in detail | Fastest path for primary action, natural deliberation for secondary | Approve requires one extra click |
| Both delete types get confirmation | Matches actual irreversibility of terminal state | Adds friction to the most common action |
| Compact rows with scope_agents | Primary dimension always visible | Row width pressure at narrow viewports |
| No SSE | No infrastructure cost | Background-created entries delayed until focus |

## Warnings

1. **Soft-delete is terminal.** The current system offers no transition out of deleted state. UI must treat soft-delete with the same gravity as hard-delete. If a future "restore" feature is added, the confirmation can be relaxed — but not before.
2. **Edit-downgrade is invisible without explicit feedback.** Editing an approved entry silently changes its trust state. The UI must surface this as inline text, not bury it.
3. **Sort continuity assumption.** The existing engine sorts `created_at` ascending. If the cockpit differs without reason, users who also interact via MCP tools will be confused by different orderings.

## Confidence

**0.78** — Position is grounded in the confirmed user needs (overview, agent filtering, delete), matches system constraints (PDS components, no drawer pattern, client-side filtering), and handles the non-obvious state machine semantics (terminal delete, approve trust semantics, edit downgrade). Remaining uncertainty: tab lifecycle (#1638 not landed) and whether approve frequency will eventually warrant row-level promotion.
