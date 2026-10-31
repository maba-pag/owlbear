import { colorContrastLowDark } from '../../dark/foreground/colorContrastLowDark.mjs';
import { colorContrastLowLight } from '../../light/foreground/colorContrastLowLight.mjs';

/** Holds the **contrast-low** color, intended only for decorative elements, as it is not accessibility-compliant. */
const colorContrastLow = `light-dark(${colorContrastLowLight},${colorContrastLowDark})`;

export { colorContrastLow };
