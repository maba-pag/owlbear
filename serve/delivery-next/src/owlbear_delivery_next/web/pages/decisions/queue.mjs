import { html, nothing } from "/assets/lit-html/3.3.3/lit-html.js";
import { repeat } from "/assets/lit-html/3.3.3/directives/repeat.js";
import { call } from "/assets/ui.mjs";
import { detail, open } from "./entry.mjs";
import { refresh } from "./list.mjs";
import { at, KINDS, notify, sameAddress, scopeOf, show, state, untagged, WRITE } from "./state.mjs";
import { button } from "./widgets.mjs";

const VARIANT = { safety: "error", blocked: "warning", uncertain: "info", improvement: "secondary" };

// One answer to a waiting read-back, at the revision the queue shows: "still right" records the read-back with its
// receipt; "ignore for now" writes nothing to the decision and moves the item to the bottom.
async function answer(q, address, action, body = {}) {
  state.pending = `${action}:${q.id}`;
  show();
  let failed = "";
  try {
    const r = await call(at(`/decisions/${encodeURIComponent(q.id)}/${action}`, address),
      { body: { revision: q.revision, ...body }, timeout: WRITE });
    state.receipts = r.receipts ?? [];
    state.notice = r.notice ?? "";
  } catch (error) {
    state.receipts = [];
    failed = error.message;
  }
  state.pending = "";
  await refresh();
  if (failed) notify(failed);
}

function item(q, address) {
  const busy = (a) => state.pending === `${a}:${q.id}`,
    opened = state.opened === q.id && state.from === "queue" && sameAddress(state.address, address);
  const choices = [
    q.derived ? nothing : button("Still right", () => answer(q, address, "read-back", { confirmed: true }),
      { busy: busy("read-back") }),
    button(opened ? "Close" : q.derived ? "Open to resolve" : "Replace or withdraw", () => open(q.id,
      { from: "queue", address }), { variant: "secondary", aria: `{ 'aria-expanded': ${opened} }` }),
    q.ignored ? nothing : button("Ignore for now", () => answer(q, address, "ignore-read-back"),
      { variant: "secondary", busy: busy("ignore-read-back") }),
  ];
  return html`<li class="queued" data-id=${q.id}>
    <div class="title"><p-tag compact="true" variant=${VARIANT[q.kind]} class="kind">${KINDS[q.kind]}</p-tag>
      <p-text weight="semibold">${q.title}</p-text><p-tag compact="true" class="scope">${scopeOf(q)}</p-tag>
      <p-tag compact="true" class="origin">${q.origin}</p-tag>
      ${q.ignored ? html`<p-tag compact="true" variant="secondary">ignored for now</p-tag>` : nothing}</div>
    <p-text class="said" size="sm">${q.statement}</p-text>
    <p-text size="sm" class="why">Asked again because: ${untagged(q.why)}</p-text>
    <div class="row" role="group" aria-label=${`Is “${q.title}” still right?`}>${choices}</div>
    ${opened ? detail() : nothing}
  </li>`;
}

// The read-backs waiting in this scope, first on the page (TD-427): most urgent first, then oldest; ignoring one
// leaves its rule in force as recorded.
export function queue() {
  const waiting = state.loaded.queue ?? [];
  return html`<section id="queue" aria-labelledby="queue-heading">
    <p-heading size="lg"><h2 id="queue-heading">Read-backs (${waiting.length})</h2></p-heading>
    ${state.notice ? html`<p-text id="notice" role="status" size="sm">${untagged(state.notice)}</p-text>` : nothing}
    ${waiting.length ? html`<ul class="entries" id="read-backs">${repeat(waiting, (q) => q.id,
      (q) => item(q, state.loaded.address))}</ul>`
      : html`<p-text size="sm" color="contrast-medium">No decision waits to be read back.</p-text>`}
  </section>`;
}
