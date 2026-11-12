// The credits chart above the split table: a bar per row of the table, in its order, stacked by model or by step;
// split by day, columns over time with an average line, without the day whose time is unknown.
import { html } from "/assets/lit-html/3.3.3/lit-html.js";
import { draw } from "./chart.mjs";
import { keysHint, lengthSwitch, stacked } from "./stacked.mjs";
import { credits } from "./runs.mjs";
import { query, show } from "./state.mjs";

const UNKNOWN = "?";
const STACKS = 7;  // more parts than this: the largest 6 and Other
const pick = { by: "model", relative: false };

/** The credits chart's switches: what its bars stack, and raw or relative lengths. */
export function creditsControls() {
  const by = (e) => {
    pick.by = e.detail.value;
    show();
  };
  return html`<div id="split-controls" class="row">
    <p-segmented-control id="split-stack" label="Stack by" compact="true" columns="2" .value=${pick.by} @change=${by}>
      <p-segmented-control-item value="model">Model</p-segmented-control-item>
      <p-segmented-control-item value="step">Step</p-segmented-control-item>
    </p-segmented-control>
    ${lengthSwitch(pick.relative, (on) => {
      pick.relative = on;
      show();
    })}</div>${keysHint}`;
}

// The stacks: each key's credits per bar, largest first; past 7 keys, the largest 6 and the rest as Other.
function stacks(rows, by) {
  const sums = new Map();
  for (const r of rows) {
    for (const p of r[by]) sums.set(p.key, { ...p, credits: (sums.get(p.key)?.credits ?? 0) + p.credits });
  }
  const ranked = [...sums.values()].sort((a, b) => b.credits - a.credits || a.label.localeCompare(b.label));
  const kept = ranked.length > STACKS ? ranked.slice(0, STACKS - 1) : ranked;
  const of = (r, key) => r[by].find((p) => p.key === key)?.credits ?? 0;
  const parts = kept.map((s) => ({ id: `${by}:${s.key}`, name: s.label, values: rows.map((r) => of(r, s.key)) }));
  if (kept.length < ranked.length) {
    const named = new Set(kept.map((s) => s.key));
    parts.push({ id: `${by}:other`, name: "Other", values: rows.map((r) => r[by]
      .filter((p) => !named.has(p.key)).reduce((sum, p) => sum + p.credits, 0)) });  // fmt: skip
  }
  return parts;
}

const date = (label) => new Date(`${label}T00:00`).toLocaleDateString(undefined, { month: "short", day: "numeric" });

/** Draws the credits chart of the split table's *rows*, split by *by*; a click drills down like the row's button. */
export function creditsChart(rows, by, drill) {
  const shown = by === "day" ? rows.filter((r) => r.key !== UNKNOWN) : rows;
  if (!shown.length) return draw("split", null);
  const day = by === "day";
  const spec = stacked({
    labels: shown.map((r) => r.label), parts: stacks(shown, `by_${pick.by}`), totals: shown.map((r) => r.credits),
    colours: (t) => t.parts, format: credits, horizontal: !day, relative: pick.relative, average: day,
    tick: day ? date : undefined,
  });  // fmt: skip
  draw("split", { ...spec, ids: shown.map((r) => r.key), key: query(), label: "Credits chart", act: (i) => drill(shown[i])?.() });
}
