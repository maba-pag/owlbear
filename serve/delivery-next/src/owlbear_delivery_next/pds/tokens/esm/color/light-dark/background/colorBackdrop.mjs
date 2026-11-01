import { colorBackdropDark } from '../../dark/background/colorBackdropDark.mjs';
import { colorBackdropLight } from '../../light/background/colorBackdropLight.mjs';

/** Holds the **backdrop** color, typically used for backdrops. */
const colorBackdrop = `light-dark(${colorBackdropLight},${colorBackdropDark})`;

export { colorBackdrop };
