'use strict';

var colorErrorDark = require('../../dark/semantic/colorErrorDark.cjs');
var colorErrorLight = require('../../light/semantic/colorErrorLight.cjs');

/** Holds the **error** color, typically used for text. */
const colorError = `light-dark(${colorErrorLight.colorErrorLight},${colorErrorDark.colorErrorDark})`;

exports.colorError = colorError;
