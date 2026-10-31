'use strict';

var colorErrorFrostedDark = require('../../dark/semantic/colorErrorFrostedDark.cjs');
var colorErrorFrostedLight = require('../../light/semantic/colorErrorFrostedLight.cjs');

/** Holds the **error-frosted** color, typically used as background in combination with a blur effect. */
const colorErrorFrosted = `light-dark(${colorErrorFrostedLight.colorErrorFrostedLight},${colorErrorFrostedDark.colorErrorFrostedDark})`;

exports.colorErrorFrosted = colorErrorFrosted;
