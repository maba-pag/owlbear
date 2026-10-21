import { html, nothing } from "/assets/lit-html/3.3.3/lit-html.js";
import { call, loaded } from "/assets/ui.mjs";
import { DIALOG, notify, show, state, untagged, WRITE } from "./state.mjs";
import { button, listed } from "./widgets.mjs";

// The owner's mark on a replacement (TD-428); not saying it counts as possibly forbidding.
export const EFFECTS = [["", "Not said (treated as possibly forbidding)"], ["forbids", "Forbids existing behaviour"],
  ["wording", "Wording only"]];

// A decision that replaced another, or was withdrawn, has an impact report.
export function reported(e) {
  return e.state === "withdrawn" || e.links.some((l) => l.type === "replaces");
}

// Under the machine host the report covers every project it serves; a clone's own host reports its project.
function route(e, action) {
  const folder = encodeURIComponent(state.loaded.project);
  return [`/decisions/${encodeURIComponent(e.id)}/${action}?folder=${folder}`, { machine: Boolean(loaded()) }];
}

async function check(e) {
  state.impact = { id: e.id, busy: true };
  show();
  try {
    const [path, how] = route(e, "impact");
    state.impact = { id: e.id, report: await call(path, { ...how, timeout: WRITE }) };
  } catch (error) {
    state.impact = { id: e.id, error: error.message };
  }
  show();
}

async function write(action, work) {
  state.pending = action;
  show();
  let failed = "";
  try {
    await work();
  } catch (error) {
    failed = error.message;
  }
  state.pending = "";
  show();
  if (failed) notify(failed);
}

async function schedule(e, r) {
  const due = r.projects.filter((p) => p.status !== "unaffected" && !p.accepted);
  const yes = await window.ask({ title: `Schedule fixes for “${r.new.title}”?`, yes: "Schedule fixes",
    now: "Backlog entries are made, one per project (split by folder when its files are many, and into parts when its "
      + "checklist is long), each naming both rules' revisions with a checklist of its Changes and files.",
    items: due.map((p) => `${p.project}: ${p.status}`),
    then: "Nothing changes code by itself: a Change takes an entry like any other and ticks only what it verified.",
    after: "Scheduling again updates the same entries: ticked items stay ticked and newly found ones are added.",
    instead: "No entry is made; the impact stays shown here." });
  if (!yes) return;
  await write("schedule", async () => {
    const [path, how] = route(e, "schedule-fixes");
    const done = await call(path, { ...how, body: { revision: r.new.revision }, timeout: WRITE });
    state.impact.scheduled = done.entries;
  });
}

async function accept(e, r, p) {
  const why = await window.ask({ title: `Keep ${p.project}'s existing code under “${r.new.title}”?`,
    yes: "Accept existing code", now: `Your decision records that code in ${p.project} built before “${r.new.title}” `
      + "stays as it is; new work follows the new rule.", instead: "Its existing code stays to be fixed or checked.",
    after: "Withdraw that decision to schedule fixes for it after all.", reason: "Why it stays (recorded with it)" });
  if (!why) return;
  await write(`accept-${p.project}`, async () => {
    const [path, how] = route(e, "accept-existing");
    const done = await call(path, { ...how, body: { revision: r.new.revision, project: p.project, reason: why },
      timeout: WRITE });
    state.receipts = done.receipts;
  });
  await check(e);
}

function change(c) {
  return `Change ${c.slug}${c.title ? `: ${c.title}` : ""} · ${c.pr || c.from}`;
}

function place(p, e, r) {
  const files = [...p.paths, ...(p.more ? [`and ${p.more} more files`] : [])];
  const records = [...(p.incomplete ?? []), ...(p.more_incomplete ? [`and ${p.more_incomplete} more`] : [])];
  const tests = p.tests.length ? `Tests among them: ${p.tests.join(", ")}${p.more_tests ? ` and ${p.more_tests} more`
    : ""}` : "";
  const open = r.fixes && p.status !== "unaffected" && !p.accepted;
  return html`<li class="impact-project" data-project=${p.project}>
    <p-text size="sm"><strong>${p.project}</strong>: <span class="status">${p.status}</span> · ${untagged(p.why)}
    </p-text>
    ${p.accepted ? html`<p-text size="sm">Existing code kept by your decision ${untagged(p.accepted)}.</p-text>`
      : nothing}
    ${listed("Built under the old rule", p.changes, change)}
    ${listed("Records that cannot rule it out", records, (x) => x)}
    ${listed("Matching files", files, (f) => f)}
    ${tests ? html`<p-text size="sm" class="tests">${tests}</p-text>` : nothing}
    ${open ? button("Accept existing code", () => accept(e, r, p), { variant: "secondary", aria: DIALOG,
      busy: state.pending === `accept-${p.project}` }) : nothing}
  </li>`;
}

function report(e, r) {
  const made = state.impact.scheduled;
  return html`<dl class="facts">
      <dt>Old rule</dt><dd class="old">${r.old.statement}</dd>
      <dt>New rule</dt><dd class="new">${r.new ? r.new.statement : "none: withdrawn"}</dd>
    </dl>
    <p-text size="sm" class="divergence">${untagged(r.divergence)}</p-text>
    <ul class="impacts">${r.projects.map((p) => place(p, e, r))}</ul>
    ${r.fixes ? html`<div class="row">${button("Schedule fixes", () => schedule(e, r), { aria: DIALOG,
      busy: state.pending === "schedule" })}</div>` : nothing}
    ${made ? listed("Backlog entries", made,
      (x) => `#${x.id} ${untagged(x.title)} · ${x.project}${x.new ? "" : ` · updated, ${x.added} new item(s)`}`) : nothing}`;
}

export function impact(e) {
  if (!reported(e)) return nothing;
  const got = state.impact?.id === e.id ? state.impact : null;
  return html`<section id="impact" aria-label="Impact"><p-heading size="sm"><h3>Impact</h3></p-heading>
    ${got?.error ? html`<p-text size="sm" color="notification-error">${got.error}</p-text>` : nothing}
    ${got?.report ? report(e, got.report) : button("Check the impact", () => check(e), { variant: "secondary",
      busy: Boolean(got?.busy) })}
  </section>`;
}
