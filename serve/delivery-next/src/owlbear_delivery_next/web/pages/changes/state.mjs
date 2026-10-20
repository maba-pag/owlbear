import { html, render } from "/assets/lit-html/3.3.3/lit-html.js";
import { call as host, HostDown, project, Restarted, shown, token } from "/assets/ui.mjs";
import { button } from "./widgets.mjs";
import { youCount, view, refresh } from "./list.mjs";
import { newChange } from "./shaping.mjs";

const TITLE = document.title;
// A Change: its project's id, then its slug (TD-241)
export const KEY = /^(?:[0-9a-f]{16}\/)?[a-z0-9][a-z0-9-]{0,63}$/;
export const DIALOG = "{ 'aria-haspopup': 'dialog' }";  // PDS's aria property, for a button that opens a dialog
export const REVERT = "Reversing the merge needs a revert you make yourself.";
// Everything the page shows comes from here (TD-264): the list and the detail as last read, the owner's unsent input
// per form (drafts: form key -> its fields), which toggles are open (by their summary), and the notes above.
export const state = {
  changes: null, detail: null, notes: [], selected: null, started: null, error: null, seen: "",
  stale: false, refused: null, drafts: new Map(), opened: new Set(), doneOpen: false, creating: false,
  choosing: false,
};
// The page's other mutable values, in an object since a module cannot reassign another's binding.
export const page = { busy: false, again: false, lastSeen: null, arrived: false };

export function show() {
  const focused = document.activeElement;
  render(view(), document.getElementById("page"));
  render(button("New Change", newChange, { icon: "add", aria: DIALOG, busy: state.creating }),
    document.getElementById("header-actions"));
  const modal = [...document.querySelectorAll("p-modal")].some((m) => m.open);
  if (focused?.isConnected && document.activeElement !== focused && !modal) {
    focused.focus({ preventScroll: true });
  }
  document.title = youCount() ? `(${youCount()}) ${TITLE}` : TITLE;
}

// One call to the project *of* (this page's by default); a Change's own calls name its project.
export function call(path, body, of = project) {
  return host(path, body === undefined ? { of } : { body, of });
}

// The key of a Change in the page: its project's id and slug, so two projects' Changes of one slug stay apart.
export function keyOf(of, slug) {
  return of ? `${of}/${slug}` : slug;
}

export function parts(key) {
  const at = key.indexOf("/");
  return at < 0 ? [project, key] : [key.slice(0, at), key.slice(at + 1)];
}

export function several() {
  return (shown()?.length ?? 0) > 1;
}

export function draft(key, fresh) {
  if (!state.drafts.has(key)) state.drafts.set(key, fresh());
  return state.drafts.get(key);
}

function unreachable(e) {
  state.error = e instanceof Restarted
    ? html`Delivery restarted at a new address — open the link from chat or <code>owlbear status</code>.`
    : html`Delivery is not running. Start it with <code>owlbear start</code>, then reload this page.`;
  state.stale = true;
  if (page.lastSeen) state.seen = `last seen ${page.lastSeen.toLocaleTimeString()}`;
}

export function failed(e) {
  if (e instanceof HostDown || e instanceof Restarted) unreachable(e);
  else state.error = token ? e.message : "Open the URL the host printed, including #token=…";
  show();
}

export function notify(message) {
  state.error = message;
  show();
}

// The forms the detail shows, as a key: a refusal stays beside them until they change.
export function formsOf(d) {
  const r = d.visual_round, asked = d.checks.filter((c) => c.waiting).map((c) => [c.id, c.url, c.inputs]);
  return JSON.stringify([d.key, d.question?.id, d.question?.options?.map((o) => o.id), d.merge?.head, asked,
    d.brief.version, d.brief.approved, d.pullback?.state, d.paused, r?.number, r?.outcome,
    d.owner_criteria.map((k) => k.id), d.retry?.attempt, d.retry?.head]);
}

// One action of the owner on the shown Change. A refusal goes beside the form that was used (*form*), so it is seen
// where he is looking; the poll keeps it until the forms change. True once the host took it.
export async function send(path, body, d, form = "") {
  try {
    await call(`/changes/${d.slug}${path}`, body, d.project);
  } catch (e) {
    if (e instanceof HostDown || e instanceof Restarted || state.selected !== d.key) return failed(e) && false;
    state.refused = { forms: formsOf(d), form, text: e.message };
    show();
    document.querySelector("#detail .refused")?.scrollIntoView({ block: "nearest" });
    return false;
  }
  state.refused = null;
  if (form) state.drafts.delete(form);
  document.activeElement?.blur?.();
  await refresh();
  return true;
}
