'use strict';

var colorInfoDark = require('../../dark/semantic/colorInfoDark.cjs');
var colorInfoLight = require('../../light/semantic/colorInfoLight.cjs');

/** Holds the **info** color, typically used for text. */
const colorInfo = `light-dark(${colorInfoLight.colorInfoLight},${colorInfoDark.colorInfoDark})`;

exports.colorInfo = colorInfo;
