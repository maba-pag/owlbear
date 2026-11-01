import { colorSurfaceDark } from '../../dark/background/colorSurfaceDark.mjs';
import { colorSurfaceLight } from '../../light/background/colorSurfaceLight.mjs';

/** Holds the **surface** color, typically used for surfaces. */
const colorSurface = `light-dark(${colorSurfaceLight},${colorSurfaceDark})`;

export { colorSurface };
