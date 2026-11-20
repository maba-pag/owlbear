// Context at start: per Delivery role, what filled its latest measured session's context after the first model call,
// a vertical bar per role stacked by part, scaled to the largest total shown; labels give the share of its window.
import { html, nothing } from "/assets/lit-html/3.3.3/lit-html.js";
import { draw } from "./chart.mjs";
import { folded } from "./fold.mjs";
import { count } from "./runs.mjs";
import { keysHint, lengthSwitch, stacked } from "./stacked.mjs";
import { query, show } from "./state.mjs";

const PARTS = [["system_prompt", "System prompt"], ["custom_instructions", "Custom instructions"],
  ["skills", "Skills"], ["subagents", "Subagents"], ["built_in_tools", "Built-in tools"], ["mcp_tools", "MCP tools"],
  ["messages", "Messages"]];
const MESSAGES = "Messages hold the task message and the first answer.";
const pick = { relative: false };

const esc = (text) => globalThis.echarts.format.encodeHTML(String(text));

/** A token count in short: 870, 4.5k, 43k, 1.2M. */
export function tokens(n) {
  const short = (v, unit) => `${v < 10 ? Number(v.toFixed(1)) : Math.round(v)}${unit}`;
  if (n >= 1e6) return short(n / 1e6, "M");
  if (n >= 1e3) return short(n / 1e3, "k");
  return count(n);
}

// A session's total and its share of the selected window: "43k, 4.5% of 952k".
function said(m) {
  if (!m.window) return tokens(m.total);
  const pct = (m.total / m.window) * 100;
  return `${tokens(m.total)}, ${pct > 0 && pct < 0.1 ? "<0.1" : Number(pct.toFixed(1))}% of ${tokens(m.window)}`;
}

const ran = (m) => (m.at ? new Date(m.at).toLocaleString() : "an unknown time");
const measured = (c) => (c?.roles ?? []).filter((r) => r.latest);

// A recorded “kept” note in the page's words: which skill or subagent tokens are still counted in another part.
const KIND = { skills: ["skill", "Skills"], subagents: ["subagent", "Subagents"] };
const kind = (part) => KIND[part] ?? [part, part];
const KEPT = [
  [/^(\w+): (\d+) tokens stay in their category, which nesting does not name$/, (part, n) =>
    `${tokens(+n)} ${kind(part)[0]} tokens are counted in one of the other parts, not in ${kind(part)[1]}: the
    attribution does not say which part holds them`],
  [/^(\w+): (\d+) tokens stay in their category, which holds fewer$/, (part, n) =>
    `${tokens(+n)} ${kind(part)[0]} tokens stay counted in the part that holds them, not in ${kind(part)[1]}: that part
    reports fewer tokens than they need`],
  [/^(\w+): the preloaded (.+) stay in their category, which the attribution does not itemize$/, (part, names) =>
    `the preloaded ${names} are counted in one of the other parts, not in ${kind(part)[1]}: the attribution does not list
    them`],
];
const keptSaid = (text) => text.split("; ").map((one) => {
  for (const [shape, say] of KEPT) {
    const m = one.match(shape);
    if (m) return say(...m.slice(1));
  }
  return one;
}).join("; ");

