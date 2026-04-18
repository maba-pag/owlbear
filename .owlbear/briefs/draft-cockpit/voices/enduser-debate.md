# End User — Critic Debate Log

**Panelist:** End User | **Critic cycles:** 5

---

## Cycle 1 — Bottom Panel vs Sidecar Conflict

**Critic challenge:** "Your bottom-panel activity layout has a major conflict with O4b. The context says 'sidecar slots are reserved' — this implies the sidecar is the designated expansion area, not a bottom panel. You're inventing a bottom panel that's nowhere in the original layout philosophy. Also, your assumption that 200+ tasks renders well at 1440×900 with both sidecar AND bottom panel open is something you yourself flagged as the highest risk — which means your proposed layout is built on your own identified weakest assumption."

**Response:** Accepted. The user's layout sketch explicitly puts sidecar right. A bottom panel is an invention that contradicts the brief and doubles the space pressure. Revised: activity panel moves to the right sidecar as a second tab alongside task detail. Status bar gets a compact summary line ("3 running · 1 stuck · 2 free") for at-a-glance activity without opening the panel. This aligns with the layout sketch and eliminates the dual-panel space conflict.

**Position change:** Activity moved from bottom panel → sidecar tab. Status bar gains compact activity summary.

---

## Cycle 2 — Drag Across Scrolled Columns

**Critic challenge:** "You say drag-to-move between columns but the kanban has 8-10 status columns. With horizontal scroll, dragging from 'backlog' to 'done' requires scrolling while dragging — terrible UX. Also, valid_transitions constrains which columns a card can move to. How does drag communicate which targets are valid?"

**Response:** Accepted as real constraint, strengthens existing position. On drag start, valid target columns light up (glow/border), invalid columns dim to ~40% opacity. This teaches transition rules visually. For long-distance moves across scrolled columns, the context menu is the better path — it shows a submenu of valid transitions. This is why having BOTH drag AND context menu is essential, not redundant.

**Position change:** Added valid-column highlighting on drag start. Strengthened dual-interaction justification.

---

## Cycle 3 — Empty State + Zero Agents + Static Demo

**Critic challenge:** "Your empty state for 'No tasks yet. Tasks are created by agents through the pipeline' is potentially confusing. A brand new user might wonder how to get started at all. Also, you haven't addressed what happens when the board has tasks but the activity surface shows zero agents — is that an error or normal? And your 'animated card transitions for demo-readiness' — what about the first demo where you show the board and nothing moves for 30 seconds? The board looks static."

**Response:** Three refinements:

1. **Empty state revised:** "Waiting for tasks. Start your pipeline in the terminal to see work appear here." More actionable — tells the user what to do next, not just what happened.

2. **Zero-agent state added:** "All agents idle" — explicitly calm informational text, not an error state. Normal between pipeline runs. Distinct from "stuck" or "error."

3. **Static demo proof-of-life:** The status bar's green traffic light and "Last sync: 3 s ago" timestamp prove the system is connected and polling even when no cards move. The demo isn't dead — it's waiting. Added to demo-readiness section.

**Position change:** Revised empty state copy. Added zero-agent state. Added static-demo mitigation.

---

## Cycle 4 — Confirmation Model Inconsistency

**Critic challenge:** "Your confirmation model is inconsistent. You require confirm for backward status moves and unclaim, but not for forward moves or reprioritise. A user accidentally dragging a card from 'review' to 'done' could skip the entire review process. Forward moves can be just as destructive as backward ones. Also, block requires a reason input — that IS a confirmation step. But unblock has none. If an agent blocked a task for a reason, shouldn't the user see that reason before unblocking?"

**Response:** Strongest challenge of the cycle.

- **Forward moves:** The engine's `valid_transitions()` already constrains legal moves. If review→done is valid, the pipeline permits it. The cockpit isn't a second gatekeeper. Forward moves don't need confirm because the system design already validates them.
- **Unblock:** Accepted. The user must see the block reason before removing it. Revised to: unblock shows current block reason, then "Unblock?" confirmation. Minimal friction but prevents blind unblocking of something an agent flagged for a real reason.

Governing principle refined: **Confirm when the action opposes expected flow direction.** Forward = expected, backward/unclaim/unblock = opposing.

**Position change:** Unblock now shows block reason before confirming. Confirmation principle articulated.

---

## Cycle 5 — Keyboard Navigation + Body Editor Jarring

**Critic challenge:** "You haven't addressed keyboard navigation at all. For a single-user power tool, keyboard shortcuts are essential. Also, you said the detail pane body edit switches to 'editor mode' — what does that mean exactly? A markdown textarea? A WYSIWYG editor? If you're rendering markdown in view mode and switching to raw markdown in edit mode, the visual context switch could be jarring."

**Response:**

1. **Keyboard shortcuts:** Acknowledged as debt. Full hotkey system is v2, but the base implementation must have keyboard-navigable tab order and arrow-key card traversal. Added as warning.

2. **Body editor:** v1 = click "Edit" → rendered markdown replaced with monospace textarea showing raw markdown + Save/Cancel buttons. Yes, the view→edit switch is a context shift. Accepted as v1 trade-off. Split-pane or live-preview editor is a fast-follow, not v1 scope. The explicit mode switch (click Edit, click Save) is intentional friction that prevents accidental body changes.

**Position change:** Added keyboard navigation warning. Clarified body editor as raw textarea with explicit mode toggle.

---

## Summary

5 cycles completed. Major position changes:
- Activity panel: bottom panel → sidecar tab (Cycle 1)
- Drag UX: added valid-column highlighting (Cycle 2)
- Empty/zero/static states: refined copy and added zero-agent state (Cycle 3)
- Unblock: now requires showing block reason (Cycle 4)
- Keyboard + editor: flagged as warnings (Cycle 5)

No manufactured objections. Each challenge produced a concrete refinement.
