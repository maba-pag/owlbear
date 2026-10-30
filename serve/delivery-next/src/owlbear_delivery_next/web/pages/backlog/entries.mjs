import { html, nothing } from "/assets/lit-html/3.3.3/lit-html.js";
import { call } from "/assets/ui.mjs";
import { KINDS, SOURCES, TAGS, WRITE, state, show, notify } from "./state.mjs";
import { button, select, field, tick, labelled } from "./widgets.mjs";
import { refresh } from "./view.mjs";

// The clones of the entry's repository on this machine: where its Changes start and its writes go.
export function clonesOf(e) {
  return state.loaded.clones.filter((c) => c.repository === e.repository);
}

function concerns(e) {
  if (e.projects === null) return `not triaged yet${e.origin ? ` (found in ${e.origin})` : ""}`;
  return `${e.projects.length ? e.projects.join(", ") : "Global"}${e.origin ? ` · found in ${e.origin}` : ""}`;
}

// The Change an entry went into: its clone's id and slug; an older bare slug only when exactly one clone of the
// project it was found in has it.
function changeLink(e) {
  if (!e.change) return nothing;
  const [id, slug] = e.change.includes("/") ? e.change.split("/") : [null, e.change];
  const owners = clonesOf(e).filter((c) => (id === null ? c.name === e.origin && c.changes.includes(slug)
    : c.id === id));
  if (owners.length !== 1) return html` · in Change ${slug} (not found on this machine)`;
  const c = owners[0], key = c.id ? `${c.id}/${slug}` : slug;
  const named = state.loaded.clones.length > 1 ? `${c.label}: ${slug}` : slug;
  return html` · in Change <a href=${`/?change=${encodeURIComponent(key)}`}>${named}</a>`;
}

function age(iso) {
  const minutes = Math.max(1, Math.round((Date.now() - Date.parse(iso)) / 60000));
  if (minutes < 60) return `${minutes} min ago`;
  if (minutes < 60 * 48) return `${Math.round(minutes / 60)} h ago`;
  return `${Math.round(minutes / 1440)} d ago`;
}

function reference(ref) {
  try {
    if (["http:", "https:"].includes(new URL(ref).protocol)) return html`<a href=${ref} rel="noopener">${ref}</a>`;
  } catch {
    // not a URL: a Change, step, session or path
  }
  return ref;
}

async function patch(e, fields, said = `Saved "${e.title}".`, of = e.via) {
  try {
    const body = { method: "PATCH", body: fields, timeout: WRITE, of };
    const r = await call(`/backlog/${encodeURIComponent(e.id)}`, body);
    if ("notes" in fields) state.notes.delete(e.key);
    state.error = "";
    state.status = `${said}${r.notice ? ` ${r.notice}` : ""}`;
    await refresh();
  } catch (error) {
    notify(error.message);
  }
}

