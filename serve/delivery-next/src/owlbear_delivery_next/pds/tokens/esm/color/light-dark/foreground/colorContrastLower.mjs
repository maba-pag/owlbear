import { colorContrastLowerDark } from '../../dark/foreground/colorContrastLowerDark.mjs';
import { colorContrastLowerLight } from '../../light/foreground/colorContrastLowerLight.mjs';

/** Holds the **contrast-lower** color, intended only for decorative elements, as it is not accessibility-compliant. */
const colorContrastLower = `light-dark(${colorContrastLowerLight},${colorContrastLowerDark})`;

export { colorContrastLower };
