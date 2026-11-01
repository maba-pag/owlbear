'use strict';

var colorFrostedStrongDark = require('../../dark/background/colorFrostedStrongDark.cjs');
var colorFrostedStrongLight = require('../../light/background/colorFrostedStrongLight.cjs');

/** Holds the **frosted-strong** color, typically used as a stronger frosted background. */
const colorFrostedStrong = `light-dark(${colorFrostedStrongLight.colorFrostedStrongLight},${colorFrostedStrongDark.colorFrostedStrongDark})`;

exports.colorFrostedStrong = colorFrostedStrong;
