import { html, nothing } from "/assets/lit-html/3.3.3/lit-html.js";

// The small parts every section of the page is made of.

export function heading(level, said, size, id) {
  const h = level === 2 ? html`<h2 id=${id ?? nothing}>${said}</h2>` : html`<h3 id=${id ?? nothing}>${said}</h3>`;
  return html`<p-heading size=${size}>${h}</p-heading>`;
}

export function text(said, { size, color, weight } = {}) {
  return html`<p-text size=${size ?? nothing} color=${color ?? nothing} weight=${weight ?? nothing}>${said}</p-text>`;
}

export function quiet(said) {
  return text(said, { size: "sm", color: "contrast-medium" });
}

export function button(label, onclick, { busy = false, disabled = false, variant, aria } = {}) {
  return html`<p-button type="button" compact="true" variant=${variant ?? "secondary"} aria=${aria ?? nothing}
    .loading=${busy} ?disabled=${disabled} @click=${onclick}>${label}</p-button>`;
}

export function tag(said, variant = "secondary") {
  return html`<p-tag compact="true" variant=${variant}>${said}</p-tag>`;
}

export function empty(said) {
  return html`<p class="empty">${text(said, { color: "contrast-medium" })}</p>`;
}

// A part that could not be read: its error in full, what still works.
export function unread(what, error) {
  return html`<p-inline-notification state="error" dismiss-button="false" heading=${`${what} could not be read`}
    description=${error}></p-inline-notification>`;
}

export function when(iso) {
  const t = new Date(iso ?? "");
  if (!iso || Number.isNaN(t.getTime())) return nothing;
  return html`<time datetime=${iso} title=${t.toLocaleString()}>${t.toLocaleString()}</time>`;
}

export const plural = (n, one) => `${n} ${one}${n === 1 ? "" : "s"}`;

export function credits(n, known = true) {
  const said = `${Number(n ?? 0).toFixed(2)} credits`;
  return known ? said : `at least ${said} (some not reported)`;
}

export const DIALOG = "{ 'aria-haspopup': 'dialog' }";  // PDS's aria property, for a button that opens a dialog
