'use strict';

var colorContrastLowerDark = require('../../dark/foreground/colorContrastLowerDark.cjs');
var colorContrastLowerLight = require('../../light/foreground/colorContrastLowerLight.cjs');

/** Holds the **contrast-lower** color, intended only for decorative elements, as it is not accessibility-compliant. */
const colorContrastLower = `light-dark(${colorContrastLowerLight.colorContrastLowerLight},${colorContrastLowerDark.colorContrastLowerDark})`;

exports.colorContrastLower = colorContrastLower;
