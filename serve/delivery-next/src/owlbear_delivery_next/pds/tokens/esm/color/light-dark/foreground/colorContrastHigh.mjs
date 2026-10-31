import { colorContrastHighDark } from '../../dark/foreground/colorContrastHighDark.mjs';
import { colorContrastHighLight } from '../../light/foreground/colorContrastHighLight.mjs';

/** Holds the **contrast-high** color, typically used for text. */
const colorContrastHigh = `light-dark(${colorContrastHighLight},${colorContrastHighDark})`;

export { colorContrastHigh };
