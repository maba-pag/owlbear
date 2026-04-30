# End-User Experience Stance

## Position

The DR/AR script replacement is a clear UX improvement — moving from raw YAML editing to a Cockpit-native resolve flow. The core interaction model should be: **persistent status bar indicator → popover list → modal resolve dialog**. This follows the established HealthBadge pattern and requires no shell layout changes.

## Usability Reasoning

### Status Bar Indicator

- **Single attention color + visible count number.** Do not differentiate DR vs AR by color. Both are pipeline-blocking; both need user attention. The distinction (decide vs. do) is informational metadata visible in the list, not a badge-level behavioral fork.
- **Always visible.** At zero pending, show dormant/OK state (not hidden). This confirms the system is monitoring — same pattern as HealthBadge's "No issues" state.
- **Responsive polling.** The indicator must NOT use the default 60s scan interval. DR creation is pipeline-blocking; the user should see the badge update within 5–10 seconds, not a minute. A dedicated short-interval poll or event-driven update is required.
- **Non-color cues.** Count number is always visible. Aria-label announces count and type ("2 pending decision requests"). Screen reader live region for count changes.

### Resolve Interaction

- **Click opens popover list.** Always the same behavior regardless of count (0 shows "No pending items," 1+ shows list). Consistent click target = predictable UX.
- **List items show:** task ID, request type label (DR/AR as text, not color), first-line preview of body.
- **Selecting a list item opens a modal dialog.** The dialog provides space for:
  - Header: task reference + agent name
  - Body: full DR content rendered as markdown (not raw YAML)
  - Response: textarea + confirm button
- **Why modal, not inline popover:** DR bodies can be multi-paragraph. The user needs to read context, think, and compose a response. A popover is too spatially constrained for this. The modal is the escalation path — consistent with existing ConfirmDialog/RepairPanel patterns.

### Stale-State Protection

- **Never auto-close the resolve dialog while it has focus or contains a draft.** If `pick_tasks` resolves the DR while the user is composing a response, show a non-dismissive banner: "This item was resolved elsewhere." Preserve textarea content. Let the user dismiss manually.
- **Popover list:** remove resolved items on next poll. If list empties while open, show "All resolved" message.

### Agent Ergonomics (`create_dr`)

- **UX principle:** minimize required parameters. The agent provides what it knows (task, type, question). The engine handles timestamps, filenames, frontmatter, and blocking.
- **Response contract:** tool must confirm that blocking was applied. The agent needs certainty that it can move on without polling. Something like: `{created: true, path: "...", task_blocked: true}`.
- **No query tool needed.** Agents don't need to read DRs — users resolve them. The engine unblocks on resolve. Clean separation.

### Fallback Path

- **Documented in the replacement skill, prominently.** Not in an appendix. Agents that lose MCP connectivity need to know the manual procedure.
- **Error messages do NOT expose raw paths.** Say: "DR creation failed — task remains unblocked. See skill documentation for manual fallback." This avoids hard-coding storage internals into the agent-visible contract.
- **The fallback is:** write a correctly-formatted file to the pending directory, then the next `pick_tasks` call picks it up. This is an escape hatch, not a primary path.

### DR Content Readability

- **Users see rendered prose, not syntax.** The resolve modal renders markdown body with proper formatting. YAML frontmatter is invisible — it's engine metadata.
- **Visual hierarchy:** metadata header (small, muted) → body (primary, full-width prose) → response area (action zone). The question dominates; chrome is minimal.

## Key Trade-offs

| Choice | Gains | Costs |
|--------|-------|-------|
| Single color (no DR/AR hue split) | No new legend to learn; works for <1/day events | Slightly less glanceable type info at badge level |
| Modal for resolve (not inline) | Room for multi-paragraph reading + composition | Extra click from popover; needs focus-trap implementation |
| Always-visible dormant state | Confirms system is monitoring; diagnostic value | Minor visual noise when nothing is pending |
| No toast notification | Simpler; avoids notification fatigue | 60s worst-case discovery if user isn't looking at status bar (mitigated by shorter poll) |
| Fallback in skill only | Doesn't hard-code internals in error contract | Requires agent to have skill loaded to recover |

## Warnings

1. **Polling interval is the critical implementation detail.** If the indicator uses the 60s scan default, the "immediate awareness" promise breaks. This must be explicitly specified and tested.
2. **Draft-loss on stale resolution is a real risk.** The modal MUST preserve user input if the backend resolves the item mid-composition. Test this scenario explicitly.
3. **Accessibility is aspirational.** Current Cockpit primitives (ConfirmDialog, RepairPanel) are thin containers without proper focus traps or aria-live regions. The DR modal should raise the bar, but acknowledge it needs investment.
4. **Don't over-invest in DR/AR type distinction.** Both are blocking attention requests. The user action is identical: read and respond. Type is metadata for context, not a UX fork.

## Confidence

0.74

Reduced from higher because: polling interval needs validation against actual implementation constraints, modal a11y relies on primitives that don't yet exist in Cockpit, and the exact create_dr contract shape is still open (my stance describes UX principles, not a frozen API).
