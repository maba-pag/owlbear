import { html, nothing } from "/assets/lit-html/3.3.3/lit-html.js";
import { live } from "/assets/lit-html/3.3.3/directives/live.js";
import { call } from "/assets/ui.mjs";
import { PERIODS, SPLITS, filter, state, show, kept, query, preselect } from "./state.mjs";
import { toolUse } from "./tools.mjs";

const UNKNOWN = "?";
const DRILL = { project: "in", agent: "agent", model: "model", change: "change" };  // a row that filters its value

const credits = (n) => n.toFixed(2);
const count = (n) => n.toLocaleString();

export async function refresh() {
  const reading = ++state.reading;  // a new list: an older answer, or a "Show more" still pending, is dropped
  state.more = false;
  try {
    const data = await call(query(), { machine: true, timeout: 30000 });
    if (reading !== state.reading) return;
    const before = filter.in;
    preselect(data.choices);
    if (filter.in !== before) return refresh();
    state.data = data;
    state.runs = data.runs.items;
    state.next = data.runs.next;
    state.error = "";
  } catch (error) {
    if (reading !== state.reading) return;
    state.error = error.message;
  }
  show();
  clearTimeout(state.again);  // a reconciling pass is running: look again until it is done
  if (state.data?.coverage.reconcile?.state === "running") state.again = setTimeout(refresh, 3000);
}

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

function changed(apply) {
  return (value) => {
    apply(value);
    kept();
    refresh();
  };
}

function select(label, id, options, value, chosen) {
  return html`<p-select id=${id} label=${label} compact="true" .value=${live(value)}
      @change=${(e) => chosen(e.target.value)}>
    ${options.map(([v, said]) => html`<p-select-option value=${v}>${said}</p-select-option>`)}</p-select>`;
}

// A date as typed: each keystroke is kept, so a re-render meanwhile never loses it; a change applies it.
function dateField(label, id, field) {
  const typed = (e) => { filter[field] = e.target.value ?? ""; };
  return html`<p-input-text id=${id} label=${label} compact="true" max-length="10" placeholder="YYYY-MM-DD"
    .value=${live(filter[field])} @input=${typed} @change=${(e) => changed(() => typed(e))()}></p-input-text>`;
}

function filters() {
  const c = state.data?.choices ?? { projects: [], agents: [], models: [], changes: [] };
  const all = (label) => [["", label]];
  const named = (list, unknown) => list.map((v) => [v, v === UNKNOWN ? unknown : v]);
  const custom = filter.period === "custom" ? html`
    ${dateField("From", "from", "from")}${dateField("To (included)", "to", "to")}` : nothing;
  return html`<div id="filters" class="row" role="group" aria-label="Show only">
    ${select("Period", "period", PERIODS, filter.period, changed((v) => { filter.period = v; }))}${custom}
    ${select("Project", "project", [...all("All projects"), ...c.projects], filter.in,
      changed((v) => { filter.in = v; filter.change = ""; }))}
    ${select("Agent", "agent", [...all("All agents"), ...named(c.agents, "Agent unknown")], filter.agent,
      changed((v) => { filter.agent = v; }))}
    ${select("Model", "model", [...all("All models"), ...named(c.models, "Model unknown")], filter.model,
      changed((v) => { filter.model = v; }))}
    ${select("Change", "change", [...all("All Changes"), ...c.changes.map((k) => [k, k.replace("/", ": ")])],
      filter.change, changed((v) => { filter.change = v; }))}
    ${select("Split by", "by", SPLITS, filter.by, changed((v) => { filter.by = v; }))}
    <p-checkbox id="stopped" label="Only runs stopped at their credit limit" .checked=${live(filter.stopped)}
      @change=${(e) => changed((v) => { filter.stopped = v; })(e.target.checked === true)}></p-checkbox>
  </div>`;
}

