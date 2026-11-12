import { html, nothing } from "/assets/lit-html/3.3.3/lit-html.js";
import { LOOPS } from "./progress.mjs";
import { reviseButton } from "./brief.mjs";
import { sendTo, starts, state } from "./state.mjs";
import { button, info, list, refusal, row, toggle } from "./widgets.mjs";

// The findings left open after approval: the worker rejected each and the next reviewer or challenger upheld it. One
// fold with a count; opened, each finding whole with the reasons it has (D-01M7866JPJ080C8545DH00WY1H).
function leftOpen(found) {
  if (!found.length) return nothing;
  const said = (f) => html`${f.where} ${f.id}: ${f.text}${[[f.worker, f.reason], [f.judge, f.judgement]]
    .filter(([, why]) => why).map(([who, why]) => html`<br>${who}: ${why}`)}`;
  return toggle("left-open", `Findings left open (${found.length})`,
    html`<p-text size="sm">The builder or planner rejected each of these and the next reviewer or challenger upheld
      it. Nothing was changed for them.</p-text>`, list(found.map(said)));
}

// What stands open on this Change, one line each in plain words, whether or not the details are shown.
export function actionItems(d) {
  const b = d.brief, shaping = d.step === "shape" && b.approved !== b.version, lines = [];
  let act = nothing, again = nothing, refused = nothing;
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
  if (shaping && b.picked?.status === "failed") {
    lines.push(`Picking the decisions failed: ${b.picked.reason}`);
    if (d.handle) {  // asked for again without a challenge round (TD-459)
      const version = b.version, key = `${d.key}:pick:${version}`;
      again = button("Pick the decisions again",
        () => sendTo("/briefs/challenge", { change: d.handle, version, retry_pick: true }, d, key), starts(d));
      if (state.refused?.form === key) refused = refusal(state.refused.text, state.refused.unsure);
    }
  }
  const r = d.rounds, repairs = (r?.unreviewed ?? []).filter((u) => !(shaping && b.unreviewed && u.loop === "brief"));
  for (const f of r?.standing ?? []) {
    lines.push(`${LOOPS(f.loop)} ${f.id}, ${f.state}: ${f.text}`);
  }
  for (const u of repairs) lines.push(`No review yet of ${u.title || u.id} (${LOOPS(u.loop)})`);
  for (const a of (d.amendments?.list ?? []).filter((x) => x.state === "applied" && x.unreviewed)) {
    lines.push(`Amendment ${a.id} was applied in a wording no challenger reviewed: turn on Show details to read it`
      + (a.object ? "" : ", and object if you disagree"));
  }
  const left = leftOpen(r?.left ?? []);
  if (!lines.length && left === nothing) return nothing;
  return html`<div class="actions">${info("Open items", lines.length ? list(lines) : nothing, left,
    act === nothing && again === nothing ? nothing : row(act, again), refused)}</div>`;
}
