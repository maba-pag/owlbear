import { colorFocusDark } from '../../dark/a11y/colorFocusDark.mjs';
import { colorFocusLight } from '../../light/a11y/colorFocusLight.mjs';

/** Holds the **focus** color, typically used as the outline for `:focus-visible` states. */
const colorFocus = `light-dark(${colorFocusLight},${colorFocusDark})`;

export { colorFocus };
