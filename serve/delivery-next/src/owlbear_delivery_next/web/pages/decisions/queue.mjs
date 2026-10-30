import { html, nothing } from "/assets/lit-html/3.3.3/lit-html.js";
import { repeat } from "/assets/lit-html/3.3.3/directives/repeat.js";
import { call } from "/assets/ui.mjs";
import { leads } from "./actions.mjs";
import { detail, open } from "./entry.mjs";
import { refresh } from "./list.mjs";
import { at, cutOff, KINDS, notify, sameAddress, scopeOf, show, state, untagged, WRITE } from "./state.mjs";
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

// The queue asks with one primary (D-01M63C7BJZZ7RQV9XS4XVR0DNE): the *lead* read-back's answer, Still right, or
// Open to resolve for a derived one; once a read-back opened in it shows its detail and that asks, its actions hold
// it instead.
const isOpen = (q, address) => state.opened === q.id && state.from === "queue" && sameAddress(state.address, address);

function item(q, address, lead) {
  const busy = (a) => state.pending === `${a}:${q.id}`, opened = isOpen(q, address);
  const choices = [
    q.derived ? nothing : button("Still right", () => answer(q, address, "read-back", { confirmed: true }),
      { variant: lead ? "primary" : "secondary", busy: busy("read-back") }),
    button(opened ? "Close" : q.derived ? "Open to resolve" : "Replace or withdraw", () => open(q.id,
      { from: "queue", address }), { variant: lead && q.derived ? "primary" : "secondary",
      aria: `{ 'aria-expanded': ${opened} }` }),
    q.ignored ? nothing : button("Ignore for now", () => answer(q, address, "ignore-read-back"),
      { variant: "secondary", busy: busy("ignore-read-back") }),
  ];
  const once = cutOff(q);
  return html`<li class="queued" data-id=${q.id}>
    <div class="title"><p-tag compact="true" variant=${VARIANT[q.kind]} class="kind">${KINDS[q.kind]}</p-tag>
      <p-text weight="semibold">${once ? q.statement : q.title}</p-text><p-tag compact="true" class="scope">
      ${scopeOf(q)}</p-tag><p-tag compact="true" class="origin">${q.origin}</p-tag>
      ${q.ignored ? html`<p-tag compact="true" variant="secondary">ignored for now</p-tag>` : nothing}</div>
    ${once ? nothing : html`<p-text class="said" size="sm">${q.statement}</p-text>`}
    <p-text size="sm" class="why">Asked again because: ${untagged(q.why)}</p-text>
    <div class="row" role="group" aria-label=${`Is “${q.title}” still right?`}>${choices}</div>
    ${opened ? detail() : nothing}
  </li>`;
}

// The read-backs waiting in this scope, first on the page (TD-427): most urgent first, then oldest; ignoring one
// leaves its rule in force as recorded. With none waiting the section is left out; what the last answer said stays.
export function queue() {
  const waiting = state.loaded.queue ?? [], address = state.loaded.address;
  const notice = state.notice ? html`<p-text id="notice" role="status" size="sm">${untagged(state.notice)}</p-text>`
    : nothing;
  if (!waiting.length) return notice;
  const reading = state.entry && waiting.some((q) => isOpen(q, address)) && leads(state.entry);
  return html`<section id="queue" aria-labelledby="queue-heading">
    <p-heading size="lg"><h2 id="queue-heading">Read-backs (${waiting.length})</h2></p-heading>
    ${notice}
    <ul class="entries" id="read-backs">${repeat(waiting, (q) => q.id, (q, i) => item(q, address, i === 0 && !reading))}
    </ul>
  </section>`;
}
