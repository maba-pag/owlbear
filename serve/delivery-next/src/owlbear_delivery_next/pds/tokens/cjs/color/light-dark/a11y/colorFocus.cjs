'use strict';

var colorFocusDark = require('../../dark/a11y/colorFocusDark.cjs');
var colorFocusLight = require('../../light/a11y/colorFocusLight.cjs');

/** Holds the **focus** color, typically used as the outline for `:focus-visible` states. */
const colorFocus = `light-dark(${colorFocusLight.colorFocusLight},${colorFocusDark.colorFocusDark})`;

exports.colorFocus = colorFocus;
