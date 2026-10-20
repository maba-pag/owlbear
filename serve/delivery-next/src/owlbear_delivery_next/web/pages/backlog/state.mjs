import { render } from "/assets/lit-html/3.3.3/lit-html.js";
import { view } from "./view.mjs";

export const KINDS = ["untriaged", "defect", "improvement", "idea", "question"];
export const SOURCES = { owner: "you", watcher: "the watcher", assistant: "the assistant", review: "a review",
  run: "a run" };
export const TAGS = { untriaged: "secondary", defect: "error", improvement: "info", idea: "success",
  question: "warning" };
export const DIALOG = "{ 'aria-haspopup': 'dialog' }";
export const GET = 15000, WRITE = 60000;  // reads and writes go to GitHub's issues, a network round trip or several
// Everything the page shows comes from here, so a re-render never loses what the person typed, ticked or opened.
export const state = {
  loaded: null, error: "", status: "", started: null, creating: false, adding: false,
  idea: { title: "", text: "", clone: "" },  // the Add an idea form, and the clone it is found in
  choosing: null,  // the entries a Change starts from while the owner picks its clone
  notes: new Map(),  // entry key -> notes typed and not saved yet (an entry's key: its repository and number)
  linkTo: new Map(),  // entry key -> the entry chosen in its "Link to another entry" list
  selected: new Set(), opened: new Set(),
};
// projects: all, global, untriaged or a folder, kept in ?show=; "" until loaded, then the page's project's folder
export const filter = { projects: new URLSearchParams(location.search).get("show") ?? "", kind: "all" };

export function show() {
  const focused = document.activeElement;
  render(view(), document.getElementById("page"));
  if (focused?.isConnected && document.activeElement !== focused) focused.focus();
}

export function notify(message = "") {
  state.error = message ? message.charAt(0).toUpperCase() + message.slice(1) : "";
  show();
}
