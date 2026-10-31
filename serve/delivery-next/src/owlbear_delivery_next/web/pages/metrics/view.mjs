import { html, nothing } from "/assets/lit-html/3.3.3/lit-html.js";
import { live } from "/assets/lit-html/3.3.3/directives/live.js";
import { call } from "/assets/ui.mjs";
import { PERIODS, SPLITS, filter, state, show, kept, query, preselect } from "./state.mjs";
import { credits, count, head, runs } from "./runs.mjs";
import { toolUse } from "./tools.mjs";
import { compaction } from "./compaction.mjs";

const UNKNOWN = "?";
const DRILL = { project: "in", agent: "agent", model: "model", change: "change" };  // a row that filters its value


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

// Spend said apart from the period: unknown credits never read as zero, a partial sum as "or more". A run may have
// spend both inside the period and outside it, so this counts the runs it came from, not runs left out.
function outside(u) {
  if (!u.credits && u.unknown) return "credits not known";
  return `${credits(u.credits)}${u.unknown || u.open || u.incomplete ? " or more" : ""} credits`;
}

// How exact the totals are, each way they may be off said once (D-01M63CEQYQ64VYQHFKCDGX7W9F).
function exactness(t, undated) {
  const runs = (n) => `${count(n)} run${n === 1 ? "" : "s"}`;
  const items = [
    t.unknown ? `${runs(t.unknown)} did not report ${t.unknown === 1 ? "its" : "their"} credits: they count as unknown,
      never as zero, so the total is a lower bound.` : "",
    t.failed ? `${runs(t.failed)} ${t.failed === 1 ? "counts" : "count"} only up to an earlier read, as
      ${t.failed === 1 ? "its" : "their"} last read failed: a lower bound.` : "",
    t.incomplete > t.failed ? `${runs(t.incomplete - t.failed)} ${t.incomplete - t.failed === 1 ? "was" : "were"} read
      while a call could still be billed: a lower bound until OwlBear reads the runtime's own records.` : "",
    t.open ? `${runs(t.open)} started with no end recorded yet: ${t.open === 1 ? "its" : "their"} credits so far
      count.` : "",
    t.uncertain_time ? `${credits(t.uncertain_time)} credits were spent at a time known only roughly, so they may
      belong to a neighbouring day.` : "",
    t.uncertain_agent ? `${credits(t.uncertain_agent)} credits are not split between an agent and its subagents.` : "",
    undated ? `Spend of ${runs(undated.runs)} may also lie in this period (${outside(undated)}): when it was spent is
      not known closely enough to say, so it is not counted.` : "",
  ].filter(Boolean);
  return html`<p-heading size="md"><h3 id="exact-title">How exact these totals are</h3></p-heading>
    <ul id="exact" class="notes" aria-labelledby="exact-title">${items.length ? items.map((i) => html`<li>${i}</li>`)
      : html`<li>Exact: every run reported its credits, at a known time and for a known agent.</li>`}</ul>`;
}

function totals() {
  const { totals: t, undated } = state.data;
  const unknown = t.unknown ? html` <p-text size="sm" color="contrast-medium">plus ${t.unknown} run${
    t.unknown === 1 ? "" : "s"} whose credits were not reported</p-text>` : nothing;
  return html`<section aria-labelledby="totals-title">
    <p-heading size="lg"><h2 id="totals-title">Totals</h2></p-heading>
    <div id="totals">
      <p-text id="total-credits"><strong>${credits(t.credits)}</strong> credits${unknown}</p-text>
      <p-text id="total-runs">${count(t.runs)} run${t.runs === 1 ? "" : "s"}</p-text>
      <p-text id="total-tokens">${count(t.tokens)} tokens, ${count(t.cache)} cached</p-text>
      <p-text id="total-stopped">${count(t.stopped)} stopped at their credit limit${t.stopped_unknown
        ? `, ${count(t.stopped_unknown)} more may have been` : ""}</p-text>
    </div>
    ${exactness(t, undated)}
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

// A row's share of the total as a bar and in words: the bar alone would say nothing to a screen reader or in print.
function share(part, total) {
  if (!total) return "–";
  const pct = (part / total) * 100;
  const said = pct > 0 && pct < 1 ? "<1%" : `${Math.round(pct)}%`;
  return html`<span class="share"><span class="share-track" aria-hidden="true"><span class="share-fill"
    style=${`width: ${Math.min(100, pct)}%`}></span></span>${said}</span>`;
}

function splitRow(row, total) {
  const go = drill(row);
  const name = go ? html`<p-button-pure size="sm" icon="filter" @click=${go}
    aria=${`{ 'aria-label': 'Show only ${row.label.replaceAll("'", "")}' }`}>${row.label}</p-button-pure>`
    : row.label;
  return html`<p-table-row><p-table-cell>${name}</p-table-cell>
    <p-table-cell class="num">${credits(row.credits)}</p-table-cell>
    <p-table-cell class="num">${share(row.credits, total)}</p-table-cell>
    <p-table-cell class="num">${count(row.runs)}</p-table-cell>
    <p-table-cell class="num">${row.unknown || ""}</p-table-cell>
    <p-table-cell class="num">${count(row.tokens)}</p-table-cell></p-table-row>`;
}

function split() {
  const rows = state.data.rows, label = SPLITS.find(([v]) => v === filter.by)?.[1] ?? filter.by;
  const total = state.data.totals.credits;
  const heads = [label, "Credits", "Share", "Runs", "Unknown", "Tokens"];
  return html`<section aria-labelledby="split-title">
    <p-heading size="lg"><h2 id="split-title">By ${label.toLowerCase()}</h2></p-heading>
    ${rows.length ? html`<p-table id="split" caption=${`Credits by ${label.toLowerCase()}`}><p-table-head>
      <p-table-head-row>${heads.map(head)}</p-table-head-row>
      </p-table-head><p-table-body>${rows.map((r) => splitRow(r, total))}</p-table-body></p-table>`
      : html`<p-text id="split-none" size="sm">Nothing was spent that these filters show.</p-text>`}
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
      <li>Not recoverable: sessions OwlBear ran outside a Change before 2026-10-25 (curator, Impeccable, lookups),
        and a Change's events dropped from its activity log beyond its totals.</li>
    </ul>
  </section>`;
}

export function view() {
  const error = state.error ? html`<p-inline-notification id="error" state="error" heading="Not shown"
    description=${state.error} dismiss-button="false"></p-inline-notification>` : nothing;
  if (!state.data) return html`${error}${filters()}<p-text id="loading">Reading the spend…</p-text>`;
  return html`${error}${filters()}${totals()}${split()}${compaction(state.data.compaction)}${runs()}
    ${toolUse(state.data.tool_use)}${coverage()}`;
}
