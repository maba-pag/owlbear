import { html, nothing } from "/assets/lit-html/3.3.3/lit-html.js";
import { live } from "/assets/lit-html/3.3.3/directives/live.js";
import { repeat } from "/assets/lit-html/3.3.3/directives/repeat.js";
import { EFFORTS, INHERIT, SOURCES, state, shown } from "./state.mjs";
import { own, inherited, edit, layerValue, preview, drafted, followsBuilder } from "./layers.mjs";
import { levels, arrows } from "./cost.mjs";
import { at } from "./sections.mjs";
import { PLAIN_NAMES, PREF_NAMES, USER_NAMES } from "./names.mjs";

// Code ships no defaults (2026-10-23): a value no layer sets is unset; its row's name says so in red (GW8RT6). While
// the edited layer has an unsaved edit of it, the line says what the save would give (#809).
function source(key, inUse, needed = true, format = (v) => v) {
  const next = preview(key), from = SOURCES[next ? next.from : state.loaded.settings.sources[key]];
  const said = (text) => html`<p-text size="xs" color="contrast-medium">${text}</p-text>`;
  const line = next ? said(from ? `in use: ${shown(format(next.value))}, from ${from}` : "in use: unset")
    : !from && !needed ? said("unset; nothing applies it yet")
      : !from ? nothing : said(inUse === undefined ? `from ${from}` : `in use: ${shown(format(inUse))}, from ${from}`);
  return html`${line}${unsetWarning(key)}`;
}

// D-01M61SEXPFT9MXZGQHYVYFQ77C: what an unset Global value leaves to the layers below, while Global's own is unset.
function unsetWarning(key) {
  if (state.layer !== "global" || layerValue("global", key) !== null || !required(key)) return nothing;
  const text = key === "curator_threshold" || key.startsWith("memory.")
    ? "Unset: no machine or project can set it, so it stays unset"
    : key.startsWith("final_review.") ? "Unset: it then takes the builder's value"
      : /^agents\.repairer\.(model|effort|context)$/.test(key) && followsBuilder()
        ? "Unset: it then takes the builder's model, effort and context, while all three stay unset"
      : "Unset: every machine or project must then set its own";
  return html`<p-text size="sm" color="warning">${text}</p-text>`;
}

// Whether a step needs *key* set, as the server's unset list says (improvement.resolve): every setting, except the
// Spotter's "verbose until" and its sample rate while the looks in use take no sample.
function required(key) {
  if (key === "spotter.verbose_until") return false;
  if (key !== "spotter.sample_rate") return true;
  const next = preview("spotter.looks");
  return ((next ? next.value : state.loaded.settings.spotter?.looks) ?? []).includes("sample");
}

// What a blank field inherits, in words; "unset" where no layer below sets it.
function said(value) {
  return value === null || value === undefined ? "unset" : value;
}

// The option or placeholder that clears the edited layer's value: on Global it leaves the value unset (SEXPFT).
function clear(below) {
  return state.layer === "global" ? "Unset" : `inherit (${said(below)})`;
}

function onOff(value) {
  return value === null || value === undefined ? value : value ? "on" : "off";
}

export function cell(...parts) {
  return html`<p-table-cell multiline="true">${parts}</p-table-cell>`;
}

// A cell an unset-list link can name by its *id* and focus its control.
export function cellWith(id, ...parts) {
  return html`<p-table-cell id=${id} tabindex="-1" multiline="true">${parts}</p-table-cell>`;
}

export function row(...cells) {
  return html`<p-table-row>${cells}</p-table-row>`;
}

// GW8RT6: a setting's row, which the unset list links to by its *id*; its name is red while a key it sets is unset.
export function setting(id, name, keys, ...cells) {
  const missing = state.loaded.settings.missing ?? [], unset = keys.some((k) => missing.includes(k));
  // The Show filter: set on the edited layer as saved, or with an unsaved edit.
  const matches = {
    all: () => true,
    unset: () => unset,
    set: () => keys.some((k) => at(state.loaded[state.layer], k) != null),
    unsaved: () => {
      const edited = keys.some((k) => drafted(k) || preview(k)), pin = `${state.layer}:${id}`;  // or follows an edit
      if (edited) state.kept.add(pin);  // undoing an edit by typing must not take the row from under the cursor
      return state.kept.has(pin);
    },
  }[state.filter]();
  // Always a colour: removing the attribute sets p-text's to null, which PDS rejects once a set name stops being red.
  return html`<p-table-row id=${id} tabindex="-1" data-setting ?hidden=${!matches}>${cell(html`<p-text
    color=${unset ? "error" : "primary"}>${name}</p-text>`)}${cells}</p-table-row>`;
}

