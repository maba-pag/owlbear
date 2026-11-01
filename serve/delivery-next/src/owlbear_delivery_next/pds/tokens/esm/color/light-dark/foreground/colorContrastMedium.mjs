import { colorContrastMediumDark } from '../../dark/foreground/colorContrastMediumDark.mjs';
import { colorContrastMediumLight } from '../../light/foreground/colorContrastMediumLight.mjs';

/** Holds the **contrast-medium** color, typically used for text. */
const colorContrastMedium = `light-dark(${colorContrastMediumLight},${colorContrastMediumDark})`;

export { colorContrastMedium };
