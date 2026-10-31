import { html, nothing } from "/assets/lit-html/3.3.3/lit-html.js";
import { live } from "/assets/lit-html/3.3.3/directives/live.js";
import { entries } from "/assets/page/changes/reports.mjs";
import { askFollowup, followupLine, said, send } from "./followup.mjs";
import { act, filter, kept, refresh, state } from "./state.mjs";
import { look, place } from "./record.mjs";
import { empty, heading, quiet, unread } from "./widgets.mjs";

// The Spotter's looks and the outside writes the watcher saw (design §6), of every loaded project, one project or one
// Change of it, each look with its follow-up. A Change's slug may repeat across projects, so the project is chosen
// first, by its id.

const changes = new Map();  // each project's Changes seen in its looks and writes, so a chosen one keeps the others

function names() {
  return Object.fromEntries(Object.entries(state.data?.spotter?.projects ?? {}).map(([pid, p]) => [pid, p.name]));
}

function choose(key, value) {
  filter[key] = value;
  if (key === "in") filter.change = "";
  kept();
  state.looks = null;
  refresh();
}

function select(id, label, value, options, key) {
  return html`<p-select id=${id} label=${label} compact="true" .value=${live(value)}
      @change=${(e) => choose(key, e.target.value)}>
    ${options.map(([v, said]) => html`<p-select-option value=${v}>${said}</p-select-option>`)}</p-select>`;
}

function filters(named) {
  if (filter.in && !filter.change && state.looks) {
    changes.set(filter.in, [...new Set([...state.looks.looks, ...state.looks.outside].map((r) => r.change)
      .filter(Boolean))].sort());
  }
  const projects = [["", "All projects"], ...Object.entries(named)];
  const seen = changes.get(filter.in) ?? [];
  const slugs = [["", "All Changes"], ...[...new Set([...seen, filter.change].filter(Boolean))].map((c) => [c, c])];
  return html`<div class="row filters">${select("looks-project", "Project", filter.in, projects, "in")}
    ${filter.in ? select("looks-change", "Change", filter.change, slugs, "change") : nothing}</div>`;
}

async function followUp(r) {
  if (state.busy || !(await askFollowup(r, "look"))) return;
  await act(`followup:${r.id}`, () => send(r), said);
}

function shown(r, named) {
  const key = `followup:${r.id}`;
  return look(r, named, followupLine(r, () => followUp(r), { busy: state.busy === key, disabled: !!state.busy }));
}

function body(named) {
  if (state.looksError && !state.looks) return unread("The looks", state.looksError);
  if (!state.looks) return quiet("Reading the looks\u2026");
  const { looks, outside, unread: missing } = state.looks;
  return html`${state.looksError ? unread("The newest looks", state.looksError) : nothing}
    ${heading(3, "The Spotter's looks", "md")}
    ${looks.length ? html`<ul class="cards">${looks.map((r) => shown(r, named))}</ul>`
      : empty("No look yet here: the Spotter looks at the moments its settings name.")}
    ${heading(3, "Outside writes", "md")}
    ${quiet("Commands the watcher observed writing outside their worktree. It only reports: nothing was stopped.")}
    ${missing.length ? unread("Some projects' writes", missing.join("; ")) : nothing}
    ${outside.length ? entries(outside, (r) => place(r, named)) : empty("No outside write observed here.")}`;
}

export function looksSection() {
  const named = names();
  return html`<section id="looks" aria-labelledby="looks-title">
    ${heading(2, "Looks and outside writes", "lg", "looks-title")}
    ${filters(named)}${body(named)}</section>`;
}