export function table(caption, heads, body, rows, { id, hidden = false } = {}) {
  return html`<p-table id=${id ?? nothing} caption=${caption} ?hidden=${hidden}><p-table-head><p-table-head-row>
    ${heads.map((h) => html`<p-table-head-cell>${h}</p-table-head-cell>`)}</p-table-head-row></p-table-head>
    <p-table-body id=${body}>${rows}</p-table-body></p-table>`;
}

// A table cell's choice: its column says what it is, so the label is for assistive technology only.
// *wrong* says why the choice cannot run, for a choice that is checked (an effort); undefined for the others.
function choose(label, options, value, chosen, { key, disabled = false, filter = false, wrong } = {}) {
  const changed = (e) => {
    chosen(e.target.value);
    handOff(e, label);
  };
  const items = options.map(([v, said]) => html`<p-select-option value=${v}>${said}</p-select-option>`);
  const checked = wrong === undefined ? nothing : wrong ? "error" : "none";
  // PDS options can receive a queued slotchange after removal; replace their select as one subtree.
  return repeat([options], (list) => JSON.stringify(list.map(([v]) => v)),
    () => html`<p-select label=${label} hide-label="true" data-key=${key ?? nothing}
      filter=${filter ? "true" : nothing} state=${checked} message=${wrong || nothing} ?disabled=${disabled}
      .value=${live(value)} @change=${changed}>${items}</p-select>`);
}

// When a choice replaced its own control, the focus moves to the control that took its place under the same *label*.
function handOff(e, label) {
  if (e.currentTarget.isConnected) return;
  const next = document.querySelector(`[label="${CSS.escape(label)}"]`);
  const focused = document.activeElement;
  Promise.resolve(next?.componentOnReady?.()).then(() => {
    if (next?.isConnected && document.activeElement === focused) next.focus({ preventScroll: true });
  });
}

function typed(label, value, onInput, { key, placeholder, inputmode, disabled = false } = {}) {
  const keep = (e) => onInput(e.target.value ?? "");
  return html`<p-input-text label=${label} hide-label="true" data-key=${key ?? nothing}
    placeholder=${placeholder ?? nothing} inputmode=${inputmode ?? nothing} ?disabled=${disabled}
    .value=${live(value)} @input=${keep} @change=${keep}></p-input-text>`;
}

function tick(label, checked, hideLabel = true) {
  return html`<p-checkbox label=${label} hide-label=${hideLabel ? "true" : "false"} disabled="true"
    .checked=${checked}></p-checkbox>`;
}

function pure(label, onclick) {
  return html`<p-button-pure type="button" size="xs" icon="reset" @click=${onclick}>${label}</p-button-pure>`;
}

export function button(label, onclick, { id, icon, variant, busy = false, disabled = false } = {}) {
  return html`<p-button id=${id ?? nothing} type="button" compact="true" icon=${icon ?? nothing}
    variant=${variant ?? nothing} .loading=${busy} ?disabled=${disabled} @click=${onclick}>${label}</p-button>`;
}

// A panel's longer explanation, behind a disclosure that starts closed, so its controls come first.
export function more(title, ...paragraphs) {
  return html`<details class="more"><summary>${title}</summary>${paragraphs.map((p) => html`<p-text>${p}</p-text>`)}
    </details>`;
}

// TD-209: one loop's round value, or a role's minutes (TD-286); blank inherits (the final review, the builder's).
export function numberCell(owner, field, label, id) {
  const key = `${owner}.${field}`, final = owner === "final_review";
  const below = final ? finalBelow(field) : inherited().agents[owner][field];
  const inUse = final ? state.loaded.settings.final_review?.[field] : state.loaded.settings.agents[owner][field];
  return (id ? (...parts) => cellWith(id, ...parts) : cell)(typed(`${label}, ${owner.replace("_", " ")}`, own(key),
    (v) => edit(key, v), { key, placeholder: clear(below), inputmode: "numeric", disabled: state.saving }),
  source(final ? key : `agents.${key}`, inUse));
}

