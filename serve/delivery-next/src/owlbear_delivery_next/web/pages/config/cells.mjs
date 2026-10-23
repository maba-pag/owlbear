import { html, nothing } from "/assets/lit-html/3.3.3/lit-html.js";
import { live } from "/assets/lit-html/3.3.3/directives/live.js";
import { EFFORTS, INHERIT, SOURCES, state, shown } from "./state.mjs";
import { own, inherited, edit } from "./layers.mjs";

// Code ships no defaults (2026-10-23): a value no layer sets is unset, an error until it is filled in.
function source(key, inUse) {
  const from = SOURCES[state.loaded.settings.sources[key]];
  if (!from) {
    return html`<p-text size="xs" color="error">unset: set it here or in a wider layer; steps that need it ask you
      until then</p-text>`;
  }
  const line = inUse === undefined ? `from ${from}` : `in use: ${shown(inUse)}, from ${from}`;
  return html`<p-text size="xs" color="contrast-medium">${line}</p-text>`;
}

// What a blank field inherits, in words; "unset" where no layer below sets it.
function said(value) {
  return value === null || value === undefined ? "unset" : value;
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
  return html`<p-button-pure type="button" size="x-small" icon="reset" @click=${onclick}>${label}</p-button-pure>`;
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
    { key, placeholder: `inherit (${said(below)})`, inputmode: "numeric", disabled: state.saving }),
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
  return cell(choose("When the design judge fails a change", [[INHERIT, `inherit (${said(below)})`],
    ["back", "back: send it back to the build"], ["ask", "ask: show it to me first"]], own(key) || INHERIT,
  (v) => edit(key, v), { key, disabled: state.saving }), source(key, state.loaded.settings.design_failures));
}

export function widths() {
  const below = inherited().widths?.join(", ");
  return cell(typed("Screenshot widths in px, comma-separated (1280 to 2400)", own("widths"),
    (v) => edit("widths", v), { key: "widths", placeholder: `inherit (${said(below)})`, disabled: state.saving }),
  source("widths", state.loaded.settings.widths));
}

// TD-336: how many agent sessions of one project run at once; the machine's total holds as well.
export function sessionsAtOnce() {
  const key = "sessions", below = inherited()[key];
  return cell(typed("Agent sessions at once in one project", own(key), (v) => edit(key, v),
    { key, placeholder: `inherit (${said(below)})`, inputmode: "numeric", disabled: state.saving }),
  source(key, state.loaded.settings[key]));
}

// TD-400: the curator decides alone at or above this confidence; one value for every machine and project.
export function curatorThreshold() {
  const key = "curator_threshold";
  if (state.layer !== "global") {
    return cell(html`<p-text>Set for all projects</p-text>`, source(key, state.loaded.settings[key]));
  }
  return cell(typed("Curator's confidence threshold in percent (50 to 100)", own(key), (v) => edit(key, v),
    { key, placeholder: `inherit (${said(inherited()[key])})`, inputmode: "numeric", disabled: state.saving }),
  source(key, state.loaded.settings[key]));
}

// The watcher judges agent steps' outside actions; on in Global, a project may turn it off (owner, 2026-10-23).
export function watcherSwitch() {
  const key = "watcher", below = onOff(inherited()[key]);
  return cell(choose("The watcher", [[INHERIT, `inherit (${said(below)})`], ["on", "on: judge agent steps"],
    ["off", "off: no watcher"]], own(key) || INHERIT, (v) => edit(key, v), { key, disabled: state.saving }),
  source(key, state.loaded.settings[key]));
}

// TD-308: the labels on every pull request OwlBear opens; a project's list replaces the global one.
export function prLabels() {
  const key = "pr_labels", below = inherited()[key] && (inherited()[key].join(", ") || "none");
  return cell(typed("Labels, comma-separated; none for no labels", own(key), (v) => edit(key, v, true),
    { key, placeholder: `inherit (${said(below)})`, disabled: state.saving }), source(key, state.loaded.settings[key]));
}

// TD-308: the line "Opened by OwlBear Delivery for …" at the end of a pull request's text; layered (2026-10-23).
export function prMarker() {
  const key = "pr_marker", below = onOff(inherited()[key]);
  return cell(choose("The line Opened by OwlBear Delivery", [[INHERIT, `inherit (${said(below)})`],
    ["on", "on: end with the line"], ["off", "off: leave it out"]], own(key) || INHERIT, (v) => edit(key, v),
  { key, disabled: state.saving }), source(key, state.loaded.settings[key]));
}

function tokens(n) {
  return n >= 1e6 ? `${+(n / 1e6).toFixed(1)}M` : `${Math.round(n / 1000)}k`;
}

