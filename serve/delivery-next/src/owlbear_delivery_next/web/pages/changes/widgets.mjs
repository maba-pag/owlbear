import { html, nothing } from "/assets/lit-html/3.3.3/lit-html.js";
import { live } from "/assets/lit-html/3.3.3/directives/live.js";
import { state, show, draft } from "./state.mjs";

// A toggle whose open state survives every render, kept under *key*: its summary, unless that changes as it runs.
export function toggle(key, summary, ...children) {
  const toggled = (e) => (e.target.open ? state.opened.add(key) : state.opened.delete(key));
  return html`<details .open=${state.opened.has(key)} @toggle=${toggled}><summary>${summary}</summary>
    ${children}</details>`;
}

export function disclosure(summary, ...children) {
  return toggle(summary, summary, ...children);
}

export function button(label, onclick, { icon, variant, aria, busy = false, disabled = false, title, keys, cls } = {}) {
  return html`<p-button type="button" compact="true" icon=${icon ?? nothing} variant=${variant ?? nothing}
    aria=${aria ?? nothing} title=${title ?? nothing} aria-keyshortcuts=${keys ?? nothing} class=${cls ?? nothing}
    .loading=${busy} ?disabled=${disabled} @click=${onclick}>${label}</p-button>`;
}

export function external(label, href) {
  let web = false;
  try {
    web = ["http:", "https:"].includes(new URL(href).protocol);
  } catch {
    web = false;
  }
  if (!web) return html`<p-text>${label}</p-text>`;
  return html`<p-link-pure icon="external"><a href=${href} target="_blank" rel="noopener">${label}</a></p-link-pure>`;
}

// A text field bound to the draft field *name* of form *key*.
export function field(key, name, label, rows = "2") {
  const d = draft(key, () => ({})), keep = (e) => { d[name] = e.target.value ?? ""; };
  return html`<p-textarea label=${label} rows=${rows} .value=${live(d[name] ?? "")} @input=${keep}
    @change=${keep}></p-textarea>`;
}

// Radio choices bound to the draft field *name* of form *key*; re-rendering never changes the choice, and a choice
// the data no longer offers is dropped, so nothing unseen is sent.
export function choice(key, name, label, options) {
  const d = draft(key, () => ({})), pick = (v) => { d[name] = v; show(); };
  if (d[name] !== undefined && !options.some((o) => o.id === d[name])) delete d[name];
  return html`<p-radio-group name=${`${key}-${name}`} label=${label} .value=${live(d[name] ?? "")}
    @change=${(e) => pick(e.target.value)}>${options.map((o) => html`<p-radio-group-option value=${o.id}
    label=${o.label}></p-radio-group-option>`)}</p-radio-group>`;
}

export function tick(label, checked, flipped) {
  const flip = (e) => flipped(e.target.checked === true);
  return html`<p-checkbox label=${label} .checked=${live(checked)} @change=${flip}></p-checkbox>`;
}

export function hd(level, title, size, { tabindex } = {}) {
  const t = { 2: html`<h2 tabindex=${tabindex ?? nothing}>${title}</h2>`, 3: html`<h3>${title}</h3>`,
    4: html`<h4>${title}</h4>`, 5: html`<h5>${title}</h5>` }[level];
  return html`<p-heading size=${size}>${t}</p-heading>`;
}

export function text(value, { size, weight, color, tag } = {}) {
  return html`<p-text size=${size ?? nothing} weight=${weight ?? nothing} color=${color ?? nothing}
    tag=${tag ?? nothing}>${value}</p-text>`;
}

export function list(items, ordered = false) {
  const lis = items.map((i) => html`<li>${i}</li>`);
  return ordered ? html`<ol>${lis}</ol>` : html`<ul>${lis}</ul>`;
}

export function row(...children) {
  return html`<div class="row">${children}</div>`;
}

// Something the owner acts on: a framed panel; the status line above already says it is his turn.
export function panel(title, form, ...children) {
  const refused = state.refused?.form === form && form ? refusal(state.refused.text) : nothing;
  return html`<section class="panel act">${hd(3, title, "md")}${children}${refused}</section>`;
}

// What Delivery knows about the Change: a plain section under a rule.
export function info(title, ...children) {
  return html`<section class="info">${hd(3, title, "md")}${children}</section>`;
}

export function notice(kind, title, ...lines) {
  return html`<p-inline-notification state=${kind} heading=${title} heading-tag="h3" description=${lines.join(" ")}
    dismiss-button="false"></p-inline-notification>`;
}

export function refusal(said) {
  return html`<div class="refused">${notice("error", "Not done", said)}</div>`;
}

export function meta(value, cls = "meta") {
  return html`<span class=${cls}>${value}</span>`;
}
