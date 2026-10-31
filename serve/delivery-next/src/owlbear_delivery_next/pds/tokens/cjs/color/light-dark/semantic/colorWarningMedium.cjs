'use strict';

var colorWarningMediumDark = require('../../dark/semantic/colorWarningMediumDark.cjs');
var colorWarningMediumLight = require('../../light/semantic/colorWarningMediumLight.cjs');

/** Holds the **warning-medium** color, typically used for text or border. */
const colorWarningMedium = `light-dark(${colorWarningMediumLight.colorWarningMediumLight},${colorWarningMediumDark.colorWarningMediumDark})`;

exports.colorWarningMedium = colorWarningMedium;