function linkPart(e, byId) {
  const others = state.loaded.entries.filter((o) => o.repository === e.repository && o.id !== e.id
    && !e.links.includes(o.id));
  // the pick as of the click, not as of the last render: choosing in the list does not render again
  const target = () => (others.some((o) => o.id === state.linkTo.get(e.key)) ? state.linkTo.get(e.key)
    : others[0]?.id);
  return html`<div class="more">
    ${e.links.length ? html`<p-text size="xs" weight="semibold">Linked entries</p-text><ul class="plain">
      ${e.links.map((id) => html`<li>${byId.get(`${e.repository}#${id}`)?.title ?? id} ${button("Unlink",
        () => patch(e, { links: e.links.filter((x) => x !== id) }), { variant: "secondary" })}</li>`)}</ul>`
      : nothing}
    ${others.length ? html`<div class="row">${select("Link to another entry", others.map((o) => [o.id, o.title]),
      target(), (v) => state.linkTo.set(e.key, v))}${button("Link", () => patch(e, { links: [...e.links, target()] }),
      { variant: "secondary" })}</div>` : nothing}
  </div>`;
}

// In the inbox Drop is a text button beside the kind, named with its entry for a screen reader's list of buttons.
function dropButton(e, pure = false) {
  const drop = () => patch(e, { status: "dropped" }, `Dropped "${e.title}"; Reopen brings it back.`);
  return pure ? html`<p-button-pure type="button" icon="close" .aria=${{ "aria-label": `Drop ${e.title}` }}
    @click=${drop}>Drop</p-button-pure>` : button("Drop", drop, { variant: "secondary", icon: "close" });
}

function statusPart(e, drop = true) {
  if (e.status === "inbox" || e.status === "open") {
    const done = button("Mark done", () => patch(e, { status: "done" }), { variant: "secondary", icon: "check" });
    return html`<div class="row">${done}${drop ? dropButton(e) : nothing}</div>`;
  }
  const reopen = button("Reopen", () => patch(e, { status: e.kind === "untriaged" ? "inbox" : "open" }),
    { variant: "secondary", icon: "refresh" });
  if (e.status !== "in-change") return html`<div class="row">${reopen}</div>`;
  const clones = clonesOf(e), several = clones.length > 1;
  const options = [["-", "not named yet"], ...clones.flatMap((c) => c.changes.map((slug) => [
    c.id ? `${c.id}/${slug}` : slug, several ? `${c.label}: ${slug}` : slug]))];
  const named = (v) => {
    if (v === "-" || v === e.change) return;
    const owner = clones.find((c) => (c.id ? v.startsWith(`${c.id}/`) : true));
    patch(e, { change: v }, undefined, owner?.id ?? e.via);  // the clone holding the Change checks and names it
  };
  return html`<div class="row">${select("The Change it went into", options, e.change || "-", named)}${reopen}</div>`;
}

function kindPicker(e, inline = false) {
  const options = KINDS.map((k) => [k, inline && k === "untriaged" ? "Choose a kind" : k]);
  const chosen = (v) => { if (v !== e.kind) patch(e, { kind: v }); };
  return select("Kind", options, e.kind, chosen, { compact: inline, hideLabel: inline });
}

// What the entry concerns: Global, or the projects ticked (TD-241); the last one ticked stays until Global is.
function concernsPicker(e) {
  const mine = e.projects ?? [], global = e.projects !== null && !mine.length;
  const folders = [...new Set([...clonesOf(e).map((c) => c.name).filter(Boolean), ...mine])].sort();
  const flip = (f) => (on) => patch(e, { projects: on ? [...mine, f] : mine.filter((x) => x !== f) });
  return html`<fieldset class="concerns"><legend>Concerns</legend>
    ${labelled("Global: every project", global, (on) => { if (on) patch(e, { projects: [] }); }, global)}
    ${folders.map((f) => labelled(f, mine.includes(f), flip(f), mine.length === 1 && mine[0] === f))}
  </fieldset>`;
}

function details(e, byId) {
  const inbox = e.status === "inbox", notes = state.notes.get(e.key) ?? e.notes;
  const toggled = (ev) => (ev.target.open ? state.opened.add(e.key) : state.opened.delete(e.key));
  return html`<details .open=${state.opened.has(e.key)} @toggle=${toggled}>
    <summary>Details, notes and links</summary>
    <div class="more">
      ${e.text ? html`<p-text class="said">${e.text}</p-text>` : nothing}
      ${e.evidence.length ? html`<p-text size="xs" weight="semibold">Evidence</p-text>
        <ul class="plain">${e.evidence.map((ref) => html`<li>${reference(ref)}</li>`)}</ul>` : nothing}
      ${inbox ? nothing : html`<div class="row">${kindPicker(e)}</div>`}
      ${concernsPicker(e)}
      ${field("Your notes: context for whoever shapes the Change", notes, (v) => state.notes.set(e.key, v),
        { multiline: true })}
      <div class="row">${button("Save notes", () => patch(e, { notes: (state.notes.get(e.key) ?? e.notes).trim() }),
        { variant: "secondary" })}
      </div>
      ${linkPart(e, byId)}
      ${statusPart(e, !inbox)}
    </div>
  </details>`;
}

// An inbox entry is one compact row: its kind to choose and Drop beside its title, the select naming the kind.
export function card(e, byId) {
  const choosable = (e.status === "inbox" || e.status === "open") && !e.opening;
  const triage = e.status === "inbox" && !e.opening;
  const seen = e.count > 1 ? `seen ${e.count} times, last ${age(e.last_seen)}` : `seen ${age(e.last_seen)}`;
  const choose = (on) => {
    if (on) state.selected.add(e.key);
    else state.selected.delete(e.key);
    show();
  };
  return html`<li class=${choosable ? "entry" : "entry unselectable"}>
    ${choosable ? tick(`Select ${e.title}`, state.selected.has(e.key), choose) : nothing}
    <div class="body">
      <div class="head"><div class="title"><p-text weight="semibold">${e.title}</p-text>
        ${triage ? nothing : html`<p-tag variant=${TAGS[e.kind]} compact="true">${e.kind}</p-tag>`}
        ${e.status !== "inbox" && e.status !== "open" ? html`<p-tag compact="true">${e.status}</p-tag>` : nothing}
        ${e.opening ? html`<p-tag variant="info" compact="true">chat opening</p-tag>` : nothing}</div>
        ${triage ? html`<div class="row triage">${kindPicker(e, true)}${dropButton(e, true)}</div>` : nothing}</div>
      <p-text size="xs" color="contrast-medium">From ${SOURCES[e.source] ?? e.source} · ${seen}${changeLink(e)}
        · <span class="concerns">${concerns(e)}</span> ·
        ${e.url ? html`<a href=${e.url} rel="noopener">#${e.id}</a>` : `#${e.id}`}</p-text>
      ${details(e, byId)}
    </div>
  </li>`;
}
