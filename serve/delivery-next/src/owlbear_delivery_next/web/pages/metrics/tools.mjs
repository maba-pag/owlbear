import { html, nothing } from "/assets/lit-html/3.3.3/lit-html.js";
import { draw } from "./chart.mjs";
import { folded } from "./fold.mjs";
import { count } from "./runs.mjs";
import { keysHint, lengthSwitch, stacked } from "./stacked.mjs";
import { query, show } from "./state.mjs";

const COLUMNS = [["calls", "Calls"], ["success", "Success %"], ["invalid", "Invalid arguments"],
  ["checks", "Failed checks"], ["order", "Wrong moment"], ["unsplit", "Refused, not split"], ["lint", "Lint"],
  ["late", "Late"], ["retries", "Retries"]];
const WRONG = [["order", "call at the wrong moment", "calls at the wrong moment"],
  ["denied", "denial by the guard", "denials by the guard"], ["no_result", "turn ended without a result",
    "turns ended without a result"], ["missing_pointless", "pointless missing-tool report",
    "pointless missing-tool reports"]];

// The seven disjoint outcomes of a tool's calls, as the chart stacks them; they add up to its calls.
const OUTCOMES = [["accepted", "accepted"], ["invalid", "invalid arguments"], ["checks", "failed checks"],
  ["order", "wrong moment"], ["unsplit", "refused not split"], ["lint", "held by lint"], ["late", "late"]];
const REFUSED = [0, 1, 3, 4, 5, 6];  // the Okabe-Ito parts of the six refusal kinds: bluish green is left to accepted
const pick = { relative: false, marked: null };  // marked: the tool a click marked, under the filters it was made at

const cell = (row, key) => key === "success" ? (row.success == null ? "–" : `${row.success}%`)
  : row[key].toLocaleString();

function row(name, r, columns) {
  const marked = pick.marked?.key === query() && pick.marked.tool === name && name === r.tool;
  return html`<p-table-row data-tool=${r.tool ?? nothing} class=${marked ? "marked" : nothing}>
    <p-table-cell>${name}</p-table-cell>${columns.map(([k]) =>
    html`<p-table-cell class="num">${cell(r, k)}</p-table-cell>`)}</p-table-row>`;
}

/** Tool use across Changes: one row per tool, the totals and the wrong tool choices, for the page's filters. */
export function toolUse(t) {
  const columns = COLUMNS.filter(([k]) => k !== "unsplit" || t.totals.unsplit);
  const since = t.since ? new Date(t.since).toLocaleDateString() : null;
  const wrong = WRONG.map(([k, one, many]) => [t.wrong[k] ?? 0, t.wrong[k] === 1 ? one : many]);
  return html`<section id="tool-use" aria-labelledby="tool-use-title">
    <p-heading size="lg"><h2 id="tool-use-title">Tool use</h2></p-heading>
    ${t.runs && t.tools.length ? html`<div id="tools-controls" class="row">${lengthSwitch(pick.relative, (on) => {
      pick.relative = on;
      show();
    })}</div>${keysHint}` : nothing}
    ${t.runs ? folded("tools", "Table: calls per tool", html`<p-table id="tools" caption="Calls of Delivery's tools">
      <p-table-head><p-table-head-row>
      <p-table-head-cell>Tool</p-table-head-cell>${columns.map(([, h]) =>
        html`<p-table-head-cell class="num">${h}</p-table-head-cell>`)}</p-table-head-row></p-table-head>
      <p-table-body>${t.tools.map((r) => row(r.tool, r, columns))}${row("All tools", t.totals, columns)}</p-table-body>
      </p-table>
      <p-heading size="md"><h3 id="wrong-title">Wrong tool choices</h3></p-heading>
      <ul id="wrong" class="notes" aria-labelledby="wrong-title">${wrong.map(([n, label]) =>
        html`<li>${n.toLocaleString()} ${label}</li>`)}</ul>`)
      : html`<p-text id="tool-use-none" size="sm">No tool use was measured for these filters.</p-text>`}
    <p-text id="tool-use-coverage" size="sm" color="contrast-medium">${since
      ? `Counted for ${t.runs.toLocaleString()} run${t.runs === 1 ? "" : "s"}; measured since ${since}.`
      : "No run has measured its tool use yet."} Runs before this release, and runs known only from logs or imported
      records, carry no tool use. Success counts every call that was accepted; a guard's denial of a bypass attempt is
      not a wrong choice; tool use belongs to a run's main agent, so a subagent shows none.</p-text>
  </section>`;
}

/** Draws the tool-use chart: a bar per tool, stacked by outcome; a click opens the table and marks the tool's row. */
export function toolsChart(t) {
  const tools = t?.runs ? t.tools : [];
  if (!tools.length) return draw("tools", null);
  const kept = OUTCOMES.map((o, j) => [...o, j]).filter(([k]) => tools.some((r) => r[k]));
  const spec = stacked({
    labels: tools.map((r) => r.tool), totals: tools.map((r) => r.calls), format: count, horizontal: true,
    parts: kept.map(([k, name]) => ({ id: `tool:${k}`, name, values: tools.map((r) => r[k]) })),
    colours: (th) => kept.map(([, , j]) => (j ? th.parts[REFUSED[j - 1]] : th.success)), relative: pick.relative,
  });  // fmt: skip
  draw("tools", { ...spec, ids: tools.map((r) => r.tool), key: query(), label: "Tool use chart", act: (i) => open(tools[i].tool) });
}

function open(tool) {
  pick.marked = { key: query(), tool };
  show();
  document.getElementById("tools-fold").open = true;
  document.querySelector(`#tools p-table-row[data-tool="${CSS.escape(tool)}"]`)?.scrollIntoView({ block: "center" });
}
