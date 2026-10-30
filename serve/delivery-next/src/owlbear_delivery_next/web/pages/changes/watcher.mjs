import { html, nothing } from "/assets/lit-html/3.3.3/lit-html.js";
import { toggle, info, text } from "./widgets.mjs";

// W1a: the watcher only reports. A report says a command was observed writing somewhere, never that it wrote.
const WRITER = "writer"; // the source of a run's summary row: what its writer did not record

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

function entries(reports) {
  return html`<ol class="log">${reports.map((r) => html`<li>${when(r.at)}<span>${r.agent} \u00b7 ${r.command
    || r.tool}<br><span class="meta">${said(r)}</span></span></li>`)}</ol>`;
}

function plural(n, one) {
  return `${n} ${one}${n === 1 ? "" : "s"}`;
}

// The Change's "Watcher" list: outside writes first, calls not classified yet apart and counted on their own.
export function watcherSection(w) {
  if (!w) return nothing;
  const calls = w.reports.filter((r) => r.source !== WRITER), lost = w.reports.filter((r) => r.source === WRITER);
  const outside = calls.filter((r) => r.targets.length), open = calls.filter((r) => !r.targets.length);
  const state = w.on === false ? "The watcher is off for this project: nothing is observed or recorded."
    : w.on === true ? "Report only: nothing is judged or stopped yet." : "The watcher's switch could not be read.";
  const counted = `${plural(w.outside, "call")} observed writing outside the worktree \u00b7 `
    + `${plural(w.unresolved, "call")} whose shell effects are not classified yet`;
  return info("Watcher", text(state, { size: "xs", color: "contrast-medium" }), text(counted),
    outside.length ? entries(outside) : nothing,
    open.length ? toggle("watcher-open", `Not classified yet (${open.length})`, text("Shell effects are not "
      + "classified yet: every shell command that may write is listed here."), entries(open)) : nothing,
    lost.map((r) => text(r.verdict, { size: "xs", color: "contrast-medium" })));
}
