'use strict';

var colorCanvasDark = require('../../dark/background/colorCanvasDark.cjs');
var colorCanvasLight = require('../../light/background/colorCanvasLight.cjs');

/** Holds the **canvas** color, typically used for surfaces. */
const colorCanvas = `light-dark(${colorCanvasLight.colorCanvasLight},${colorCanvasDark.colorCanvasDark})`;

exports.colorCanvas = colorCanvas;
