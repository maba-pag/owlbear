import { html, nothing } from "/assets/lit-html/3.3.3/lit-html.js";
import { live } from "/assets/lit-html/3.3.3/directives/live.js";
import { here, loaded as clones, project as current } from "/assets/ui.mjs";
import { SOURCES, ROUNDS, LOOPS, state, drafts, show, notify, shown } from "./state.mjs";
import {
  cell, row, table, button, numberCell, designFailures, widths, sessionsAtOnce, prLabels, prMarker, subagentsCell,
  curatorThreshold, watcherSwitch,
  contextCell, ratesCell, editable, inactive,
} from "./cells.mjs";
import { pendingLine, save, rename } from "./layers.mjs";
import { packSection } from "./pack.mjs";
import { machineSection } from "./machine.mjs";

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
    <p-heading size="lg"><h2 id="scope-title">Where you edit</h2></p-heading>
    <div class="row">${control}<p-text id="scope-note" size="xs" color="contrast-medium">${loaded.global_location ? ""
      : "No shared settings location is set up (run owlbear-next data PATH), so only this project's and this "
        + "machine's settings can be saved, locally."}</p-text></div>
    <p-text>A blank project value uses this machine's; a blank value on this machine uses the global one. OwlBear's
      code has no defaults: a value no layer sets is unset, and a step that needs it asks you to fill it in.</p-text>
  </section>`;
}

// Why another project may not open now: edits of either layer or a folder name typed and not saved.
export function unsaved() {
  const folder = state.folder !== null && state.folder.trim() !== (state.loaded?.folder ?? "");
  return Object.values(drafts).some((d) => Object.keys(d).length) || folder || state.machineDraft
    ? "Save or discard your edits before you open another project." : "";
}

// A value in the overview: a list or a record in full, never "[object Object]".
function plain(value) {
  return value !== null && typeof value === "object" && !(Array.isArray(value) && value.every((v) => typeof v
    !== "object")) ? JSON.stringify(value) : shown(value);
}

function at(value, key) {
  return key.split(".").reduce((o, k) => o?.[k], value);
}

// Each setting a project sets apart from the global value, with that global value and where it comes from.
function acrossSection() {
  if (!clones()) return nothing;  // a clone's own host serves one project
  const loaded = state.loaded, all = [{ name: named(), config: loaded }, ...state.others];
  const rows = Object.keys(loaded.settings.sources).map((key) => {
    const below = loaded.inherited.project, wide = loaded.inherited.machine, source = wide.sources[key];
    const global = at(wide, key), from = SOURCES[source] ?? source;  // global, built-in or the builder's
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
    <p-heading size="lg"><h2 id="across-title">Across projects</h2></p-heading>
    ${showAll}
    ${rows.length ? table(state.everything ? "Every setting, with the projects that set it apart"
      : "Settings a project or this machine sets apart from the global value",
      ["Setting", "Global", "This machine", "Projects"],
      "across", body, { id: "across-table" })
      : html`<p-text id="across-none">Every project uses the global settings.</p-text>`}
    ${unread ? html`<p-text id="across-unread" size="xs">${unread}</p-text>` : nothing}
  </section>`;
}

function folderSection() {
  const loaded = state.loaded, off = !loaded.folder || state.saving, value = state.folder ?? loaded.folder ?? "";
  const keep = (e) => { state.folder = e.target.value ?? ""; };
  const label = "Folder in the shared settings repository";
  const input = html`<p-input-text id="folder" label=${label} ?disabled=${off} .value=${live(value)} @input=${keep}
    @change=${keep}></p-input-text>`;
  return html`<section class="panel" aria-labelledby="folder-title">
    <p-heading size="lg"><h2 id="folder-title">Project folder</h2></p-heading>
    <div class="row">${input}${button("Rename folder", rename, { id: "rename", icon: "edit", disabled: off })}</div>
    <p-text id="folder-note">${loaded.folder ? "Named after the repository unless renamed. Renaming moves the folder "
      + "with its settings, memory and visual decisions, then commits and pushes the move; it is refused while a "
      + "step of this project runs." : "No shared settings location is set up, so this project has no folder there."}
    </p-text>
  </section>`;
}

