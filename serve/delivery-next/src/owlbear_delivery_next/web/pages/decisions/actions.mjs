import { html, nothing } from "/assets/lit-html/3.3.3/lit-html.js";
import { call } from "/assets/ui.mjs";
import { refresh } from "./list.mjs";
import { EFFECTS } from "./impact.mjs";
import { at, DIALOG, KINDS, notify, projectName, readBack, show, state, untagged, WRITE } from "./state.mjs";
import { button, field, select } from "./widgets.mjs";

const SUBMIT = { replace: "Replace", exception: "Record the exception", "queue-read-back": "Queue the read-back" };
const WIDER = { change: "the project", project: "Global" };
const WHY = "Why it changes (recorded with the new rule)";

// One receipt in words: each step the save reached, or why it was not saved; the decision named by its title.
export function said(r) {
  const name = untagged(r.id);
  if (!r.saved) return `${name}: not saved. ${untagged(r.notice)}`;
  const steps = ["saved", r.committed ? "committed" : "not committed", r.committed && (r.published ? "published"
    : "not published"), r.active ? "active" : r.conflict ? "in conflict, not active" : "not active"];
  return `${name}: ${steps.filter(Boolean).join(" · ")}${r.notice ? `. ${untagged(r.notice)}` : ""}`;
}

export function receipts() {
  if (!state.receipts.length) return nothing;
  return html`<section id="receipts" role="status" aria-label="Receipts"><p-heading size="sm"><h2>What the last
    action did</h2></p-heading><ul>${state.receipts.map((r) => html`<li>${said(r)}</li>`)}</ul></section>`;
}

// One write for the opened decision, at the revision the page shows (keep names each revision itself); its receipts
// replace the last ones, and a refused write stays said after the refresh.
async function act(e, action, body = {}) {
  state.pending = action;
  state.notice = "";
  show();
  let failed = "";
  try {
    const r = await call(at(`/decisions/${encodeURIComponent(e.id)}/${action}`, e.address),
      { body: action === "keep" ? body : { revision: e.revision, ...body }, timeout: WRITE });
    state.receipts = r.receipts;
    if (r.saved) state.form = null;
  } catch (error) {
    state.receipts = [];
    failed = error.message;
  }
  state.pending = "";
  await refresh();
  if (failed) notify(failed);
}

// A decided decision changes only once the owner re-decides it: he ticks that he does.
function redecide(e) {
  if (e.origin !== "decided") return {};
  return { tick: "I re-decide this decision", items: [`You decided it · ${readBack(e)}`] };
}

const ASKS = {
  replace: (e, d) => ({
    title: `${e.origin === "decided" ? "Re-decide" : "Replace"} “${e.title}”?`, yes: "Replace",
    now: "Your successor comes into force as your decision, confirmed today; this decision is marked replaced and "
      + "stays in history.",
    items: [`Now: ${e.statement}`, `Then: ${d.statement}`, `Existing work: ${effect(d.effect)}`,
      ...(redecide(e).items ?? [])],
    then: "A running Change that pinned it stops at its next step and asks whether to continue on the new rule.",
    after: "Replace or withdraw the successor in the same way; nothing is deleted.",
    instead: "The decision stays in force as it reads.", tick: redecide(e).tick, reason: WHY,
  }),
  exception: (e, d) => ({
    title: `Record an exception to “${e.title}” for ${projectName(e.address)}?`, yes: "Record the exception",
    now: `${projectName(e.address)} works by your exception; the Global decision stays in force for every other `
      + "project.", items: [`Global: ${e.statement}`, `Here: ${d.statement}`],
    instead: "The Global decision applies here too.",
  }),
};

function begin(action) {
  state.form = { action, draft: { title: "", statement: "", rationale: "", why: "", kind: "uncertain", effect: "" } };
  show();
}

function effect(value) {
  return EFFECTS.find(([v]) => v === value)[1].toLowerCase();
}

