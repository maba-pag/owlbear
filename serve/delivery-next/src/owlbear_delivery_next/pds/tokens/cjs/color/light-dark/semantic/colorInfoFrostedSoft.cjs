'use strict';

var colorInfoFrostedSoftDark = require('../../dark/semantic/colorInfoFrostedSoftDark.cjs');
var colorInfoFrostedSoftLight = require('../../light/semantic/colorInfoFrostedSoftLight.cjs');

/** Holds the **info-frosted-soft** color, typically used as background `:hover`. */
const colorInfoFrostedSoft = `light-dark(${colorInfoFrostedSoftLight.colorInfoFrostedSoftLight},${colorInfoFrostedSoftDark.colorInfoFrostedSoftDark})`;

exports.colorInfoFrostedSoft = colorInfoFrostedSoft;
