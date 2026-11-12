import { html, nothing } from "/assets/lit-html/3.3.3/lit-html.js";
import { here } from "/assets/ui.mjs";
import { draw } from "./chart.mjs";
import { folded } from "./fold.mjs";
import { query } from "./state.mjs";

const HEADS = ["Agent", "Project", "Sessions", "Compacted", "Compactions", "How early (median)", "Earliest",
  "Context setting"];
const LAYERS = { project: "project layer", machine: "This machine", global: "Global" };

const percent = (share) => `${Math.round(share * 100)}%`;

function sessions(r) {
  const more = [r.missing ? `${r.missing.toLocaleString()} without a log` : "",
    r.unreadable ? `${r.unreadable.toLocaleString()} unreadable` : ""].filter(Boolean);
  return [r.sessions.toLocaleString(), ...more].join(" · ");
}

// A link to where the role's context is set, on the project and layer whose value applies, or why there is none.
function setting(role, e) {
  if (e.why) return html`<span>${e.name}: ${e.why}</span>`;
  const text = `${e.project ? `${e.name}: ` : ""}${LAYERS[e.layer]}${e.unset ? " (unset)" : ""}`;
  const back = `${location.pathname}${location.search}#compaction`;
  return html`<a href=${here({ project: e.clone, layer: e.layer, back }, `/config#set-agents-${role}`)}
    aria-label=${`${text}, ${role}'s context setting`}>${text}</a>`;
}

const named = (r) => (r.subagent ? `${r.subagent} (subagent of ${r.agent})` : r.agent);
const place = (r) => (r.project === null ? "All projects" : r.project === "" ? "This machine" : r.name || r.project);

function row(r) {
  const agent = named(r), where = place(r);
  const links = r.subagent ? "–" : html`${r.settings.map((e, i) => html`${i ? html`<br>` : nothing}${setting(r.agent,
    e)}`)}`;
  return html`<p-table-row><p-table-cell>${agent}</p-table-cell><p-table-cell>${where}</p-table-cell>
    <p-table-cell class="num">${sessions(r)}</p-table-cell>
    <p-table-cell class="num">${r.logs ? `${r.compacted} of ${r.logs} (${percent(r.compacted / r.logs)})` : "–"}
    </p-table-cell>
    <p-table-cell class="num">${r.compactions.toLocaleString()}</p-table-cell>
    <p-table-cell class="num">${r.median == null ? "–" : `${percent(r.median)} of its model calls`}</p-table-cell>
    <p-table-cell class="num">${r.earliest == null ? "–" : percent(r.earliest)}</p-table-cell>
    <p-table-cell>${links}</p-table-cell></p-table-row>`;
}

/** Per agent, how often its sessions compacted their context and how early, with links to its context setting. */
export function compaction(c) {
  const read = c.rows.some((r) => r.logs), errors = c.errors.length || c.settings_errors.length;
  return html`<section id="compaction" aria-labelledby="compaction-title">
    <p-heading size="lg"><h2 id="compaction-title" tabindex="-1">Context compaction</h2></p-heading>
    <p-text size="sm">A session compacts its context when its conversation nears the model's context window: the
      runtime replaces earlier turns with a summary. How early is the share of the agent's model calls made before
      its first compaction, over the sessions that compacted; only sessions whose runtime log is readable count.
      </p-text>
    ${read ? nothing : html`<p-text id="compaction-none" size="sm">No session of these filters has a readable log.
      </p-text>`}
    ${read && !c.rows.some((r) => r.compacted) ? html`<p-text id="compaction-calm" size="sm">None of the sessions
      whose log is readable compacted its context.</p-text>` : nothing}
    ${c.rows.some((r) => r.compacted) ? keys : nothing}
    ${c.rows.length || errors ? folded("compaction", "Table: compaction per agent", html`
    ${c.rows.length ? html`<p-table id="compaction-table" caption="Compaction per agent"><p-table-head>
      <p-table-head-row>${HEADS.map((h) => html`<p-table-head-cell>${h}</p-table-head-cell>`)}</p-table-head-row>
      </p-table-head><p-table-body>${c.rows.map(row)}</p-table-body></p-table>` : nothing}
    ${errors ? html`<ul id="compaction-errors" class="notes">
      ${c.errors.map((e) => html`<li class="error">Could not read the log of session ${e.session}
        (${e.project || "this machine"}): ${e.error}</li>`)}
      ${c.settings_errors.map((e) => html`<li class="error">Could not read the settings of ${e.project}
        (${e.file}): ${e.error}</li>`)}</ul>` : nothing}`) : nothing}
  </section>`;
}

const keys = html`<p class="chart-keys">Arrow keys move between agents and their sessions, Enter shows only that
  agent.</p>`;
const esc = (text) => globalThis.echarts.format.encodeHTML(String(text));

// A row's tooltip: what the table says of its timing, the focused session's share, and the sessions without one.
function tip(r, label, session) {
  const lines = [`<strong>${esc(label)}</strong>`,
    `${r.compacted} of ${r.logs} sessions compacted, ${r.shares.length} with a timing share`,
    session == null ? "" : `This session: ${percent(session / 100)} of its model calls before compacting`,
    r.median == null ? "No median" : `How early (median): ${percent(r.median)} of its model calls`,
    r.earliest == null ? "" : `Earliest: ${percent(r.earliest)}`,
    `Compacted without a timing share: ${r.unshared}`];
  return lines.filter(Boolean).join("<br>");
}

/**
 * Draws the compaction chart of the table's rows that compacted: a dot per session with a timing share on a 0-100%
 * axis and a mark at the row's median. A click or Enter on a row calls *pick* with its agent.
 */
export function compactionChart(c, pick) {
  const rows = (c?.rows ?? []).filter((r) => r.compacted);
  if (!rows.length) return draw("compaction", null);
  const labels = rows.map((r) => `${named(r)} · ${place(r)}`);
  // Each item carries its tooltip, so a refresh that changes only the counts still changes the option.
  const dots = rows.flatMap((r, i) => [...r.shares].sort((a, b) => a - b)
    .map((s) => ({ value: [s * 100, i], tip: tip(r, labels[i], s * 100) })));
  const medians = rows.flatMap((r, i) => (r.median == null ? []
    : [{ value: [r.median * 100, i], tip: tip(r, labels[i], null) }]));
  const of = (list, i) => list.flatMap((d, at) => (d.value[1] === i ? [at] : []));
  const rowOf = (p) => (p.seriesId === "row" ? p.dataIndex : p.value?.[1]);
  function build(t, mark) {
    const category = { type: "category", data: labels, inverse: true, axisTick: { show: false },
      axisLine: { lineStyle: { color: t.grid } },
      axisLabel: { color: t.muted, width: 160, overflow: "truncate" } };  // fmt: skip
    const value = { type: "value", min: 0, max: 100, splitLine: { lineStyle: { color: t.grid } },
      axisLabel: { color: t.muted, formatter: "{value}%" } };  // fmt: skip
    const marked = { color: t.surface, borderColor: t.text, borderWidth: 3 };
    return {
      grid: { left: 8, right: 24, top: 40, bottom: 8, containLabel: true },
      legend: { top: 0, left: 0, selectedMode: false, data: ["Session", "Median"], textStyle: { color: t.text } },
      tooltip: { trigger: "item", confine: true, backgroundColor: t.surface, borderColor: t.grid,
        textStyle: { color: t.text },
        formatter: (p) => p.data.tip },
      xAxis: value, yAxis: category,
      series: [
        // A transparent band per row: hovering or focusing it shows the row, a click picks its agent.
        { id: "row", name: "Row", type: "bar", barWidth: "90%", z: 1, data: rows.map((r, i) => ({ value: 100,
          tip: tip(r, labels[i], null), ...(i === mark ? { itemStyle: marked } : {}) })),
          itemStyle: { color: "transparent" },
          emphasis: { itemStyle: { color: t.surface, borderColor: t.text, borderWidth: 2 } } },
        { id: "dots", name: "Session", type: "scatter", z: 3, symbolSize: 10, data: dots,
          itemStyle: { color: t.parts[1], borderColor: t.canvas, borderWidth: 1 },
          emphasis: { scale: 1.6, itemStyle: { borderColor: t.text, borderWidth: 2 } } },
        { id: "median", name: "Median", type: "scatter", z: 4, symbol: "rect", symbolSize: [4, 22], data: medians,
          itemStyle: { color: t.text }, emphasis: { scale: 1.3 } },
      ],
    };  // fmt: skip
  }
  draw("compaction", {
    key: query(), label: "Compaction timing chart", ids: labels, rows: rows.length, horizontal: true, build,
    height: 88 + rows.length * 36,
    items: (i, inst) => {
      const ids = (inst.getOption()?.series ?? []).map((s) => s?.id);
      const at = (id, list) => list.map((dataIndex) => ({ seriesIndex: ids.indexOf(id), dataIndex }));
      return [...at("row", [i]), ...at("dots", of(dots, i)), ...at("median", of(medians, i))];
    },
    row: (p) => (p.componentType === "series" ? rowOf(p) ?? null : null),
    act: (i) => pick(rows[i].subagent || rows[i].agent),
  });  // fmt: skip
}

// Arriving at #compaction, from a context setting's way back: the section scrolls into view with its heading focused.
export function arrive() {
  const title = document.getElementById("compaction-title");
  if (location.hash !== "#compaction" || !title) return;
  title.scrollIntoView({ block: "start" });
  title.focus({ preventScroll: true });
}
