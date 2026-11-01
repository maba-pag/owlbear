import { colorErrorDark } from '../../dark/semantic/colorErrorDark.mjs';
import { colorErrorLight } from '../../light/semantic/colorErrorLight.mjs';

/** Holds the **error** color, typically used for text. */
const colorError = `light-dark(${colorErrorLight},${colorErrorDark})`;

export { colorError };
