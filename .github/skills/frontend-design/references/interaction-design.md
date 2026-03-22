# Interaction Design Reference

> OwlBear adaptation — see `../NOTICE.md` for attribution.

Interaction design defines how a UI responds to user input. Every interactive
element must communicate its state, support keyboard and pointer input, and give
the user a clear model of what will happen before they commit.

---

## Interactive States

Every interactive element (button, link, input, toggle) must have all five states:

| State | CSS pseudo-class | Visual treatment |
|-------|-----------------|-----------------|
| Default | (none) | Baseline appearance |
| Hover | `:hover` | Subtle background or border change |
| Focus | `:focus-visible` | Visible focus ring (see below) |
| Active | `:active` | Pressed treatment — slight inset, darker |
| Disabled | `:disabled` | Reduced opacity (≥ 40%), not-allowed cursor |

Disabled elements should use `aria-disabled="true"` on non-native elements and
must not receive keyboard focus.

---

## Focus Indicators

`:focus-visible` is the correct selector. Never simply remove focus outline
without providing a replacement — this is a **universal blocker**.

```css
:focus-visible {
  outline: 2px solid var(--color-brand);
  outline-offset: 2px;
  border-radius: inherit;
}

/* High-contrast offset for dark backgrounds */
:focus-visible {
  outline: 2px solid var(--color-brand);
  box-shadow: 0 0 0 4px oklch(100% 0 0 / 80%);
}
```

WCAG 2.2 SC 2.4.11: Focus appearance must have a contrast ratio ≥ 3:1 against
adjacent colors and differ from the non-focused state.

---

## Form Inputs

- **Always use `<label>`** associated via `for`/`id` or wrapping. Placeholder
  text is not a label — it disappears on input and fails screen readers.
- Group related fields with `<fieldset>` + `<legend>`.
- Show validation feedback **after the user leaves a field** (on blur), not while
  they are typing.
- For required fields, mark them visually (asterisk) and in the `required` attribute.

```html
<label for="email">Email address <span aria-hidden="true">*</span></label>
<input id="email" type="email" required autocomplete="email"
       aria-describedby="email-hint">
<div id="email-hint" class="hint">We'll send confirmation here.</div>
```

---

## Dialog and Popover

Native `<dialog>` now has good browser support. Prefer it over custom ARIA
solutions:

```html
<dialog id="confirm-dialog" aria-labelledby="dialog-title">
  <h2 id="dialog-title">Delete item?</h2>
  <p>This action cannot be undone.</p>
  <button autofocus>Cancel</button>
  <button>Delete</button>
</dialog>
```

Rules for dialogs:
- Focus must move to the dialog on open and return to the trigger on close.
- Trap focus inside the dialog while open (`Tab` cycles within).
- `Esc` must close the dialog.
- Use `inert` on background content to prevent interaction leak.

---

## Undo vs. Confirm

Choose the right constraint model:

| Pattern | Use when | Avoid when |
|---------|----------|------------|
| **Undo** (reversible action, toast with Undo) | Soft delete, dismiss, archive | Immediate destructive or external effects |
| **Confirm dialog** | Irreversible, destructive, or external action | Simple operations the user can undo |
| **Optimistic UI** (do it immediately, roll back on error) | Network calls with low failure rate | Irreversible operations |

Avoid confirm dialogs for low-stakes actions — they train users to click past them.

---

## Keyboard Patterns

Common keyboard navigation contracts:

| Pattern | Keys |
|---------|------|
| Single-select list | Arrow keys to move selection, Enter to activate |
| Menu | Arrow keys to navigate, Esc to close, Tab to leave |
| Tab panel | Arrow keys to switch tabs (roving tabindex) |
| Combobox/autocomplete | Arrow keys to navigate suggestions, Enter to select |

Use `roving tabindex` (one `tabindex="0"`, rest `-1`) for widget-internal navigation.
Use `role="listbox"`, `role="option"`, `role="combobox"` as appropriate.

---

## Destructive Actions

- Primary CTA must be visually dominant; destructive actions should be de-emphasised.
- Destructive buttons use `--color-danger` but should NOT be the auto-focus target.
- In a confirm dialog, focus the Cancel button (or the dialog container), not Delete.
