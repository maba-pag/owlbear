'use strict';

var colorSuccessMediumDark = require('../../dark/semantic/colorSuccessMediumDark.cjs');
var colorSuccessMediumLight = require('../../light/semantic/colorSuccessMediumLight.cjs');

/** Holds the **success-medium** color, typically used for text or border. */
const colorSuccessMedium = `light-dark(${colorSuccessMediumLight.colorSuccessMediumLight},${colorSuccessMediumDark.colorSuccessMediumDark})`;

exports.colorSuccessMedium = colorSuccessMedium;
