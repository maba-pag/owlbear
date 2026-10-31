# p-link

The `p-link` component is essential to perform changes in **page routes**. For an optimal user guidance and dedicated pursuit of business or sales goals, different types of Links (**Primary** and **Secondary**) are available for usage. A Link can be used with or without a label, but it's recommended to keep the **label visible** for better **usability** whenever possible. When used without a label, it is mandatory for **accessibility** to provide a descriptive label text for screen readers. In case you want the user to execute an action, you should select the [Button](../p-button/p-button.md) component instead.

You can use native `click`, `focus`, `focusin`, `blur` and `focusout` events on the `p-link`.

## Usage

### Do:

- Use a Link to navigate to another page.
- Use a [Button](../p-button/p-button.md) instead of a Link if you want to change a state (e.g. send form)
- Use a Primary Link filled for one or two high-priority actions within a page.
- Use a Secondary Link for all other stand-alone Links that aren't high priority.
- Use a [Link Pure](../p-link-pure/p-link-pure.md) as a subordinated link version in combination with a filled link (primary or secondary) or stand-alone when the priority of the action is lower compared to all other link actions within the page.
- Use an Icon and text variant only when appropriate (e.g. external link).
- Use an Icon-only variant only in cases where the user is fully aware of the link function.
- Ensure that the link remains legible even in a multiline state by using max. 100 characters per line.

### Don't:

- Don't use a Primary Link for all links on a page.
- Don't use a multiline Link, as it is recommended to keep the text label short and avoid multiline links.
- Don't use a width that's too wide and makes the link difficult to read.

---

## Related components

- [Button](../p-button/p-button.md)
- [Link Pure](../p-link-pure/p-link-pure.md)

## Accessibility support

### Keyboard

| Key / state | Function |
| --- | --- |
| `Tab`, `Shift-Tab` | Moves focus to the next (or previous) focusable element. |
| `Enter` | Activates the link. |

### ARIA enhancements

#### External **ARIA** provided by the `aria` property:

| ARIA | Usage |
| --- | --- |
| `aria-label` | Defines a string value that labels the interactive element. |
| `aria-description` | Defines a string value that adds a more detailed description of the interactive element. |
| `aria-current` | Exposes the current state of the link. |
| `aria-haspopup` | Defines that the link opens a popup (e.g. `dialog`). |

#### Internal **ARIA** that is managed by the component:

| ARIA | Usage |
| --- | --- |
| `aria-hidden="true"` | When the `icon` prop is set, the icon is hidden from the screen reader. |

## Development considerations

### Labelling

If the text of a link does not clearly indicate what the link's target is, add a brief, descriptive label using the `aria` property with the `aria-label` value to provide more context for screen reader users. Phrases like "Detail" or "Click" can be unclear when read out of context by a screen reader. In such instances, provide an alternative text that offers more detailed information, such as "Details of product XYZ."

### Common do's and don'ts

- **Do** pass ARIA attributes via the `aria` prop, for example `aria="{ 'aria-current': 'page' }"` when indicating the current page.
- **Do** provide a clear accessible name for icon-only actions via slotted label or `aria` property.
- **Don't** add native `aria-*` attributes directly on the component host.
- **Don't** rely on short generic link labels like "Show" or "Add" without context.

## Integration examples

See [accessibility integration examples](./accessibility.md) for paired anti-pattern and recommended implementations.

## API

### Properties

| Property | Type | Default | Description |
| --- | --- | --- | --- |
| `aria` | `LinkAriaAttribute` | `undefined` | Sets ARIA attributes on the link element to improve accessibility for screen readers. |
| `compact` | `boolean`<br>`BreakpointCustomizable<boolean>` | `false` | Reduces the link's padding and height for denser layouts. Supports responsive breakpoint values. |
| `download` | `string` | `undefined` | Sets the native `download` attribute to trigger a file download. Only applies when `href` is set. |
| `hideLabel` | `boolean`<br>`BreakpointCustomizable<boolean>` | `false` | Hides the visible label while keeping it accessible to screen readers. Supports responsive breakpoint values. |
| `href` | `string` | `undefined` | When set, the component renders as an anchor navigating to this URL. Otherwise, provide a slotted anchor element, but not both. Without either, it renders as plain text. |
| `icon` | `'none'`<br>one of 294 icon names — see [icon names](references/icons.md) | `'none'` | Sets the icon displayed next to the link label. Use `none` to show no icon. |
| `iconSource` | `string` | `undefined` | Sets a path to a custom SVG icon, used instead of the built-in icon set. |
| `rel` | `string` | `undefined` | Sets the `rel` attribute on the link (e.g. `noopener`). Only applies when `href` is set. |
| `target` | `'_self'` `'_blank'` `'_parent'` `'_top'` `'string'` | `'_self'` | Specifies where to open the linked URL (e.g. `_self`, `_blank`). Only applies when `href` is set. |
| `variant` | `'primary'` `'secondary'` | `'primary'` | Sets the visual style variant of the link (`primary` or `secondary`). |

### Slots

| Slot | Required | Allowed tag names | Description |
| --- | --- | --- | --- |
| _(default)_ | no | — | Default slot to render the link label. This slot can be used to slot an anchor tag instead of using the `href` prop, but not in combination with it. |

### CSS Variables

| CSS Variable | Default | Description |
| --- | --- | --- |
| `--p-link-bg` | — | Overrides the background color of the link in every state, including hover. You are responsible for ensuring sufficient contrast and brand compliance. |
| `--p-link-fg` | — | Overrides the foreground color (label and icon) of the link in every state, including hover. You are responsible for ensuring sufficient contrast and brand compliance. |
| `--p-link-px` | — | Horizontal padding of the link. |
| `--p-link-py` | — | Vertical padding of the link. |
| `--p-link-gap` | — | Gap between the link's content (label and icon). |
| `--p-link-radius` | — | Radius of the link |

## Examples

| Example | When to use | File |
| --- | --- | --- |
| Default | Minimal default configuration. | [./examples/Default.html](./examples/Default.html) |
| Framework routing (anchor nesting) | To support custom anchor tags (e.g. framework specific routing) you can provide them as a **slotted element** of the component. | [./examples/FrameworkRouting.html](./examples/FrameworkRouting.html) |
| Link with specific icon | If an icon needs to be implemented, just set another predefined icon. | [./examples/Icon.html](./examples/Icon.html) |
