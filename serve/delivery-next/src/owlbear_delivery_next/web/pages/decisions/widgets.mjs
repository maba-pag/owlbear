import { html, nothing } from "/assets/lit-html/3.3.3/lit-html.js";
import { live } from "/assets/lit-html/3.3.3/directives/live.js";

export function button(label, onclick, { variant, icon, aria, busy = false } = {}) {
  return html`<p-button type="button" compact="true" variant=${variant ?? nothing} icon=${icon ?? nothing}
    aria=${aria ?? nothing} .loading=${busy} @click=${onclick}>${label}</p-button>`;
}

// A choice list showing *value*; *chosen* gets the owner's pick.
export function select(label, options, value, chosen) {
  return html`<p-select label=${label} .value=${live(value)} @change=${(e) => chosen(e.target.value)}>
    ${options.map(([v, said]) => html`<p-select-option value=${v}>${said}</p-select-option>`)}</p-select>`;
}

// A text field bound to a draft: *typed* keeps each keystroke, so a re-render shows the draft again.
export function field(label, value, typed, { multiline = false, max = 200, description, changed } = {}) {
  const keep = (e) => typed(e.target.value ?? "");
  const done = changed ? (e) => { keep(e); changed(); } : keep;
  return multiline
    ? html`<p-textarea label=${label} description=${description ?? nothing} max-length=${max} rows="3"
        .value=${live(value)} @input=${keep} @change=${done}></p-textarea>`
    : html`<p-input-text label=${label} description=${description ?? nothing} max-length=${max}
        .value=${live(value)} @input=${keep} @change=${done}></p-input-text>`;
}

// A titled list, or *empty* when it has no items.
export function listed(title, items, item, empty = "") {
  if (!items.length && !empty) return nothing;
  return html`<section><p-heading size="sm"><h3>${title}</h3></p-heading>
    ${items.length ? html`<ul>${items.map((i) => html`<li>${item(i)}</li>`)}</ul>`
      : html`<p-text size="sm" color="contrast-medium">${empty}</p-text>`}</section>`;
}
