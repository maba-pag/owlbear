'use strict';

var colorSuccessFrostedSoftDark = require('../../dark/semantic/colorSuccessFrostedSoftDark.cjs');
var colorSuccessFrostedSoftLight = require('../../light/semantic/colorSuccessFrostedSoftLight.cjs');

/** Holds the **success-frosted-soft** color, typically used as background `:hover`. */
const colorSuccessFrostedSoft = `light-dark(${colorSuccessFrostedSoftLight.colorSuccessFrostedSoftLight},${colorSuccessFrostedSoftDark.colorSuccessFrostedSoftDark})`;

exports.colorSuccessFrostedSoft = colorSuccessFrostedSoft;
