import { html, nothing } from "/assets/lit-html/3.3.3/lit-html.js";
import { repeat } from "/assets/lit-html/3.3.3/directives/repeat.js";
import { begin } from "/assets/page/sending/feedback.mjs";
import { call } from "/assets/ui.mjs";
import { askFollowup, followupForm, followupLine, said, send } from "/assets/page/improvement/followup.mjs";
import { finding, look } from "/assets/page/improvement/record.mjs";
import { show } from "./state.mjs";
import { button, info, notice, text } from "./widgets.mjs";
import { detailsOn } from "./details.mjs";

// The Spotter's and Retro's detail of one Change (#716), shown only with the page's details: its looks and Retro's
// findings, each with its follow-up. A Change stopped for irreversible harm says so above, switch or not.

const FRESH = 30000;  // ms a Change's read is kept: the page redraws every few seconds
const read = new Map();  // key -> { at, data, error, reading, stale }
const outcome = new Map();  // key -> the last follow-up's notice
const sent = new Map();  // item id -> the item as sent, its row drawn from it until its checkmark is over


function fetched(d) {
  const kept = read.get(d.key);
  if (kept && !kept.stale && (kept.reading || Date.now() - kept.at < FRESH)) return kept;
  const next = { at: Date.now(), data: kept?.data ?? null, error: "", reading: true };
  read.set(d.key, next);
  const q = new URLSearchParams({ project: d.project, slug: d.slug });
  call(`/improvement/change?${q}`, { machine: true, timeout: 30000 })
    .then((data) => { next.data = data; }, (error) => { next.error = error.message; })
    .finally(() => { next.reading = false; next.at = Date.now(); show(); });
  return next;
}

// Each follow-up row shows its own send (sending/feedback.mjs) and locks alone; its answer may take 30 s.
async function followUp(d, item, what) {
  if (!(await askFollowup(item, what))) return;
  const sending = begin(followupForm(item), { hold: false });
  if (!sending) return;
  outcome.delete(d.key);
  sent.set(item.id, item);  // a read meanwhile (its 30 s refresh, another row's follow-up) may already say queued
  show();
  try {
    const answer = await send(item);
    outcome.set(d.key, ["success", "Done", said(answer)]);
    await sending.done();
  } catch (error) {
    sending.failed(error);
    outcome.set(d.key, ["error", "That was not done", error.reread ?? error.message]);
  } finally {
    sent.delete(item.id);
  }
  const kept = read.get(d.key);
  if (kept) kept.stale = true;  // read again, its rows kept meanwhile so a refused one still says so
  show();
}

function line(d, item, what) {
  const shown = sent.get(item.id) ?? item;
  return followupLine(shown, () => followUp(d, shown, what), { button });
}

function shownFinding(d, f) {
  return finding(f, "", line(d, f, "finding"));
}

function body(d, r) {
  if (!r.data) return r.error ? notice("error", "The Spotter's and Retro's detail could not be read", r.error)
    : text("Reading\u2026", { size: "sm" });
  const { looks, findings } = r.data, last = outcome.get(d.key);
  const missing = r.data.record_unread ?? [];
  return html`${last ? notice(...last) : nothing}
    ${r.error ? notice("error", "The newest detail could not be read", r.error) : nothing}
    ${text("The Spotter's looks", { weight: "semibold" })}
    ${missing.length ? notice("error", "Some Spotter records could not be read", missing.join("\n")) : nothing}
    ${looks.length ? html`<ul class="cards">${repeat(looks, (l) => l.id, (l) => look(l, {}, line(d, l, "look")))}</ul>`
      : text(missing.length ? "No readable look at this Change; some records could not be read."
        : "No look at this Change.", { size: "sm", color: "contrast-medium" })}
    ${text("Retro's findings", { weight: "semibold" })}
    ${findings.length ? html`<ul class="cards">${repeat(findings, (f) => f.id, (f) => shownFinding(d, f))}</ul>`
      : text("Retro has found nothing in this Change.", { size: "sm", color: "contrast-medium" })}`;
}

export function improvementSection(d) {
  if (!detailsOn() || !d.project) return nothing;
  return html`<div id="improvement-detail">${info("The Spotter and Retro", body(d, fetched(d)))}</div>`;
}
