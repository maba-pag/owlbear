'use strict';

var colorSuccessLowDark = require('../../dark/semantic/colorSuccessLowDark.cjs');
var colorSuccessLowLight = require('../../light/semantic/colorSuccessLowLight.cjs');

/** Holds the **success-low** color, typically used for text or border. */
const colorSuccessLow = `light-dark(${colorSuccessLowLight.colorSuccessLowLight},${colorSuccessLowDark.colorSuccessLowDark})`;

exports.colorSuccessLow = colorSuccessLow;
