import { html, nothing } from "/assets/lit-html/3.3.3/lit-html.js";
import { call } from "/assets/ui.mjs";
import { DIALOG, button } from "./widgets.mjs";

// A Retro finding's or a Spotter record's follow-up, shared by the Improvement page and a Change's page: what this
// machine knows of it, and the button that asks for one.

const RUNNING = { queued: "queued", open: "running", waiting: "waiting for a credit or a slot" };

function entryLink(e) {
  return html`<a href=${e.link} target="_blank" rel="noopener">${e.title}</a> (${e.repository} #${e.id})`;
}

// What the follow-up of *item* is: its backlog entry, its run, how its run ended, or nothing yet.
function followupState(item) {
  const f = item.followup ?? { state: "" };
  if (f.state === "saved") return html`Followed up: ${entryLink(f.entry)}`;
  if (RUNNING[f.state]) return `Follow-up ${RUNNING[f.state]}: Retro writes its backlog entry, then it shows here.`;
  if (f.state === "ended") return `The follow-up run ended without an entry: ${f.result || "no result"}`
    + `${f.why ? `, ${f.why}` : ""}.`;
  return "";
}

// The confirmation: what a follow-up does now, by itself afterwards, and what stays.
export function askFollowup(item, what) {
  return ask({
    title: `Follow up this ${what}?`,
    now: `OwlBear adds one backlog entry for ${item.id}, in the backlog of the project it happened in, or the `
      + "shared one when that project is not loaded; a synthetic one's only in the sandbox's. One already made is "
      + "shown instead of a second.",
    then: "Unless a reviewed proposal already put it in words, a Retro run writes them first: one paid call within "
      + "Retro's limits. Words holding a credential, an email address or a home path are refused, nothing written.",
    after: "The entry stays in the backlog: close it there if it is not needed.",
    instead: "Nothing is written.",
    yes: "Follow up",
  });
}

export function send(item) {
  return call("/improvement/followups", { method: "POST", body: { finding: item.id }, machine: true,
    timeout: 30000 });
}

export function said(answer) {
  return answer.entry ? `Followed up: ${answer.entry.title} (${answer.entry.repository} #${answer.entry.id}).`
    : `Follow-up queued as ${answer.queued}: Retro writes its backlog entry on its next run.`;
}

// The follow-up line of *item*, with its button while none is saved or running; *go* runs the follow-up.
export function followupLine(item, go, { busy = false, disabled = false } = {}) {
  const now = followupState(item), f = item.followup?.state ?? "";
  const open = !now || f === "ended";
  return html`<div class="row followup">${now ? html`<p-text size="sm">${now}</p-text>` : nothing}
    ${open ? button(f === "ended" ? "Follow up again" : "Follow up", go, { busy, disabled, aria: DIALOG }) : nothing}
  </div>`;
}
