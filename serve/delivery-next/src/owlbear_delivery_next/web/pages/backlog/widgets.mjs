import { html, nothing } from "/assets/lit-html/3.3.3/lit-html.js";
import { live } from "/assets/lit-html/3.3.3/directives/live.js";

export function button(label, onclick, { variant, icon, aria, busy = false, disabled = false } = {}) {
  return html`<p-button type="button" compact="true" variant=${variant ?? nothing} icon=${icon ?? nothing}
    aria=${aria ?? nothing} .loading=${busy} ?disabled=${disabled} @click=${onclick}>${label}</p-button>`;
}

// A choice list showing *value* as the data has it; *chosen* gets the person's pick.
export function select(label, options, value, chosen, { compact = false, hideLabel = false } = {}) {
  const changed = (e) => chosen(e.target.value);
  return html`<p-select label=${label} compact=${compact ? "true" : nothing}
      hide-label=${hideLabel ? "true" : nothing} .value=${live(value)} @change=${changed}>
    ${options.map(([v, said]) => html`<p-select-option value=${v}>${said}</p-select-option>`)}</p-select>`;
}

// A text field bound to a draft: *typed* keeps each keystroke, so a re-render shows the draft again.
export function field(label, value, typed, { multiline = false, rows = "3" } = {}) {
  const max = multiline ? "4000" : "200", keep = (e) => typed(e.target.value ?? "");
  return multiline
    ? html`<p-textarea label=${label} max-length=${max} rows=${rows} .value=${live(value)} @input=${keep}
        @change=${keep}></p-textarea>`
    : html`<p-input-text label=${label} max-length=${max} .value=${live(value)} @input=${keep}
        @change=${keep}></p-input-text>`;
}

export function tick(label, checked, flipped) {
  const flip = (e) => flipped(e.target.checked === true);
  return html`<p-checkbox label=${label} hide-label="true" .checked=${live(checked)} @change=${flip}></p-checkbox>`;
}

export function labelled(label, checked, flipped, disabled = false) {
  const flip = (e) => flipped(e.target.checked === true);
  return html`<p-checkbox label=${label} .checked=${live(checked)} ?disabled=${disabled} @change=${flip}></p-checkbox>`;
}