// What a blank final-review value takes: the global one when editing this project, else the builder's as edited.
function finalBelow(field) {
  const wide = { project: [state.loaded.machine, state.loaded.global], machine: [state.loaded.global] }[state.layer];
  const above = (wide ?? []).map((l) => l?.final_review?.[field]).find((v) => v !== null && v !== undefined);
  if (above !== undefined) return above;
  return own(`builder.${field}`).trim() || inherited().agents.builder[field];
}

// TD-78: a design judge's fail goes back to the build, or to the owner's decision page.
export function designFailures() {
  const key = "design_failures", below = inherited()[key];
  return cell(choose("When the design judge fails a change", [[INHERIT, clear(below)],
    ["back", "back: send it back to the build"], ["ask", "ask: show it to me first"]], own(key) || INHERIT,
  (v) => edit(key, v), { key, disabled: state.saving }), source(key, state.loaded.settings.design_failures));
}

// R15: five preferences, each set per layer and never defaulted in code; the project's value wins, then this
// machine's, then Global's. A blank or "inherit" choice clears the layer's own value.
const PREF_CHOICES = { merge_method: [["merge", "merge commit"], ["squash", "squash"], ["rebase", "rebase"]],
  delete_remote_branch: [["on", "on"], ["off", "off"]], ask_before_merge: [["on", "on"], ["off", "off"]] };

function prefCell(field) {
  const key = `prefs.${field}`, below = inherited().prefs?.[field];
  const shownBelow = typeof below === "boolean" ? (below ? "on" : "off") : (below ?? "unset");
  const choices = PREF_CHOICES[field];
  const control = choices
    ? choose(PREF_NAMES[field], [[INHERIT, clear(shownBelow)], ...choices], own(key) || INHERIT,
      (v) => edit(key, v), { key, disabled: state.saving })
    : typed(PREF_NAMES[field], own(key), (v) => edit(key, v),
      { key, placeholder: clear(shownBelow), inputmode: "numeric", disabled: state.saving });
  return cell(control, source(key, state.loaded.settings.prefs[field]));
}

export function prefRows() {
  return Object.entries(PREF_NAMES).map(([field, name]) =>
    setting(`set-prefs-${field}`, name, [`prefs.${field}`], prefCell(field)));
}

export function widths() {
  const below = inherited().widths?.join(", ");
  return cell(typed("Screenshot widths in px, comma-separated (1280 to 2400)", own("widths"),
    (v) => edit("widths", v), { key: "widths", placeholder: clear(below), disabled: state.saving }),
  source("widths", state.loaded.settings.widths, true,
    (v) => (Array.isArray(v) && v.some(Number.isNaN) ? own("widths") : v)));
}

// TD-336: how many agent sessions of one project run at once; the machine's total holds as well.
export function sessionsAtOnce() {
  const key = "sessions", below = inherited()[key];
  return cell(typed(PLAIN_NAMES.sessions, own(key), (v) => edit(key, v),
    { key, placeholder: clear(below), inputmode: "numeric", disabled: state.saving }),
  source(key, state.loaded.settings[key]));
}

// A setting only Global holds, for every project and machine: another layer shows it read-only with where it is set
// (#809). *key* is the draft's and the resolved settings' path alike.
function globalOnly(key, label, inUse, inputmode) {
  if (state.layer !== "global") {
    return cell(typed(label, String(inUse ?? ""), () => undefined, { placeholder: "unset", inputmode, disabled: true }),
      source(key, inUse), html`<p-text size="sm" color="contrast-medium">set on Global</p-text>`);
  }
  return cell(typed(label, own(key), (v) => edit(key, v),
    { key, placeholder: clear(at(inherited(), key)), inputmode, disabled: state.saving }), source(key, inUse));
}

// TD-400: the curator decides alone at or above this confidence; one value for every machine and project.
export function curatorThreshold() {
  const key = "curator_threshold", label = "Curator's confidence threshold in percent (50 to 100)";
  return globalOnly(key, label, state.loaded.settings[key], "numeric");
}

