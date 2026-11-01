import { colorCanvasDark } from '../../dark/background/colorCanvasDark.mjs';
import { colorCanvasLight } from '../../light/background/colorCanvasLight.mjs';

/** Holds the **canvas** color, typically used for surfaces. */
const colorCanvas = `light-dark(${colorCanvasLight},${colorCanvasDark})`;

export { colorCanvas };
