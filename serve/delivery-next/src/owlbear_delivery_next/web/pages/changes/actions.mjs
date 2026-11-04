import { html, nothing } from "/assets/lit-html/3.3.3/lit-html.js";
import { LOOPS } from "./progress.mjs";
import { reviseButton } from "./brief.mjs";
import { info, list, row } from "./widgets.mjs";

// What stands open on this Change, one line each in plain words, whether or not the details are shown.
export function actionItems(d) {
  const b = d.brief, shaping = d.step === "shape" && b.approved !== b.version, lines = [];
  let act = nothing;
  if (shaping && b.unreviewed) {
    lines.push(`v${b.version} changed after its last challenge and no challenger read it: approve it as it is, or `
      + "challenge it");
  }
  if (shaping && b.revising.length) {
    lines.push(`The shaper revises brief v${b.version} for ${b.revising.join(", ")}: continue in the shaping chat, `
      + "or open a new one");
    act = reviseButton(d);
  }
  // The shaping chat's own state (#961) goes here.
  if (shaping && b.picked?.status === "owed") lines.push("Delivery is picking the decisions this version follows");
  if (shaping && b.picked?.status === "failed") lines.push(`Picking the decisions failed: ${b.picked.reason}`);
  const r = d.rounds, repairs = (r?.unreviewed ?? []).filter((u) => !(shaping && b.unreviewed && u.loop === "brief"));
  for (const f of r?.standing ?? []) {
    lines.push(`${LOOPS(f.loop)} ${f.id}, ${f.state}: ${f.text}`);
  }
  for (const u of repairs) lines.push(`No review yet of ${u.title || u.id} (${LOOPS(u.loop)})`);
  for (const a of (d.amendments?.list ?? []).filter((x) => x.state === "applied" && x.unreviewed)) {
    lines.push(`Amendment ${a.id} was applied in a wording no challenger reviewed: turn on Show details to read it`
      + (a.object ? "" : ", and object if you disagree"));
  }
  if (!lines.length) return nothing;
  return html`<div class="actions">${info("Open items", list(lines),
    act === nothing ? nothing : row(act))}</div>`;
}
