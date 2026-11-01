import { colorInfoDark } from '../../dark/semantic/colorInfoDark.mjs';
import { colorInfoLight } from '../../light/semantic/colorInfoLight.mjs';

/** Holds the **info** color, typically used for text. */
const colorInfo = `light-dark(${colorInfoLight},${colorInfoDark})`;

export { colorInfo };
