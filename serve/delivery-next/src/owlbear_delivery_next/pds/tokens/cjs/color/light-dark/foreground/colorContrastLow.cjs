'use strict';

var colorContrastLowDark = require('../../dark/foreground/colorContrastLowDark.cjs');
var colorContrastLowLight = require('../../light/foreground/colorContrastLowLight.cjs');

/** Holds the **contrast-low** color, intended only for decorative elements, as it is not accessibility-compliant. */
const colorContrastLow = `light-dark(${colorContrastLowLight.colorContrastLowLight},${colorContrastLowDark.colorContrastLowDark})`;

exports.colorContrastLow = colorContrastLow;
