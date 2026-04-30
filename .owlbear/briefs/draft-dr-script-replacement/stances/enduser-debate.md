# End-User Debate Log

## Cycle 1

### Draft Position

1. **Multi-color badge**: Amber for DR, blue for AR, red for critical. Mixed state shows highest-priority color + count.
2. **Panel, not popover**: Status bar opens sidebar panel listing DRs; selecting one opens focused resolve view.
3. **Agent ergonomics**: 3 required params (task_id, request_type, body). Response confirms blocking applied.
4. **Fallback**: Document in skill AND surface in error messages with exact file paths.
5. **Toast notification**: VS Code toast when DR created, linking to resolve UI. Status bar insufficient alone.
6. **Content readability**: Card with task link, agent name, rendered markdown body, textarea for response.

### Critic Challenges (Cycle 1)

1. **(critical)** Color contradiction: DRs are blocking by definition — calling them "amber" while acknowledging they stall the pipeline is inconsistent with reserving red for "critical/blocking."
2. **(critical)** Mixed-state rule recreates the conflation: collapsing DR+AR into "highest priority color + count" still hides whether user needs to decide or act.
3. **(moderate)** Cockpit already uses red/orange/blue for priorities. Teaching a new rare-event color legend for <1/day events adds cognitive load.
4. **(moderate)** HealthBadge already uses popover-with-actions pattern. "Popover is inappropriate" is asserted, not demonstrated.
5. **(critical)** Sidebar demands shell reallocation — sidecar already committed to Detail/Activity tabs. No coexistence model provided.
6. **(moderate)** Toast argument ungrounded — 3s polling + persistent indicator may suffice. "30+ minutes" miss scenario assumes Cockpit closed, which neither toast nor indicator solves.
7. **(moderate)** create_dr contract frozen too early — marked as open tension in context.
8. **(moderate)** Fallback over-exposed — error messages with raw paths hard-code storage internals into visible contract.

**Blind spots**: No stale-state model, no accessibility beyond color, no empty/single-item behavior, no task-context routing model, no Cockpit-closed notification model.

### Revisions Applied

- Dropped multi-color badge → single attention color + count
- Dropped sidebar → popover list + modal dialog (consistent with HealthBadge pattern)
- Dropped toast requirement → persistent indicator sufficient
- Dropped frozen create_dr contract → UX principle only
- Dropped path-in-error-messages → skill-documented fallback
- Added: accessibility (aria-label, non-color cue), stale-state handling, special cases (0/1/2+ items)

---

## Cycle 2

### Refined Position

1. Single attention color + visible count. Type differentiation inside list, not on badge.
2. Popover list → modal dialog for resolve. 1-item shortcut: skip list, open dialog directly.
3. UX principle: minimize params, confirm blocking in response. No frozen contract.
4. Skill-documented fallback, not error-message-exposed paths.
5. Persistent indicator only. Toast dropped.
6. Modal renders: task ref, agent, markdown body, textarea. Stale = show resolved + close.
7. Accessibility: aria-label with count, non-color via number, focus management.

### Critic Challenges (Cycle 2)

1. **(critical)** Polling interval claim wrong: scan polling defaults to 60s (useScanPolling.ts), not 3s. "Almost immediate" appearance is unsupported.
2. **(moderate)** 1-item shortcut makes click behavior count-dependent and unstable. HealthBadge always opens same container regardless of count.
3. **(critical)** Stale-state handling has draft-loss gap: auto-closing while user is typing destroys their response. No draft preservation defined.
4. **(moderate)** Hidden-at-zero removes observability. HealthBadge shows explicit "No issues" / OK state. Collapsing "none" into "absent" loses diagnostic confirmation.
5. **(moderate)** Popover-to-dialog escalation assumes mature a11y layering that current Cockpit doesn't demonstrate.
6. **(minor)** DR/AR distinction still conceptually unsettled — dropped at badge level but retained in list without clear user value.

**Blind spots**: No loading/error state for indicator, no behavior for count mutation while popover open, no live-announcement model for screen readers on count change, no post-auto-resolve inspectability.

### Final Revisions

- Dropped 1-item shortcut → always show popover list (consistent click behavior)
- Stale state → never auto-close while dialog has focus; show banner "resolved elsewhere," preserve draft
- Zero state → show dormant indicator (like HealthBadge "No issues") rather than hiding
- Polling → note that DR indicator needs responsive interval, not 60s scan default
- A11y → acknowledge current primitives are thin; proper focus trap is aspirational for P3
- DR/AR → both are "items needing attention"; type is informational metadata in list, not behavioral fork