function totals() {
  const { totals: t, undated } = state.data;
  const unknown = t.unknown ? html` <p-text size="sm" color="contrast-medium">plus ${t.unknown} run${
    t.unknown === 1 ? "" : "s"} whose credits were not reported</p-text>` : nothing;
  const uncertain = [];
  if (t.uncertain_time) uncertain.push(`${credits(t.uncertain_time)} of them at a time known only roughly`);
  if (t.uncertain_agent) uncertain.push(`${credits(t.uncertain_agent)} not split between an agent and its subagents`);
  if (t.incomplete) uncertain.push(`${t.incomplete} run${t.incomplete === 1 ? "" : "s"} counted up to an earlier read`);
  return html`<section aria-labelledby="totals-title">
    <p-heading size="lg"><h2 id="totals-title">Totals</h2></p-heading>
    <div id="totals">
      <p-text id="total-credits"><strong>${credits(t.credits)}</strong> credits${unknown}</p-text>
      <p-text id="total-runs">${count(t.runs)} run${t.runs === 1 ? "" : "s"}</p-text>
      <p-text id="total-tokens">${count(t.tokens)} tokens, ${count(t.cache)} cached</p-text>
      <p-text id="total-stopped">${count(t.stopped)} stopped at their credit limit${t.stopped_unknown
        ? `, ${count(t.stopped_unknown)} more may have been` : ""}</p-text>
    </div>
    ${uncertain.length ? html`<p-text id="uncertain" size="sm">${uncertain.join("; ")}.</p-text>` : nothing}
    ${undated ? html`<p-text id="undated" size="sm">${credits(undated.credits)} more credits may lie in this period:
      when they were spent is not known closely enough to say.</p-text>` : nothing}
  </section>`;
}

function drill(row) {
  const key = DRILL[filter.by];
  if (filter.by === "day" && row.key !== UNKNOWN) {
    return () => changed(() => { filter.period = "custom"; filter.from = row.key; filter.to = row.key; })();
  }
  if (!key || (filter.by === "change" && row.key === UNKNOWN)) return null;
  return () => changed(() => {
    filter[key] = row.key;
    filter.by = filter.by === "agent" ? "model" : "agent";  // the next useful split of what was picked
  })();
}

