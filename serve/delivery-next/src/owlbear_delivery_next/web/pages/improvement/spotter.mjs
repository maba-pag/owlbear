import { html, nothing } from "/assets/lit-html/3.3.3/lit-html.js";
import { here } from "/assets/ui.mjs";
import { credits, empty, heading, plural, quiet, text } from "./widgets.mjs";

// The Spotter (design §6): each loaded project's settings and where each comes from, linked to Settings, and its
// spend over the last week. Its looks are listed under Looks.

// Where each setting comes from, in the Settings page's words.
const SOURCES = { default: "built-in default", global: "global", machine: "this machine", project: "this project",
  builder: "the builder's value" };

// What it does when it sees each category, as live delivery will act on it.
const CATEGORIES = [["hand_off_fitness", "Unfit hand-off"], ["course_and_constraints", "Wrong course"],
  ["outside_state_changes", "Change outside the task"], ["irreversible_harm", "Irreversible harm"]];

function setting(s, key, label, said = (v) => String(v)) {
  const v = s.spotter?.[key], from = s.sources?.[`spotter.${key}`];
  if (v === null || v === undefined) return nothing;
  return html`<li>${label}: ${said(v)}${from ? html` <span class="from">(${SOURCES[from] ?? from})</span>` : nothing}
    </li>`;
}

function model(s) {
  const m = s.model ?? {}, from = s.sources?.["agents.spotter.model"];
  if (!m.model) return html`<li>Model: the default</li>`;
  return html`<li>Model: ${m.model}${m.effort ? `, ${m.effort} effort` : ""}${from ? html` <span class="from">
    (${SOURCES[from] ?? from})</span>` : nothing}</li>`;
}

function spent(s) {
  if (!s) return "No looks in the last week.";
  const unknown = s.unknown ? `, ${plural(s.unknown, "look")} whose credits were not reported` : "";
  const stopped = s.stopped ? `, ${plural(s.stopped, "look")} stopped at its credit limit` : "";
  return `${plural(s.looks, "look")}, ${credits(s.credits)}${unknown}${stopped}.`;
}

function project(pid, p, spend) {
  const settings = p.error ? html`<p-inline-notification state="error" dismiss-button="false"
      heading="Its settings could not be read" description=${p.error}></p-inline-notification>`
    : html`<ul class="meta">${setting(p, "switch", "Switch")}${setting(p, "looks", "Looks", (v) => v.join(", "))}
      ${setting(p, "sample_rate", "Sample", (v) => `${v}% of completed actions`)}
      ${setting(p, "look_credit_limit", "Credit limit per look", (v) => `${v} credits`)}
      ${CATEGORIES.map(([key, label]) => setting(p, key, label))}${setting(p, "verbose", "Verbose")}${model(p)}</ul>`;
  return html`<li class="panel" id=${`spotter-${pid}`}>${heading(3, p.name, "sm")}${settings}
    ${text(`Last ${spend.window}: ${spent(spend.of)}`, { size: "sm" })}
    <p-link-pure icon="arrow-right"><a href=${here({ project: pid }, p.link)}>Change the Spotter's settings</a>
    </p-link-pure></li>`;
}

export function spotterSection(s) {
  const window = plural(s.window_days, "day"), ids = Object.keys(s.projects);
  const elsewhere = Object.entries(s.spend).filter(([pid]) => !s.projects[pid]);
  return html`<section id="spotter" aria-labelledby="spotter-title">
    ${heading(2, "The Spotter", "lg", "spotter-title")}
    ${quiet("It looks at agents' work at the moments its settings name and records what it sees. A look stopped at "
      + "its credit limit stops only that look.")}
    ${ids.length ? html`<ul class="cards">${ids.map((pid) => project(pid, s.projects[pid],
      { window, of: s.spend[pid] }))}</ul>` : empty("No project is loaded on this machine.")}
    ${elsewhere.map(([pid, of]) => quiet(`${pid ? `Project ${pid}, not loaded now` : "Outside a project"}, last `
      + `${window}: ${spent(of)}`))}
  </section>`;
}
