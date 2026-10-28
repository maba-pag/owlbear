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
  "intervention_cap", "sample_rate"];  // whole numbers
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
  ["updater", "Design pack updates (updater)"]];
export const WRITE = 60000;  // a save commits and pushes the shared settings repository (TD-64): a network round trip
// TD-101: the design pack update runs in the host; the page starts it and follows its stages.
export const RESULTS = { pending: "not run", running: "running", passed: "passed", failed: "failed", skipped: "skipped",
  returned: "findings back to the updater", waiting: "waiting for you", completed: "session completed",
  findings: "findings", reused: "reused for this identity", answered: "answered by you",
  discarded: "discarded by you", stopped: "stopped", "not-reached": "not reached" };
export const TAGS = { pending: "secondary", running: "info", passed: "success", failed: "error", skipped: "secondary",
  returned: "warning", waiting: "warning", completed: "info", findings: "warning", reused: "info", answered: "info",
  discarded: "secondary", stopped: "warning", "not-reached": "secondary" };
export const ENDINGS = { idle: "Never run.", passed: "Last run passed: its pull request was merged into main.",
  failed: "Last run failed.", "up-to-date": "Last run: already up to date.",
  waiting: "The update waits for your answers below.", discarded: "Last run discarded: nothing changed." };
// TD-220: what became of each finding of the update's challenge rounds, in words.
export const FOUND = { open: "to fix", fixed: "fixed by the updater",
  rejected: "rejected by the updater, not judged yet",
  standing: "rejected by the updater; the challenger accepted that",
  escalated: "rejected by the updater; the challenger upheld it", "owner-fix": "you decided: fix it",
  "owner-drop": "you dropped it", withdrawn: "withdrawn by the challenger" };
// Everything shown comes from here (TD-264): drafts per layer ("role.field" -> as typed), the folder being typed,
// the offered models once read, and the design pack's update with the notes typed for its questions.
export const state = {
  loaded: null, layer: "project", saving: false, offered: null, modelsNote: "", error: "", status: "",
  folder: null, pack: null, packProblem: "", update: null, packNotes: new Map(),
  machine: null, others: [], unread: [],  // the machine's values and the other projects' settings (TD-243)
  everything: false,  // the overview shows every setting, not only those a project sets apart (TD-295)
  machineDraft: null, machineSaving: false,  // the machine's settings as edited, before they are saved
  machineText: null,  // a list setting's text as typed, until a save
  machineWrites: 0,  // counts machine saves, so a read that started before one never shows older values
  // Owner edited or cleared a project Merge and cleanup preference; kept until a save publishes.
  prefsReview: false,
};
export const drafts = { project: {}, machine: {}, global: {} };
// arrived: models read while a setting held the focus, applied once it leaves; an object since a module cannot
// reassign another's binding
export const page = { arrived: null };

export function show() {
  render(view(), document.getElementById("page"));
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
