'use strict';

var colorSurfaceDark = require('../../dark/background/colorSurfaceDark.cjs');
var colorSurfaceLight = require('../../light/background/colorSurfaceLight.cjs');

/** Holds the **surface** color, typically used for surfaces. */
const colorSurface = `light-dark(${colorSurfaceLight.colorSurfaceLight},${colorSurfaceDark.colorSurfaceDark})`;

exports.colorSurface = colorSurface;
