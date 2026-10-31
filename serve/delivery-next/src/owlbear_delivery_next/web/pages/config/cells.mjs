import { html, nothing } from "/assets/lit-html/3.3.3/lit-html.js";
import { live } from "/assets/lit-html/3.3.3/directives/live.js";
import { EFFORTS, INHERIT, SOURCES, state, shown } from "./state.mjs";
import { own, inherited, edit, layerValue, preview } from "./layers.mjs";
import { levels, arrows } from "./cost.mjs";

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
  const text = key === "curator_threshold" ? "Unset: no machine or project can set it, so it stays unset"
    : key.startsWith("final_review.") ? "Unset: it then takes the builder's value"
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

export function row(...cells) {
  return html`<p-table-row>${cells}</p-table-row>`;
}

// GW8RT6: a setting's row, which the unset list links to by its *id*; its name is red while a key it sets is unset.
export function setting(id, name, keys, ...cells) {
  const missing = state.loaded.settings.missing ?? [], unset = keys.some((k) => missing.includes(k));
  return html`<p-table-row id=${id} tabindex="-1">${cell(html`<p-text color=${unset ? "error" : nothing}>${name}
    </p-text>`)}${cells}</p-table-row>`;
}

export function table(caption, heads, body, rows, { id, hidden = false } = {}) {
  return html`<p-table id=${id ?? nothing} caption=${caption} ?hidden=${hidden}><p-table-head><p-table-head-row>
    ${heads.map((h) => html`<p-table-head-cell>${h}</p-table-head-cell>`)}</p-table-head-row></p-table-head>
    <p-table-body id=${body}>${rows}</p-table-body></p-table>`;
}

