# p-input-text

The `p-input-text` component provides a versatile, user‑friendly interface for entering freeform text. It supports direct keyboard input and includes `start` and `end` slots to allow flexible integration of icons, buttons, or other content within the input field.

A `label` is a caption which informs the user what information a particular form field is asking for. The `p-input-text` component can be used with or without a label, but it's recommended to keep the label visible for better accessibility whenever possible. When used without a label, it's mandatory to provide a descriptive label text for screen readers.

While a `placeholder` is optional but recommended to be set whenever bits of example content or hints shall be shown to give the user visual cues to fill out the form.

## Usage

`p-input-text` is intended for freeform text input scenarios. It is suitable for entering names, addresses, or any other non-restricted textual content. It should not be used where semantic or functional input types like numbers, emails, or dates are more appropriate. In such cases, consider using a more specific input type or component optimized for that data. For further guidance, see the [MDN documentation on text inputs](https://developer.mozilla.org/en-US/docs/Web/HTML/Reference/Elements/input/text#using_text_inputs).

### Do:

- Use when freeform text input is required or optional.
- Use without a label only when the context is clear.
- Use for validation and error of input.
- Use asterisk for required fields.

### Don't:

- Don't use labels with more than two words whenever possible (keep it short and descriptive).
- Don't use an instructional or description text for the label.

---

## Related Components

- [Input Date](../p-input-date/p-input-date.md)
- [Input Email](../p-input-email/p-input-email.md)
- [Input Month](../p-input-month/p-input-month.md)
- [Input Number](../p-input-number/p-input-number.md)
- [Input Password](../p-input-password/p-input-password.md)
- [Input Search](../p-input-search/p-input-search.md)
- [Input Tel](../p-input-tel/p-input-tel.md)
- [Input Time](../p-input-time/p-input-time.md)
- [Input URL](../p-input-url/p-input-url.md)
- [Input Week](../p-input-week/p-input-week.md)

## Accessibility support

### Keyboard

| Key / state | Function |
| --- | --- |
| `Tab`, `Shift-Tab` | Moves focus to the next (or previous) focusable element. |

### ARIA enhancements

#### External **ARIA** provided by the `aria` property:

Use the `aria` property to pass supported attributes to the **native control inside the shadow DOM**. Prefer a visible `label` for the accessible name. Use `aria-label` when the label is hidden or insufficient, and `aria-description` for extra context that should not replace the name.

| ARIA | Usage |
| --- | --- |
| `aria-label` | Defines an accessible name when the visible label is insufficient or hidden; prefer a visible `label` for most cases. |
| `aria-description` | Provides additional context for assistive technologies without replacing the accessible name. |

#### Internal **ARIA** that is managed by the component:

| ARIA | Usage |
| --- | --- |
| `aria-describedby="IDREF"` | Defines the accessible description combined with the status message. |
| `role="status"`, `role="alert"` | When `message` and `state` or `loading` prop change, the status message is announced. |
| `aria-hidden="true"` | If `required` attribute is set, the visible asterisk indicator is hidden from assistive technologies. |
| `aria-invalid="true"` | If `error` state is set. |
| `aria-live="polite"` | If the `maxlength` attribute is present, the counter is announced via ARIA live region. |

## Development considerations

### Exposing the `unit` prop

The `unit` prop is not exposed to assistive technologies by default. If you provide a `unit` abbreviation, you need to dissolve it in real text through the `description` prop. For example, if you use `kmh`, you can set the `description` prop to `kilometers per hour`. This way, the screen reader will read out the full text.

### Disabled state

In general, avoid using the `disabled` state. Disabled elements are no longer focusable and may be missed by screen reader users. They can also confuse sighted users if the reason they are disabled is not made clear.

### Common do's and don'ts

- **Do** pass extra labelling through the `aria` prop (`aria-label`, `aria-description`).
- **Do** keep a persistent label and use helper/description text when additional context is required.
- **Do** use the component state/message API so validation and status changes are announced.
- **Do** use clear error wording that helps users recover.
- **Don't** rely on placeholder text as the only label.
- **Don't** use `hide-label` without an accessible name.
- **Don't** add native `aria-*` attributes directly on the component host.

## Limitations

Due to the nature of **Web Components** and **shadow DOM**, there are limitations when using some **ARIA** attributes to define relationships between elements across different shadow DOMs or shadow DOM/light DOM combinations.

| ARIA | Support |
| --- | --- |
| `aria-labelledby` | 🚫 |
| `aria-describedby` | 🚫 |

## Integration examples

See [accessibility integration examples](./accessibility.md) for paired anti-pattern and recommended implementations.

## API

### Properties

| Property | Type | Default | Description |
| --- | --- | --- | --- |
| `aria` | `InputTextAriaAttribute` | `undefined` | Sets additional ARIA attributes on the native input to improve accessibility for screen readers. |
| `autoComplete` | `string` | `undefined` | Provides the browser with a data type hint to enable relevant autofill suggestions (e.g. `autocomplete='name'`). |
| `compact` | `boolean` | `false` | Reduces the input height and padding for a more compact layout. |
| `counter` | `boolean` | `false` | Shows a live character counter below the field indicating how many characters have been entered relative to `maxLength`. |
| `description` | `string` | `''` | Sets a supplementary description displayed below the label to provide additional context. |
| `disabled` | `boolean` | `false` | Disables the field, preventing all input. The value is not submitted with the form. |
| `form` | `string` | `undefined` | Associates the field with a form element by its ID when the field is not nested directly inside it. |
| `hideLabel` | `boolean`<br>`BreakpointCustomizable<boolean>` | `false` | Hides the visible label while keeping it accessible to screen readers. Supports responsive breakpoint values. |
| `label` | `string` | `''` | Sets the visible label text displayed above the input field. |
| `loading` _(experimental)_ | `boolean` | `false` | @experimental Disables the field and displays a loading spinner to indicate an ongoing operation. |
| `maxLength` | `number` | `undefined` | Sets the maximum number of characters the user can enter. |
| `message` | `string` | `''` | Sets the validation feedback message displayed below the field when `state` is `success` or `error`. |
| `minLength` | `number` | `undefined` | Sets the minimum number of characters required for the field to be considered valid. |
| `name` _(required)_ | `string` | `undefined` | Sets the name submitted with the form data to identify this field's value on the server. |
| `placeholder` | `string` | `''` | Sets placeholder text shown inside the field when it is empty, to hint at the expected format. |
| `readOnly` | `boolean` | `false` | Makes the field read-only — the value is displayed but cannot be edited by the user. The value is still submitted with the form. |
| `required` | `boolean` | `false` | Marks the field as required — form submission is blocked while this field is empty. |
| `spellCheck` | `boolean` | `undefined` | Controls whether the browser's built-in spell-checking is enabled for this field. |
| `state` | `'none'` `'error'` `'success'` | `'none'` | Sets the validation state, controlling the visual appearance and style of the feedback message (`none`, `success`, `error`). |
| `value` | `string | number | null` | `''` | Sets the current text value. Numbers are accepted for programmatic assignment, but user input updates the value as a string. |

### Events

| Event | Type | Description |
| --- | --- | --- |
| `blur` | `CustomEvent<InputTextBlurEventDetail>`<br>`Event` | Emitted when the input loses focus, regardless of whether the value changed. |
| `change` | `CustomEvent<InputTextChangeEventDetail>`<br>`Event` | Emitted when the input loses focus after its value was changed. The component value and native event target value are strings after user input. |
| `input` | `CustomEvent<InputTextInputEventDetail>`<br>`InputEvent` | Emitted on every value change as the user types. The component value and native event target value are strings. |

### Slots

| Slot | Required | Allowed tag names | Description |
| --- | --- | --- | --- |
| `label` | no | — | Shows a label. Only [phrasing content](https://developer.mozilla.org/en-US/docs/Web/Guide/HTML/Content_categories#Phrasing_content) is allowed. |
| `label-after` | no | — | Places additional content after the label text (for content that should not be part of the label, e.g. external links or `p-popover`). |
| `description` | no | — | Shows a description. Only [phrasing content](https://developer.mozilla.org/en-US/docs/Web/Guide/HTML/Content_categories#Phrasing_content) is allowed. |
| `message` | no | — | Shows a state message. Only [phrasing content](https://developer.mozilla.org/en-US/docs/Web/Guide/HTML/Content_categories#Phrasing_content) is allowed. |
| `start` | no | — | Shows content at the start of the input (e.g. unit prefix). |
| `end` | no | — | Shows content at the end of the input (e.g. toggle button, unit suffix). |

### CSS Variables

| CSS Variable | Default | Description |
| --- | --- | --- |
| `--ref-p-input-slotted-padding` | — | When slotting a `p-button-pure` or `p-link-pure` this variable needs to be set as `padding` in oder to adjust the alignment correctly. |
| `--ref-p-input-slotted-margin` | — | When slotting a `p-button-pure` or `p-link-pure` this variable needs to be set as `margin` in oder to adjust the spacings correctly. |

## Examples

| Example | When to use | File |
| --- | --- | --- |
| Default | Minimal default configuration. | [./examples/Default.html](./examples/Default.html) |
| Form | The `p-input-text` can be integrated into a form in two ways: **controlled** or **uncontrolled**, depending on your needs. | [./examples/Form.html](./examples/Form.html) |
| Controlled Input (Preventing User Input) | In some cases you may want to fully control the input value (for example to limit or validate user input). | [./examples/Controlled.html](./examples/Controlled.html) |
| Slots | Use named slots when `label`, `description` or `message` need markup such as a link. | [./examples/Slots.html](./examples/Slots.html) |
