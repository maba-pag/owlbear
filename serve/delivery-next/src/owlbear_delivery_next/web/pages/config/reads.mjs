// Outside data (#810): one read of the shared settings, the offered models, Impeccable's releases and this machine's
// settings, run when the page opens, when the host starts, every hour and by Read again; and the Global settings
// changed elsewhere, each kept until dismissed here or on Changes.
import { html, nothing } from "/assets/lit-html/3.3.3/lit-html.js";
import { call, here, reread, loaded as clones, project as current } from "/assets/ui.mjs";
import { state, show, showIdle, notify, turns } from "./state.mjs";
import { reload, readModels } from "./layers.mjs";
import { readAcross } from "./machine.mjs";
import { rowOf } from "./groups.mjs";
import { button } from "./cells.mjs";
import { unsaved } from "./sections.mjs";

function when(iso) {
  return iso ? new Date(iso).toLocaleString([], { dateStyle: "medium", timeStyle: "short" }) : "never";
}

// A value as the read keeps it (JSON text), in words: a text without its quotes, nothing as "unset".
function value(text) {
  if (text === null || text === undefined) return "unset";
  try {
    const v = JSON.parse(text);
    return typeof v === "string" ? v : text;
  } catch {
    return text;
  }
}

// What the page last showed of the reads: a poll naming another read or other notices refreshes it.
function seen(readAt, ids) {
  return `${readAt ?? ""}|${ids.join(",")}`;
}

const readAt = (reads) => (reads?.read_at ? Date.parse(reads.read_at) : 0);

const readStates = turns();  // the read state's answers overlap: the page's, the poll's and a dismissal's

// The read state (*reads*, or the host's now), unless an answer asked later or a later read's is shown: answers may
// arrive in any order. A state that does not read has no read time and is shown with its failure.
async function readState(reads) {
  const n = readStates.ask();
  try {
    const got = reads ?? (await call("/config/read")).reads;
    if (readStates.take(n) && !(got.read_at && readAt(got) < readAt(state.reads))) {
      state.reads = got;
      state.readsSeen = seen(got.read_at, got.notices.map((x) => x.id));
    }
    if (readStates.says(n)) state.readsError = "";
  } catch (e) {
    if (readStates.says(n)) state.readsError = e.message;
  }
}

// Everything the page shows from outside, as last read, with no read of its own: the read state, the layers (a 409
// says which file does not read and keeps what is shown), the machine and the other projects, then the models. Drafts
// stay.
export async function refresh(reads) {
  await readState(reads);
  show();
  if (await reload()) show();
  if (state.loaded) {
    await readAcross();
    show();
  }
  await readModels();
}

// Read every outside source now, then show what was found.
export async function readAgain() {
  if (state.reading) return;
  state.reading = true;
  state.readsError = "";
  show();
  let released = false;  // once this read has answered, another may start: its busy state is its own
  try {
    // a read pulls the shared repository and starts the Copilot runtime: minutes at worst
    const answer = await call("/config/read", { method: "POST", timeout: 200000 });
    state.reading = false;
    released = true;
    await refresh(answer.reads);
  } catch (e) {
    state.readsError = e.reread ?? e.message;
  } finally {
    if (!released) state.reading = false;
    showIdle();
  }
}

// The machine's poll: a read the page did not start (the hourly one, another page's) or a dismissal elsewhere.
export function followPolled(event) {
  const polled = event.detail?.reads;
  if (!polled || state.reading || state.saving || state.machineSaving) return;
  if (seen(polled.read_at, polled.notices) !== state.readsSeen) refresh();
}

async function dismiss(id) {
  try {
    await call("/settings-read/dismiss", { method: "POST", machine: true, body: { ids: [id] } });
  } catch (e) {
    notify(e.message);
    show();
    return;
  }
  await readState();  // asked after the dismissal, so no answer asked before it shows the notice again
  reread();  // the bar's poll knows at once, so no page refreshes for it again
  show();
}