// The memory values: what a rating is worth, when an entry goes stale, how much recall returns, when deleted files go.
// Each is Global's alone, with no code default: unset, it holds the projects' work and the memory tools refuse.
export function memoryValue(field, label, inputmode = "numeric") {
  return globalOnly(`memory.${field}`, label, state.loaded.settings.memory?.[field], inputmode);
}

// Improvement's Spotter (design §4): each setting layered field by field; a project may set its own (2026-10-25).
// Each category's actions are the server's (``spotter_actions``): an action outside its category is refused there.
const SPOT_CHOICES = {
  switch: [["off", "off"], ["on", "on"]],
  verbose: [["off", "off"], ["on", "on: a short rationale with its evidence per look"]],
};
const ACTION_NAMES = { record: "record", "show-owner": "show the owner", steer: "steer: a note into the running turn",
  "refuse-hand-off": "refuse the hand-off", "stop-and-resume": "stop, then resume with the note",
  "stop-and-ask": "stop and ask the owner" };

function spotChoices(field) {
  const actions = state.loaded.settings.spotter_actions?.[field];
  return actions ? actions.map((a) => [a, ACTION_NAMES[a] ?? a]) : SPOT_CHOICES[field];
}

export function spotterCell(field, label) {
  const key = `spot.${field}`, value = own(key), below = inherited().spotter?.[field];
  const words = (v) => (Array.isArray(v) ? v.join(", ") : v);
  const needed = (state.loaded.settings.missing ?? []).includes(`spotter.${field}`);  // the server's rule
  const choices = spotChoices(field);
  const control = choices
    ? choose(label, [[INHERIT, clear(below)], ...choices], value || INHERIT,
      (v) => edit(key, v), { key, disabled: state.saving })
    : typed(label, value, (v) => edit(key, v, true), { key, placeholder: clear(words(below)),
      inputmode: ["looks", "verbose_until"].includes(field) ? undefined
        : field === "look_credit_limit" ? "decimal" : "numeric", disabled: state.saving });
  return cell(control, source(`spotter.${field}`, state.loaded.settings.spotter?.[field], needed, words));
}

// TD-308: the labels on every pull request OwlBear opens; a project's list replaces the global one.
export function prLabels() {
  const key = "pr_labels", below = inherited()[key] && (inherited()[key].join(", ") || "none");
  return cell(typed("Labels, comma-separated; none for no labels", own(key), (v) => edit(key, v, true),
    { key, placeholder: clear(below), disabled: state.saving }), source(key, state.loaded.settings[key]));
}

// TD-308: the line "Opened by OwlBear Delivery for …" at the end of a pull request's text; layered (2026-10-23).
export function prMarker() {
  const key = "pr_marker", below = onOff(inherited()[key]);
  return cell(choose("The line Opened by OwlBear Delivery", [[INHERIT, clear(below)],
    ["on", "on: end with the line"], ["off", "off: leave it out"]], own(key) || INHERIT, (v) => edit(key, v),
  { key, disabled: state.saving }), source(key, state.loaded.settings[key]));
}

// TD-402: the account a project's GitHub writes are made by; repository-owner shows the account TD-402's rule gives on
// this project's origin now, whatever layer holds it (D-01M6G9XSXY0G5N65PBJ3RKKPK7).
export function githubAccount() {
  const key = "github_account", rule = state.loaded.github_rule ?? {};
  const named = (v) => v !== "repository-owner" ? v
    : rule.error ? `repository-owner: ${rule.error}` : `${rule.login || "no account"} (${rule.why})`;
  return cell(typed("GitHub account: a login, or repository-owner", own(key), (v) => edit(key, v, true),
    { key, placeholder: clear(inherited()[key]), disabled: state.saving }),
  source(key, state.loaded.settings[key], true, named));
}

// D-01M5YE4P5317N1HWD0QN6N05E0: whether a Delivery step loads the owner's own instruction files or is offered his own
// skills, from his Copilot folder; layered, with no default: steps refuse while either is unset.
const USER_CONFIG = {
  load_user_instructions: ["on: your instruction files load too", "off: only the repository's instructions"],
  load_user_skills: ["on: your skills are offered too", "off: only Delivery's skills"],
  load_user_memory: ["on: they recall it; producing steps may save",
    "off: no Copilot Memory (recommended)"], // D-01M69EBRBBW97001KZ43C0BJM1
};
export const USER_KEYS = Object.keys(USER_CONFIG);

