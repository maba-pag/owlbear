import { render } from "/assets/lit-html/3.3.3/lit-html.js";
import { view } from "./sections.mjs";

export const EFFORTS = ["low", "medium", "high", "xhigh", "max"];
export const INHERIT = "inherit";  // the option that clears the layer's own value
export const SOURCES = { default: "built-in default", global: "global", machine: "this machine",
  project: "this project", builder: "the builder's value" };
export const LAYERS = { project: "This project", machine: "This machine", global: "All projects" };
export const ROUNDS = [["max_rounds", "Rounds at most"], ["max_findings", "New findings per round at most"],
  ["last_round_at", "Last round at or below"], ["ask_owner_at", "Ask you at or above"]];  // TD-209
export const NUMBERS = [...ROUNDS.map(([f]) => f), "minutes", "sessions", "curator_threshold", "steer_share",
  "intervention_cap", "sample_rate", "update_check_hours_owlbear", "update_check_hours_pds",
  "update_check_hours_impeccable"];  // whole numbers
// Credit limits (D-01M5XCD49YHHR1NQKKY8TQD0C3): credit amounts, a fraction allowed.
export const CREDITS = ["look_credit_limit", "retro_run_credit_limit", "replay_run_credit_limit"];
// A typed number as sent: a whole number for NUMBERS, a decimal one for CREDITS; other text as typed, which the
// server refuses with its reason.
export function typedNumber(field, value) {
  if (CREDITS.includes(field)) return /^\d+(\.\d+)?$/.test(value) ? Number(value) : value;
  return /^\d+$/.test(value) ? Number(value) : value;
}
export const LOOPS = [["shaper", "Brief challenges (shaper)"], ["planner", "Plan challenges (planner)"],
  ["builder", "Task reviews (builder)"], ["final_review", "Final review"],
  ["updater", "Impeccable updates (updater)"]];
export const WRITE = 60000;  // a save commits and pushes the shared settings repository (TD-64): a network round trip
// Everything shown comes from here (TD-264): drafts per layer ("role.field" -> as typed), the folder being typed and
// the offered models once read.
export const state = {
  loaded: null, layer: "project", saving: false, offered: null, modelsNote: "", error: "", status: "",
  group: "overview",  // the group shown (D-01M63C8QQMANY46N8GMNNKH1V9); drafts of every group stay meanwhile
  folder: null,
  machine: null, others: [], unread: [],  // the machine's values and the other projects' settings (TD-243)
  everything: false,  // the overview shows every setting, not only those a project sets apart (TD-295)
  machineDraft: null, machineSaving: false,  // the machine's settings as edited, before they are saved
  machineText: null,  // a list setting's text as typed, until a save
  machineWrites: 0,  // counts machine saves, so a read that started before one never shows older values
  machineUnread: "",  // why this machine's settings could not be read, until a read succeeds
  // Owner edited or cleared a project Merge and cleanup preference; kept until a save publishes.
  prefsReview: false,
};
export const drafts = { project: {}, machine: {}, global: {} };
// arrived: models read while a setting held the focus, applied once it leaves; target: a selector of the element an
// address named (a row, a heading), focused once it shows; an object since a module cannot reassign another's binding
export const page = { arrived: null, target: null };

export function show() {
  render(view(), document.getElementById("page"));
  const target = page.target && document.querySelector(page.target);
  if (target) {
    page.target = null;
    reveal(target);
  }
}

// Focus *target*, or a row's first control: the menu's dialog puts the focus back on its button as it closes, so the
// focus is put back until it has stayed a few frames, for at most a second.
async function reveal(target) {
  const control = target.matches("p-table-row, div") ? target.querySelector("[data-key], [id^='machine-'], "
    + "[id^='global-machine-'], p-select, p-input-text, p-segmented-control") : null;
  const into = control ?? target;
  into.scrollIntoView({ block: control ? "center" : "start" });
  for (let frame = 0, kept = 0; frame < 60 && kept < 10; frame++) {
    if (into.matches(":focus")) kept++;
    else into.focus({ preventScroll: true });
    await new Promise(requestAnimationFrame);
  }
}

// Render, applying arrived models only once no setting holds the focus, so they never replace the control in use.
export function showIdle() {
  const using = document.activeElement?.closest?.("main [data-key]");
  if (!using && page.arrived) {
    [state.offered, state.modelsNote, page.arrived] = [page.arrived.offered, page.arrived.note, null];
  }
  show();
  if (using && page.arrived) {
    document.querySelector("main").addEventListener("focusout", () => setTimeout(showIdle), { once: true });
  }
}

export function notify(message) {
  state.error = message ? message.charAt(0).toUpperCase() + message.slice(1) : "";
  show();
}

export function shown(value) {
  if (Array.isArray(value)) return value.length ? value.join(", ") : "none";
  if (typeof value === "boolean") return value ? "yes" : "no";
  return String(value);
}
