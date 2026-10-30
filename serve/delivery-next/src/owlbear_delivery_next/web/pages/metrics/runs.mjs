import { html, nothing } from "/assets/lit-html/3.3.3/lit-html.js";
import { call } from "/assets/ui.mjs";
import { query, show, state } from "./state.mjs";

export const credits = (n) => n.toFixed(2);
export const count = (n) => n.toLocaleString();
const NUMBERS = ["Credits", "Runs", "Unknown", "Tokens", "Share"];  // columns of numbers, aligned under their headers
export const head = (h) =>
  html`<p-table-head-cell class=${NUMBERS.includes(h) ? "num" : nothing}>${h}</p-table-head-cell>`;
const plural = (n, one, many = `${one}s`) => `${count(n)} ${n === 1 ? one : many}`;

async function more() {
  const reading = state.reading, asked = query(state.next);  // the list it continues
  state.more = true;
  show();
  try {
    const data = await call(asked, { machine: true, timeout: 30000 });
    if (reading !== state.reading) return;  // the filters changed meanwhile: it continues a list no longer shown
    state.runs = [...state.runs, ...data.runs.items];
    state.next = data.runs.next;
  } catch (error) {
    if (reading !== state.reading) return;
    state.error = error.message;
  }
  state.more = false;
  show();
}

// Consecutive runs of one agent and job, newest first: a "Show more" extends the last (D-01M63CEQYQ64VYQHFKCDGX7W9F).
function folds(runs) {
  const out = [];
  for (const r of runs) {
    const last = out.at(-1);
    if (last && last[0].agent === r.agent && last[0].job === r.job) last.push(r);
    else out.push([r]);
  }
  return out;
}

const when = (at) => (at ? new Date(at).toLocaleString() : "Time unknown");
const who = (agent, job) => `${agent || "Agent unknown"}${job ? ` (${job})` : ""}`;
const where = (r) => `${r.change || "Outside a Change"}${r.step ? ` · ${r.step}` : ""}`;
const project = (r) => r.name || "No project";
const models = (r) => r.models.join(", ");
const lower = (r) => r.unknown || r.incomplete || r.open;  // what was read so far; the run spent at least this
const bound = html`<p-tag class="lower" color="background-surface" compact="true">lower bound</p-tag>`;
const one = (rows, said, many) => {
  const kinds = [...new Set(rows.map(said))];
  return kinds.length === 1 ? kinds[0] : `${kinds.length} ${many}`;
};

function stops(rows) {
  const limits = [...new Set(rows.filter((r) => r.stopped).map((r) => `${r.limit != null ? ` of ${r.limit}` : ""}${
    r.stopped_by ? ` (${r.stopped_by})` : ""}`))];
  const of = limits.length === 1 ? limits[0] : "";
  const reached = rows.filter((r) => r.stopped === "reached").length;
  const maybe = rows.filter((r) => r.stopped === "unknown").length;
  const lead = rows.length > 1 ? (n) => `${count(n)} ` : () => "";
  return [
    reached ? html`<p-tag color="notification-warning-soft" compact="true">${lead(reached)}stopped at ${rows.length > 1
      ? "their" : "its"} credit limit${of}</p-tag>` : nothing,
    maybe ? html`<p-tag color="background-surface" compact="true">${lead(maybe)}may have reached ${rows.length > 1
      ? "their" : "its"} credit limit${of}: not known</p-tag>` : nothing,
  ];
}

function ended(rows) {
  const endings = [...new Set(rows.map((r) => r.ending).filter(Boolean))].join(", ");
  const unsure = [...new Set(rows.flatMap((r) => r.uncertain))];
  const tag = unsure.length ? html`<p-tag color="background-surface" compact="true">${unsure
    .map((u) => (u === "at" ? "time uncertain" : "agent uncertain")).join(", ")}</p-tag>` : nothing;
  return html`${endings} ${stops(rows)} ${tag}`;
}

// A lower bound is tagged once on its row; an opened fold's runs only mark theirs with "+" under the fold's tag.
function spent(rows, tagged = true) {
  const tag = tagged ? html`<br>${bound}` : nothing;
  if (rows.length === 1 && rows[0].open) return html`open: no end recorded${tag}`;
  const sum = credits(rows.reduce((s, r) => s + r.credits, 0));
  return rows.some(lower) ? html`${sum}+${tag}` : sum;
}

