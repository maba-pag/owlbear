import { html, nothing } from "/assets/lit-html/3.3.3/lit-html.js";
import { repeat } from "/assets/lit-html/3.3.3/directives/repeat.js";
import { call } from "/assets/ui.mjs";
import { receipts } from "./actions.mjs";
import { detail, open } from "./entry.mjs";
import { queue } from "./queue.mjs";
import { filter, readBack, STATES, scopeOf, show, state, TAGS } from "./state.mjs";
import { button, field, select } from "./widgets.mjs";

const WHERE = [["all", "This project and Global"], ["project", "This project"], ["global", "Global"],
  ["owlbear", "OwlBear"]];
const SHOWN = [["", "In force and drafts"], ...Object.entries(STATES), ["all", "All, retired included"]];
const ORIGINS = [["", "Any"], ["decided", "decided"], ["approved", "approved"], ["autonomous", "autonomous"]];
const READ = [["", "Any"], ["none", "Not read back"], ["pending", "Waiting to be read back"], ["done", "Read back"]];

function query() {
  const q = new URLSearchParams({ where: filter.where });
  for (const key of ["topic", "origin", "read_back", "text"]) if (filter[key]) q.set(key, filter[key]);
  if (filter.state === "all") q.set("retired", "true");
  else if (filter.state) q.set("state", filter.state);
  return q.toString();
}

// The list as the filters ask for it, then the opened decision again so its actions use its current revision.
export async function refresh() {
  try {
    state.loaded = await call(`/decisions?${query()}`);
    state.error = "";
  } catch (error) {
    state.error = error.message;
  }
  show();
  if (state.opened) await open(state.opened, { again: true });
}

function chose(key) {
  return (value) => {
    filter[key] = value;
    refresh();
  };
}

function filters() {
  const topics = [["", "Any"], ...state.loaded.topics.map((t) => [t, t])];
  if (!topics.some(([t]) => t === filter.topic)) filter.topic = "";
  return html`<section id="filters" class="row" aria-label="Filters">
    ${select("Show", WHERE, filter.where, chose("where"))}
    ${select("State", SHOWN, filter.state, chose("state"))}
    ${select("Topic", topics, filter.topic, chose("topic"))}
    ${select("Origin", ORIGINS, filter.origin, chose("origin"))}
    ${select("Read-back", READ, filter.read_back, chose("read_back"))}
    ${field("Search", filter.text, (v) => { filter.text = v; }, { changed: refresh,
      description: "Words in the title or statement; press Enter" })}
  </section>`;
}

function card(d) {
  const opened = state.opened === d.id && state.from === "list";
  return html`<li class="entry" data-id=${d.id}>
    <div class="title"><p-text weight="semibold">${d.title}</p-text>
      <p-tag compact="true" class="scope">${scopeOf(d)}</p-tag>
      <p-tag compact="true" class="origin">${d.origin}</p-tag>
      <p-tag compact="true" variant=${TAGS[d.state]} class="state">${STATES[d.state]}</p-tag>
      ${d.conflict ? html`<p-tag compact="true" variant="error" class="conflict">conflict</p-tag>` : nothing}
      ${d.findings && !d.conflict ? html`<p-tag compact="true" variant="warning">problem</p-tag>` : nothing}
      ${d.read_back === "none" ? nothing : html`<p-tag compact="true" class="read-back">${readBack(d.read_back)}
        </p-tag>`}</div>
    <p-text class="said" size="sm">${d.statement}</p-text>
    <div class="row">${button(opened ? "Close" : "Open", () => open(d.id), { variant: "secondary",
      aria: `{ 'aria-expanded': ${opened} }` })}</div>
    ${opened ? detail() : nothing}
  </li>`;
}

export function view() {
  const loaded = state.loaded, available = loaded?.available;
  const rows = available ? loaded.decisions : [];
  document.getElementById("shown").textContent = available ? `${rows.length} of ${loaded.total} shown` : "";
  const empty = loaded?.total ? "No decision matches these filters." : "No decision is recorded yet.";
  return html`
    <p-inline-notification id="error" state="error" dismiss-button="false" ?hidden=${!state.error}>${state.error}
    </p-inline-notification>
    <p-inline-notification id="unavailable" state="info" heading="Decisions cannot be read" heading-tag="h2"
      dismiss-button="false" ?hidden=${!loaded || available}>${loaded && !available ? loaded.reason : ""}
    </p-inline-notification>
    ${receipts()}
    ${available ? queue() : nothing}
    ${available ? filters() : nothing}
    ${available && rows.length ? html`<ul class="entries" id="entries">${repeat(rows, (d) => d.id, card)}</ul>`
      : nothing}
    ${available && !rows.length ? html`<p-text class="empty" color="contrast-medium">${empty}</p-text>` : nothing}`;
}
