import { html, nothing } from "/assets/lit-html/3.3.3/lit-html.js";
import { repeat } from "/assets/lit-html/3.3.3/directives/repeat.js";
import { call } from "/assets/ui.mjs";
import { receipts } from "./actions.mjs";
import { detail, open } from "./entry.mjs";
import { queue } from "./queue.mjs";
import { loadRecovery, recoveryView } from "./recovery.mjs";
import { addressOf, cutOff, filter, readBack, sameAddress, STATES, scopeOf, show, state, TAGS } from "./state.mjs";
import { field, select } from "./widgets.mjs";

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

let listTurn = 0;

export async function refresh() {
  const turn = ++listTurn, where = filter.where;
  await loadRecovery();
  try {
    const list = await call(`/decisions?${query()}`);
    if (turn !== listTurn) return;
    state.loaded = { ...list, address: addressOf(where, list.project) };
    state.error = "";
  } catch (error) {
    if (turn !== listTurn) return;
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

function tags(d) {
  return html`<div class="tags">
    <p-tag compact="true" class="scope">${scopeOf(d)}</p-tag>
    <p-tag compact="true" class="origin">${d.origin}</p-tag>
    <p-tag compact="true" variant=${TAGS[d.state]} class="state">${STATES[d.state]}</p-tag>
    ${d.conflict ? html`<p-tag compact="true" variant="error" class="conflict">conflict</p-tag>` : nothing}
    ${d.findings && !d.conflict ? html`<p-tag compact="true" variant="warning">problem</p-tag>` : nothing}
    ${d.read_back === "none" && !d.inherited ? nothing : html`<p-tag compact="true" class="read-back">${readBack(d)}
      </p-tag>`}</div>`;
}

// One decision as PDS's accordion: its heading and statement stay visible, its detail opens below them.
function card(d, address) {
  const opened = state.opened === d.id && state.from === "list" && sameAddress(state.address, address);
  const once = cutOff(d);
  return html`<li class="entry" data-id=${d.id}>
    <p-accordion compact="true" background="surface" .open=${opened} @update=${() => open(d.id, { address })}>
      <div slot="summary" class="summary"><div class="named"><p-heading tag="h3" size="sm" weight="semibold"
        class="heading">${once ? d.statement : d.title}</p-heading>
        ${once ? nothing : html`<p-text class="said" size="sm">${d.statement}</p-text>`}</div>${tags(d)}</div>
      ${opened ? detail() : nothing}
    </p-accordion>
  </li>`;
}

function listView(loaded) {
  const rows = loaded.decisions;
  const empty = loaded.total ? "No decision matches these filters." : "No decision is recorded yet.";
  return html`<section id="decisions" aria-labelledby="decisions-heading">
    <p-heading size="lg"><h2 id="decisions-heading">Recorded decisions</h2></p-heading>
    ${filters()}
    ${rows.length ? html`<ul class="entries" id="entries">${repeat(rows, (d) => d.id, (d) => card(d, loaded.address))}
      </ul>` : html`<p-text class="empty" color="contrast-medium">${empty}</p-text>`}
  </section>`;
}

export function view() {
  const loaded = state.loaded, available = loaded?.available;
  document.getElementById("shown").textContent = available ? `${loaded.decisions.length} of ${loaded.total} shown`
    : "";
  return html`
    ${recoveryView()}
    <p-inline-notification id="error" state="error" dismiss-button="false" ?hidden=${!state.error}>${state.error}
    </p-inline-notification>
    <p-inline-notification id="unavailable" state="info" heading="Decisions cannot be read" heading-tag="h2"
      dismiss-button="false" ?hidden=${!loaded || available}>${loaded && !available ? loaded.reason : ""}
    </p-inline-notification>
    ${receipts()}
    ${available ? queue() : nothing}
    ${available ? listView(loaded) : nothing}`;
}
