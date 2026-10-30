import { html, nothing } from "/assets/lit-html/3.3.3/lit-html.js";
import { repeat } from "/assets/lit-html/3.3.3/directives/repeat.js";
import { call, here, loaded, project } from "/assets/ui.mjs";
import { KINDS, DIALOG, GET, WRITE, state, filter, show, notify } from "./state.mjs";
import { button, select, field } from "./widgets.mjs";
import { card } from "./entries.mjs";
import { chooser, createChange } from "./change.mjs";

// An untriaged entry shows under its origin too, so the project it was found in sees it to triage (TD-241).
function shows(e) {
  const f = filter.projects, untriaged = e.projects === null;
  const concerned = f === "all" || (f === "global" ? !untriaged && !e.projects.length
    : f === "untriaged" ? untriaged : (e.projects ?? []).includes(f) || (untriaged && e.origin === f));
  return concerned && (filter.kind === "all" || e.kind === filter.kind);
}

// The selectable entries still ticked; an entry that moved on or is opening a chat drops out.
export function chosen() {
  return state.loaded.entries.filter((e) => state.selected.has(e.key) && !e.opening
    && ["inbox", "open"].includes(e.status));
}

// The filter row: the projects an entry concerns and its class; the state is the page's sections. The page's
// project (?project=) is the first choice; a vanished project falls back to all.
function filters() {
  const { entries, clones } = state.loaded;
  const folders = [...new Set([...clones.map((c) => c.name), ...entries.flatMap((e) => e.projects ?? [])]
    .filter(Boolean))].sort();
  if (!filter.projects) filter.projects = clones.find((c) => c.id && c.id === project)?.name ?? "all";
  if (!["all", "global", "untriaged", ...folders].includes(filter.projects)) filter.projects = "all";
  const options = [["all", "All"], ["global", "Global"], ["untriaged", "Not triaged yet"],
    ...folders.map((f) => [f, f])];
  const shown = (v) => {
    filter.projects = v;
    history.replaceState(null, "", here({ show: v }));  // a reload or link keeps it, All too over ?project=
    show();
  };
  const kinds = select("Class", [["all", "all"], ...KINDS.map((k) => [k, k])], filter.kind,
    (v) => { filter.kind = v; show(); });
  return html`<div id="filters" class="row" role="group" aria-label="Show only">
    ${select("Projects", options, filter.projects, shown)}${kinds}</div>`;
}

function list(id, entries, byId, empty) {
  const items = entries.length ? repeat(entries, (e) => e.key, (e) => card(e, byId))
    : html`<li><p-text size="sm" color="contrast-medium">${empty}</p-text></li>`;
  return html`<ul id=${id} class="entries" aria-labelledby=${id === "later" ? "later-title" : nothing}>${items}</ul>`;
}

function addForm() {
  const add = () => addIdea(), clones = state.loaded.clones;
  if (!clones.some((c) => c.id === state.idea.clone)) state.idea.clone = clones[0]?.id ?? "";
  const where = clones.length > 1 ? select("Found in", clones.map((c) => [c.id, c.label]), state.idea.clone,
    (v) => { state.idea.clone = v; }) : nothing;
  return html`<section class="panel" aria-labelledby="add-title">
    <p-heading size="md"><h2 id="add-title">Add an idea</h2></p-heading>
    <div id="add" class="row">${where}
      ${field("Title", state.idea.title, (v) => { state.idea.title = v; })}
      ${field("What you noticed (optional)", state.idea.text, (v) => { state.idea.text = v; },
        { multiline: true, rows: "1" })}
      ${button("Add idea", add, { icon: "add", busy: state.adding })}
    </div>
  </section>`;
}

function started() {
  if (state.choosing) return chooser();
  const s = state.started;
  if (!s) return html`<p-text id="started" aria-live="polite"></p-text>`;
  return html`<p-text id="started" aria-live="polite">${s.text ?? html`Could not open the chat: ${s.reason}. Run this
    command instead:<pre><code>${s.command}</code></pre>`}</p-text>`;
}

