import { html } from "/assets/lit-html/3.3.3/lit-html.js";

// The watcher's reports as rows, shared by a Change's Watcher list and the Improvement page's outside writes.
// W1a: the watcher only reports. A report says a command was observed writing somewhere, never that it wrote.

function when(iso) {
  const t = new Date(iso);
  if (Number.isNaN(t.getTime())) return html`<span></span>`;
  return html`<time datetime=${iso} title=${t.toLocaleString()}>${t.toLocaleTimeString()}</time>`;
}

function said(r) {
  const parts = r.targets.length ? [`observed a command writing to ${r.targets.join(", ")}`, r.verdict] : [r.verdict];
  if (r.targets.length && r.unresolved) parts.push(`and its ${r.unresolved}`);
  return parts.join(" \u00b7 ");
}

// The reports as timed rows; *label* names a row's place (its project and Change) where several are listed.
export function entries(reports, label = () => "") {
  return html`<ol class="log">${reports.map((r) => html`<li>${when(r.at)}<span>${label(r) ? `${label(r)} \u00b7 `
    : ""}${r.agent} \u00b7 ${r.command || r.tool}<br><span class="meta">${said(r)}</span></span></li>`)}</ol>`;
}
