# Cockpit Visual Audit — May 14, 2026

**Method:** Code read + playwright screenshot. Every finding verified against source.
**Scope:** All areas visible in the browser — status bar, nav rail, board, cards, sidecar, filter panel.
**Reference:** Porsche Design System React 4 component catalog.

---

## Executive Summary

The cockpit renders. The data flows. But visually it is a skeleton without skin: structural HTML with
near-zero intentional visual design. Most components render at browser-default styling. The PDS token
system is defined and partially wired, but the component catalog is almost entirely unused. Eight distinct
areas have either zero CSS, wrong component choices, or missing visual content.

Score breakdown: Status Bar 1/10 · Nav Rail 2/10 · Cards 2/10 · Sidecar 0/10 · Filter Button 0/10 ·
Filter Panel 5/10 · Columns 5/10 · Global Typography 2/10.

---

## 1. Status Bar

### What renders
```
[Health 4 issues] [Cleanup] [DR 1] [Auto]
```

### Problems

**1.1 Traffic light span is invisible.**
`<span data-testid="traffic-light" data-health={statusHealth} />` — empty span, no CSS rule targets
`[data-health]`. The intent is a status dot. It renders as zero-width invisible element.

**1.2 Task count span is always empty.**
`<span data-testid="task-count" />` — never populated with text or content. Dead placeholder.

**1.3 HealthBadge popover has no CSS.**
The popover is `<div ref={popoverRef} role="dialog">` — raw div with no `position: absolute`,
no `z-index`, no `background`, no `box-shadow`, no `border`. When opened, it appears inline inside
the flex status bar, displacing other items. No CSS file exists for HealthBadge.

**1.4 DRStatusIndicator popover has no CSS.**
Same pattern — `<div ref={popoverRef}>` with no positioning or visual styling. Opens inline,
displaces status bar content.

**1.5 CleanupPanel inline states are unstyled.**
In `confirming` state: a raw `<div role="dialog">` renders inline in the status bar with two
`PButton`s. No overlay, no modal, no positioning. Same for `done` state (results list).

**1.6 No app identity.**
The visible `<h1>OwlBear Cockpit</h1>` is fully hidden (`clip: rect(0,0,0,0)`). No logo, no app
name, no brand mark is visible anywhere in the status bar. The bar looks like a random row of
secondary buttons.

**1.7 All status bar actions look identical.**
Health badge, Cleanup, DR indicator, and ThemeToggle all render as PDS `variant="secondary"` buttons
or as the custom `icon-button` class. No visual differentiation by role, urgency, or type. A user
cannot distinguish "system health alert" from "maintenance action" from "theme switcher".

**1.8 PButton is the wrong component for status indicators.**
Status bar indicators (Health, DR count) would be better served by `PBadge` or `PTag` with color
variants. `PButton variant="secondary"` implies a discrete action, not a status reading.

### PDS components available but unused here
- `PBadge` — count badge with semantic color (success/warning/error/neutral)
- `PTag` — compact labeled indicators
- `PPopover` — would handle popover positioning automatically

---

## 2. Nav Rail

### What renders
A 56px column with a `PButton` containing an SVG grid icon and the text "Kanban".

### Problems

**2.1 PButton is wrong for nav items.**
`PButton` is a call-to-action component. For navigation, `PButtonPure` (icon-only, no border/fill)
is the correct PDS pattern. The current button has a border and fill that conflicts with the nav rail's
role as a persistent sidebar.

**2.2 "Kanban" text is redundant and overflows.**
The nav rail is 56px wide. The `PButton` renders "Kanban" as text next to the icon. The text is either
truncated or overflowed, and adds no value when there is only one nav destination.

**2.3 No active/hover visual state.**
`aria-current="page"` is set but no CSS rule targets `[aria-current="page"]` to show a visual active
state. The nav item always looks the same regardless of page.

**2.4 `tabIndex={-1}` makes the nav button keyboard-inaccessible.**
This is a deliberate but unexplained choice. A nav button that cannot be reached by keyboard Tab
traversal is an accessibility regression.

**2.5 Only one nav destination exists.**
The nav rail is designed for multiple items but has one. Routing for future items (settings, etc.)
is not scaffolded.

### PDS components available but unused here
- `PButtonPure` — icon button without background/border, appropriate for nav items

---

## 3. Board (Kanban Grid)

### What renders
A grid of columns. The board toolbar has a plain `<button>` for filters.

### Problems

**3.1 Filters button is browser-default.**
```tsx
<button ref={filterToggleRef} type="button" tabIndex={-1}>Filters</button>
```
No `className`, no CSS rule. Renders as the platform's native `<button>` style. Does not match
PDS button styling. Also has `tabIndex={-1}` (keyboard-inaccessible by design — unexplained).

