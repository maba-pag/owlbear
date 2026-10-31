'use strict';

var colorContrastHighDark = require('../../dark/foreground/colorContrastHighDark.cjs');
var colorContrastHighLight = require('../../light/foreground/colorContrastHighLight.cjs');

/** Holds the **contrast-high** color, typically used for text. */
const colorContrastHigh = `light-dark(${colorContrastHighLight.colorContrastHighLight},${colorContrastHighDark.colorContrastHighDark})`;

exports.colorContrastHigh = colorContrastHigh;