export function view() {
  const loaded = state.loaded;
  const body = [];
  if (loaded) {
    for (const key of [...state.selected]) if (!chosen().some((e) => e.key === key)) state.selected.delete(key);
    const byId = new Map(loaded.entries.map((e) => [e.key, e]));
    const head = filters();
    const lists = { inbox: [], open: [], later: [] };
    for (const e of loaded.entries.filter(shows)) lists[e.status in lists ? e.status : "later"].push(e);
    const repositories = [...new Set(loaded.clones.map((c) => c.repository))];
    const notes = [`The backlog is the issues of ${repositories.join(" and ")}.`,
      loaded.unreadable.length ? `Issues without a readable entry: ${loaded.unreadable.join(", ")}.` : "",
      ...loaded.failed.map((f) => `Not read just now: ${f}.`)];
    const ticked = chosen().length;
    body.push(html`<p-text id="where" color="contrast-medium">${notes.filter(Boolean).join(" ")}</p-text>
      ${head}
      ${addForm()}
      <section aria-labelledby="inbox-title">
        <div><p-heading size="xl"><h2 id="inbox-title">Inbox (${lists.inbox.length})</h2></p-heading>
          <p-text>Choose a kind to move an entry to Open, or drop it.</p-text></div>
        ${list("inbox", lists.inbox, byId, "Nothing new to triage.")}
      </section>
      <section aria-labelledby="open-title">
        <div><p-heading size="xl"><h2 id="open-title">Open (${lists.open.length})</h2></p-heading>
          <p-text>Tick entries to shape a Change from them.</p-text></div>
        ${list("open", lists.open, byId, "No open entries.")}
      </section>
      <details class="later quiet">
        <summary id="later-title">In a Change, done or dropped (${lists.later.length})</summary>
        ${list("later", lists.later, byId, "Nothing here yet.")}
      </details>
      <div id="selection" class="bar" role="region" aria-label="Selected entries" ?hidden=${!ticked && !state.creating}>
        <p-text id="chosen" weight="semibold">${ticked} selected</p-text>
        <div id="actions" class="row">
          ${button(`Create Change from ${ticked}`, createChange, { icon: "add", aria: DIALOG, busy: state.creating })}
          ${button("Clear selection", () => { state.selected.clear(); show(); }, { variant: "secondary" })}
        </div>
      </div>`);
  }
  return html`
    <p-inline-notification id="error" state="error" dismiss-button="false" ?hidden=${!state.error}>${state.error}
    </p-inline-notification>
    ${started()}
    <p-text id="status" role="status" aria-live="polite">${state.status}</p-text>
    ${body}`;
}

// Each repository's backlog once, from the first of its clones that answers; a chat opening in another clone shows on
// its entries too. An entry's key is its repository and number, since numbers repeat across repositories. Every clone
// is read whatever the filter shows: each is a place a Change may start or a Change was made.
async function load() {
  const projects = loaded() ?? [{ id: "", name: "", path: "" }];
  const each = await Promise.allSettled(projects.map((p) => call("/backlog", { timeout: GET, of: p.id })));
  const clones = [], first = new Map(), unreadable = [], failed = [];
  each.forEach((r, i) => {
    const p = projects[i];
    if (r.status === "rejected") return failed.push(`${p.name || "this project"}: ${r.reason.message}`);
    const b = r.value, mark = (e) => ({ ...e, key: `${b.repository}#${e.id}`, via: p.id, repository: b.repository });
    const name = b.project || p.name, twin = projects.some((o) => o !== p && o.name === p.name);
    clones.push({ id: p.id, name, label: twin ? `${name} (${p.path})` : name, repository: b.repository,
      changes: b.changes });
    if (!first.has(b.repository)) {
      first.set(b.repository, b.entries.map(mark));
      unreadable.push(...b.unreadable);
      return undefined;
    }
    const opening = new Map(b.entries.filter((e) => e.opening).map((e) => [e.id, e.opening]));
    for (const e of first.get(b.repository)) e.opening ||= opening.get(e.id);
    return undefined;
  });
  if (!clones.length && failed.length) throw each.find((r) => r.status === "rejected").reason;
  return { entries: [...first.values()].flat(), unreadable, clones, failed };
}

export async function refresh() {
  try {
    state.loaded = await load();
  } catch (e) {
    return notify(e.message);
  }
  show();
}

async function addIdea() {
  const title = state.idea.title.trim(), text = state.idea.text.trim();
  if (!title) return notify("Give the idea a title.");
  state.adding = true;
  show();
  try {
    const of = state.idea.clone;
    const r = await call("/backlog", { method: "POST", body: { title, text }, timeout: WRITE, of });
    state.idea = { title: "", text: "", clone: of };
    state.error = "";
    const what = r.new ? `Added "${r.entry.title}" to the inbox.` : `"${r.entry.title}" was already there; `
      + `seen ${r.entry.count} times now.`;
    state.status = `${what}${r.notice ? ` ${r.notice}` : ""}`;
    state.adding = false;
    await refresh();
  } catch (e) {
    state.adding = false;
    notify(e.message);
  }
}