function body(action, d) {
  if (action === "queue-read-back") return { why: d.why.trim(), kind: d.kind };
  // the owner acting on his page confirms the rule he writes (TD-449: no words are sent)
  const rule = { title: d.title.trim(), statement: d.statement.trim(), rationale: d.rationale.trim(),
    confirmed: true };
  return action === "replace" ? { ...rule, effect: d.effect } : rule;
}

async function submit(e) {
  const { action, draft } = state.form;
  if (["replace", "exception"].includes(action) && !draft.statement.trim()) return notify("Write the new rule.");
  if (action === "queue-read-back") {  // asks nothing yet: it waits in the queue for the owner's answer
    return draft.why.trim() ? act(e, action, body(action, draft)) : notify("Say what makes it worth asking again.");
  }
  const told = ASKS[action](e, draft), answer = await ask(told);
  if (!answer) return;
  act(e, action, { ...body(action, draft), ...(told.reason ? { reason: answer } : {}),
    ...(told.tick ? { redecide: true } : {}) });
}

export function form(e) {
  if (!state.form) return nothing;
  const { action, draft } = state.form, set = (key) => (v) => { draft[key] = v; };
  const fields = {
    replace: () => [field("Title", draft.title, set("title"), { description: `Empty keeps “${e.title}”` }),
      field("New rule", draft.statement, set("statement"), { multiline: true, max: 240 }),
      field("Why", draft.rationale, set("rationale"), { multiline: true, max: 4000 }),
      select("Effect on existing work", EFFECTS, draft.effect, (v) => { draft.effect = v; show(); })],
    "queue-read-back": () => [field("Why ask again", draft.why, set("why"), { multiline: true, max: 600,
      description: "Only ambiguity, new evidence, a conflict or changed consequences" }),
    select("How urgent", Object.entries(KINDS), draft.kind, (v) => { draft.kind = v; show(); })],
  };
  fields.exception = () => [...fields.replace().slice(1, -1)];
  return html`<section class="form" aria-label=${SUBMIT[action]}>${fields[action]()}
    <div class="row">${button(SUBMIT[action], () => submit(e), { aria: DIALOG, busy: state.pending === action })}
      ${button("Cancel", () => { state.form = null; show(); }, { variant: "secondary" })}</div></section>`;
}

async function promote(e) {
  const why = await ask({ title: `Promote “${e.title}” to ${WIDER[e.scope]}?`, yes: "Promote",
    now: `A linked copy comes into force for ${WIDER[e.scope]} as your decision, confirmed today; this one is `
      + "marked replaced and stays in history.", after: "Every widening is yours; it is never narrowed back here.",
    instead: "It stays where it applies now.", reason: "Why it widens (recorded with the wider copy)" });
  if (why) act(e, "promote", { reason: why });
}

async function withdraw(e) {
  const why = await ask({ title: `Withdraw “${e.title}”?`, yes: "Withdraw", ...redecide(e), destructive: true,
    now: "It no longer applies and has no successor; it stays in history, hidden by default.",
    then: e.state === "in_force" ? "A running Change it applied to stops at its next step and asks." : undefined,
    after: "Record a new decision if the rule is needed again.", instead: "It stays as it is.",
    reason: "Why it no longer applies (recorded with it)" });
  if (why) act(e, "withdraw", { reason: why, ...(e.origin === "decided" ? { redecide: true } : {}) });
}

async function activate(e) {
  const replaces = e.links.filter((l) => l.type === "replaces");
  const answer = await ask({ title: `Activate “${e.title}”?`, yes: "Activate",
    now: e.redecide ? "It replaces a decided or already reversed decision: it comes into force as your re-decision."
      : "It comes into force as your decision, confirmed today.", items: [e.statement,
      ...replaces.map((l) => `It replaces ${l.title}`), ...(replaces.length ? [`Existing work: ${effect(state.effect)}`]
        : [])],
    then: "Running Changes it applies to stop at their next step and ask.", instead: "It stays a draft.",
    tick: e.redecide ? "I re-decide what it replaces" : "", reason: replaces.length ? WHY : "" });
  if (answer) act(e, "activate", { ...(replaces.length ? { reason: answer, effect: state.effect } : {}),
    ...(e.redecide ? { redecide: true } : {}) });
}

