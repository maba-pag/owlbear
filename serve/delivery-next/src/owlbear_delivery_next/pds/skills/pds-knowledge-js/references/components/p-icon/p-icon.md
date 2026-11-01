# p-icon

Along with other Porsche basic elements - such as colors, typography and the Porsche marque - icons are core components of the Porsche design. The clear graphic symbols allow quick orientation and are internationally recognized. The Porsche Design System is using an **SVG icon system (integrated by `<img/>`)** to visually present an icon object. Each icon is hosted on the Porsche Design System CDN to be served and cached as fast as possible.

## Usage

### Do:

- Use the available icons from [Porsche Icons](https://icons.porsche.com).
- Use icons as an additional element for faster recognition.

### Don't:

- Don't use icons without label.

## Custom icons

We want to enable you to use the icons you need. Check the [Porsche Design System](https://icons.porsche.com) for an appropriate icon you are looking for. If there is no match, we encourage you to build, test and use the icons you need. To help you meet the quality standards of Porsche, you will find the guidelines below.

Do you have an icon that is mandatory for several teams and purposes? We are happy to include it in the Porsche Design System. Feel free to get in touch with us on our [Porsche Design System Slack](https://porschedev.slack.com/archives/CT7AVHTTQ)

### Metaphor and Appearance

- Check the Porsche environment for similar or close icons to adapt (Web, App, In Car, Print)
- Stick to the basic geometric shapes.
- Use easy and commonly known metaphors.
- Keep the details and complexity to a minimum.
- Make sure corresponding icons have the same position, e.g. the "add" and "remove" icons.
- Check your design about other icons from the Porsche Design System.

### Quality assurance

- Build your icons based on the default grid (48x48px). Default Porsche icons use 2px lines.
- Fill areas smaller than 4px.
- Snap pixels to the grid to ensure a sharp visual appearance (prevents blurred lines because of anti-aliasing on low-resolution displays).
- Try to balance the width and height of the icon to ensure a uniform appearance in icon groups.
- Respect the safe area around the icon (approximately 4px, which can vary depending on the ratio of the icon).
- Design with only one color.

### SVG Export

- Transform vector forms in a full, coherent vector shape. (convert strokes to shapes and merge objects).
- Delete everything that is not necessary (layers, strokes, variants, etc.).
- Export your icon as an SVG.
- Name SVG files according to the icon (e.g. "delete.svg" or "edit.svg").
- Name social icons "logo-companyname.svg".
- Run an SVG optimizer to create clean, semantic code.

### Read more on

[Nielsen Norman Group](https://nngroup.com/articles/icon-testing)

[UsabilityHub](https://usabilityhub.com/examples/easiest-icon-to-understand)

## Accessibility support

### ARIA enhancements

#### External **ARIA** provided by the `aria` property:

| ARIA | Usage |
| --- | --- |
| `aria-label` | Defines a string value that labels the element (through the `alt` attribute). |

## Development considerations

### Hiding an icon from assistive technologies

Sometimes icons are used purely for **decorative purposes** and do not convey any additional information. In these cases, it is important to **hide** the icon from assistive technologies. This can be achieved by setting the `aria-hidden` attribute directly on the `Icon` component.

```html
<p-icon aria-hidden="true" name="phone" /><p-text>+49 123 456 7890</p-text>
```

### Common do's and don'ts

- **Do** pass meaningful names through the `aria` prop when the icon conveys information on its own.
- **Do** hide decorative icons from assistive technologies when adjacent text provides the meaning.
- **Don't** add redundant `aria-label` to decorative icons beside visible text.

## Integration examples

See [accessibility integration examples](./accessibility.md) for paired anti-pattern and recommended implementations.

## Tests

### Automated

| Technology | Support |
| --- | --- |
| AXE-Core (WCAG 2.2 AA, Best-Practice) (WCAG 2.2 AA, Best-Practice) | ✅ |
| High-Contrast Mode (light/dark) | 🟠(partially supported: Depending on the selected theme, there may be problems reproducing the complementary color) |
| Text-Zoom (200%) | ✅ |

### Manual

| Technology | Support |
| --- | --- |
| Screen reader (VoiceOver, NVDA) | ✅ |

## API

### Properties

| Property | Type | Default | Description |
| --- | --- | --- | --- |
| `aria` | `IconAriaAttribute` | `undefined` | Sets ARIA attributes on the icon — use `aria-label` to make the icon meaningful to screen readers when it conveys information. |
| `color` | `'primary'` `'contrast-higher'` `'contrast-high'` `'contrast-medium'` `'contrast-low'` `'contrast-lower'` `'success'` `'warning'` `'error'` `'info'` `'inherit'` | `'primary'` | Sets the fill color of the icon using PDS color tokens. |
| `name` | one of 294 icon names — see [icon names](references/icons.md) | `'arrow-right'` | Selects an icon from the built-in PDS icon library by name (e.g. `arrow-right`, `close`). |
| `size` | `'2xs'` `'xs'` `'sm'` `'md'` `'lg'` `'xl'` `'2xl'` `'3xl'` `'4xl'` `'5xl'` `'inherit'`<br>_deprecated:_ `'xx-small'` `'x-small'` `'small'` `'medium'` `'large'` `'x-large'` `'xx-large'`<br>`BreakpointCustomizable<IconSize>` | `'sm'` | Sets the icon size using the PDS typographic scale. Use `inherit` to derive size from the parent element. Supports responsive breakpoint values. |
| `source` | `string` | `undefined` | Sets a path to a custom SVG icon, used instead of the built-in icon library. |

### CSS Variables

| CSS Variable | Default | Description |
| --- | --- | --- |
| `--p-icon-size` | — | Defines the width and height of the icon. Overrides the `size` property when set. |
| `--p-icon-color` | — | Defines the icon color. Overrides the `color` property when set. |

## Examples

| Example | When to use | File |
| --- | --- | --- |
| Default | Minimal default configuration. | [./examples/Default.html](./examples/Default.html) |
| Overview | For more information and a complete overview of all available Porsche icons, head over to Porsche Icons ([Porsche Icons](https://icons.porsche.com)). | [./examples/Overview.html](./examples/Overview.html) |
| Size via Prop | There are predefined sizes for the component available which should cover most use cases. | [./examples/Size.html](./examples/Size.html) |
| Size via CSS Variable | Alternatively, the size can be controlled via the custom CSS variable `--p-icon-size`, which accepts any valid CSS length value. | [./examples/SizeCssVar.html](./examples/SizeCssVar.html) |
| Responsive Size | The `size` property supports `BreakpointCustomizable` values, allowing you to define different sizes for each major breakpoint (`xs`, `s`, `m`, `l`, `xl`). | [./examples/ResponsiveSize.html](./examples/ResponsiveSize.html) |
| Color via Prop | The `color` property can be set to `inherit` to derive the icon's color from the `currentcolor` of a parent element (e.g. a `p-text`). | [./examples/Color.html](./examples/Color.html) |
| Color via CSS Variable | Alternatively, the color can be controlled via the custom CSS variable `--p-icon-color`, which accepts any valid CSS color value. | [./examples/ColorCssVar.html](./examples/ColorCssVar.html) |
| Custom Icon | The whole Porsche icon set is hosted on the Porsche Design System CDN. | [./examples/Custom.html](./examples/Custom.html) |
