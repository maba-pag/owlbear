# Cockpit Browser Notifications for Decision Requests

## Problem

When an agent creates a DR or blocks a task, the user only discovers it by actively checking the cockpit or board. DRs can sit pending for hours while the pipeline stalls and the user is unaware. There's no push notification mechanism.

## Proposed Feature

Use the Web Notifications API to send browser-level notifications when DRs are created or tasks need attention. Works even when the cockpit tab is backgrounded or minimized.

### How it works

1. **Permission request:** On first cockpit visit (or via a settings toggle), call `Notification.requestPermission()` — the browser shows its native "Allow notifications from this site?" prompt.
2. **SSE listener:** The cockpit frontend already subscribes to SSE events for board changes. When an SSE event indicates a new DR was created, fire a browser notification.
3. **Notification content:** Title: "Decision needed" or "Action required". Body: task ID, agent name, preview of the DR question. Icon: cockpit favicon.
4. **Click action:** Clicking the notification focuses the cockpit tab and navigates to the DR (or the new Decisions tab once that exists).

### Implementation

**Frontend only — no backend changes needed** (assuming SSE already delivers DR-creation events).

```typescript
// Pseudo-code
if ('Notification' in window && Notification.permission === 'granted') {
  const n = new Notification('Decision needed', {
    body: `Task #${dr.taskId}: ${dr.preview}`,
    icon: '/favicon.ico',
    tag: `dr-${dr.id}`, // prevents duplicate notifications
  });
  n.onclick = () => {
    window.focus();
    navigate(`/decisions/${dr.id}`);
  };
}
```

### SSE event prerequisite

Verify that SSE events include DR creation. If not, the backend needs to emit a `dr_created` event type when `create_dr` is called. This may require adding an SSE publish call in the DR creation route.

### Scope

- Frontend: ~20 lines of notification logic + permission request UI
- Backend: possibly one SSE event emission in DR creation route (if not already present)
- No new dependencies
- No system-level daemon or extension needed

### UX considerations

- Don't spam: only notify for pending DRs, not resolved ones
- Notification tag (`dr-${id}`) prevents duplicates if SSE reconnects
- Respect permission: if user denies, don't ask again (browser handles this)
- Consider a cockpit settings toggle for notification preferences
- Sound: browser notifications can include sound — default to silent, let user enable

### Extensions

- Notify for other events: task blocked for >1h, stale claims, pipeline stalls
- Notification grouping: "3 decisions pending" instead of individual notifications
- Desktop badge on the cockpit PWA icon (if cockpit becomes a PWA)
