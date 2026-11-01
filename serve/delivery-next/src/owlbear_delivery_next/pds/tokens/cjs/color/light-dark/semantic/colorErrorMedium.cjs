'use strict';

var colorErrorMediumDark = require('../../dark/semantic/colorErrorMediumDark.cjs');
var colorErrorMediumLight = require('../../light/semantic/colorErrorMediumLight.cjs');

/** Holds the **error-medium** color, typically used for text or border. */
const colorErrorMedium = `light-dark(${colorErrorMediumLight.colorErrorMediumLight},${colorErrorMediumDark.colorErrorMediumDark})`;

exports.colorErrorMedium = colorErrorMedium;