export function userConfig(key) {
  const [on, off] = USER_CONFIG[key], below = onOff(inherited()[key]);
  return cell(choose(USER_NAMES[key], [[INHERIT, clear(below)], ["on", on], ["off", off]], own(key) || INHERIT,
    (v) => edit(key, v), { key, disabled: state.saving }), source(key, state.loaded.settings[key], true, onOff));
}

// D-01M6DX04FRP680Z4GGHK5B9VRC: what the shell guard refuses or only warns about in a step's shell commands that
// skip Git hooks or signing or force-push; layered, with no default: steps refuse while it is unset.
const GUARD = [["strict", "strict: refuse what it finds, warn on weak signs"],
  ["standard", "standard: refuse the known ways, warn on new variants"], ["lenient", "lenient: only warn"],
  ["off", "off: check none of them"]];

export function guardLevel() {
  const key = "guard_level", below = inherited()[key];
  return cell(choose(PLAIN_NAMES.guard_level, [[INHERIT, clear(below)], ...GUARD], own(key) || INHERIT,
    (v) => edit(key, v), { key, disabled: state.saving }), source(key, state.loaded.settings[key]));
}

function tokens(n) {
  return n >= 1e6 ? `${+(n / 1e6).toFixed(1)}M` : `${Math.round(n / 1000)}k`;
}

// TD-376: whether a role's sessions may start the runtime's built-in subagents; on unless a layer says off.
export function subagentsCell(role) {
  const key = `${role}.subagents`, below = onOff(inherited().agents[role].subagents);
  return cellWith(`set-agents-${role}-subagents`, choose(`Built-in subagents, ${role}`, [[INHERIT, clear(below)],
    ["true", "on: may start them"], ["false", "off: none"]], own(key) || INHERIT, (v) => edit(key, v),
    { key, disabled: state.saving }),
  source(`agents.${key}`, state.loaded.settings.agents[role].subagents));
}

// What a blank model, effort or context of *role* gives in the edited layer. The repairer's are the builder's as
// edited while all three of its own are unset; once one is set, an inherited builder value no longer applies
// (D-01M6SY11CY5SN5ZKYJNM0K6BDM).
function below(role, field) {
  if (role !== "repairer") return inherited().agents[role][field];
  if (followsBuilder(field)) return own(`builder.${field}`).trim() || inherited().agents.builder[field];
  return inherited().sources[`agents.repairer.${field}`] === "builder" ? null : inherited().agents.repairer[field];
}

// The model a role runs with in the edited layer: its own draft or saved value, else what it inherits.
function modelOf(role) {
  return own(`${role}.model`).trim() || below(role, "model");
}

function offeredModel(role) {
  return state.offered?.find((m) => m.id === modelOf(role));
}

// Why the role's effort, its own or inherited, cannot run with its model; empty when it can or nothing is known.
export function mismatch(role) {
  const model = offeredModel(role), mine = own(`${role}.effort`);
  const effort = mine || below(role, "effort");
  if (!effort || !model || !model.efforts.length || model.efforts.includes(effort)) return "";  // unset: listed
  return `${model.id} does not offer effort ${effort}${mine ? "" : " (inherited)"}; choose one it offers`;
}

function tierOf(role) {
  return own(`${role}.context`) || below(role, "context");
}

// Why the role's context tier cannot run with its model; empty when it can or nothing is known.
export function tierMismatch(role) {
  const model = offeredModel(role);
  if (!model || model.long || tierOf(role) !== "long") return "";
  return `${model.id} has no long context${own(`${role}.context`) ? "" : " (inherited)"}; choose its default`;
}

