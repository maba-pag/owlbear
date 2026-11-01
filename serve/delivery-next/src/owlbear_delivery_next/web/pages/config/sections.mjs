import { html, nothing } from "/assets/lit-html/3.3.3/lit-html.js";
import { live } from "/assets/lit-html/3.3.3/directives/live.js";
import { here, moved, loaded as clones, project as current } from "/assets/ui.mjs";
import { SOURCES, state, drafts, page, show, notify, shown } from "./state.mjs";
import { cell, row, table, button } from "./cells.mjs";
import { pendingLine, save, rename, reviewPrefs, hasEdits, anyEdits, pendingIn } from "./layers.mjs";
import { machineSection } from "./machine.mjs";
import { agentsGroup, runsGroup, checksGroup } from "./panels.mjs";
import { GROUPS, groupOf, rowOf } from "./groups.mjs";
import { readsView } from "./reads.mjs";

// The project this page edits, by its name in the machine host's list; "This project" on a clone's own host.
export function named(id = current) {
  return clones()?.find((p) => p.id === id)?.name ?? "";
}

function scopeSection() {
  const loaded = state.loaded, mine = named();
  const all = clones() ?? [], twin = (p) => all.some((o) => o !== p && o.name === p.name);
  const others = all.filter((p) => p.id !== current)
    .map((p) => [`go:${p.id}`, `Project ${p.name}${twin(p) ? ` (${p.path})` : ""}`]);
  const options = [["project", mine ? `Project ${mine}` : "This project"], ["machine", "This machine (its projects)"],
    ["global", "Global (every project)"], ...others];
  const pick = (v) => {
    if (!v.startsWith("go:")) {
      state.layer = v;
      return show();
    }
    if (unsaved()) {
      show();  // the select shows the layer being edited again
      return notify(unsaved());
    }
    location.assign(here({ project: v.slice(3) }));
  };
  const control = html`<p-select id="scope" label="Layer" ?disabled=${state.saving} .value=${live(state.layer)}
    @change=${(e) => pick(e.target.value)}>${options.map(([v, said]) => html`<p-select-option value=${v}
    ?disabled=${v === "global" && !loaded.global_location}>${said}</p-select-option>`)}</p-select>`;
  return html`<section class="panel" aria-labelledby="scope-title">
    <p-heading size="lg"><h2 id="scope-title" tabindex="-1">Where you edit</h2></p-heading>
    <div class="row">${control}<p-text id="scope-note" size="xs" color="contrast-medium">${loaded.global_location ? ""
      : "No shared settings location is set up (run owlbear-next data PATH), so only this project's and this "
        + "machine's settings can be saved, locally."}</p-text></div>
    <p-text>A blank project value uses this machine's; a blank value on this machine uses the global one. OwlBear's
      code has no defaults: a value no layer sets is unset, and the project's work waits until it is set; the Changes
      page names each project that waits.</p-text>
  </section>`;
}

// Why this page may not be left now (another page or project): edits of either layer or a folder name typed and not
// saved.
export function unsaved() {
  const folder = state.folder !== null && state.folder.trim() !== (state.loaded?.folder ?? "");
  return Object.values(drafts).some((d) => Object.keys(d).length) || folder || state.machineDraft
    ? "Save or discard your edits before you leave this page." : "";
}

// A value in the overview: a list or a record in full, never "[object Object]".
function plain(value) {
  if (value === null || value === undefined) return "unset";
  return typeof value === "object" && !(Array.isArray(value) && value.every((v) => typeof v
    !== "object")) ? JSON.stringify(value) : shown(value);
}

export function at(value, key) {
  return key.split(".").reduce((o, k) => o?.[k], value);
}