// The notes under the chart, as one list: kinds still counted in another part, and the sessions without a
// measurement with why (each failed read with its error; the others ran before measuring).
function notes(c, kept) {
  const errors = c.roles.flatMap((r) => r.errors.map((e) => ({ ...e, role: r.role })));
  const failed = new Set(errors.map((e) => e.session)).size, before = c.unmeasured - failed;
  const sessions = (n) => `${count(n)} session${n === 1 ? "" : "s"}`;
  const why = [before ? `${count(before)} ran before this release` : "",
    failed ? `${count(failed)} failed to read` : ""].filter(Boolean);
  if (!kept.length && !c.unmeasured) return nothing;
  return html`<p-heading size="md"><h3 id="context-notes-title">About these numbers</h3></p-heading>
    <ul id="context-notes" class="notes" aria-labelledby="context-notes-title">
    ${kept.map((r) => html`<li class="kept">${r.role}: ${keptSaid(r.latest.kept)}.</li>`)}
    ${c.unmeasured ? html`<li id="context-unmeasured">${sessions(c.unmeasured)} in these filters
      ${c.unmeasured === 1 ? "has" : "have"} no measurement:
      ${why.join(", ")}.${errors.length ? html`<ul id="context-errors" class="notes">${errors.map((e) =>
        html`<li class="error">Could not read the context of ${e.role}'s session ${e.session}${e.at
          ? ` at ${new Date(e.at).toLocaleString()}` : ""}:<span class="why">${e.error}</span></li>`)}</ul>`
        : nothing}</li>` : nothing}
    </ul>`;
}

function row(r) {
  const m = r.latest;
  return html`<p-table-row><p-table-cell>${r.role}</p-table-cell>
    ${PARTS.map(([k]) => html`<p-table-cell class="num">${count(m.parts?.[k] ?? 0)}</p-table-cell>`)}
    <p-table-cell class="num">${count(m.total)}</p-table-cell>
    <p-table-cell class="num">${said(m)}</p-table-cell>
    <p-table-cell>${m.model || "–"}</p-table-cell><p-table-cell>${ran(m)}</p-table-cell></p-table-row>`;
}

/** The section: the chart's switch and keys, its folded table, or a notice; notes on its numbers. */
export function contextAtStart(c) {
  if (!c) return nothing;
  const rows = measured(c), kept = rows.filter((r) => r.latest.kept);
  const heads = ["Role", ...PARTS.map(([, h]) => h), "Total", "Share of window", "Model", "Ran"];
  return html`<section id="context" aria-labelledby="context-title">
    <p-heading size="lg"><h2 id="context-title">Context at start</h2></p-heading>
    <p-text size="sm">Each role's latest measured session after its first model call, on one shared scale; labels
      give the share of its window.</p-text>
    ${rows.length ? html`<div id="context-controls" class="row">${lengthSwitch(pick.relative, (on) => {
      pick.relative = on;
      show();
    })}</div>${keysHint}
    ${folded("context", "Table: context at start per role", html`<p-table id="context-table"
      caption="Context at start per role, in tokens"><p-table-head><p-table-head-row>${heads.map((h, i) =>
        html`<p-table-head-cell class=${i && i < 10 ? "num" : nothing}>${h}</p-table-head-cell>`)}</p-table-head-row>
      </p-table-head><p-table-body>${rows.map(row)}</p-table-body></p-table>`)}`
      : html`<p-text id="context-none" size="sm">No session in these filters has a context measurement.</p-text>`}
    ${notes(c, kept)}
  </section>`;
}

/** Draws the chart: a vertical bar per measured role, stacked by part; a click or Enter calls *pick* with its role. */
export function contextChart(c, choose) {
  const rows = measured(c);
  if (!rows.length) return draw("context", null);
  const m = rows.map((r) => r.latest);
  const spec = stacked({
    labels: rows.map((r) => r.role), totals: m.map((x) => x.total), format: tokens, horizontal: false,
    parts: PARTS.map(([k, name]) => ({ id: `context:${k}`, name, values: m.map((x) => x.parts?.[k] ?? 0) })),
    colours: (t) => t.parts, relative: pick.relative, said: (r) => said(m[r]),
    about: (r) => `${esc(m[r].model || "Model unknown")}, ran ${esc(ran(m[r]))}`, note: () => esc(MESSAGES),
  });  // fmt: skip
  draw("context", { ...spec, height: 270, facts: [...spec.facts, m.map((x) => [x.window, x.model, x.at])],
    ids: rows.map((r) => r.role), key: query(), label: "Context at start chart", act: (i) => choose(rows[i].role) });
}