**3.2 Active filter count indicator is an unstyled `<span>`.**
When filters are active: `<span data-testid="filter-result-count">N / M tasks</span>` renders
as plain inline text with no visual emphasis. There is no visual indication that filters are active
beyond this text.

**3.3 Board grid layout is in JSX inline styles, not CSS.**
The grid is styled via `style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: ..., padding: ... }}`.
This works but: (a) it cannot be overridden by breakpoints in CSS, (b) it is not themeable via
tokens, (c) it creates inconsistency with the rest of the codebase.

**3.4 Board toolbar has no layout class.**
The filter toggle + result count strip is `<div style={{ display: 'flex', ... }}>` — also inline.
No `className`, no CSS file entry for the board toolbar.

**3.5 Loading state is a bare `<div>`.**
```tsx
if (loading) return <div data-testid="loading-indicator">Loading…</div>
```
Plain text. No `PSpinner`, no visual treatment.

**3.6 Error state is a bare `<div>`.**
```tsx
if (error) return <div data-testid="error-message">{error}</div>
```
Plain text. No `PInlineNotification`, no icon, no color.

### PDS components available but unused here
- `PButton` or `PButtonPure` — for the Filters toggle
- `PSpinner` — for board loading state
- `PInlineNotification` — for board error state
- `PChip` or `PTag` — for active filter count indicator

---

## 4. Cards

### What renders
A white card with a left-border color signal, containing one `<span>` with the task title.

### Problems

**4.1 Cards show only the task title.**
`Card.tsx` renders exactly one text element:
```tsx
<span data-testid="card-title">{task.title}</span>
```
Everything else — task ID, priority level, tags, blocked/claimed state, timestamps — is invisible.
The left border changes color by signal state, but there is no text or icon indicator for the signal.

**4.2 No task ID visible.**
Users cannot identify which task they are looking at without clicking into the detail panel.

**4.3 No priority display.**
Priority (critical / needed / important / nice-to-have / someday) is stored in `data-priority`
attribute but never rendered as text, badge, or visual indicator. Critical tasks look identical
to someday tasks.

**4.4 No tags displayed.**
`task.tags` exists but is never rendered on the card. A task with 5 tags looks identical to one
with none.

**4.5 No blocked/claimed text or icon.**
The left border changes color when blocked or claimed but there is no explicit "Blocked" label,
lock icon, or similar. Color-only signaling fails for color-blind users and is not self-explanatory.

**4.6 Card has no minimum height enforcement.**
`min-height: 48px` is in Card.css, but very short titles produce very short cards. Long lists
of short-titled tasks look cramped and hard to read.

### PDS components available but unused here
- `PTag` — for status/priority tags on cards
- `PBadge` — for priority count indicators
- `PIcon` — for blocked/claimed icons

---

## 5. Sidecar

### What renders
A right panel with: collapse button, DR list as `<ul><li>`, `<p-tabs>` with Detail and Activity tabs.

### Problems

**5.1 DR list renders as raw HTML `<ul><li>` with bullet points.**
`DecisionViewport.tsx` returns:
```tsx
<ul>
  {items.map(item => (
    <li key={item.id}>
      <button>{item.task_id}</button>
      <button>
        <PText>{item.agent}</PText>
        <PText>{item.request_type}</PText>
        <PText>{item.created}</PText>
        <PText>{item.body_preview}</PText>
      </button>
    </li>
  ))}
</ul>
```
Visible in the screenshot: a bullet point "•" followed by "1534", then a bordered box with raw text.
There is no CSS file for `DecisionViewport`. The outer `<button>` containing stacked `<PText>` nodes
has browser-default button styling (border, background, padding). All text is the same size and weight.
There is no visual hierarchy between task ID, agent name, age, and body preview.

**5.2 Sidecar has no layout CSS.**
The sidecar `<aside className="shell__sidecar">` has `overflow: hidden` and a border, but no
internal layout — no padding, no flex/grid structure, no gap between sections. The collapse button,
DR list, and tabs are stacked with zero space between them.

**5.3 Collapse sidecar button has wrong placement and styling.**
The "Collapse sidecar" `<button className="icon-button">` renders at the top of the sidecar with
no visual separation from the content below it. It looks like body text with a border.
Good pattern: a small arrow icon button pinned to the left edge of the sidecar.