// Each setting a project sets apart from the global value, with that global value and where it comes from.
function acrossSection() {
  if (!clones()) return nothing;  // a clone's own host serves one project
  const loaded = state.loaded, all = [{ name: named(), config: loaded }, ...state.others];
  const keys = new Set([...Object.keys(loaded.settings.sources), ...(loaded.settings.missing ?? [])]);
  const rows = [...keys].map((key) => {
    const below = loaded.inherited.project, wide = loaded.inherited.machine, source = wide.sources[key];
    const global = at(wide, key), from = SOURCES[source] ?? source ?? "no layer";  // global or the builder's
    const here = at(below, key), apart = JSON.stringify(here) !== JSON.stringify(global);  // derived values too
    const differ = all.filter((p) => JSON.stringify(at(p.config.settings, key)) !== JSON.stringify(here));
    return { key, global, from, machine: apart ? plain(here) : "same", differ, apart };
  }).filter((r) => state.everything || r.differ.length || r.apart);
  const body = rows.map((r) => row(cell(r.key.replaceAll(".", " · ")), cell(`${plain(r.global)} (${r.from})`),
    cell(r.machine),
    cell(r.differ.map((p) => `${p.name}: ${plain(at(p.config.settings, r.key))}`).join("; ") || "none")));
  const flip = (e) => { state.everything = e.target.checked === true; show(); };
  const showAll = html`<p-checkbox id="across-all" label="Show all settings" .checked=${live(state.everything)}
    @change=${flip}></p-checkbox>`;
  const unread = state.unread.length ? `Not read: ${state.unread.join("; ")}.` : "";
  return html`<section class="panel" aria-labelledby="across-title">
    <p-heading size="lg"><h2 id="across-title" tabindex="-1">Across projects</h2></p-heading>
    ${showAll}
    ${rows.length ? table(state.everything ? "Every setting, with the projects that set it apart"
      : "Settings a project or this machine sets apart from the global value",
      ["Setting", "Global", "This machine", "Projects"],
      "across", body, { id: "across-table" })
      : html`<p-text id="across-none">Every project uses the global settings.</p-text>`}
    ${unread ? html`<p-text id="across-unread" size="xs">${unread}</p-text>` : nothing}
  </section>`;
}

// Rename is the panel's primary once a different name is typed, the one thing it then asks.
function folderSection() {
  const loaded = state.loaded, off = !loaded.folder || state.saving, value = state.folder ?? loaded.folder ?? "";
  const renaming = !off && value.trim() !== "" && value.trim() !== loaded.folder;
  const keep = (e) => { state.folder = e.target.value ?? ""; show(); };
  const label = "Folder in the shared settings repository";
  const input = html`<p-input-text id="folder" label=${label} ?disabled=${off} .value=${live(value)} @input=${keep}
    @change=${keep}></p-input-text>`;
  return html`<section class="panel" aria-labelledby="folder-title">
    <p-heading size="lg"><h2 id="folder-title" tabindex="-1">Project folder</h2></p-heading>
    <div class="row">${input}${button("Rename folder", rename, { id: "rename", icon: "edit",
      variant: renaming ? "primary" : "secondary", disabled: off })}</div>
    <p-text id="folder-note">${loaded.folder ? "Named after the repository unless renamed. Renaming moves the folder "
      + "with its settings, memory and visual decisions, then commits and pushes the move; it is refused while a "
      + "step of this project or its memory curation runs."
      : "No shared settings location is set up, so this project has no folder there."}
    </p-text>
  </section>`;
}

// The unset settings by group (D-01M66B6GS0HKACV9C4R4QKFX7T): each group's count and its first three, each linking to
// the row that sets it, then "and N more" opening the group, whose view shows every unset name red. Or that every
// setting is set, unless this machine's are not read yet (its own, in force, can be unset too).
const FIRST = 3;

