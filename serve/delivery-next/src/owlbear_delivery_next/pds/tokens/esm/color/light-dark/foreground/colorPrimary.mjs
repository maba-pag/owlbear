import { colorPrimaryDark } from '../../dark/foreground/colorPrimaryDark.mjs';
import { colorPrimaryLight } from '../../light/foreground/colorPrimaryLight.mjs';

/** Holds the **primary** color, typically used for text. */
const colorPrimary = `light-dark(${colorPrimaryLight},${colorPrimaryDark})`;

export { colorPrimary };
