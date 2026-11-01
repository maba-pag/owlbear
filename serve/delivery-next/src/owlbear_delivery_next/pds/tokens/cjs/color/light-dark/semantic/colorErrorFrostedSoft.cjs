'use strict';

var colorErrorFrostedSoftDark = require('../../dark/semantic/colorErrorFrostedSoftDark.cjs');
var colorErrorFrostedSoftLight = require('../../light/semantic/colorErrorFrostedSoftLight.cjs');

/** Holds the **error-frosted-soft** color, typically used as background `:hover`. */
const colorErrorFrostedSoft = `light-dark(${colorErrorFrostedSoftLight.colorErrorFrostedSoftLight},${colorErrorFrostedSoftDark.colorErrorFrostedSoftDark})`;

exports.colorErrorFrostedSoft = colorErrorFrostedSoft;