function unsetSection() {
  const machine = (state.machine?.resolved?.missing ?? []).map((k) => `machine.${k}`);
  const unset = [...(state.loaded.settings.missing ?? []), ...machine];
  const heading = html`<p-heading size="lg"><h2 id="unset-title" tabindex="-1">Unset settings</h2></p-heading>`;
  const unread = clones() && !state.machine;
  if (!unset.length) {
    return html`<section class="panel" id="unset-none" aria-labelledby="unset-title">${heading}
      <p-text>${!unread ? "Every setting is set." : state.machineUnread ? "Every project setting is set; this "
        + `machine's could not be read (${state.machineUnread}), so whether they are is not known.`
        : "Every project setting is set; this machine's are being read."}</p-text></section>`;
  }
  const link = (key, i) => html`${i ? ", " : ""}<a href=${`#${rowOf(key)}`}>${key}</a>`;
  const more = (id, keys) => keys.length > FIRST
    ? html` <a href=${`#${id}`}>and ${keys.length - FIRST} more</a>` : nothing;
  const item = ([id, label], keys) => html`<li id=${`unset-${id}`}><strong>${label}</strong>, ${
    keys.length} unset: ${keys.slice(0, FIRST).map(link)}${more(id, keys)}</li>`;
  return html`<section class="panel" id="unset" aria-labelledby="unset-title">${heading}
    <p-text color="error">${unset.length} setting${unset.length === 1 ? " is" : "s are"} unset. Code ships no
      defaults: set ${unset.length === 1 ? "it" : "each"} in its group, best in the global layer; until then the
      project's work waits. Each name below opens its setting.</p-text>
    <ul id="unset-groups">${GROUPS.map((g) => [g, unset.filter((key) => groupOf(rowOf(key)) === g[0])])
      .filter(([, keys]) => keys.length).map(([g, keys]) => item(g, keys))}</ul>
    ${unread ? html`<p-text size="xs" id="unset-machine">${state.machineUnread ? "This machine's settings could not "
      + `be read (${state.machineUnread}), so they are not listed.` : "This machine's settings are being read."}
      </p-text>` : nothing}
  </section>`;
}

// The groups, each with its unsaved edits counted; their links change the address, which shows the group (route).
function groupNav() {
  const link = ([id, label]) => {
    const n = id === "overview" ? 0 : pendingIn(id);
    return html`<a href=${`#${id}`} aria-current=${state.group === id ? "page" : nothing}>${label}${n
      ? html` <p-tag compact="true" variant="warning">${n} unsaved</p-tag>` : nothing}</a>`;
  };
  return html`<nav id="groups" aria-label="Settings groups">${GROUPS.map(link)}</nav>`;
}

const GROUP_VIEWS = {
  overview: () => html`${readsView()}${unsetSection()}${acrossSection()}`,
  agents: agentsGroup,
  runs: runsGroup,
  checks: checksGroup,
  project: folderSection,
  "this-machine": machineSection,
};

// One Save for the layered settings, whichever group holds them (D-01M63C92B83D61XFXTRXG8JAVB): shown with a group
// of them, and anywhere while a layer has edits to save. This machine's own settings keep their own Save.
function saveBar() {
  const layered = ["agents", "runs", "checks"].includes(state.group)
    || (state.group === "this-machine" && state.layer === "global");
  if (!layered && !anyEdits()) return nothing;
  const edits = hasEdits();
  return html`<div class="bar" role="region" aria-label="Save settings">
    ${button({ global: "Save global defaults", machine: "Save this machine's preferences" }[state.layer]
      ?? "Save project settings", save,
      { id: "save", icon: "check", variant: edits ? "primary" : "secondary", busy: state.saving })}
    <p-text id="pending" size="sm" aria-live="polite">${pendingLine()}</p-text>
    ${state.layer === "project" && state.loaded.prefs_pending
      ? button("Confirm merge preferences reviewed", reviewPrefs, {
          id: "review-prefs",
          icon: "check",
          variant: edits ? "secondary" : "primary",
          busy: state.saving,
        })
      : nothing}
  </div>`;
}

// The id the address names; one that doesn't decode (#%) is replaced by the overview's.
function addressed() {
  try {
    return decodeURIComponent(location.hash.slice(1));
  } catch {
    history.replaceState(history.state, "", `${location.pathname}${location.search}#overview`);
    return "overview";
  }
}

// Show the group the address names (D-01M63C8QQMANY46N8GMNNKH1V9): a group's own, or an older one naming a section or
// a row (#machine-title, #set-prefs-merge_method), which then gets the focus. A switch from elsewhere than the groups'
// links (the menu, the back button) puts the focus on the group's first heading; *initial* is the page's first view.
export function route(initial = false) {
  if (moved()) return;  // ui.mjs opens the page it moved to
  const id = addressed(), group = id ? groupOf(id) : "overview";
  if (id && id !== group) history.replaceState(history.state, "", `${location.pathname}${location.search}#${group}`);
  const switched = group !== state.group, nav = document.activeElement?.closest?.("#groups");
  state.group = group;
  if (id && id !== group) page.target = `#${CSS.escape(id)}`;
  else if (switched && !initial && !nav) page.target = "#groups ~ section h2";
  show();
}

export function view() {
  const loaded = state.loaded;
  if (loaded && !loaded.global_location && state.layer === "global") state.layer = "project";
  return html`
    <p-inline-notification id="error" state="error" dismiss-button="false" ?hidden=${!state.error}>${state.error}
    </p-inline-notification>
    <p-text id="status" role="status" aria-live="polite">${state.status}</p-text>
    ${loaded ? html`${scopeSection()}${groupNav()}${GROUP_VIEWS[state.group]()}${saveBar()}`
      : state.reads ? readsView() : nothing}`;  // a layer that does not read: Read again and why stay
}
