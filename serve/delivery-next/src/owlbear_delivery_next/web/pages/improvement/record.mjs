import { html, nothing } from "/assets/lit-html/3.3.3/lit-html.js";
import { credits, plural, tag, when } from "./widgets.mjs";

// One Spotter look as a row, shared by the Improvement page's looks and a Change's page.

export const CATEGORY = { "hand-off-fitness": "Unfit hand-off", "course-and-constraints": "Wrong course",
  "outside-state-changes": "Change outside the task", "irreversible-harm": "Irreversible harm" };

// Where a look or a write happened: its project's name (or id) and its Change.
export function place(r, named) {
  return [named[r.project] ?? (r.project || "outside a project"), r.change].filter(Boolean).join(" \u00b7 ");
}

function grade(g) {
  const said = `${g.preliminary ? "Preliminary grade" : "Graded"}: ${g.grade}${g.should ? `, should have been ${
    g.should}` : ""}`;
  return html`<li>${said}${g.reason ? html`<br><span class="meta">${g.reason}</span>` : nothing}</li>`;
}

// What a look found: a category, nothing, or why it did not look.
function found(r) {
  if (r.skipped) return tag(`Skipped: ${r.skipped}`);
  if (!r.category) return tag("Nothing found", "success");
  return tag(CATEGORY[r.category] ?? r.category, r.category === "irreversible-harm" ? "error" : "warning");
}

// One look: its moment, what it found and why, what it spent, how it ended and how Retro graded it; *more* follows.
export function look(r, named = {}, more = nothing) {
  const evidence = r.evidence?.length ? `${plural(r.evidence.length, "piece")} of evidence: ${r.evidence.join(", ")}`
    : "";
  return html`<li class="panel look" id=${`look-${r.id}`}>
    <div class="row">${found(r)}
      ${r.stopped_step ? tag("Stopped the step: irreversible harm", "error") : nothing}
      ${r.credit_stop ? tag("Stopped at its credit limit", "warning") : nothing}</div>
    <p class="meta">${when(r.at)} \u00b7 ${place(r, named)}${r.step ? ` \u00b7 ${r.step}` : ""} \u00b7 ${r.look
      || "look"} \u00b7 ${r.credits_known ? credits(r.credits) : "credits not reported"}</p>
    ${r.note ? html`<p-text size="sm">${r.note}</p-text>` : nothing}
    ${r.rationale ? html`<p class="meta">Why: ${r.rationale}</p>` : nothing}
    ${evidence ? html`<p class="meta">${evidence}</p>` : nothing}
    ${r.action ? html`<p class="meta">Its setting for this: ${r.action}${r.stopped_step ? ""
      : " (recorded; nothing acts on it yet)"}</p>` : nothing}
    ${r.grades?.length ? html`<ul class="meta">${r.grades.map(grade)}</ul>` : nothing}${more}
  </li>`;
}
