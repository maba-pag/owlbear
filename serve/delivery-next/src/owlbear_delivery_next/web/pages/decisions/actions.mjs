import { html, nothing } from "/assets/lit-html/3.3.3/lit-html.js";
import { call } from "/assets/ui.mjs";
import { refresh } from "./list.mjs";
import { DIALOG, notify, show, state, WRITE } from "./state.mjs";
import { button, field } from "./widgets.mjs";

const SUBMIT = { replace: "Replace", exception: "Record the exception", "read-back": "Record the read-back" };
const WIDER = { change: "the project", project: "Global" };
const WHY = "Why it changes (recorded with the new rule)";

// One receipt in words: each step the save reached, or why it was not saved.
export function said(r) {
  if (!r.saved) return `${r.id}: not saved. ${r.notice}`;
  const steps = ["saved", r.committed ? "committed" : "not committed", r.committed && (r.published ? "published"
    : "not published"), r.active ? "active" : r.conflict ? "in conflict, not active" : "not active"];
  return `${r.id}: ${steps.filter(Boolean).join(" · ")}${r.notice ? `. ${r.notice}` : ""}`;
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
  show();
  let failed = "";
  try {
    const r = await call(`/decisions/${encodeURIComponent(e.id)}/${action}`,
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
  const words = e.owner_words.map((w) => `“${w.text}” (${w.date})`).join("; ");
  return { tick: "I re-decide this decision", items: [`You decided it: ${words}`] };
}

const ASKS = {
  replace: (e, d) => ({
    title: `${e.origin === "decided" ? "Re-decide" : "Replace"} “${e.title}”?`, yes: "Replace",
    now: "A successor in your words comes into force; this decision is marked replaced and stays in history.",
    items: [`Now: ${e.statement}`, `Then: ${d.statement}`, ...(redecide(e).items ?? [])],
    then: "A running Change that pinned it stops at its next step and asks whether to continue on the new rule.",
    after: "Replace or withdraw the successor in the same way; nothing is deleted.",
    instead: "The decision stays in force as it reads.", tick: redecide(e).tick, reason: WHY,
  }),
  exception: (e, d) => ({
    title: `Record an exception to “${e.title}” for ${state.loaded.project}?`, yes: "Record the exception",
    now: `${state.loaded.project} works by your exception; the Global decision stays in force for every other `
      + "project.", items: [`Global: ${e.statement}`, `Here: ${d.statement}`],
    instead: "The Global decision applies here too.",
  }),
  "read-back": (e) => ({
    title: `Record the read-back of “${e.title}”?`, yes: "Record the read-back",
    now: "Today's read-back and your answer are recorded; the decision and its origin stay as they are.",
    after: "To change the rule, replace it.", instead: "Nothing is recorded.",
  }),
};

function begin(action) {
  state.form = { action, draft: { title: "", statement: "", rationale: "", words: "", answer: "" } };
  show();
}

function body(action, d) {
  if (action === "read-back") return { answer: d.answer.trim() };
  return { title: d.title.trim(), statement: d.statement.trim(), rationale: d.rationale.trim(), words: d.words.trim() };
}

async function submit(e) {
  const { action, draft } = state.form;
  if (["replace", "exception"].includes(action) && !draft.statement.trim()) return notify("Write the new rule.");
  if (action === "read-back" && !draft.answer.trim()) return notify("Write the owner's answer.");
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
      field("Your words", draft.words, set("words"), { multiline: true, max: 4000,
        description: "As you decide it; empty records the new rule as your words" })],
    "read-back": () => [field("Your answer", draft.answer, set("answer"), { multiline: true, max: 2000 })],
  };
  fields.exception = () => [...fields.replace().slice(1)];
  return html`<section class="form" aria-label=${SUBMIT[action]}>${fields[action]()}
    <div class="row">${button(SUBMIT[action], () => submit(e), { aria: DIALOG, busy: state.pending === action })}
      ${button("Cancel", () => { state.form = null; show(); }, { variant: "secondary" })}</div></section>`;
}

async function promote(e) {
  const why = await ask({ title: `Promote “${e.title}” to ${WIDER[e.scope]}?`, yes: "Promote",
    now: `A linked copy comes into force for ${WIDER[e.scope]}, with this decision's origin and words; this one is `
      + "marked replaced and stays in history.", after: "Every widening is yours; it is never narrowed back here.",
    instead: "It stays where it applies now.", reason: "Why it widens (recorded with the wider copy)" });
  if (why) act(e, "promote", { reason: why });
}

async function withdraw(e) {
  const why = await ask({ title: `Withdraw “${e.title}”?`, yes: "Withdraw", ...redecide(e),
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
      : "The proposal comes into force as you approve it.", items: replaces.map((l) => `It replaces ${l.title}`),
    then: "Running Changes it applies to stop at their next step and ask.", instead: "It stays a draft.",
    tick: e.redecide ? "I re-decide what it replaces" : "", reason: replaces.length ? WHY : "" });
  if (answer) act(e, "activate", { ...(replaces.length ? { reason: answer } : {}),
    ...(e.redecide ? { redecide: true } : {}) });
}

async function keep(e) {
  const why = await ask({ title: `Keep “${e.title}” in force?`, yes: "Keep this one",
    now: "The other successors of the same decision are withdrawn and the conflict is cleared.",
    items: e.rivals.map((r) => `Withdrawn: ${r.title}`), instead: "Neither applies until the conflict is resolved.",
    reason: "Why this one stays (recorded with the ones withdrawn)" });
  const revisions = Object.fromEntries([[e.id, e.revision], ...e.rivals.map((r) => [r.id, r.revision])]);
  if (why) act(e, "keep", { revisions, reason: why });
}

export function actions(e) {
  const busy = (a) => state.pending === a, parts = [];
  const opens = (label, action) => button(label, () => begin(action), { variant: "secondary" });
  const asks = (label, work, action) => button(label, () => work(e), { aria: DIALOG, busy: busy(action) });
  if (e.state === "in_force") {
    parts.push(opens("Read back", "read-back"), opens("Replace", "replace"), asks("Withdraw", withdraw, "withdraw"));
    parts.push(e.scope === "global" ? opens("Record an exception", "exception") : asks("Promote", promote, "promote"));
    if (e.conflict || e.rivals.length) parts.push(asks("Keep this one", keep, "keep"));
  }
  if (e.state === "draft") parts.push(asks("Activate", activate, "activate"), asks("Withdraw", withdraw, "withdraw"));
  return parts.length && !state.form ? html`<div class="row" role="group" aria-label="Actions">${parts}</div>`
    : nothing;
}