// A read-back records only that the owner confirms the statement as it reads; a different intent is a replacement.
async function stillRight(e) {
  const yes = await ask({ title: `Is “${e.title}” still what you want?`, yes: "Confirm as it reads",
    now: "Today is recorded as the day you confirmed it; the statement and its origin stay as they are.",
    items: [e.statement], after: "If you want something different, replace it instead.",
    instead: "Nothing is recorded." });
  if (yes) act(e, "read-back", { confirmed: true });
}

// The owner says he never decided it: its origin goes one step down; its statement and state stay.
const LOWER = { decided: "approved", approved: "autonomous" };
const WAS = { approved: "an agent's proposal you accepted, not your own decision",
  autonomous: "an agent's own choice, neither made nor accepted by you" };

async function correct(e) {
  const to = LOWER[e.origin];
  const why = await ask({ title: `Mark “${e.title}” ${to}?`, yes: `Mark ${to}`,
    now: `It is recorded as ${WAS[to]}; it applies as it reads.`, items: [e.statement],
    after: "Making it your decision again is a replacement you confirm; a read-back keeps this origin.",
    instead: `It stays ${e.origin}.`,
    reason: "Where it really came from (recorded with it)" });
  if (why) act(e, "correct-origin", { origin: to, reason: why, confirmed: true });
}

async function keep(e) {
  const why = await ask({ title: `Keep “${e.title}” in force?`, yes: "Keep this one",
    now: "The other successors of the same decision are withdrawn and the conflict is cleared.",
    items: e.rivals.map((r) => `Withdrawn: ${r.title}`), instead: "Neither applies until the conflict is resolved.",
    reason: "Why this one stays (recorded with the ones withdrawn)" });
  const revisions = Object.fromEntries([[e.id, e.revision], ...e.rivals.map((r) => [r.id, r.revision])]);
  if (why) act(e, "keep", { revisions, reason: why });
}

// One primary per decision, by its state: a conflict asks which one to keep, a draft whether to activate it, a
// decision in force whether it is still right; Withdraw is never primary (D-01M63C7BJZZ7RQV9XS4XVR0DNE).
function primary(e) {
  if (e.state === "draft") return "activate";
  if (e.state !== "in_force") return "";
  return e.conflict || e.rivals.length ? "keep" : "read-back";
}

export function actions(e) {
  const busy = (a) => state.pending === a, parts = [], first = primary(e);
  const opens = (label, action) => button(label, () => begin(action), { variant: "secondary" });
  const asks = (label, work, action) => button(label, () => work(e), { aria: DIALOG, busy: busy(action),
    variant: action === first ? "primary" : "secondary" });
  if (e.state === "in_force") {
    parts.push(asks("Read back", stillRight, "read-back"), opens("Replace", "replace"),
      asks("Withdraw", withdraw, "withdraw"));
    parts.push(e.scope === "global" ? opens("Record an exception", "exception") : asks("Promote", promote, "promote"));
    if (e.conflict || e.rivals.length) parts.push(asks("Keep this one", keep, "keep"));
  }
  if (e.state === "draft") {
    if (e.links.some((l) => l.type === "replaces")) {
      parts.push(select("Effect on existing work", EFFECTS, state.effect, (v) => { state.effect = v; show(); }));
    }
    parts.push(asks("Activate", activate, "activate"), asks("Withdraw", withdraw, "withdraw"));
  }
  if (["in_force", "draft"].includes(e.state)) parts.push(opens("Queue a read-back", "queue-read-back"));
  if (["in_force", "draft"].includes(e.state) && LOWER[e.origin]) {
    parts.push(asks(`Mark ${LOWER[e.origin]}`, correct, "correct-origin"));
  }
  return parts.length && !state.form ? html`<div class="row" role="group" aria-label="Actions">${parts}</div>`
    : nothing;
}
