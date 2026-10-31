'use strict';

var colorFrostedSoftDark = require('../../dark/background/colorFrostedSoftDark.cjs');
var colorFrostedSoftLight = require('../../light/background/colorFrostedSoftLight.cjs');

/** Holds the **frosted-soft** color, typically used as a background `:hover`. */
const colorFrostedSoft = `light-dark(${colorFrostedSoftLight.colorFrostedSoftLight},${colorFrostedSoftDark.colorFrostedSoftDark})`;

exports.colorFrostedSoft = colorFrostedSoft;
