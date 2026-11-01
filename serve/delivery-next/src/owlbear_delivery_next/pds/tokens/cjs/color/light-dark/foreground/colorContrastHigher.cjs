'use strict';

var colorContrastHigherDark = require('../../dark/foreground/colorContrastHigherDark.cjs');
var colorContrastHigherLight = require('../../light/foreground/colorContrastHigherLight.cjs');

/** Holds the **contrast-higher** color, typically used for text. */
const colorContrastHigher = `light-dark(${colorContrastHigherLight.colorContrastHigherLight},${colorContrastHigherDark.colorContrastHigherDark})`;

exports.colorContrastHigher = colorContrastHigher;
