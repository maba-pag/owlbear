# p-switch

The `p-switch` component is a control that is used to quickly switch between two possible states. A switch is only used for these binary actions that occur immediately after the user “flips the switch”. Commonly it is used for “on/off” state.

It is a controlled component. This means it does not contain any internal state, and you got full control over its behavior.

The `p-switch` component can be used with a visible or hidden label, but it's recommended to keep the label visible for better accessibility whenever possible. A `label` is a caption which informs the user which action is followed by interaction. When used with hidden label, it's best practice to provide a descriptive label text for screen readers.

You can use native `click`, `focus`, `focusin`, `blur` and `focusout` events on the `p-switch`.

## Usage

### Do:

- Use it when an instant response to applied settings is required without explicit action.
- Use to enable or disable a mode, feature, or function.
- Use when the user is toggling independent features or behaviors.
- Use the label to describe the affected property.
- Use the right-aligned version for lists (especially for handling on mobile devices).
- Use the stretched version for lists on mobile or smaller containers.

### Don't:

- Don't use it if a setting requires a button press before it can take effect (use a [Checkbox](../p-checkbox/p-checkbox.md) instead).
- Don't use anything longer than two words in the label whenever possible.
- Don't use the switch for multiple-choice questions.
- Don't use slide Switch when an intermediate state is required (Use [Checkbox](../p-checkbox/p-checkbox.md) instead).
- Don't use the label to describe the state of the component.

---

## Related Components

- [Checkbox](../p-checkbox/p-checkbox.md)
- [Button](../p-button/p-button.md)

## Accessibility support

### Keyboard

| Key / state | Function |
| --- | --- |
| `Tab`, `Shift-Tab` | Moves focus to the scroll container or to next (or previous) focusable element. |
| `Enter`, `Space` | Activates the completed and current step-item. |
| `disabled` | Step-item still focusable. |

### ARIA enhancements

#### External **ARIA** provided by the `aria` property:

Use the `aria` property to pass supported attributes to the **native control inside the shadow DOM**. Prefer a visible slotted label for the accessible name. Use `aria-label` when the label is hidden or missing, and `aria-description` for extra context that should not replace the name. Do not use `aria-label` to replace a different visible label (WCAG 2.5.3).

| ARIA | Usage |
| --- | --- |
| `aria-label` | Defines an accessible name when the visible label is insufficient or hidden; prefer a visible `label` for most cases. |
| `aria-description` | Provides additional context for assistive technologies without replacing the accessible name. |

#### Internal **ARIA** that is managed by the component:

| ARIA | Usage |
| --- | --- |
| `role="switch"` | Indicates the element as switch element. |
| `aria-checked="BOOLEAN"` | Indicates the status of the switch element. |
| `role="status"` | When `loading` prop is set, the component announces the loading state (start and finish). |

## Development considerations

### Labelling

The switch accessible name comes from the default slot. Provide concise, descriptive text that states what the switch controls and its on/off meaning.

### Common do's and don'ts

- **Do** pass extra labelling through the `aria` prop (`aria-label`, `aria-description`).
- **Do** provide a clear slotted label that describes what the switch controls.
- **Do** use `hide-label` only when the label text remains in the slot for screen readers.
- **Don't** use an icon or visual state alone without descriptive label text.
- **Don't** add native `aria-*` attributes directly on the component host.

## Integration examples

See [accessibility integration examples](./accessibility.md) for paired anti-pattern and recommended implementations.

## API

### Properties

| Property | Type | Default | Description |
| --- | --- | --- | --- |
| `alignLabel` | `'start'` `'end'`<br>`BreakpointCustomizable<SwitchAlignLabel>` | `'end'` | Sets the position of the slotted label relative to the switch toggle, either before (`start`) or after (`end`) it. Supports responsive breakpoint values. |
| `aria` | `SwitchAriaAttribute` | `undefined` | Sets additional ARIA attributes on the switch to improve accessibility for screen readers. |
| `checked` | `boolean` | `false` | Reflects the switch's current on/off state and allows setting the initial checked value when the component first renders. |
| `compact` | `boolean` | `false` | Reduces the switch size and spacing for use in dense layouts where vertical space is limited. |
| `disabled` | `boolean` | `false` | Prevents user interaction with the switch and blocks all click and keyboard events while it is disabled. |
| `hideLabel` | `boolean`<br>`BreakpointCustomizable<boolean>` | `false` | Hides the visible label while keeping it accessible to screen readers. Supports responsive breakpoint values. |
| `loading` | `boolean` | `false` | Disables the switch and shows a loading spinner to indicate an ongoing asynchronous toggle operation. |
| `stretch` | `boolean`<br>`BreakpointCustomizable<boolean>` | `false` | Expands the space between the switch toggle and its label to fill the full available width of the container. Supports responsive breakpoint values. |

### Events

| Event | Type | Description |
| --- | --- | --- |
| `update` | `CustomEvent<SwitchUpdateEventDetail>`<br>`{ checked: boolean }` | Emitted when the user toggles the switch, carrying the new `checked` state in the event detail. |

### Controlled properties

- `checked` — a controlled prop: the component does **not** update it itself. Handle the `update` event and assign the new value to `checked` yourself, or the change will not take effect.

### Slots

| Slot | Required | Allowed tag names | Description |
| --- | --- | --- | --- |
| _(default)_ | no | — | Default slot for the label. |

## Examples

| Example | When to use | File |
| --- | --- | --- |
| Default | Minimal default configuration. | [./examples/Default.html](./examples/Default.html) |
