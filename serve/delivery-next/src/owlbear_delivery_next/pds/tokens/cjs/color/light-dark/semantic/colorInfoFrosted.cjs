'use strict';

var colorInfoFrostedDark = require('../../dark/semantic/colorInfoFrostedDark.cjs');
var colorInfoFrostedLight = require('../../light/semantic/colorInfoFrostedLight.cjs');

/** Holds the **info-frosted** color, typically used as background in combination with a blur effect. */
const colorInfoFrosted = `light-dark(${colorInfoFrostedLight.colorInfoFrostedLight},${colorInfoFrostedDark.colorInfoFrostedDark})`;

exports.colorInfoFrosted = colorInfoFrosted;
