import { html, nothing } from "/assets/lit-html/3.3.3/lit-html.js";
import { call, loaded } from "/assets/ui.mjs";
import { actions, form } from "./actions.mjs";
import { impact } from "./impact.mjs";
import { at, readBack, STATES, show, state } from "./state.mjs";
import { listed } from "./widgets.mjs";

// Open one decision in full (or close it), under its read-back (*from* "queue") or in the list; *again* reads the
// opened one afresh and keeps its form.
export async function open(id, { again = false, from = "list" } = {}) {
  if (state.opened === id && !again && state.from === from) {
    Object.assign(state, { opened: null, entry: null, form: null });
    return show();
  }
  if (!again) Object.assign(state, { opened: id, from, entry: null, form: null, effect: "" });
  show();
  const path = `/decisions/${encodeURIComponent(id)}`;
  try {
    const entry = await call(at(path));
    if (loaded()) entry.changes = (await call(`${path}/changes`, { machine: true })).changes;  // every project's
    if (state.opened === id) state.entry = entry;
  } catch (error) {
    state.error = error.message;
  }
  show();
}

function link(l) {
  const where = l.state ? ` (${STATES[l.state] ?? l.state})` : "";
  return `${l.type.replace("_", " ")} ${l.title}${where} · ${l.id}`;
}

function change(c) {
  const where = c.project ? `${c.project}: ` : "";
  return `${where}${c.handle || c.slug} ${c.title} · ${c.step}${c.applies ? " · applies to it" : ""}`;
}

export function detail() {
  const e = state.entry;
  if (!e) return html`<p-text size="sm" color="contrast-medium" role="status">Reading the decision…</p-text>`;
  const words = e.owner_words.map((w) => html`<li>“${w.text}” (${w.date})</li>`);
  return html`<div class="detail" id="detail">
    <dl class="facts">
      <dt>Id</dt><dd>${e.id}${e.aliases.length ? ` (${e.aliases.join(", ")})` : ""}</dd>
      <dt>Origin</dt><dd>${e.origin}</dd>
      <dt>Recorded</dt><dd>${e.created_at.slice(0, 10)} by ${e.actor}${e.source ? ` · ${e.source}` : ""}</dd>
      <dt>State</dt><dd>${STATES[e.state]}${e.active ? " · active" : ""}${e.conflict ? " · in conflict" : ""}</dd>
      <dt>Read-back</dt><dd>${readBack(e.read_back)}</dd>
      ${e.topic ? html`<dt>Topic</dt><dd>${e.topic}</dd>` : nothing}
      <dt>Revision</dt><dd>${e.revision.slice(0, 12)}</dd>
    </dl>
    ${words.length ? html`<section><p-heading size="sm"><h3>The owner's words</h3></p-heading><ul>${words}</ul>
      </section>` : nothing}
    ${e.rationale ? html`<section><p-heading size="sm"><h3>Why</h3></p-heading>
      <p-text class="said" size="sm">${e.rationale}</p-text></section>` : nothing}
    ${e.problems.length ? html`<p-inline-notification state="warning" heading="Not active" heading-tag="h3"
      dismiss-button="false">${e.problems.map((p) => `${p.rule}: ${p.message}`).join(" ")}
      </p-inline-notification>` : nothing}
    ${listed("Links", e.links, link)}
    ${listed("Linked from", e.linked_from, link)}
    ${listed("History", e.history, (h) => `${h.at.slice(0, 10)} ${h.commit} ${h.subject}`, "Not committed yet.")}
    ${listed("Changes that pinned it", e.changes, change, "No Change pinned it.")}
    ${impact(e)}
    ${form(e)}
    ${actions(e)}
  </div>`;
}
