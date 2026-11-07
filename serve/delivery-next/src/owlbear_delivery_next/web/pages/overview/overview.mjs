// Under All projects a page shows one summary per scope, each opening that scope's own view
// (D-01M63C6PMT4FX370W6B2VS9HAM). A project that cannot be read says so and why; it is never left out, and the others
// still show as each is read.
import { html, nothing } from "/assets/lit-html/3.3.3/lit-html.js";
import { repeat } from "/assets/lit-html/3.3.3/directives/repeat.js";
import { OWN_TAG, call, displayName, here, isOwn, machineState, ownFirst } from "/assets/ui.mjs";

// *fixed* scopes ({ key, name, href, path, own }) come first, then every registered project, loaded or not, OwlBear's
// own first, read at its own API's *path*; a fixed scope marked *own* is OwlBear's, so its project gets no second row.
// *said* turns what was read into [tags, text]; *unread* says why an answer holds nothing, which then fails the read as
// an error would; *show* renders the page again. While *live()* says the overview shows, *again()* reads the page again
// when a project is added, removed, or loaded or stopped.
export function overview({ fixed = [], path, said, unread = () => "", show, live = () => true, again: reread,
  timeout = 15000 }) {
  const rows = new Map();
  let turn = 0, known = "";
  const projects = () => machineState()?.projects ?? [];
  const states = () => JSON.stringify(projects().map((p) => [p.id, p.state, p.reason, p.name, p.path, p.kind]));

  async function readOne(row, n) {
    try {
      const got = await call(row.path ?? path, { of: row.of ?? "", timeout }), why = unread(got);
      if (n === turn) Object.assign(row, why ? { state: "failed", why } : { state: "read", got, why: "" });
    } catch (error) {
      if (n === turn) Object.assign(row, { state: "failed", why: error.message });
    }
    if (n === turn) show();
  }

  function again(row) {
    row.state = "reading";
    show();
    return readOne(row, turn);
  }

  // Reads every scope again; until its answer comes a scope says it is being read.
  async function refresh() {
    const n = ++turn, all = projects();
    known = states();
    const listed = ownFirst(all).filter((p) => !(isOwn(p) && fixed.some((f) => f.own)));
    const wanted = [...fixed, ...listed.map((p) => project(p, all))];
    const before = new Map(rows);
    rows.clear();
    for (const w of wanted) rows.set(w.key, { ...before.get(w.key), ...w, state: w.down ? "down" : "reading" });
    show();
    await Promise.all([...rows.values()].filter((r) => !r.down).map((r) => readOne(r, n)));
  }

  function view({ id, heading, intro }) {
    const list = [...rows.values()];
    return html`<section id=${id} aria-labelledby=${`${id}-heading`}>
      <p-heading size="lg"><h2 id=${`${id}-heading`}>${heading}</h2></p-heading>
      ${intro ? html`<p-text size="sm">${intro}</p-text>` : nothing}
      ${list.length ? html`<ul class="scopes">${repeat(list, (r) => r.key, (r) => item(r, said, again))}</ul>`
        : html`<p-text class="empty" color="contrast-medium">No project is registered yet.
          <a href=${here({}, "/projects")}>Add one on Projects</a>.</p-text>`}
    </section>`;
  }

  const follow = () => { if (live() && states() !== known) (reread ?? refresh)(); };
  for (const kind of ["owlbear-machine", "owlbear-polled"]) document.addEventListener(kind, follow);
  return { refresh, view };
}

// A registered project as a scope: its own view, or why it cannot be read while it is not loaded.
function project(p, all) {
  const name = displayName(p), twin = all.some((o) => o !== p && displayName(o) === name);
  const said = `${name} is ${p.state}${p.reason ? `: ${p.reason}` : ""}`;
  const down = p.state === "loaded" ? "" : /[.!?]$/.test(said) ? said : `${said}.`;
  return { key: p.id, of: p.id, name: `${name}${twin ? ` (${p.path})` : ""}`, href: here({ project: p.id }), down,
    tag: p.state, own: isOwn(p) };
}

function item(r, said, again) {
  const [tags, text] = r.state === "read" ? said(r.got) : [nothing, nothing];
  const name = r.down ? r.name : html`<p-link-pure icon="arrow-right" align-label="start" size="inherit">
    <a href=${r.href}>${r.name}</a></p-link-pure>`;
  return html`<li class="scope" data-key=${r.key} aria-busy=${r.state === "reading" ? "true" : "false"}>
    <div class="title"><p-heading size="md"><h3>${name}</h3></p-heading>
      ${r.own ? html`<p-tag compact="true">${OWN_TAG}</p-tag>` : nothing}
      ${r.down ? html`<p-tag compact="true" variant="error">${r.tag}</p-tag>` : nothing}
      ${r.state === "failed" ? html`<p-tag compact="true" variant="error">cannot be read</p-tag>` : tags}</div>
    ${r.state === "reading" ? html`<p-text size="sm" color="contrast-medium">Reading…</p-text>` : nothing}
    ${r.state === "read" ? text : nothing}
    ${r.down ? html`<p-text size="sm" class="why">${r.down} <a href=${here({}, "/projects")}>Open Projects</a>
      </p-text>` : nothing}
    ${r.state === "failed" ? html`<p-text size="sm" class="why">Could not read it: ${r.why}</p-text>
      <div><p-button type="button" compact="true" variant="secondary" .aria=${{ "aria-label": `Read ${r.name} again` }}
        @click=${() => again(r)}>Read again</p-button></div>` : nothing}
  </li>`;
}