function settingsSections() {
  const loaded = state.loaded, roles = Object.keys(loaded.settings.agents);
  const share = (n, of) => `${n} (${Math.round((100 * n) / of)}%)`;
  const later = [["runtime", "Runtime"], ["visible", "Needs visibility"], ["categories", "Categories"]];
  const general = [["Always visible (global switch)", loaded.settings.visible, "visible"],
    ...Object.entries(loaded.settings.runtimes).map(([n, on]) => [`Runtime ${n} switched on`, on, `runtimes.${n}`])];
  const { baseline, runtimes, categories } = loaded.catalogue;
  const text = (v) => cell(html`<p-text>${v}</p-text>`);
  const unset = loaded.settings.missing ?? [];
  return html`
    ${unset.length ? html`<section class="panel" id="unset" aria-labelledby="unset-title">
      <p-heading size="lg"><h2 id="unset-title">Unset settings</h2></p-heading>
      <p-text color="error">${unset.length} setting${unset.length === 1 ? " is" : "s are"} unset. Code ships no
        defaults: set ${unset.length === 1 ? "it" : "them"} below, best in the global layer; a step that needs one asks
        you until then.</p-text>
      <p-text size="xs">${unset.join(", ")}</p-text></section>` : nothing}
    <section class="panel" aria-labelledby="agents-title">
      <p-heading size="lg"><h2 id="agents-title">Agents</h2></p-heading>
      ${table("Agents: model, effort and context apply to the next session",
        ["Agent", "Model", "Effort", "Context", "AI credits per 1M tokens"], "agents",
        roles.map((role) => row(text(role === "shaper" ? "shaper (a recommendation)" : role), editable(role, "model"),
          editable(role, "effort"), contextCell(role), ratesCell(role))))}
      <p-text id="shaper-note" size="xs" color="contrast-medium">The shaper's model and effort are a recommendation
        (TD-328): Delivery's own turns in the shaping chat use them; what you type there runs on the chat's model
        picker, which the chat reminds you of once.</p-text>
      <p-text id="models-note" size="xs" color="contrast-medium" aria-live="polite">${state.modelsNote}</p-text>
    </section>
    <section class="panel" aria-labelledby="rounds-title">
      <p-heading size="lg"><h2 id="rounds-title">Challenge rounds</h2></p-heading>
      <p-text>A reviewer and the worker go back and forth in rounds. A round with few new findings is the last; after
        the last allowed round with many, Delivery asks you. A loop keeps the values it started with.</p-text>
      ${table("Challenge rounds: they apply to loops that start after a save", ["Loop", ...ROUNDS.map(([, l]) => l)],
        "rounds", LOOPS.map(([owner, said]) => row(text(said),
          ...ROUNDS.map(([field, label]) => numberCell(owner, field, label)))))}
      <p-text size="xs" color="contrast-medium">Findings per round: 1 to 20. "Last round at or below" must be lower
        than "ask you at or above", which may not exceed the findings per round. The final review inherits the
        builder's values.</p-text>
    </section>
    <section class="panel" aria-labelledby="limits-title">
      <p-heading size="lg"><h2 id="limits-title">Session time limits</h2></p-heading>
      <p-text>An agent session ends after this many minutes in total; its step then counts as a failed attempt and
        runs again. The shaper's chat has no limit.</p-text>
      ${table("Session time limits: they apply to the next session", ["Agent", "Minutes per session"], "limits",
        roles.filter((role) => !["shaper", "watcher"].includes(role)).map((role) => row(text(role),
          numberCell(role, "minutes", "Minutes per session"))))}
      <p-text size="xs" color="contrast-medium">1 to 480 minutes.</p-text>
    </section>
    <section class="panel" aria-labelledby="at-once-title">
      <p-heading size="lg"><h2 id="at-once-title">Sessions at once</h2></p-heading>
      <p-text>A step waits for a free slot before it starts. A visual check runs its judges in waves of the slots it
        gets; a design pack update takes one slot per session. This machine's total holds across its projects.</p-text>
      ${table("Sessions at once: they apply to the next step that starts", ["Setting", "Value"], "at-once",
        [row(text("Agent sessions at once in one project"), sessionsAtOnce())])}
      <p-text size="xs" color="contrast-medium">At least 1. Steps running now keep their sessions.</p-text>
    </section>
    <section class="panel" aria-labelledby="curation-title">
      <p-heading size="lg"><h2 id="curation-title">Memory curation</h2></p-heading>
      <p-text>The memory curator states its confidence in everything it would do to an entry. At or above this
        threshold it acts alone, Make global included; below it, it asks you in an interactive session and leaves the
        entry as it is in an automatic run.</p-text>
      ${table("Memory curation: it applies to the next curation", ["Setting", "Value"], "curation",
        [row(text("Curator's confidence threshold (%)"), curatorThreshold())])}
      <p-text size="xs" color="contrast-medium">50 to 100; one value for every project and machine.</p-text>
    </section>
    <section class="panel" aria-labelledby="watcher-title">
      <p-heading size="lg"><h2 id="watcher-title">Watcher</h2></p-heading>
      <p-text>The watcher judges what an agent step does outside its work folder and what it sends out: it stops the
        step when an action is dangerous or inappropriate for the task, and reports the rest. Its model, effort and
        context are the watcher row under Agents. It is not built yet; the switch applies once it is.</p-text>
      ${table("Watcher: it applies to the next step", ["Setting", "Value"], "watcher",
        [row(text("The watcher"), watcherSwitch())])}
    </section>
    <section class="panel" aria-labelledby="subagents-title">
      <p-heading size="lg"><h2 id="subagents-title">Subagents</h2></p-heading>
      <p-text>An agent may start the runtime's built-in subagents, such as explore or code-review, for side
        questions. They work under the step's own permissions, and Delivery records each one; Maintenance shows their
        use per agent.</p-text>
      ${table("Subagents: they apply to the next session", ["Agent", "Built-in subagents"], "subagents",
        roles.filter((role) => !["shaper", "watcher"].includes(role)).map((role) =>
          row(text(role), subagentsCell(role))))}
    </section>
    <section class="panel" aria-labelledby="general-title">
      <p-heading size="lg"><h2 id="general-title">Visual checks</h2></p-heading>
      ${table("Visual check settings: they apply to the next visual check", ["Setting", "Value"], "general",
        [row(text("Screenshot widths"), widths()), row(text("Design failures"), designFailures())])}
      <p-heading size="md"><h3 id="agreement-title">Agreement with your visual decisions</h3></p-heading>
      <p-text id="design-pack" size="xs">${loaded.design_pack}</p-text>
      <p-text id="agreement-note" size="xs" color="contrast-medium">${loaded.agreement.length
        ? "From the decided rounds kept in the shared repository; below 20 rounds the numbers only inform."
        : "No decided visual rounds yet, or no shared repository is set up."}</p-text>
      ${table("How often each judge's verdict matched your Pass or Fail, per model",
        ["Judge", "Model", "Decided", "Agreed", "Disagreed", "Unsure"], "agreement",
        loaded.agreement.map((a) => row(...[a.judge, a.model, String(a.decided), share(a.agreed, a.decided),
          share(a.disagreed, a.decided), share(a.unsure, a.decided)].map(text))),
        { id: "agreement-table", hidden: !loaded.agreement.length })}
    </section>
    <section class="panel" aria-labelledby="pr-title">
      <p-heading size="lg"><h2 id="pr-title">Pull requests</h2></p-heading>
      <p-text>What OwlBear adds to each pull request it opens.</p-text>
      ${table("Pull request settings: they apply to the next pull request", ["Setting", "Value"], "pr",
        [row(text("Labels"), prLabels()), row(text("Marker line"), prMarker())])}
    </section>
    ${packSection()}
    <details class="panel">
      <summary>Not applied yet: runtimes, visibility and tool categories</summary>
      ${table("Per agent; not applied yet", ["Agent", "Runtime", "Needs visibility", "Categories"], "agents-later",
        Object.entries(loaded.settings.agents).map(([role, eff]) => row(text(role),
          ...later.map(([f, label]) => inactive(`${label} for ${role}`, eff[f], `agents.${role}.${f}`)))))}
      ${table("Switches; not applied yet", ["Setting", "Value"], "general-later",
        general.map(([label, value, key]) => row(text(label), inactive(label, value, key))))}
      <p-text id="baseline" size="xs" color="contrast-medium">Every runtime has the baseline: ${baseline}.</p-text>
      ${table("What each runtime adds; not used for routing yet", ["Runtime", "Adds over the baseline", "MCP servers",
        "Live view", "Writes outside the work folder"], "runtimes", runtimes.map((r) => row(
        ...[r.runtime, r.adds, r.mcp, r.live_view, r.outside_writes].map(text))))}
      ${table("Tool categories an agent can ask for; not applied yet", ["Category", "Runtime", "Tools"], "categories",
        Object.entries(categories).map(([name, c]) => row(...[name, c.runtime, c.tools.join(", ")].map(text))))}
    </details>
    <div class="bar" role="region" aria-label="Save settings">
      ${button({ global: "Save global defaults", machine: "Save this machine's preferences" }[state.layer]
        ?? "Save project settings", save,
        { id: "save", icon: "check", busy: state.saving })}
      <p-text id="pending" size="sm" aria-live="polite">${pendingLine()}</p-text>
    </div>`;
}

export function view() {
  const loaded = state.loaded;
  if (loaded && !loaded.global_location && state.layer === "global") state.layer = "project";
  return html`
    <p-inline-notification id="error" state="error" dismiss-button="false" ?hidden=${!state.error}>${state.error}
    </p-inline-notification>
    <p-text id="status" role="status" aria-live="polite">${state.status}</p-text>
    ${loaded ? html`${scopeSection()}${folderSection()}${settingsSections()}${acrossSection()}${machineSection()}`
      : packSection()}`;
}