function splitRow(row, top) {
  const go = drill(row);
  const name = go ? html`<p-button-pure size="small" icon="filter" @click=${go}
    aria=${`{ 'aria-label': 'Show only ${row.label.replaceAll("'", "")}' }`}>${row.label}</p-button-pure>`
    : row.label;
  const share = top ? Math.round((row.credits / top) * 100) : 0;
  return html`<p-table-row><p-table-cell>${name}</p-table-cell>
    <p-table-cell class="num">${credits(row.credits)}</p-table-cell>
    <p-table-cell><span class="share" style="width: ${share}%; max-width: 8rem"
      aria-hidden="true"></span></p-table-cell>
    <p-table-cell class="num">${count(row.runs)}</p-table-cell>
    <p-table-cell class="num">${row.unknown || ""}</p-table-cell>
    <p-table-cell class="num">${count(row.tokens)}</p-table-cell></p-table-row>`;
}

function split() {
  const rows = state.data.rows, label = SPLITS.find(([v]) => v === filter.by)?.[1] ?? filter.by;
  const top = Math.max(0, ...rows.map((r) => r.credits));
  const heads = [label, "Credits", "", "Runs", "Unknown", "Tokens"];
  return html`<section aria-labelledby="split-title">
    <p-heading size="lg"><h2 id="split-title">By ${label.toLowerCase()}</h2></p-heading>
    ${rows.length ? html`<p-table id="split" caption=${`Credits by ${label.toLowerCase()}`}><p-table-head>
      <p-table-head-row>${heads.map((h) => html`<p-table-head-cell>${h}</p-table-head-cell>`)}</p-table-head-row>
      </p-table-head><p-table-body>${rows.map((r) => splitRow(r, top))}</p-table-body></p-table>`
      : html`<p-text id="split-none" size="sm">Nothing was spent that these filters show.</p-text>`}
  </section>`;
}

function runRow(r) {
  const when = r.at ? new Date(r.at).toLocaleString() : "Time unknown";
  const who = `${r.agent || "Agent unknown"}${r.job ? ` (${r.job})` : ""}${r.subagents.length
    ? ` with ${r.subagents.join(", ")}` : ""}`;
  const spent = r.open ? "open: no end recorded" : r.unknown ? `${credits(r.credits)}+ (not all reported)`
    : r.incomplete ? `${credits(r.credits)}+ (its last read failed)` : credits(r.credits);
  const of = `${r.limit != null ? ` of ${r.limit}` : ""}${r.stopped_by ? ` (${r.stopped_by})` : ""}`;
  const stop = r.stopped === "reached" ? html`<p-tag color="notification-warning-soft" compact="true">stopped at its
    credit limit${of}</p-tag>` : r.stopped === "unknown" ? html`<p-tag color="background-surface" compact="true">may
    have reached its credit limit${of}: not known</p-tag>` : nothing;
  const unsure = r.uncertain.length ? html`<p-tag color="background-surface" compact="true">${r.uncertain
    .map((u) => (u === "at" ? "time uncertain" : "agent uncertain")).join(", ")}</p-tag>` : nothing;
  return html`<p-table-row><p-table-cell>${when}</p-table-cell><p-table-cell>${r.name || "No project"}</p-table-cell>
    <p-table-cell>${r.change || ""}${r.step ? ` · ${r.step}` : ""}</p-table-cell><p-table-cell>${who}</p-table-cell>
    <p-table-cell>${r.models.join(", ")}</p-table-cell><p-table-cell class="num">${spent}</p-table-cell>
    <p-table-cell>${r.ending || ""} ${stop} ${unsure}</p-table-cell></p-table-row>`;
}

function runs() {
  const total = state.data.runs.total, heads = ["When", "Project", "Change", "Agent", "Models", "Credits", "Ended"];
  const shown = state.runs.length;
  return html`<section aria-labelledby="runs-title">
    <p-heading size="lg"><h2 id="runs-title">Runs, newest first</h2></p-heading>
    <p-text id="runs-count" size="sm">${shown < total ? `The newest ${shown} of ${total} runs.` : `All ${total} runs.`}
      A run counts on the day it ended.</p-text>
    ${shown ? html`<p-table id="runs" caption="Runs"><p-table-head><p-table-head-row>
      ${heads.map((h) => html`<p-table-head-cell>${h}</p-table-head-cell>`)}</p-table-head-row></p-table-head>
      <p-table-body>${state.runs.map(runRow)}</p-table-body></p-table>` : nothing}
    ${state.next != null ? html`<div><p-button id="more" type="button" compact="true" variant="secondary"
      .loading=${state.more} @click=${more}>Show more runs</p-button></div>` : nothing}
  </section>`;
}

const SOURCES = { recorded: "recorded as they ran", "import:activity": "Changes' step events",
  "import:change": "Changes' totals", "import:spotter": "Spotter records", "import:runtime-log": "runtime logs" };

function coverage() {
  const c = state.data.coverage, r = c.reconcile ?? {};
  const since = c.recorded_since ? new Date(c.recorded_since).toLocaleDateString() : null;
  const sources = Object.entries(c.sources).map(([k, v]) => `${SOURCES[k] ?? k} ${credits(v)}`).join(", ");
  const pass = r.state === "running" ? `Reading earlier records: ${r.done ?? 0} of ${r.sources ?? "?"} sources done.`
    : r.state === "done" ? `Earlier records last read ${new Date(r.finished).toLocaleString()}.`
      : "Earlier records are not read yet.";
  return html`<section aria-labelledby="coverage-title">
    <p-heading size="lg"><h2 id="coverage-title">What is covered</h2></p-heading>
    <ul id="coverage" class="notes">
      <li>${since ? `Runs recorded as they ran since ${since}.` : "No run was recorded as it ran yet."}
        ${sources ? `All time, by source: ${sources}.` : ""}</li>
      <li id="reconcile">${pass}</li>
      ${c.open ? html`<li id="open">${c.open} run${c.open === 1 ? "" : "s"} started with no end recorded yet; a
        later run of the same session, or the runtime's log, accounts for it.</li>` : nothing}
      ${c.unknown ? html`<li>${c.unknown} run${c.unknown === 1 ? "" : "s"} whose credits were not reported count as
        unknown, never as zero.</li>` : nothing}
      ${(r.errors ?? []).map((e) => html`<li class="error">Could not read: ${e}</li>`)}
      <li>Not recoverable: sessions OwlBear ran outside a Change before 2026-10-25 (curator, design pack, lookups),
        and a Change's events dropped from its activity log beyond its totals.</li>
    </ul>
  </section>`;
}

export function view() {
  const error = state.error ? html`<p-inline-notification id="error" state="error" heading="Not shown"
    description=${state.error} dismiss-button="false"></p-inline-notification>` : nothing;
  if (!state.data) return html`${error}${filters()}<p-text id="loading">Reading the spend…</p-text>`;
  return html`${error}${filters()}${totals()}${split()}${runs()}${toolUse(state.data.tool_use)}${coverage()}`;
}
