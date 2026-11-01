'use strict';

var colorPrimaryDark = require('../../dark/foreground/colorPrimaryDark.cjs');
var colorPrimaryLight = require('../../light/foreground/colorPrimaryLight.cjs');

/** Holds the **primary** color, typically used for text. */
const colorPrimary = `light-dark(${colorPrimaryLight.colorPrimaryLight},${colorPrimaryDark.colorPrimaryDark})`;

exports.colorPrimary = colorPrimary;
