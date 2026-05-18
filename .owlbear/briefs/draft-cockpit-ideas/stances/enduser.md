# End-User Stance — Cockpit Ideas Notebook

## User Experience Stance

The Ideas tab is a preference feature (acknowledged in D5) — its value is cockpit co-location, not editing superiority. That makes the UX bar different from a primary tool: it must feel *intentional and safe*, not necessarily *powerful*. A textarea + save button is the right v1 pattern. The feature succeeds if capturing an idea is fast and losing an idea is impossible. It fails if data loss is possible or if the interaction feels like an afterthought bolted onto the dashboard.

## Usability Reasoning

### Tiered Recommendations

**Must-have for usable v1:**

1. **Unsaved-changes guard on all exit paths.** Explicit-save means the user controls persistence — but that contract only works if every exit path respects it. Route navigation (tab switch), browser refresh, and browser close must all warn when dirty state exists. Route-switch uses a confirmation dialog; browser refresh/close uses `beforeunload`. Without this, explicit-save becomes a data-loss trap. This is not a feature — it's the minimum contract that makes explicit save trustworthy.

2. **File-absence is empty state, not an error.** When `.owlbear/ideas.md` doesn't exist, show an empty textarea with placeholder text (e.g., "Capture your ideas...") and create the file on first save. The user opened the Ideas tab to write — put them in the editor immediately. File creation is an implementation detail. Separately, actual API failures (network, disk, server) must show proper error feedback via the existing error envelope. Note: the create-on-first-save behavior needs to be agreed as a cross-layer contract between frontend and backend; the UX intent is clear but the backend contract is still open per research-notes Q2.

3. **Default to edit mode.** The existing TaskFieldsEditor starts in preview mode with an Edit toggle — that's wrong for the Ideas tab. The primary action on the Ideas tab is *writing*, not reading. The textarea must be visible and focused when the tab opens. If preview is included, it's a secondary mode the user switches to; edit is home.

**Should-have (strongly recommended for v1):**

4. **Preview toggle.** The dependencies (react-markdown, remark-gfm, rehype-sanitize) are already bundled. The implementation cost is real but bounded — mode state, dual render paths, toggle control, and test coverage; not trivial but small relative to the page component. The UX argument: a scratchpad you revisit benefits from rendered markdown. Headings, lists, and links are significantly easier to scan when rendered vs raw. However, I acknowledge the evidence gap: the primary use case may be capture-and-go rather than revisit-in-cockpit (the user may revisit in VS Code instead). If the team wants to cut it to keep v1 minimal, the feature still works without it — but re-reading raw markdown in a textarea is a noticeable quality drop. Phase 2 inclusion is acceptable. Note: if included, the toggle must default to edit mode (see #3).

5. **External-edit awareness.** The user accepted that VS Code is the better editor (D5), which means dual-surface use is *expected*, not an edge case. If someone jots an idea in VS Code and then opens the cockpit, they should see the current content. Minimum viable approach: re-fetch content when the Ideas route becomes active (or on tab focus via `visibilitychange`). The complication: mtime and OCC were explicitly cut from the API contract. Without version tracking, the only safe behavior on re-fetch is: if local state is clean, silently replace with fresh content; if local state is dirty, show a notice ("File changed externally — reload or keep editing"). This is imperfect but better than silently showing stale content.

**Nice-to-have (polish, can defer):**

6. **Cmd+S / Ctrl+S keyboard shortcut.** Deeply ingrained text-editing reflex that improves the feel of longer writing sessions. However, the existing cockpit task editor uses button-only save and users accept it — so this isn't essential. If added, scope the handler to the Ideas route/focused textarea to avoid conflicts with document-level keyboard handlers elsewhere in the shell (KanbanBoard, modals, etc.). Recommended as a post-v1 polish item.

7. **Tab icon.** The icon and accessible label should work together. "Ideas" as the aria-label is clear. For the visual icon, prefer something that signals user-authored content (writing, document, note) over abstract concepts. The specific PDS icon choice is a minor detail — consistency with the nav-rail pattern matters more than the exact glyph.

## Key Trade-offs

| Decision | Trade-off |
|----------|-----------|
| Explicit save over auto-save | Gives user control but requires unsaved-changes guards on every exit path |
| Preview toggle in v1 vs Phase 2 | Better re-reading experience vs smaller initial scope; dependencies are bundled but integration isn't free |
| External-edit re-fetch without mtime | Better freshness but no true conflict resolution; dirty + external change is a degraded experience |
| Cmd+S deferred | Slightly worse flow during long sessions but consistent with existing cockpit save patterns |

## Warnings

- **Data-loss guard is non-negotiable.** Without unsaved-changes interception on route change, refresh, and close, explicit save actively harms the user. This is the one item that must not be cut.
- **Dual-surface use is the norm, not an edge case.** The feature's entire justification is co-location alongside VS Code. Design accordingly — stale content will be encountered.
- **Don't confuse "small feature" with "no UX requirements."** The feature is small in code but touches a trust-sensitive interaction (text I typed + save I control). Getting the save contract wrong has outsized impact on whether the user trusts and returns to the feature.

## Confidence

0.76 — Strong on data-loss prevention and empty-state positions; moderate on preview toggle (evidence gap on revisit-in-cockpit vs revisit-in-VS-Code); low on specific icon recommendation. The tiered structure reflects honest uncertainty about what must ship in v1 vs what can follow.
