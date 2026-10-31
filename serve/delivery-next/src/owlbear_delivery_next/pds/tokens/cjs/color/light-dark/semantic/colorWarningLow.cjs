'use strict';

var colorWarningLowDark = require('../../dark/semantic/colorWarningLowDark.cjs');
var colorWarningLowLight = require('../../light/semantic/colorWarningLowLight.cjs');

/** Holds the **warning-low** color, typically used for text or border. */
const colorWarningLow = `light-dark(${colorWarningLowLight.colorWarningLowLight},${colorWarningLowDark.colorWarningLowDark})`;

exports.colorWarningLow = colorWarningLow;
