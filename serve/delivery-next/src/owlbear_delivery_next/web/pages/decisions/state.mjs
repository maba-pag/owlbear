import { render } from "/assets/lit-html/3.3.3/lit-html.js";
import { view } from "./list.mjs";

export const WRITE = 60000;  // a write commits and pushes to the shared data repository
export const DIALOG = "{ 'aria-haspopup': 'dialog' }";
export const STATES = { draft: "draft", in_force: "in force", replaced: "replaced", withdrawn: "withdrawn",
  spent: "spent" };
export const TAGS = { draft: "info", in_force: "success", replaced: "secondary", withdrawn: "secondary",
  spent: "secondary" };
// The read-back queue's kinds, most urgent first (TD-427).
export const KINDS = { safety: "Safety or irreversible", blocked: "Blocks work", uncertain: "Uncertain",
  improvement: "Improvement" };
// Everything the page shows comes from here, so a re-render never loses what the owner typed or opened.
export const state = {
  loaded: null, error: "", receipts: [], notice: "",
  opened: null,  // the id of the decision shown in full
  from: "list",  // where it is shown: under its read-back in the queue, or in the list
  entry: null,  // its details as last read
  form: null,  // { action, draft } of the opened decision's form
  pending: "",  // the action whose request is under way
};
// where: project | global | all | owlbear; state: "" (in force and drafts), a state, or "all" (retired included)
export const filter = { where: "all", topic: "", origin: "", state: "", read_back: "", text: "" };

// A decision's address: OwlBear's own decisions are read and acted on with where=owlbear (TD-435).
export function at(path) {
  return filter.where === "owlbear" ? `${path}?where=owlbear` : path;
}

export function show() {
  const focused = document.activeElement;
  render(view(), document.getElementById("page"));
  if (focused?.isConnected && document.activeElement !== focused) focused.focus();
}

export function notify(message = "") {
  state.error = message ? message.charAt(0).toUpperCase() + message.slice(1) : "";
  show();
}

export function scopeOf(d) {
  if (d.scope === "global") return "Global";
  const project = d.project === "owlbear" ? "OwlBear" : d.project;
  return d.change ? `${project} · Change ${d.change}` : project;
}

export function readBack(value) {
  if (value === "none") return "not read back";
  return value === "pending" ? "waiting to be read back" : `read back ${value}`;
}
