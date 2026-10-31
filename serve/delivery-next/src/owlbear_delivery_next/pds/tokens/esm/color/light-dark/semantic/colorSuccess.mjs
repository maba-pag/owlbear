import { colorSuccessDark } from '../../dark/semantic/colorSuccessDark.mjs';
import { colorSuccessLight } from '../../light/semantic/colorSuccessLight.mjs';

/** Holds the **success** color, typically used for text. */
const colorSuccess = `light-dark(${colorSuccessLight},${colorSuccessDark})`;

export { colorSuccess };