// A table cell's choice: its column says what it is, so the label is for assistive technology only.
// *wrong* says why the choice cannot run, for a choice that is checked (an effort); undefined for the others.
function choose(label, options, value, chosen, { key, disabled = false, filter = false, wrong } = {}) {
  const changed = (e) => chosen(e.target.value);
  const items = options.map(([v, said]) => html`<p-select-option value=${v}>${said}</p-select-option>`);
  const checked = wrong === undefined ? nothing : wrong ? "error" : "none";
  return html`<p-select label=${label} hide-label="true" data-key=${key ?? nothing}
    filter=${filter ? "true" : nothing} state=${checked} message=${wrong || nothing} ?disabled=${disabled}
    .value=${live(value)} @change=${changed}>${items}</p-select>`;
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

// TD-209: one loop's round value, or a role's minutes (TD-286); blank inherits (the final review, the builder's).
export function numberCell(owner, field, label) {
  const key = `${owner}.${field}`, final = owner === "final_review";
  const below = final ? finalBelow(field) : inherited().agents[owner][field];
  const inUse = final ? state.loaded.settings.final_review?.[field] : state.loaded.settings.agents[owner][field];
  return cell(typed(`${label}, ${owner.replace("_", " ")}`, own(key), (v) => edit(key, v),
    { key, placeholder: clear(below), inputmode: "numeric", disabled: state.saving }),
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
export const PREFS = ["merge_method", "delete_remote_branch", "ci_poll_seconds", "ci_start_window_seconds",
  "ask_before_merge"];
const PREF_NAMES = { merge_method: "Merge method", delete_remote_branch: "Delete the remote branch after merging",
  ci_poll_seconds: "CI poll interval (seconds)", ci_start_window_seconds: "CI start window (seconds)",
  ask_before_merge: "Ask before merging" };
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
  return PREFS.map((field) => setting(`set-prefs-${field}`, PREF_NAMES[field], [`prefs.${field}`], prefCell(field)));
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
  return cell(typed("Agent sessions at once in one project", own(key), (v) => edit(key, v),
    { key, placeholder: clear(below), inputmode: "numeric", disabled: state.saving }),
  source(key, state.loaded.settings[key]));
}

// TD-400: the curator decides alone at or above this confidence; one value for every machine and project, so
// another layer shows it read-only with where it is set (#809).
export function curatorThreshold() {
  const key = "curator_threshold", label = "Curator's confidence threshold in percent (50 to 100)";
  if (state.layer !== "global") {
    const inUse = state.loaded.settings[key];
    return cell(typed(label, String(inUse ?? ""), () => undefined,
      { placeholder: "unset", inputmode: "numeric", disabled: true }), source(key, inUse),
    html`<p-text size="sm" color="contrast-medium">set on Global</p-text>`);
  }
  return cell(typed(label, own(key), (v) => edit(key, v),
    { key, placeholder: clear(inherited()[key]), inputmode: "numeric", disabled: state.saving }),
  source(key, state.loaded.settings[key]));
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

// D-01M5YE4P5317N1HWD0QN6N05E0: whether a Delivery step loads the owner's own instruction files or is offered his own
// skills, from his Copilot folder; layered, with no default: steps refuse while either is unset.
const USER_CONFIG = {
  load_user_instructions: ["Your instructions in Delivery steps", "on: your instruction files load too",
    "off: only the repository's instructions"],
  load_user_skills: ["Your skills in Delivery steps", "on: your skills are offered too", "off: only Delivery's skills"],
};
export const USER_KEYS = Object.keys(USER_CONFIG);

export function userConfigLabel(key) {
  return USER_CONFIG[key][0];
}

export function userConfig(key) {
  const [label, on, off] = USER_CONFIG[key], below = onOff(inherited()[key]);
  return cell(choose(label, [[INHERIT, clear(below)], ["on", on], ["off", off]], own(key) || INHERIT,
    (v) => edit(key, v), { key, disabled: state.saving }), source(key, state.loaded.settings[key], true, onOff));
}

function tokens(n) {
  return n >= 1e6 ? `${+(n / 1e6).toFixed(1)}M` : `${Math.round(n / 1000)}k`;
}

// TD-376: whether a role's sessions may start the runtime's built-in subagents; on unless a layer says off.
export function subagentsCell(role) {
  const key = `${role}.subagents`, below = onOff(inherited().agents[role].subagents);
  return cell(choose(`Built-in subagents, ${role}`, [[INHERIT, clear(below)],
    ["true", "on: may start them"], ["false", "off: none"]], own(key) || INHERIT, (v) => edit(key, v),
    { key, disabled: state.saving }),
  source(`agents.${key}`, state.loaded.settings.agents[role].subagents));
}

// The model a role runs with in the edited layer: its own draft or saved value, else what it inherits.
function modelOf(role) {
  return own(`${role}.model`).trim() || inherited().agents[role].model;
}

function offeredModel(role) {
  return state.offered?.find((m) => m.id === modelOf(role));
}

// Why the role's effort, its own or inherited, cannot run with its model; empty when it can or nothing is known.
export function mismatch(role) {
  const model = offeredModel(role), mine = own(`${role}.effort`);
  const effort = mine || inherited().agents[role].effort;
  if (!effort || !model || !model.efforts.length || model.efforts.includes(effort)) return "";  // unset: listed
  return `${model.id} does not offer effort ${effort}${mine ? "" : " (inherited)"}; choose one it offers`;
}

function tierOf(role) {
  return own(`${role}.context`) || inherited().agents[role].context;
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
      ?disabled=${state.saving} .value=${live(tierOf(role))} @change=${(e) => edit(key, e.target.value)}>
      ${items.map(([v, said, aria]) => html`<p-segmented-control-item value=${v}
        aria=${`{ 'aria-label': '${aria}' }`}>${said}</p-segmented-control-item>`)}</p-segmented-control>`;
  } else if (model) {
    const wrong = tierMismatch(role) || (tierOf(role) ? "" : "no layer sets a context tier");
    control = html`<p-text size="sm">${tokens(model.context)} \u00b7 only tier</p-text>${wrong ? html`
      <p-text size="xs" color="error">${wrong}</p-text>${pure("Use the default tier", () => edit(key, "default"))}`
      : nothing}`;  // the default tier fills an unset one and overrides an inherited long one
  } else {
    const below = inherited().agents[role].context;
    control = choose(label, [[INHERIT, clear(below)], ["default", "default"], ["long", "long"]],
      mine || INHERIT, (v) => edit(key, v), { key, disabled: state.saving });
  }
  const reset = model && mine
    ? pure(state.layer === "global" ? "Unset" : "Use inherited", () => edit(key, "")) : nothing;
  return cell(control, reset, source(`agents.${key}`, state.loaded.settings.agents[role].context));
}

function amount(n) {
  return n.toLocaleString("en", { maximumFractionDigits: 2 });
}

export function ratesCell(role) {
  const model = offeredModel(role), long = tierOf(role) === "long" && model?.long;
  const rates = long ? model.long.rates : model?.rates;
  if (!rates) return cell(html`<p-text>\u2014</p-text><p-text size="xs" color="contrast-medium">not known</p-text>`);
  const write = rates.cache_write ? ` \u00b7 cache\u00a0write\u00a0${amount(rates.cache_write)}` : "";
  const flow = `in\u00a0${amount(rates.input)} \u00b7 out\u00a0${amount(rates.output)}`;
  const line = `${flow} \u00b7 cache\u00a0${rates.cache == null ? "not known" : amount(rates.cache)}${write}`;
  const effort = own(`${role}.effort`) || inherited().agents[role].effort;  // the runtime prices no effort
  return cell(html`<p-text>${line}</p-text><p-text color="contrast-medium">${model.id}, ${long ? "long"
    : "default"} context \u00b7 effort\u00a0${said(effort)}; same rates at every effort</p-text>`);
}

export function editable(role, field) {
  const key = `${role}.${field}`, below = inherited().agents[role][field], value = own(key);
  const label = `${field === "model" ? "Model" : "Effort"} for ${role}`, model = offeredModel(role);
  const set = (v) => edit(key, v), common = { key, disabled: state.saving };
  let control, note = nothing;
  if (field === "effort") {
    const efforts = model?.efforts.length ? model.efforts : EFFORTS;  // a model without efforts ignores the value
    const options = [[INHERIT, clear(below)],
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
    const options = [[INHERIT, clear(below)], ...state.offered.map((m) => {
      const long = m.long ? ` / ${tokens(m.long.context)} long` : "";
      const sizes = m.context ? ` \u00b7 ${tokens(m.context)}${long} context` : "";
      return [m.id, `${m.name} (${m.id})${sizes}`];
    })];
    if (value && !state.offered.some((m) => m.id === value)) options.push([value, `${value} (not offered here)`]);
    control = choose(label, options, value || INHERIT, set, { ...common, filter: true });
  } else {
    control = typed(label, value, set, { ...common, placeholder: clear(below) });
  }
  return cell(control, note, source(`agents.${key}`, state.loaded.settings.agents[role][field]));
}