// A run on its own row, or under its opened fold (*fold*), leaving blank what the fold's row already says.
function runRow(r, fold) {
  const same = (said) => fold && one(fold, said, "") === said(r);
  const helpers = r.subagents.length ? `with ${r.subagents.join(", ")}` : "";
  const agent = fold ? helpers : `${who(r.agent, r.job)}${helpers ? ` ${helpers}` : ""}`;
  return html`<p-table-row class=${fold ? "member" : nothing} data-run=${r.run}>
    <p-table-cell>${when(r.at)}</p-table-cell>
    <p-table-cell>${same(project) ? "" : project(r)}</p-table-cell><p-table-cell>${same(where) ? "" : where(r)}
    </p-table-cell><p-table-cell multiline="true">${agent}</p-table-cell>
    <p-table-cell>${same(models) ? "" : models(r)}</p-table-cell>
    <p-table-cell class="num">${spent([r], !fold)}</p-table-cell>
    <p-table-cell multiline="true">${ended([r])}</p-table-cell>
  </p-table-row>`;
}

// A fold says what its runs share, or how many differ, and opens to list them under it.
function foldRow(rows) {
  const key = rows[0].run, open = state.unfolded.has(key), newest = rows[0], oldest = rows.at(-1);
  const toggle = () => {
    if (open) state.unfolded.delete(key);
    else state.unfolded.add(key);
    show();
  };
  const helpers = [...new Set(rows.flatMap((r) => r.subagents))];
  return html`<p-table-row class="fold" data-runs=${rows.length}>
    <p-table-cell>${when(newest.at)}<br><p-text size="xs" color="contrast-medium">from ${when(oldest.at)}</p-text>
    </p-table-cell>
    <p-table-cell>${one(rows, project, "projects")}</p-table-cell>
    <p-table-cell>${one(rows, where, "Changes")}</p-table-cell>
    <p-table-cell multiline="true"><p-button-pure size="sm" @click=${toggle}
      icon=${open ? "arrow-head-down" : "arrow-head-right"} aria=${`{ 'aria-expanded': ${open} }`}>${
        who(newest.agent, newest.job)} · ${plural(rows.length, "run")}
      </p-button-pure>${helpers.length ? ` with ${helpers.join(", ")}` : ""}</p-table-cell>
    <p-table-cell>${[...new Set(rows.flatMap((r) => r.models))].join(", ")}</p-table-cell>
    <p-table-cell class="num">${spent(rows)}</p-table-cell>
    <p-table-cell multiline="true">${ended(rows)}</p-table-cell></p-table-row>
    ${open ? rows.map((r) => runRow(r, rows)) : nothing}`;
}

export function runs() {
  const total = state.data.runs.total, heads = ["When", "Project", "Change", "Agent", "Models", "Credits", "Ended"];
  const shown = state.runs.length;
  const lowerNote = state.runs.some(lower) ? html`<p-text id="lower-bound" size="sm">A run tagged
    <strong>lower bound</strong>, its credits marked +, spent at least this: some of its credits were not reported,
    its last read failed, or it has no end recorded yet.</p-text>` : nothing;
  return html`<section aria-labelledby="runs-title">
    <p-heading size="lg"><h2 id="runs-title">Runs, newest first</h2></p-heading>
    <p-text id="runs-count" size="sm">${shown < total ? `The newest ${shown} of ${total} runs.` : `All ${total} runs.`}
      A run counts on the day it ended. Consecutive runs of one agent and job share a row that opens.</p-text>
    ${shown ? html`<p-table id="runs" caption="Runs"><p-table-head><p-table-head-row>
      ${heads.map(head)}</p-table-head-row></p-table-head>
      <p-table-body>${folds(state.runs).map((f) => (f.length > 1 ? foldRow(f) : runRow(f[0])))}</p-table-body>
      </p-table>` : nothing}
    ${lowerNote}
    ${state.next != null ? html`<div><p-button id="more" type="button" compact="true" variant="secondary"
      .loading=${state.more} @click=${more}>Show more runs</p-button></div>` : nothing}
  </section>`;
}
