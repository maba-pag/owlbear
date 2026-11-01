import { render } from "/assets/lit-html/3.3.3/lit-html.js";
import { call } from "/assets/ui.mjs";
import { view } from "./view.mjs";

// The filters of the looks, kept in the address: ?in= is the project's id (?project= is the top row's clone),
// ?change= a Change's slug in it.
const q = new URLSearchParams(location.search);
export const filter = { in: q.get("in") ?? "", change: q.get("change") ?? "" };
// What the page shows: each part as last read, or why it could not be read; the notice of the last action; the
// button running, so no second one starts; the owner's chosen Change to run Retro on, and each case's chosen stage.
export const state = { data: null, error: "", looks: null, looksError: "", notice: null, busy: "", reading: 0,
  retroOn: "", stages: new Map() };

export function show() {
  render(view(), document.getElementById("page"));
}

export function kept() {
  const at = new URL(location.href);
  for (const [k, v] of Object.entries(filter)) {
    if (v) at.searchParams.set(k, v);
    else at.searchParams.delete(k);
  }
  history.replaceState(null, "", at.pathname + at.search + at.hash);
}

function looksQuery() {
  const p = new URLSearchParams();
  if (filter.in) p.set("project", filter.in);
  if (filter.in && filter.change) p.set("change", filter.change);
  return `/improvement/looks${p.size ? `?${p}` : ""}`;
}

// Both reads at once; one that fails keeps what the other found and says why it failed. An older answer never
// replaces a newer one's.
export async function refresh() {
  const reading = ++state.reading;
  const [data, looks] = await Promise.allSettled([call("/improvement", { machine: true, timeout: 30000 }),
    call(looksQuery(), { machine: true, timeout: 30000 })]);
  if (reading !== state.reading) return;
  if (data.status === "fulfilled") [state.data, state.error] = [data.value, ""];
  else state.error = data.reason.message;
  if (looks.status === "fulfilled") [state.looks, state.looksError] = [looks.value, ""];
  else state.looksError = looks.reason.message;
  show();
}

// One action of the owner's, *key* naming its button: the host's answer said in words, or its full error; the page
// is read again either way. A call that may have been done (Slow) is not sent again.
export async function act(key, run, said) {
  if (state.busy) return;
  state.busy = key;
  state.notice = null;
  show();
  try {
    const answer = await run();
    state.notice = { state: "success", text: typeof said === "function" ? said(answer) : said };
  } catch (error) {
    state.notice = { state: "error", text: error.reread ?? error.message };
  }
  state.busy = "";
  await refresh();
}

export function post(path, body) {
  return call(path, { method: "POST", body, machine: true, timeout: 30000 });
}
