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
  address: null,
  entry: null,  // its details as last read
  unread: false,  // whether reading them failed, so the opened decision says so instead of "Reading…"
  form: null,  // { action, draft } of the opened decision's form
  pending: "",  // the action whose request is under way
  impact: null,  // { id, address, report | error | busy, scheduled } of the opened decision's impact (TD-428)
  effect: "",  // the owner's mark on a draft that replaces one, sent when he activates it
  recovery: { status: null, error: "", notice: "", pending: "" },  // the interrupted batch, read apart from the list
};
// where: project | global | all | owlbear; state: "" (in force and drafts), a state, or "all" (retired included)
export const filter = { where: "all", topic: "", origin: "", state: "", read_back: "", text: "" };

// Capture the list's address so a later filter cannot retarget its reads, confirmations or writes.
export function addressOf(where, project = "") {
  return { where: where === "owlbear" ? "owlbear" : "", project };
}

export function at(path, address) {
  return address.where ? `${path}?where=${address.where}` : path;
}

export function sameAddress(a, b) {
  return (a?.where ?? "") === (b?.where ?? "");
}

export function projectName(address) {
  return address.where === "owlbear" ? "OwlBear" : address.project;
}

export function show() {
  const focused = document.activeElement;
  render(view(), document.getElementById("page"));
  if (focused?.isConnected && document.activeElement !== focused) focused.focus();
}

export function notify(message = "") {
  const said = untagged(message);
  state.error = said ? said.charAt(0).toUpperCase() + said.slice(1) : "";
  show();
}

export function scopeOf(d) {
  if (d.scope === "global") return "Global";
  const project = d.project === "owlbear" ? "OwlBear" : d.project;
  return d.change ? `${project} · Change ${d.change}` : project;
}

// Whether the title is only the statement cut off (shortened with "…", or its first clause): the statement then
// shows once, as the heading (D-01M63CEE5C9K50RXGCYBSP64VK).
export function cutOff(d) {
  const flat = (text) => text.split(/\s+/).join(" ").trim();
  const title = flat(d.title).replace(/\s*(…|\.\.\.)$/, ""), said = flat(d.statement);
  return title !== "" && said.startsWith(title) && !/[\p{L}\p{N}]/u.test(said.charAt(title.length));
}

// When the owner last confirmed the statement (TD-449), or that it was inherited and never read back (TD-454).
export function readBack(d) {
  if (/^\d{4}-\d{2}-\d{2}$/.test(d.read_back)) return `Confirmed ${d.read_back}`;
  if (d.read_back === "pending") return "waiting to be read back";
  return d.inherited ? "Inherited, never read back" : "not read back";
}

// Titles identify decisions on this page; ids stay in attributes and requests.
const ID = /\bD-[0-7][0-9A-HJKMNP-TV-Z]{25}\b/g;

function titles() {
  const e = state.entry, found = new Map();
  const seen = [...(state.loaded?.decisions ?? []), ...(state.loaded?.queue ?? []),
    ...(e ? [e, ...e.links.map((l) => ({ id: l.id, title: l.title })), ...e.linked_from.map((l) => ({ id: l.id,
      title: l.title })), ...e.rivals] : [])];
  for (const d of seen) if (d.title && d.title !== "not in this view") found.set(d.id, d.title);
  return found;
}

export function untagged(text = "") {
  const known = titles();
  return String(text).replace(ID, (id) => (known.has(id) ? `“${known.get(id)}”` : "a decision"));
}
