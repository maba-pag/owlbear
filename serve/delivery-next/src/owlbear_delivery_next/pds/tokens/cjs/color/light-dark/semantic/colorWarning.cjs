'use strict';

var colorWarningDark = require('../../dark/semantic/colorWarningDark.cjs');
var colorWarningLight = require('../../light/semantic/colorWarningLight.cjs');

/** Holds the **warning** color, typically used for text. */
const colorWarning = `light-dark(${colorWarningLight.colorWarningLight},${colorWarningDark.colorWarningDark})`;

exports.colorWarning = colorWarning;
