'use strict';

var colorBackdropDark = require('../../dark/background/colorBackdropDark.cjs');
var colorBackdropLight = require('../../light/background/colorBackdropLight.cjs');

/** Holds the **backdrop** color, typically used for backdrops. */
const colorBackdrop = `light-dark(${colorBackdropLight.colorBackdropLight},${colorBackdropDark.colorBackdropDark})`;

exports.colorBackdrop = colorBackdrop;
