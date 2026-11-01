'use strict';

var colorWarningFrostedSoftDark = require('../../dark/semantic/colorWarningFrostedSoftDark.cjs');
var colorWarningFrostedSoftLight = require('../../light/semantic/colorWarningFrostedSoftLight.cjs');

/** Holds the **warning-frosted-soft** color, typically used as background `:hover`. */
const colorWarningFrostedSoft = `light-dark(${colorWarningFrostedSoftLight.colorWarningFrostedSoftLight},${colorWarningFrostedSoftDark.colorWarningFrostedSoftDark})`;

exports.colorWarningFrostedSoft = colorWarningFrostedSoft;