export function contextCell(role) {
  const key = `${role}.context`, mine = own(key), model = offeredModel(role), label = `Context for ${role}`;
  let control;
  if (model?.long) {
    const [low, high] = levels([model.rates, model.long.rates]);
    const items = [["default", model.context, low], ["long", model.long.context, high]].map(([v, size, level]) => [
      v, `${tokens(size)}${arrows(level)}`, `${tokens(size)}, ${v} context${level ? ", higher rates per token" : ""}`]);
    control = html`<p-segmented-control label=${label} hide-label="true" compact="true" columns="2" data-key=${key}
      ?disabled=${state.saving} .value=${live(tierOf(role))}
      @change=${(e) => { edit(key, e.target.value); handOff(e, label); }}>
      ${items.map(([v, said, aria]) => html`<p-segmented-control-item value=${v}
        aria=${`{ 'aria-label': '${aria}' }`}>${said}</p-segmented-control-item>`)}</p-segmented-control>`;
  } else if (model) {
    const wrong = tierMismatch(role) || (tierOf(role) ? "" : "no layer sets a context tier");
    control = html`<p-text size="sm">${tokens(model.context)} \u00b7 only tier</p-text>${wrong ? html`
      <p-text size="xs" color="error">${wrong}</p-text>${pure("Use the default tier", () => edit(key, "default"))}`
      : nothing}`;  // the default tier fills an unset one and overrides an inherited long one
  } else {
    control = choose(label, [[INHERIT, clear(below(role, "context"))], ["default", "default"], ["long", "long"]],
      mine || INHERIT, (v) => edit(key, v), { key, disabled: state.saving });
  }
  const reset = model && mine
    ? pure(state.layer === "global" ? "Unset" : "Use inherited", () => edit(key, "")) : nothing;
  return cell(control, reset, source(`agents.${key}`, state.loaded.settings.agents[role].context));
}

function amount(n) {
  return n.toLocaleString("en", { maximumFractionDigits: 2 });
}

// The chosen model's rates at the row's context tier, shown under its select, with the effort in use: the runtime
// prices no effort, so the rates are the same at every one.
function ratesNote(role) {
  const model = offeredModel(role), long = tierOf(role) === "long" && model?.long;
  const rates = long ? model.long.rates : model?.rates;
  if (!rates) return html`<p-text size="xs" color="contrast-medium">AI credits per 1M tokens: not known</p-text>`;
  const write = rates.cache_write ? ` \u00b7 cache\u00a0write\u00a0${amount(rates.cache_write)}` : "";
  const flow = `in\u00a0${amount(rates.input)} \u00b7 out\u00a0${amount(rates.output)}`;
  const line = `${flow} \u00b7 cache\u00a0${rates.cache == null ? "not known" : amount(rates.cache)}${write}`;
  const effort = own(`${role}.effort`) || below(role, "effort");
  return html`<p-text size="xs">AI credits per 1M tokens: ${line}</p-text><p-text size="xs"
    color="contrast-medium">effort\u00a0${said(effort)}: same rates at every effort</p-text>`;
}

export function editable(role, field) {
  const key = `${role}.${field}`, blank = below(role, field), value = own(key);
  const label = `${field === "model" ? "Model" : "Effort"} for ${role}`, model = offeredModel(role);
  const set = (v) => edit(key, v), common = { key, disabled: state.saving };
  let control, note = nothing;
  if (field === "effort") {
    const efforts = model?.efforts.length ? model.efforts : EFFORTS;  // a model without efforts ignores the value
    const options = [[INHERIT, clear(blank)],
      ...efforts.map((e) => [e, e === model?.default_effort ? `${e} (model default)` : e])];
    if (value && !efforts.includes(value)) {
      options.push([value, `${value} (not offered by ${model?.id ?? "this model"})`]);
    }
    control = choose(label, options, value || INHERIT, set, { ...common, wrong: mismatch(role) });
    if (model && !model.efforts.length) {
      note = html`<p-text size="xs" color="contrast-medium">${model.id} takes no effort setting; it ignores
        this one</p-text>`;
    }
  } else if (state.offered?.length) {
    const options = [[INHERIT, clear(blank)], ...state.offered.map((m) => {
      const long = m.long ? ` / ${tokens(m.long.context)} long` : "";
      const sizes = m.context ? ` \u00b7 ${tokens(m.context)}${long} context` : "";
      return [m.id, `${m.name} (${m.id})${sizes}`];
    })];
    if (value && !state.offered.some((m) => m.id === value)) options.push([value, `${value} (not offered here)`]);
    control = choose(label, options, value || INHERIT, set, { ...common, filter: true });
  } else {
    control = typed(label, value, set, { ...common, placeholder: clear(blank) });
  }
  return cell(control, note, source(`agents.${key}`, state.loaded.settings.agents[role][field]),
    field === "model" ? ratesNote(role) : nothing);
}
