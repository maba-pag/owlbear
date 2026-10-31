# p-sheet

The `p-sheet` is a temporary overlay to focus the user's attention on one or multiple tasks while the underlying page is still visible but interactions with it are blocked. It should be used thoughtfully and sparingly.

It is a controlled component. This grants flexible control over the sheet's behavior especially whether it should stay open after user interaction like submission of a form.

> **Scroll-lock**
>
> This component sets `overflow: hidden` on the body when opened in order to prevent background scrolling.
>
> This doesn't work completely reliable under iOS but is the most stable solution.
>
> Feel free to address this issue in an Open Source PR, if you can provide a better solution. See the [current implementation of the scroll lock](https://github.com/porsche-design-system/porsche-design-system/blob/main/packages/components/src/utils/setScrollLock.ts).

Following **web standards**, the component uses the native `<dialog />` element internally which ensures proper focus handling including a **focus trap**. In addition, it's rendered on the `#top-layer` which ensures the element to be on top of the page independent of where `p-sheet` is placed in the DOM hierarchy (`z-index` is not relevant anymore and won't have any effect).

The most important property of `p-sheet` is its `open` property. When it's set to `true` the sheet will be visible. In order to get notified when the sheet gets closed by clicking the `x` button, the backdrop or by pressing the `Escape` key you need to register an event listener for the `dismiss` event which is emitted by `p-sheet`.

## Usage

### Do:

- Use an sheet only for critical decisions or when multiple related actions need to be presented.
- Keep the options clear, concise, and easy to understand.
- Limit the number of choices to avoid overwhelming the user.
- Use descriptive labels that indicate the outcome of each action.
- Include a cancel option to allow users to dismiss the sheet without making a selection.

### Don't:

- Don’t use sheets for non-essential or minor tasks.
- Avoid presenting too many options or complex decisions.
- Don’t use vague labels like “OK” or “Cancel” without context.
- Avoid stacking multiple sheets on top of each other.
- Don’t interrupt the user’s workflow unnecessarily.

## Accessibility support

The `Sheet` component uses the native `dialog` element to provide a modal dialog which comes with browser-specific behavior. As a result, accessibility features may vary across different browsers.

### Keyboard

| Key / state | Function |
| --- | --- |
| `Tab`, `Shift-Tab` | Moves focus to the next (or previous) focusable element inside the dialog. Focus is trapped (browser behavior). |
| `ESC` | Closes the dialog. |
| `focus` on trigger element | The focus is returned to the trigger element after closing the dialog (browser behavior). |

### ARIA enhancements

#### External **ARIA** provided by the `aria` property:

| ARIA | Usage |
| --- | --- |
| `aria-label` | Defines a string value that labels the dialog element. |
| `role` | Defines the semantic of the dialog element (`dialog` or `alertdialog`). |

#### Internal **ARIA** that is managed by the component:

| ARIA | Usage |
| --- | --- |
| `aria-label="STRING"` | Defines the accessible name if no `aria` property is provided, uses the contents of the header slot and falls back to a fixed name. |

## Development considerations

Set `aria-haspopup` on the trigger so users know a dialog will open. Ensure the sheet has a meaningful title via the header slot or `aria` property.

### Common do's and don'ts

- **Do** use a semantic trigger (usually a button) with a meaningful accessible name.
- **Do** set `aria-haspopup` through the trigger component `aria` prop when opening the sheet.
- **Do** ensure a meaningful title/label is available via the header slot or `aria` property.
- **Don't** add raw host-level ARIA attributes as a workaround.
- **Don't** use unclear trigger copy like "Open" when the sheet purpose is not obvious.

## Integration examples

See [accessibility integration examples](./accessibility.md) for paired anti-pattern and recommended implementations.

## API

### Properties

| Property | Type | Default | Description |
| --- | --- | --- | --- |
| `aria` | `SheetAriaAttribute` | `undefined` | Sets ARIA attributes on the sheet dialog element for improved accessibility when the default `aria-label` is insufficient. |
| `background` | `'canvas'` `'surface'` | `'canvas'` | Sets the background color of the sheet panel (`canvas` or `surface`). |
| `disableBackdropClick` | `boolean` | `false` | When enabled, clicking the backdrop will not close the sheet. |
| `dismissButton` | `boolean` | `true` | Shows a dismiss button in the sheet header so users can manually close it. |
| `open` _(required)_ | `boolean` | `false` | Controls whether the sheet panel slides in from the bottom and is visible to the user. |

### Events

| Event | Type | Description |
| --- | --- | --- |
| `dismiss` | `CustomEvent<SheetDismissEventDetail>`<br>`{ reason: 'dismiss-button' | 'backdrop' | 'escape' }` | Emitted when the user closes the sheet via the dismiss button, backdrop click, or Escape key. The event detail identifies which of the three was used. |
| `motionHiddenEnd` | `CustomEvent<SheetMotionHiddenEndEventDetail>`<br>`TransitionEvent` | Emitted after the sheet's close transition has fully completed and the panel is hidden. |
| `motionVisibleEnd` | `CustomEvent<SheetMotionVisibleEndEventDetail>`<br>`TransitionEvent` | Emitted after the sheet's open transition has fully completed and the panel is visible. |

### Controlled properties

- `open` — a controlled prop: the component does **not** update it itself. Handle the `dismiss` event and assign the new value to `open` yourself, or the change will not take effect.

### Slots

| Slot | Required | Allowed tag names | Description |
| --- | --- | --- | --- |
| `header` | no | — | Renders a header section above the content area. |
| _(default)_ | no | — | Default slot for the main content. |

### CSS Variables

| CSS Variable | Default | Description |
| --- | --- | --- |
| `--ref-p-sheet-pt` | — | Exposes the internally used padding-top of the Sheet as read only CSS variable. When slotting e.g. a media container, this variable can be used to stretch the element to the top of the Sheet. |
| `--ref-p-sheet-pb` | — | Exposes the internally used padding-bottom of the Sheet as read only CSS variable. When slotting e.g. a media container, this variable can be used to stretch the element to the bottom of the Sheet. |
| `--ref-p-sheet-px` | — | Exposes the internally used padding-inline of the Sheet as read only CSS variable. When slotting e.g. a media container, this variable can be used to stretch the element to the full horizontal size of the Sheet. |

## Examples

| Example | When to use | File |
| --- | --- | --- |
| Default | Minimal default configuration. | [./examples/Default.html](./examples/Default.html) |