**5.4 `<p-tabs>` web components render with no visual tab bar.**
The tabs are declared as `<p-tabs>` / `<p-tabs-item>` (PDS web component syntax). In the
screenshot, the tabs appear as "Detail Activity" — two text nodes side-by-side with no separator,
no underline, no active indicator, no background. Either (a) PDS web components are not fully
initialized in the Playwright snapshot, or (b) the tab bar itself lacks styling context.
The correct pattern in this React app would be the React component `<PTabs>` / `<PTabsItem>`.

**5.5 Task detail placeholder has no styling.**
"Select a task to view details." renders as a plain text `<div>`. No padding, no centering,
no color treatment. It sits at the top of the detail tab area with zero visual affordance.

**5.6 Sidecar content area has no padding.**
All content in the sidecar `<div id="shell-sidecar-content">` starts at the raw edge. No margin,
no padding. Text touches the sidecar border.

### PDS components available but unused here
- `PTabs` / `PTabsItem` — React wrapper (vs. raw web component) — handles tab styling
- `PText` with `size` / `weight` props — for DR item hierarchy
- No CSS file exists for DecisionViewport at all

---

## 6. Filter Panel

### What renders
A panel with: close button, text input, priority select, tags multi-select, blocked checkbox.

### Problems

**6.1 Text search input is a raw `<input>`, no PDS wrapper.**
The filter panel uses `<input ref={textInputRef} type="text" ...>` with no `PTextFieldWrapper`.
The input has browser-default styling (thin border, no label styling, no focus ring matching PDS).

**6.2 Blocked checkbox is a raw `<input type="checkbox">`.**
No PDS `PCheckboxWrapper` or equivalent. Renders as browser-default checkbox with a label.

**6.3 FilterPanel.css has no layout rules.**
The CSS file has only:
```css
.filter-panel { background: ...; border: ...; padding: ...; }
```
No layout for the filter controls (label+input groups, spacing between filter rows, button alignment).

**6.4 Panel appears inline below the filter button, not as a floating panel.**
The FilterPanel is placed in document flow below the filter toggle, pushing the board grid down.
This is functional but awkward — the board jumps when the panel opens. A floating overlay panel
would be a better pattern.

### PDS components available but unused here
- `PTextFieldWrapper` — for the text input
- `PCheckboxWrapper` — for the blocked checkbox

---

## 7. Columns

### What renders
A grid of column cards with header (status name + count badge) and scrollable body.

### Problems (minor compared to other areas)

**7.1 Column header text is all-lowercase from data.**
Status names come from the API as lowercase (`backlog`, `in-progress`). CSS `text-transform: capitalize`
is applied, which handles `Backlog` correctly but renders `In-Progress` (capitalizing both words
around the hyphen). This is visually inconsistent with standard title casing.

**7.2 No "Done" column visual distinction.**
Completed tasks in "Done" look identical to tasks in any other column. Common pattern: Done column
has a muted/dimmed card style.

**7.3 Empty-state text for named statuses reveals internal API names.**
"No in-progress tasks" exposes the internal status string. "No tasks in progress" or "Nothing here"
would be more polished.

---

## 8. Global Typography & Spacing

### Problems

**8.1 No font size scale.**
PDS defines a type scale but the cockpit does not use it. All body text uses browser-default 16px.
Card titles, column headers, sidecar text, and status bar labels are all the same size.

**8.2 No semantic text hierarchy.**
There is no `h2`, `h3`, or `PHeadline` usage in the cockpit outside the hidden `<h1>`. The DR
section has no heading. The sidecar has no section labels. The board has no page title.

**8.3 Line-height and letter-spacing are browser defaults.**
PDS specifies tighter letter-spacing for labels and UI text. This is not applied.

---

## PDS Catalog: Used vs Available

| Component | Used | Available | Gap |
|-----------|------|-----------|-----|
| PButton | ✅ | ✅ | Overused — used where PBadge or PTag would fit better |
| PButtonPure | ❌ | ✅ | Should be used for nav rail, icon-only actions |
| PBanner | ✅ | ✅ | OK — used for mutation errors |
| PSpinner | ✅ | ✅ | OK — used in cleanup, not in board loading |
| PText | ✅ | ✅ | Used but without `size` or `weight` props |
| PSelect | ✅ | ✅ | OK — filter priority |
| PMultiSelect | ✅ | ✅ | OK — filter tags |
| p-tabs / p-tabs-item | ⚠️ | ✅ | Web component syntax, not React wrapper |
| PTabs / PTabsItem | ❌ | ✅ | React wrapper — should replace web component syntax |
| PBadge | ❌ | ✅ | **Missing** — needed for DR count, health status |
| PTag | ❌ | ✅ | **Missing** — needed for card tags, priority indicators |
| PIcon | ❌ | ✅ | **Missing** — needed for blocked/claimed/nav |
| PPopover | ❌ | ✅ | **Missing** — needed for health/DR popovers |
| PTextFieldWrapper | ❌ | ✅ | **Missing** — filter text input |
| PCheckboxWrapper | ❌ | ✅ | **Missing** — filter blocked checkbox |
| PInlineNotification | ❌ | ✅ | **Missing** — board loading/error states |
| PModal | ❌ | ✅ | **Missing** — cleanup confirm, archival confirm |
| PDivider | ❌ | ✅ | **Missing** — section separators in sidecar |
| PSegmentedControl | ❌ | ✅ | **Missing** — activity filter (all/active/blocked) |
| PHeadline | ❌ | ✅ | **Missing** — section headings |
| PChip | ❌ | ✅ | **Missing** — active filter chips |

