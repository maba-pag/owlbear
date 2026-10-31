'use strict';

var colorInfoMediumDark = require('../../dark/semantic/colorInfoMediumDark.cjs');
var colorInfoMediumLight = require('../../light/semantic/colorInfoMediumLight.cjs');

/** Holds the **info-medium** color, typically used for text or border. */
const colorInfoMedium = `light-dark(${colorInfoMediumLight.colorInfoMediumLight},${colorInfoMediumDark.colorInfoMediumDark})`;

exports.colorInfoMedium = colorInfoMedium;
