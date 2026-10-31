'use strict';

var colorFrostedDark = require('../../dark/background/colorFrostedDark.cjs');
var colorFrostedLight = require('../../light/background/colorFrostedLight.cjs');

/** Holds the **frosted** color, typically used as a background in combination with a blur effect. */
const colorFrosted = `light-dark(${colorFrostedLight.colorFrostedLight},${colorFrostedDark.colorFrostedDark})`;

exports.colorFrosted = colorFrosted;
