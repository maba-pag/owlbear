'use strict';

var colorContrastMediumDark = require('../../dark/foreground/colorContrastMediumDark.cjs');
var colorContrastMediumLight = require('../../light/foreground/colorContrastMediumLight.cjs');

/** Holds the **contrast-medium** color, typically used for text. */
const colorContrastMedium = `light-dark(${colorContrastMediumLight.colorContrastMediumLight},${colorContrastMediumDark.colorContrastMediumDark})`;

exports.colorContrastMedium = colorContrastMedium;
