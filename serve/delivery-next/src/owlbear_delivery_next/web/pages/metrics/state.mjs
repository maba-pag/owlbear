import { render } from "/assets/lit-html/3.3.3/lit-html.js";
import { here, project } from "/assets/ui.mjs";
import { view } from "./view.mjs";

export const PERIODS = [["today", "Today"], ["7", "Last 7 days"], ["30", "Last 30 days"], ["month", "This month"],
  ["last-month", "Last month"], ["all", "All time"], ["custom", "Chosen dates"]];
export const SPLITS = [["agent", "Agent"], ["project", "Project"], ["model", "Model"], ["day", "Day"],
  ["change", "Change"], ["step", "Step"]];
export const ZONE = Intl.DateTimeFormat().resolvedOptions().timeZone || "UTC";

// The filters, kept in the address so a reload or a link shows the same: the ledger's own project key is ?in=,
// apart from the bar's ?project=, which picks a clone; the bar's clone only preselects its project once.
const q = new URLSearchParams(location.search);
export const filter = {
  period: q.get("period") || "30", from: q.get("from") || "", to: q.get("to") || "", in: q.get("in") ?? "",
  agent: q.get("agent") || "", model: q.get("model") || "", change: q.get("change") || "",
  stopped: q.get("stopped") === "1", by: q.get("by") || "agent",
};
export const state = { data: null, error: "", reading: 0, runs: [], next: null, more: false, picked: !!q.get("in") };

export function show() {
  render(view(), document.getElementById("page"));
}

export function kept() {
  history.replaceState(null, "", here({ period: filter.period, from: filter.period === "custom" ? filter.from : "",
    to: filter.period === "custom" ? filter.to : "", in: filter.in, agent: filter.agent, model: filter.model,
    change: filter.change, stopped: filter.stopped ? "1" : "", by: filter.by }));
}

function day(d) {
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}

// The period as the half-open range [from, to) of local dates the host takes; empty ends are open.
export function range(now = new Date()) {
  const y = now.getFullYear(), m = now.getMonth(), d = now.getDate();
  const at = (yy, mm, dd) => day(new Date(yy, mm, dd));
  switch (filter.period) {
    case "today": return [at(y, m, d), at(y, m, d + 1)];
    case "7": return [at(y, m, d - 6), at(y, m, d + 1)];
    case "30": return [at(y, m, d - 29), at(y, m, d + 1)];
    case "month": return [at(y, m, 1), at(y, m + 1, 1)];
    case "last-month": return [at(y, m - 1, 1), at(y, m, 1)];
    case "custom": {
      const to = /^\d{4}-\d{2}-\d{2}$/.test(filter.to) ? filter.to.split("-").map(Number) : null;
      return [filter.from, to ? at(to[0], to[1] - 1, to[2] + 1) : ""];  // the last day chosen is included
    }
    default: return ["", ""];
  }
}

// The query for the host: the filters, the range and this browser's time zone.
export function query(cursor = 0) {
  const [from, to] = range();
  const p = new URLSearchParams({ tz: ZONE, by: filter.by });
  for (const [k, v] of Object.entries({ from, to, project: filter.in, agent: filter.agent, model: filter.model,
    change: filter.change, stopped: filter.stopped ? "true" : "", cursor: cursor ? String(cursor) : "" })) {
    if (v) p.set(k, v);
  }
  return `/metrics?${p}`;
}

// The bar's clone picks its project's key the first time the page loads with ?project= and no ?in=.
export function preselect(choices) {
  if (state.picked || !project) return;
  state.picked = true;
  if (choices.clones?.[project]) filter.in = choices.clones[project];
}
