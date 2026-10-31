'use strict';

var colorErrorLowDark = require('../../dark/semantic/colorErrorLowDark.cjs');
var colorErrorLowLight = require('../../light/semantic/colorErrorLowLight.cjs');

/** Holds the **error-low** color, typically used for text or border. */
const colorErrorLow = `light-dark(${colorErrorLowLight.colorErrorLowLight},${colorErrorLowDark.colorErrorLowDark})`;

exports.colorErrorLow = colorErrorLow;
