'use strict';

var colorInfoLowDark = require('../../dark/semantic/colorInfoLowDark.cjs');
var colorInfoLowLight = require('../../light/semantic/colorInfoLowLight.cjs');

/** Holds the **info-low** color, typically used for text or border. */
const colorInfoLow = `light-dark(${colorInfoLowLight.colorInfoLowLight},${colorInfoLowDark.colorInfoLowDark})`;

exports.colorInfoLow = colorInfoLow;