// TD-376: whether a role's sessions may start the runtime's built-in subagents; on unless a layer says off.
export function subagentsCell(role) {
  const key = `${role}.subagents`, below = onOff(inherited().agents[role].subagents);
  return cell(choose(`Built-in subagents, ${role}`, [[INHERIT, `inherit (${said(below)})`],
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
  if (!model || !model.efforts.length || model.efforts.includes(effort)) return "";
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

// The long tier costs more per token: higher input or output rates than the default tier.
function dearer(model) {
  const [base, long] = [model.rates, model.long?.rates];
  return Boolean(base && long && (long.input > base.input || long.output > base.output));
}

export function contextCell(role) {
  const key = `${role}.context`, mine = own(key), model = offeredModel(role), label = `Context for ${role}`;
  let control;
  if (model?.long) {
    const up = dearer(model), more = up ? "higher rates per token" : "same rates per token";
    const items = [["default", tokens(model.context), `${tokens(model.context)}, default context`],
      ["long", `${tokens(model.long.context)}${up ? "\u00a0\u2191" : ""}`,
        `${tokens(model.long.context)}, long context, ${more}`]];
    control = html`<p-segmented-control label=${label} hide-label="true" compact="true" columns="2" data-key=${key}
      ?disabled=${state.saving} .value=${live(tierOf(role))} @change=${(e) => edit(key, e.target.value)}>
      ${items.map(([v, said, aria]) => html`<p-segmented-control-item value=${v}
        aria=${`{ 'aria-label': '${aria}' }`}>${said}</p-segmented-control-item>`)}</p-segmented-control>`;
  } else if (model) {
    const wrong = tierMismatch(role);
    control = html`<p-text size="sm">${tokens(model.context)} \u00b7 only tier</p-text>${wrong ? html`
      <p-text size="xs" color="error">${wrong}</p-text>${pure("Use the default tier", () => edit(key, "default"))}`
      : nothing}`;  // the default tier overrides an inherited long one
  } else {
    const below = inherited().agents[role].context;
    control = choose(label, [[INHERIT, `inherit (${said(below)})`], ["default", "default"], ["long", "long"]],
      mine || INHERIT, (v) => edit(key, v), { key, disabled: state.saving });
  }
  const reset = model && mine ? pure("Use inherited", () => edit(key, "")) : nothing;
  return cell(control, reset, source(`agents.${key}`, state.loaded.settings.agents[role].context));
}

function amount(n) {
  return n.toLocaleString("en", { maximumFractionDigits: 2 });
}

export function ratesCell(role) {
  const model = offeredModel(role), long = tierOf(role) === "long" && model?.long;
  const rates = long ? model.long.rates : model?.rates;
  if (!rates) return cell(html`<p-text>\u2014</p-text><p-text size="xs" color="contrast-medium">not known</p-text>`);
  const write = rates.cache_write ? ` \u00b7 cache write ${amount(rates.cache_write)}` : "";
  const flow = `in ${amount(rates.input)} \u00b7 out ${amount(rates.output)}`;
  const line = `${flow} \u00b7 cache ${rates.cache == null ? "not known" : amount(rates.cache)}${write}`;
  return cell(html`<p-text>${line}</p-text><p-text size="xs" color="contrast-medium">${model.id}, ${long ? "long"
    : "default"} context</p-text>`);
}

export function editable(role, field) {
  const key = `${role}.${field}`, below = inherited().agents[role][field], value = own(key);
  const label = `${field === "model" ? "Model" : "Effort"} for ${role}`, model = offeredModel(role);
  const set = (v) => edit(key, v), common = { key, disabled: state.saving };
  let control, note = nothing;
  if (field === "effort") {
    const efforts = model ? model.efforts : EFFORTS;
    const options = [[INHERIT, `inherit (${said(below)})`],
      ...efforts.map((e) => [e, e === model?.default_effort ? `${e} (model default)` : e])];
    if (value && !efforts.includes(value)) {
      options.push([value, `${value} (not offered by ${model?.id ?? "this model"})`]);
    }
    control = choose(label, options, value || INHERIT, set, { ...common, wrong: mismatch(role) });
    if (model && !model.efforts.length) {
      note = html`<p-text size="xs" color="contrast-medium">${model.id} takes no effort setting</p-text>`;
    }
  } else if (state.offered?.length) {
    const options = [[INHERIT, `inherit (${said(below)})`], ...state.offered.map((m) => {
      const long = m.long ? ` / ${tokens(m.long.context)} long` : "";
      const sizes = m.context ? ` \u00b7 ${tokens(m.context)}${long} context` : "";
      return [m.id, `${m.name} (${m.id})${sizes}`];
    })];
    if (value && !state.offered.some((m) => m.id === value)) options.push([value, `${value} (not offered here)`]);
    control = choose(label, options, value || INHERIT, set, { ...common, filter: true });
  } else {
    control = typed(label, value, set, { ...common, placeholder: `inherit (${said(below)})` });
  }
  return cell(control, note, source(`agents.${key}`, state.loaded.settings.agents[role][field]));
}

// A setting Delivery does not apply yet: its control, disabled, with where its value comes from.
export function inactive(label, value, key) {
  let control;
  if (value === null || value === undefined) {
    control = typed(label, "", () => {}, { disabled: true });
  } else if (typeof value === "boolean") {
    control = tick(label, value);
  } else if (key.endsWith(".runtime")) {
    control = choose(label, state.loaded.catalogue.runtimes.map((r) => [r.runtime, r.runtime]), value, () => {},
      { disabled: true });
  } else if (key.endsWith(".categories")) {
    const names = Object.keys(state.loaded.catalogue.categories);
    control = html`<div>${names.map((name) => tick(name, value.includes(name), false))}</div>`;
  } else {
    control = typed(label, shown(value), () => {}, { disabled: true });
  }
  return cell(control, source(key));
}
