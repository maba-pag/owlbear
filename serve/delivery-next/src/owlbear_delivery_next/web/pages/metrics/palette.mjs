// The charts' colours, per colour scheme. A test reads PARTS and SUCCESS and checks each against the PDS canvas.

// Okabe-Ito without black: orange, sky blue, bluish green, yellow, blue, vermillion, reddish purple. In light mode
// orange, sky blue and yellow are darkened in their own hue to reach 3:1 on the canvas; dark mode keeps the originals.
export const PARTS = {
  light: ["#BD8300", "#1D96DB", "#009E73", "#9C920C", "#0072B2", "#D55E00", "#CC79A7"],
  dark: ["#E69F00", "#56B4E9", "#009E73", "#F0E442", "#0072B2", "#D55E00", "#CC79A7"],
};
// PDS --p-color-success, for accepted tool calls.
export const SUCCESS = { light: "#197E10", dark: "#10C47F" };

// PDS canvas, surface, primary and contrast colours as solid colours over the canvas.
const BASE = {
  light: { canvas: "#FFFFFF", surface: "#F1F1F3", text: "#010205", muted: "#5F5F62", grid: "#D2D2D5" },
  dark: { canvas: "#010205", surface: "#19191A", text: "#FBFCFF", muted: "#A5A5A8", grid: "#3A3A3D" },
};

export const dark = matchMedia("(prefers-color-scheme: dark)");

/** The colours of the scheme the page shows now. */
export function theme() {
  const scheme = dark.matches ? "dark" : "light";
  return { ...BASE[scheme], parts: PARTS[scheme], success: SUCCESS[scheme] };
}
