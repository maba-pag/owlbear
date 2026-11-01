'use strict';

var colorWarningFrostedDark = require('../../dark/semantic/colorWarningFrostedDark.cjs');
var colorWarningFrostedLight = require('../../light/semantic/colorWarningFrostedLight.cjs');

/** Holds the **warning-frosted** color, typically used as background in combination with a blur effect. */
const colorWarningFrosted = `light-dark(${colorWarningFrostedLight.colorWarningFrostedLight},${colorWarningFrostedDark.colorWarningFrostedDark})`;

exports.colorWarningFrosted = colorWarningFrosted;