// A link to the row that sets *key* in the layer *layer*, on this page or another project's.
function rowLink(key, layer, label) {
  const row = rowOf(key);
  if (!layer.startsWith("go:")) {
    const go = (e) => {
      if (e.button || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;  // a new tab or window loads it
      e.preventDefault();  // this page keeps its edits
      state.layer = layer;
      location.hash = row;
    };
    const to = here({ layer: layer === "project" ? "" : layer }, `/config#${row}`);
    return html`<a href=${to} @click=${go}>${label}</a>`;
  }
  const leave = (e) => {
    if (unsaved()) {
      e.preventDefault();
      notify(unsaved());
    }
  };
  return html`<a href=${here({ project: layer.slice(3) }, `/config#${row}`)} @click=${leave}>${label}</a>`;
}

// Where this machine sets the key apart from Global: this machine, this project or another one, each a link.
function overrides(n) {
  if (!n.overridden?.length) return nothing;
  const links = n.overridden.map((where, i) => {
    const p = clones()?.find((o) => o.name === where);
    const layer = where === "this machine" ? "machine" : !p ? "" : p.id === current ? "project" : `go:${p.id}`;
    return html`${i ? ", " : ""}${layer ? rowLink(n.key, layer, where) : where}`;
  });
  return html`<br>Set apart by ${links}, so it does not apply there.`;
}

function notice(n) {
  const aria = { "aria-label": `Dismiss the change of ${n.key}` };
  return html`<li id=${`reads-${n.id}`}><p-text>${rowLink(n.key, state.loaded?.global_location ? "global"
    : "project", n.key)}: ${value(n.old)} → ${value(n.new)} (found ${when(n.at)})
    ${overrides(n)}</p-text><p-button type="button" compact="true" variant="secondary" icon="close" .aria=${aria}
    @click=${() => dismiss(n.id)}>Dismiss</p-button></li>`;
}

function status(reads) {
  if (state.reading) return html`<p-text id="reads-status">Reading every outside source…</p-text>`;
  const failures = (reads?.failures ?? []).map((f) => html`<p-text class="reads-failure" color="error">Could not read:
    ${f.source} — ${f.error}</p-text>`);
  if (!reads?.read_at) {
    return html`${failures}<p-text id="reads-status">${failures.length ? "No read is on record; Read again records one."
      : "Outside data has not been read yet."}</p-text>`;
  }
  if (!failures.length) return html`<p-text id="reads-status">Last read ${when(reads.read_at)}, all sources.</p-text>`;
  return html`${failures}<p-text id="reads-status">Last read ${when(reads.read_at)}; last full read
    ${when(reads.succeeded_at)}.</p-text>`;
}

export function readsView() {
  const reads = state.reads;
  const notices = reads?.notices ?? [];
  return html`<section class="panel" id="reads" aria-labelledby="reads-title">
    <p-heading size="lg"><h2 id="reads-title" tabindex="-1">Outside data</h2></p-heading>
    <p-text>The shared settings, the models this machine's Copilot offers, Impeccable's releases and this machine's
      settings are read when this page opens, when OwlBear starts and every hour.</p-text>
    <div class="row">${button("Read again", readAgain, { id: "read-again", icon: "refresh", busy: state.reading,
      disabled: state.reading })}</div>
    <div aria-live="polite">${status(reads)}
      ${state.readsError ? html`<p-text id="reads-error" color="error">${state.readsError}</p-text>` : nothing}
      ${reads?.unshared ? html`<p-text id="reads-unshared" size="xs">No shared settings location is set up, so Global
        changes made elsewhere are not read.</p-text>` : nothing}</div>
    ${notices.length ? html`<p-heading size="md"><h3 id="reads-changed-title">Global settings changed elsewhere
      </h3></p-heading>
      <ul id="reads-changed" tabindex="-1" aria-labelledby="reads-changed-title">${notices.map(notice)}</ul>`
      : nothing}
  </section>`;
}