---

## Proposed Work Areas (for Planner)

The following are 8 distinct work areas in priority order. Each is independent enough to be a
separate task. Exact AC, test strategy, and sequencing are for the Planner to determine.

### WA-1: Sidecar layout + DR list (Highest priority — worst area)
- Add CSS for `shell__sidecar` interior: padding, flex column layout, gap between sections
- Redesign `DecisionViewport`: replace `<ul><li>` with styled DR cards, add typography hierarchy
  (agent name bold, age muted, preview normal), add CSS file
- Replace `<p-tabs>` / `<p-tabs-item>` web component syntax with `<PTabs>` / `<PTabsItem>` React
  wrapper for proper tab bar rendering
- Style the task detail empty state (centered, muted, with padding)
- Reposition or restyle the collapse button (icon-only, pinned to sidecar edge)

### WA-2: Status bar indicators
- Replace `traffic-light` invisible span with a visible dot/status indicator (CSS `[data-health]` rule)
- Remove or populate the `task-count` span
- Style HealthBadge and DRStatusIndicator popovers: `position: absolute`, `z-index`, `box-shadow`,
  `background`, `border-radius`, `min-width`
- Add visual differentiation between Health (error-color), DR (warning-color), and Cleanup (neutral)
- Consider: app name or icon in status bar (branding)

### WA-3: Card content richness
- Add task ID (e.g., `#1534`) to card as muted secondary text
- Add priority badge/tag (color-coded or icon)  
- Add tags as small `PTag` chips (truncated if too many)
- Add explicit blocked/claimed label or icon (not color-only)
- Consider: two-line card layout (title + metadata row)

### WA-4: Filter button and toolbar
- Replace plain `<button>` with `PButton` or styled equivalent
- Remove `tabIndex={-1}` from filter toggle (accessibility)
- Style active filter count indicator as `PChip` or badge
- Extract board toolbar inline styles to `KanbanBoard.css`

### WA-5: Filter panel polish
- Wrap text input in `PTextFieldWrapper` with label
- Wrap blocked checkbox in PDS checkbox wrapper
- Add layout CSS to `FilterPanel.css` (label+control rows, spacing)
- Assess: floating panel vs inline (floating preferred)

### WA-6: Board states (loading/error)
- Replace `<div>Loading…</div>` with `PSpinner` centered in board area
- Replace `<div>{error}</div>` with `PInlineNotification` with appropriate state

### WA-7: CleanupPanel dialog states
- Replace inline confirming/done divs with `PModal` or positioned overlay
- The confirm dialog currently renders inline in the status bar, displacing content

### WA-8: Nav rail (Low priority — single item)
- Replace `PButton` with `PButtonPure` for icon-only nav item
- Add CSS rule for `[aria-current="page"]` active state
- Address `tabIndex={-1}` — should this be keyboard-accessible?

---

## What NOT to touch

- Token architecture (`tokens.css`) — 20 color + 13 non-color tokens, tested and stable
- Column.css — structure is correct (header/body/empty/count badge), only minor text issues
- Card.css — layout, signal colors, shadow are correct — extend don't replace
- Shell.css grid layout — status bar/nav-rail/workspace/sidecar grid is correct
- SessionRows.css — session row state colors are correct
- All existing test contracts — do not change test assertions, only implementation

---

## References
- PDS React 4 component catalog: https://designsystem.porsche.com/v3/components/overview
- Screenshot captured: `/tmp/cockpit-loaded.png`
- Key source files: `Shell.tsx`, `Card.tsx`, `DecisionViewport.tsx`, `FilterPanel.css`,
  `KanbanBoard.tsx`, `Column.tsx`, `DRStatusIndicator.tsx`, `HealthBadge.tsx`
