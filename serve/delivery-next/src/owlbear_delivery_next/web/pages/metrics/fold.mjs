import { html } from "/assets/lit-html/3.3.3/lit-html.js";

/** A section's chart slot above its table, folded: a native fold, closed at each page load, opened on demand. */
export function folded(name, label, body) {
  return html`<div id=${`${name}-chart`} class="chart"></div>
    <details id=${`${name}-fold`} class="fold"><summary>${label}</summary>${body}</details>`;
}
