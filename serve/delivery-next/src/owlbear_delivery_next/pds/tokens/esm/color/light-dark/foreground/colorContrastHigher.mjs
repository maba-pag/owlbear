import { colorContrastHigherDark } from '../../dark/foreground/colorContrastHigherDark.mjs';
import { colorContrastHigherLight } from '../../light/foreground/colorContrastHigherLight.mjs';

/** Holds the **contrast-higher** color, typically used for text. */
const colorContrastHigher = `light-dark(${colorContrastHigherLight},${colorContrastHigherDark})`;

export { colorContrastHigher };
