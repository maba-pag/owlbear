import { html, nothing } from "/assets/lit-html/3.3.3/lit-html.js";
import { live } from "/assets/lit-html/3.3.3/directives/live.js";
import { here, loaded as clones, project as current } from "/assets/ui.mjs";
import { SOURCES, ROUNDS, LOOPS, state, drafts, show, notify, shown } from "./state.mjs";
import {
  cell, row, table, button, numberCell, designFailures, widths, sessionsAtOnce, prLabels, prMarker, subagentsCell,
  curatorThreshold, spotterCell, prefRows, USER_KEYS, userConfig, userConfigLabel,
  contextCell, ratesCell, editable,
} from "./cells.mjs";
import { pendingLine, save, rename, reviewPrefs } from "./layers.mjs";
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
  if (value === null || value === undefined) return "unset";
  return typeof value === "object" && !(Array.isArray(value) && value.every((v) => typeof v
    !== "object")) ? JSON.stringify(value) : shown(value);
}

function at(value, key) {
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
      + "step of this project or its memory curation runs."
      : "No shared settings location is set up, so this project has no folder there."}
    </p-text>
  </section>`;
}

function settingsSections() {
  const loaded = state.loaded, roles = Object.keys(loaded.settings.agents);
  const share = (n, of) => `${n} (${Math.round((100 * n) / of)}%)`;
  const text = (v) => cell(html`<p-text>${v}</p-text>`);
  const machine = (state.machine?.resolved?.missing ?? []).map((k) => `machine.${k}`);  // this machine's in force
  const unset = [...(loaded.settings.missing ?? []), ...machine];
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
        roles.filter((role) => !["shaper", "spotter"].includes(role)).map((role) => row(text(role),
          numberCell(role, "minutes", "Minutes per session"))))}
      <p-text size="xs" color="contrast-medium">1 to 480 minutes.</p-text>
    </section>
    <section class="panel" aria-labelledby="at-once-title">
      <p-heading size="lg"><h2 id="at-once-title">Sessions at once</h2></p-heading>
      <p-text>A step waits for a free slot before it starts. A visual check runs its judges in waves of the slots it
        gets; an Impeccable update takes one slot per session. This machine's total holds across its projects.</p-text>
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
    <section class="panel" aria-labelledby="spotter-title">
      <p-heading size="lg"><h2 id="spotter-title">Spotter</h2></p-heading>
      <p-text>The Spotter looks at an agent's work beside it: at hand-offs, plans, state changes and a sample of
        actions. It files each finding under one of four categories, each set to an action its category allows; so
        far every look only records its finding with that action, and Retro grades those records. Steering,
        refusing and stopping come with live delivery, discretionary ones only after a steered-versus-silent test.
        Its model, effort and context are the spotter row under Agents; the enrolled chats are a machine setting.
        Each look stops at its own credit limit, also when replayed: once the spend the runtime reports reaches it, the
        look is stopped and its record says so; a call already under way still finishes, so a look may pass its limit
        a little. There is no daily budget. Off stops its looks and the recording of new outside writes for each
        Change's page; the reports already recorded stay, and steps no longer need its other settings.</p-text>
      ${table("Spotter: it applies to the next look", ["Setting", "Value"], "spotter", [
        row(text("On or off"), spotterCell("switch", "On or off")),
        row(text("Hand-off fitness: the result should not be accepted as it stands"),
          spotterCell("hand_off_fitness", "Hand-off fitness")),
        row(text("Course and constraints: recoverable work heading materially wrong"),
          spotterCell("course_and_constraints", "Course and constraints")),
        row(text("Outside-state changes: a consequential change beyond the task's files"),
          spotterCell("outside_state_changes", "Outside-state changes")),
        row(text("Irreversible harm, in the Spotter's own judgement; it takes precedence"),
          spotterCell("irreversible_harm", "Irreversible harm")),
        row(text("Steered share (%)"), spotterCell("steer_share", "Steered share")),
        row(text("Steering notes at most, per step or chat turn"), spotterCell("intervention_cap", "Notes at most")),
        row(text("Verbose"), spotterCell("verbose", "Verbose")),
        row(text("Verbose until (YYYY-MM-DD; empty: no end)"), spotterCell("verbose_until", "Verbose until")),
        row(text("Looks (hand-off, plan, state-change, sample)"), spotterCell("looks", "Looks")),
        row(text("Sampled actions (%)"), spotterCell("sample_rate", "Sampled actions")),
        row(text("Credit limit per look (credits)"), spotterCell("look_credit_limit", "Credit limit per look")),
      ])}
    </section>
    <section class="panel" aria-labelledby="subagents-title">
      <p-heading size="lg"><h2 id="subagents-title">Subagents</h2></p-heading>
      <p-text>An agent may start the runtime's built-in subagents, such as explore or code-review, for side
        questions. They work under the step's own permissions, and Delivery records each one; Maintenance shows their
        use per agent.</p-text>
      ${table("Subagents: they apply to the next session", ["Agent", "Built-in subagents"], "subagents",
        roles.filter((role) => !["shaper", "spotter"].includes(role)).map((role) =>
          row(text(role), subagentsCell(role))))}
    </section>
    <section class="panel" aria-labelledby="user-config-title">
      <p-heading size="lg"><h2 id="user-config-title">Your instructions and skills</h2></p-heading>
      <p-text>A Delivery step reads its repository's instructions and Delivery's own skills. Switched on, it also
        reads your own instruction files in your Copilot folder (instructions/ and copilot-instructions.md, links
        followed), and is offered your own skills there (skills/), never one named as Delivery's. A plugin's files and
        your agents stay off either way. Neither has a default: until both are set, a step asks you to set them
        instead of starting its session.</p-text>
      ${table("Your instructions and skills: they apply to the next session", ["Setting", "Value"], "user-config",
        USER_KEYS.map((key) => row(text(userConfigLabel(key)), userConfig(key))))}
    </section>
    <section class="panel" aria-labelledby="general-title">
      <p-heading size="lg"><h2 id="general-title">Visual checks</h2></p-heading>
      ${table("Visual check settings: they apply to the next visual check", ["Setting", "Value"], "general",
        [row(text("Screenshot widths"), widths()), row(text("Design failures"), designFailures())])}
      <p-heading size="md"><h3 id="agreement-title">Agreement with your visual decisions</h3></p-heading>
      <p-text id="impeccable" size="xs">${loaded.impeccable}</p-text>
      <p-text id="agreement-note" size="xs" color="contrast-medium">${loaded.agreement.length
        ? "From the decided rounds kept in the shared repository; below 20 rounds the numbers only inform."
        : "No decided visual rounds yet, or no shared repository is set up."}</p-text>
      ${table("How often each judge's verdict matched your Pass or Fail, per model",
        ["Judge", "Model", "Decided", "Agreed", "Disagreed", "Unsure"], "agreement",
        loaded.agreement.map((a) => row(...[a.judge, a.model, String(a.decided), share(a.agreed, a.decided),
          share(a.disagreed, a.decided), share(a.unsure, a.decided)].map(text))),
        { id: "agreement-table", hidden: !loaded.agreement.length })}
    </section>
    <section class="panel" aria-labelledby="merge-title">
      <p-heading size="lg"><h2 id="merge-title">Merge and cleanup</h2></p-heading>
      <p-text>How OwlBear merges a pull request, cleans up its branch and waits for CI. Each setting is set in this
        project, on this machine or globally; the project's value wins, then this machine's, then the global one. None
        has a built-in default: a step that needs one asks you until it is set.</p-text>
      ${table("Merge and cleanup: they apply to the next merge", ["Setting", "Value"], "prefs", prefRows())}
      <p-text size="xs" color="contrast-medium">Seconds are whole numbers; blank inherits.</p-text>
    </section>
    <section class="panel" aria-labelledby="pr-title">
      <p-heading size="lg"><h2 id="pr-title">Pull requests</h2></p-heading>
      <p-text>What OwlBear adds to each pull request it opens.</p-text>
      ${table("Pull request settings: they apply to the next pull request", ["Setting", "Value"], "pr",
        [row(text("Labels"), prLabels()), row(text("Marker line"), prMarker())])}
    </section>
    <div class="bar" role="region" aria-label="Save settings">
      ${button({ global: "Save global defaults", machine: "Save this machine's preferences" }[state.layer]
        ?? "Save project settings", save,
        { id: "save", icon: "check", busy: state.saving })}
      <p-text id="pending" size="sm" aria-live="polite">${pendingLine()}</p-text>
      ${state.layer === "project" && state.loaded.prefs_pending
        ? button("Confirm merge preferences reviewed", reviewPrefs, {
            id: "review-prefs",
            icon: "check",
            busy: state.saving,
          })
        : nothing}
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
      : nothing}`;
}
