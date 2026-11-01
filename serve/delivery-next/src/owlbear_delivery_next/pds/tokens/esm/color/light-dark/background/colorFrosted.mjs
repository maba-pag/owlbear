import { colorFrostedDark } from '../../dark/background/colorFrostedDark.mjs';
import { colorFrostedLight } from '../../light/background/colorFrostedLight.mjs';

/** Holds the **frosted** color, typically used as a background in combination with a blur effect. */
const colorFrosted = `light-dark(${colorFrostedLight},${colorFrostedDark})`;

export { colorFrosted };
