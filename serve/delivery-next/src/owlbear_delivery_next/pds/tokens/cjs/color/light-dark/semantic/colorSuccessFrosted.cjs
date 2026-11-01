'use strict';

var colorSuccessFrostedDark = require('../../dark/semantic/colorSuccessFrostedDark.cjs');
var colorSuccessFrostedLight = require('../../light/semantic/colorSuccessFrostedLight.cjs');

/** Holds the **success-frosted** color, typically used as background in combination with a blur effect. */
const colorSuccessFrosted = `light-dark(${colorSuccessFrostedLight.colorSuccessFrostedLight},${colorSuccessFrostedDark.colorSuccessFrostedDark})`;

exports.colorSuccessFrosted = colorSuccessFrosted;
