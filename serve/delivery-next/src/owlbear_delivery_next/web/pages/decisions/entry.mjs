import { html, nothing } from "/assets/lit-html/3.3.3/lit-html.js";
import { call, loaded } from "/assets/ui.mjs";
import { actions, form } from "./actions.mjs";
import { impact } from "./impact.mjs";
import { at, readBack, sameAddress, STATES, show, state, untagged } from "./state.mjs";
import { listed } from "./widgets.mjs";

let detailTurn = 0;

export async function open(id, { again = false, from = "list", address = null } = {}) {
  if (!again && state.opened === id && state.from === from && sameAddress(state.address, address)) {
    detailTurn++;
    Object.assign(state, { opened: null, entry: null, unread: false, form: null, address: null });
    return show();
  }
  const turn = ++detailTurn, reading = again ? state.address : address;
  if (!again) Object.assign(state, { opened: id, from, address, entry: null, unread: false, form: null, effect: "" });
  show();
  const path = `/decisions/${encodeURIComponent(id)}`;
  try {
    const entry = await call(at(path, reading));
    if (loaded()) entry.changes = (await call(`${path}/changes`, { machine: true })).changes;  // every project's
    if (turn === detailTurn && state.opened === id) state.entry = { ...entry, address: reading };
  } catch (error) {
    if (turn === detailTurn) Object.assign(state, { error: error.message, unread: state.opened === id });
  }
  show();
}

function link(l) {
  const where = l.state ? ` (${STATES[l.state] ?? l.state})` : "";
  return `${l.type.replace("_", " ")} ${l.title}${where}`;
}

function change(c) {
  const where = c.project ? `${c.project}: ` : "";
  return `${where}${c.handle || c.slug} ${c.title} · ${c.step}${c.applies ? " · applies to it" : ""}`;
}

export function detail() {
  const e = state.entry;
  if (!e) {
    return html`<p-text size="sm" color="contrast-medium" role="status">${state.unread
      ? "This decision could not be read. Close it and open it again to retry." : "Reading the decision…"}</p-text>`;
  }
  return html`<div class="detail" id="detail">
    <dl class="facts">
      <dt>Origin</dt><dd>${e.origin}</dd>
      <dt>Recorded</dt><dd>${e.created_at.slice(0, 10)} by ${e.actor}${e.source ? ` · ${e.source}` : ""}</dd>
      <dt>State</dt><dd>${STATES[e.state]}${e.active ? " · active" : ""}${e.conflict ? " · in conflict" : ""}</dd>
      <dt>Read-back</dt><dd>${readBack(e)}</dd>
      ${e.topic ? html`<dt>Topic</dt><dd>${e.topic}</dd>` : nothing}
      <dt>Revision</dt><dd>${e.revision.slice(0, 12)}</dd>
    </dl>
    ${e.rationale ? html`<section><p-heading size="sm"><h3>Why</h3></p-heading>
      <p-text class="said" size="sm">${untagged(e.rationale)}</p-text></section>` : nothing}
    ${e.problems.length ? html`<p-inline-notification state="warning" heading="Not active" heading-tag="h3"
      dismiss-button="false">${e.problems.map((p) => `${p.rule}: ${untagged(p.message)}`).join(" ")}
      </p-inline-notification>` : nothing}
    ${listed("Links", e.links, link)}
    ${listed("Linked from", e.linked_from, link)}
    ${listed("History", e.history, (h) => `${h.at.slice(0, 10)} ${h.commit} ${h.action}`,
      "Not committed yet.")}
    ${listed("Changes that pinned it", e.changes, change, "No Change pinned it.")}
    ${impact(e)}
    ${form(e)}
    ${actions(e)}
  </div>`;
}
