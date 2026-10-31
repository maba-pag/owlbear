'use strict';

var colorSuccessDark = require('../../dark/semantic/colorSuccessDark.cjs');
var colorSuccessLight = require('../../light/semantic/colorSuccessLight.cjs');

/** Holds the **success** color, typically used for text. */
const colorSuccess = `light-dark(${colorSuccessLight.colorSuccessLight},${colorSuccessDark.colorSuccessDark})`;

exports.colorSuccess = colorSuccess;
