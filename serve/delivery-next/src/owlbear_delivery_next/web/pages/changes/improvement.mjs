import { html, nothing } from "/assets/lit-html/3.3.3/lit-html.js";
import { call } from "/assets/ui.mjs";
import { askFollowup, followupLine, said, send } from "/assets/page/improvement/followup.mjs";
import { look } from "/assets/page/improvement/record.mjs";
import { show } from "./state.mjs";
import { info, notice, text } from "./widgets.mjs";

// The Spotter's and Retro's detail of one Change (#716), shown only while the menu's switch is on: its looks and
// Retro's findings, each with its follow-up. A Change stopped for irreversible harm says so above, switch or not.

export const DETAIL = "owlbear-improvement-detail";  // the switch, in localStorage: "on" shows this section
const FRESH = 30000;  // ms a Change's read is kept: the page redraws every few seconds
const read = new Map();  // key -> { at, data, error, reading }
const outcome = new Map();  // key -> the last follow-up's notice
let busy = "";

export const detailOn = () => localStorage.getItem(DETAIL) === "on";
for (const event of [DETAIL, "storage"]) addEventListener(event, () => show());

function fetched(d) {
  const kept = read.get(d.key);
  if (kept && (kept.reading || Date.now() - kept.at < FRESH)) return kept;
  const next = { at: Date.now(), data: kept?.data ?? null, error: "", reading: true };
  read.set(d.key, next);
  const q = new URLSearchParams({ project: d.project, slug: d.slug });
  call(`/improvement/change?${q}`, { machine: true, timeout: 30000 })
    .then((data) => { next.data = data; }, (error) => { next.error = error.message; })
    .finally(() => { next.reading = false; next.at = Date.now(); show(); });
  return next;
}

async function followUp(d, item, what) {
  if (busy || !(await askFollowup(item, what))) return;
  busy = item.id;
  outcome.delete(d.key);
  show();
  try {
    outcome.set(d.key, ["success", "Done", said(await send(item))]);
  } catch (error) {
    outcome.set(d.key, ["error", "That was not done", error.reread ?? error.message]);
  }
  busy = "";
  read.delete(d.key);
  show();
}

function finding(d, f) {
  const lines = [f.mechanism && `How: ${f.mechanism}`, f.cost && `Cost: ${f.cost}`, f.cause && `Cause: ${f.cause}`];
  return html`<li class="panel finding" id=${`finding-${f.id}`}>${text(f.what || f.id)}
    ${lines.some(Boolean) ? html`<p class="meta">${lines.filter(Boolean).join(" \u00b7 ")}</p>` : nothing}
    ${followupLine(f, () => followUp(d, f, "finding"), { busy: busy === f.id, disabled: !!busy })}</li>`;
}

function body(d, r) {
  if (!r.data) return r.error ? notice("error", "The Spotter's and Retro's detail could not be read", r.error)
    : text("Reading\u2026", { size: "sm" });
  const { looks, findings } = r.data, last = outcome.get(d.key);
  return html`${last ? notice(...last) : nothing}
    ${r.error ? notice("error", "The newest detail could not be read", r.error) : nothing}
    ${text("The Spotter's looks", { weight: "semibold" })}
    ${looks.length ? html`<ul class="cards">${looks.map((l) => look(l, {}, followupLine(l,
      () => followUp(d, l, "look"), { busy: busy === l.id, disabled: !!busy })))}</ul>`
      : text("No look at this Change.", { size: "sm", color: "contrast-medium" })}
    ${text("Retro's findings", { weight: "semibold" })}
    ${findings.length ? html`<ul class="cards">${findings.map((f) => finding(d, f))}</ul>`
      : text("Retro has found nothing in this Change.", { size: "sm", color: "contrast-medium" })}`;
}

export function improvementSection(d) {
  if (!detailOn() || !d.project) return nothing;
  return html`<div id="improvement-detail">${info("The Spotter and Retro", body(d, fetched(d)))}</div>`;
}
