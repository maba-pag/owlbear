import { html, nothing } from "/assets/lit-html/3.3.3/lit-html.js";

const COLUMNS = [["calls", "Calls"], ["success", "Success %"], ["invalid", "Invalid arguments"],
  ["checks", "Failed checks"], ["order", "Wrong moment"], ["unsplit", "Refused, not split"], ["lint", "Lint"],
  ["late", "Late"], ["retries", "Retries"]];
const WRONG = [["order", "call at the wrong moment", "calls at the wrong moment"],
  ["denied", "denial by the guard", "denials by the guard"], ["no_result", "turn ended without a result",
    "turns ended without a result"], ["missing_pointless", "pointless missing-tool report",
    "pointless missing-tool reports"]];

const cell = (row, key) => key === "success" ? (row.success == null ? "–" : `${row.success}%`)
  : row[key].toLocaleString();

function row(name, r, columns) {
  return html`<p-table-row><p-table-cell>${name}</p-table-cell>${columns.map(([k]) =>
    html`<p-table-cell class="num">${cell(r, k)}</p-table-cell>`)}</p-table-row>`;
}

/** Tool use across Changes: one row per tool, the totals and the wrong tool choices, for the page's filters. */
export function toolUse(t) {
  const columns = COLUMNS.filter(([k]) => k !== "unsplit" || t.totals.unsplit);
  const since = t.since ? new Date(t.since).toLocaleDateString() : null;
  const wrong = WRONG.map(([k, one, many]) => [t.wrong[k] ?? 0, t.wrong[k] === 1 ? one : many]);
  return html`<section id="tool-use" aria-labelledby="tool-use-title">
    <p-heading size="lg"><h2 id="tool-use-title">Tool use</h2></p-heading>
    ${t.runs ? html`<p-table id="tools" caption="Calls of Delivery's tools"><p-table-head><p-table-head-row>
      <p-table-head-cell>Tool</p-table-head-cell>${columns.map(([, h]) =>
        html`<p-table-head-cell class="num">${h}</p-table-head-cell>`)}</p-table-head-row></p-table-head>
      <p-table-body>${t.tools.map((r) => row(r.tool, r, columns))}${row("All tools", t.totals, columns)}</p-table-body>
      </p-table>
      <p-heading size="md"><h3 id="wrong-title">Wrong tool choices</h3></p-heading>
      <ul id="wrong" class="notes" aria-labelledby="wrong-title">${wrong.map(([n, label]) =>
        html`<li>${n.toLocaleString()} ${label}</li>`)}</ul>`
      : html`<p-text id="tool-use-none" size="sm">No tool use was measured for these filters.</p-text>`}
    <p-text id="tool-use-coverage" size="sm" color="contrast-medium">${since
      ? `Counted for ${t.runs.toLocaleString()} run${t.runs === 1 ? "" : "s"}; measured since ${since}.`
      : "No run has measured its tool use yet."} Runs before this release, and runs known only from logs or imported
      records, carry no tool use. Success counts every call that was accepted; a guard's denial of a bypass attempt is
      not a wrong choice; tool use belongs to a run's main agent, so a subagent shows none.</p-text>
  </section>`;
}
