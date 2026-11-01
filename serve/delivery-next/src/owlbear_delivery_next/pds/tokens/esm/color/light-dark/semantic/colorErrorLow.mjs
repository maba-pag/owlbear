import { colorErrorLowDark } from '../../dark/semantic/colorErrorLowDark.mjs';
import { colorErrorLowLight } from '../../light/semantic/colorErrorLowLight.mjs';

/** Holds the **error-low** color, typically used for text or border. */
const colorErrorLow = `light-dark(${colorErrorLowLight},${colorErrorLowDark})`;

export { colorErrorLow };
