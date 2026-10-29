// The Impeccable update's state and actions (D-01M63C5VGFVT3DVCC888B78K2A): the one update of this machine, kept in
// the project that started it, whose endpoints its actions go to from whichever project the page shows, or from All
// projects. Its view is run.mjs; Updates ▸ Impeccable (impeccable.mjs) shows both.
import { html, nothing } from "/assets/lit-html/3.3.3/lit-html.js";
import { Slow, call, machineState, project } from "/assets/ui.mjs";

const WRITE = 60000;  // an answer may commit and push: a network round trip
export const ADMIT = 90000;  // a start that timed out may still be admitted: its pull request lookup can take a while
const LOOK = 2500;  // how often the page looks for that run meanwhile
const IDLE = 15000;  // how often it looks for a run started or answered elsewhere
// TD-220: what became of each finding of the update's challenge rounds, in words.
export const FOUND = { open: "to fix", fixed: "fixed by the updater",
  rejected: "rejected by the updater, not judged yet",
  standing: "rejected by the updater; the challenger accepted that",
  escalated: "rejected by the updater; the challenger upheld it", "owner-fix": "you decided: fix it",
  "owner-drop": "you dropped it", withdrawn: "withdrawn by the challenger" };

export const own = { pinned: null, runs: null, unread: { pinned: "", runs: "" }, error: "", notes: new Map(),
  missing: "", busy: "", polling: null, reading: 0, awaiting: null, lost: false, show: () => {} };

// *show* renders the whole page; the panel calls it whenever its state changes.
export function follow(show) {
  own.show = show;
  for (const kind of ["owlbear-machine", "owlbear-polled"]) document.addEventListener(kind, () => own.show());
}

export async function readPack() {
  const generation = ++own.reading;
  const [pinned, runs] = await Promise.allSettled([
    call("/maintenance/pack", { timeout: 15000 }), call("/maintenance/pack/runs", { timeout: 15000 }),
  ]);
  if (generation !== own.reading) return;  // a later read is under way; it shows the newer state
  if (pinned.status === "fulfilled") [own.pinned, own.unread.pinned] = [pinned.value, ""];
  else own.unread.pinned = pinned.reason.message;
  if (runs.status === "fulfilled") [own.runs, own.unread.runs] = [runs.value, ""];
  else own.unread.runs = runs.reason.message;
  const run = own.runs?.run;
  if (own.awaiting && runs.status === "fulfilled" && key(run) !== own.awaiting.before) own.awaiting = null;
  else if (own.awaiting && Date.now() >= own.awaiting.until) [own.awaiting, own.lost] = [null, true];
  own.show();
  clearTimeout(own.polling);
  if (own.awaiting) own.polling = setTimeout(readPack, LOOK);  // never sent again: only read until it shows
  else if (own.unread.runs || (run?.state === "running" && !run.interrupted)) {
    own.polling = setTimeout(readPack, 2000);
  } else if (!document.hidden) own.polling = setTimeout(readPack, IDLE);  // showing again reads at once
}

// Which run a record is: a start that went through shows another one.
function key(run) {
  return run ? `${run.pid}:${run.run}:${run.started_at}` : "";
}

// Where the run's actions go: the project that started it, from any project the page shows or from All projects,
// while the machine host has it loaded. None on a clone's own host for another project's run: only the machine host
// reaches that one.
export function reach(run) {
  const bar = machineState();
  if (!bar) return run.own ? { of: project } : null;
  return bar.projects.some((p) => p.id === run.pid && p.state === "loaded") ? { of: run.pid } : null;
}

async function act(name, work) {
  own.busy = name;
  own.error = "";
  own.show();
  try {
    await work();
  } catch (e) {
    own.error = e instanceof Slow ? e.reread : e.message;  // a timed-out action is never sent again: read back
  }
  own.busy = "";
  await readPack();
}

export async function answer(run, q, o) {
  const to = reach(run), note = own.notes.get(q.id) ?? "";
  if (o.id === "reconsider" && !note.trim()) {  // the host refuses it too; said here before anything is sent
    own.missing = q.id;
    own.show();
    const field = document.querySelector(`[data-note="${CSS.escape(q.id)}"]`);  // focused once PDS has rendered it
    return Promise.resolve(field?.componentOnReady?.()).then(() => field?.isConnected && field.focus());
  }
  own.missing = "";
  const left = ["rejected", "standing", "owner-drop"], loop = run.loop;
  const standing = (loop?.findings ?? []).filter((f) => left.includes(f.state));
  const items = [...(loop?.unreviewed ?? []).map((r) => `Repair ${r}: no challenger reviewed it.`),
    ...standing.map((f) => `${f.id} not changed for (${FOUND[f.state]}): ${f.text}`)];
  if (o.id === "activate" && !(await ask({
    title: "Activate the pack without a passing challenge?", yes: "Activate", no: "Keep it waiting",
    now: "Delivery activates the candidate as it is now: it commits impeccable.json, skills/NOTICE.md and the "
      + "files the updater changed, opens a pull request to main and merges it once CI passes. It activates "
      + (items.length ? "with these left as they are:" : "with no repair left unreviewed and no finding left open."),
    items,
    then: "The commit message records that the rounds ended without a pass and which findings were not changed for.",
    after: "Later visual rounds use the new pack; run another update when upstream moves on.",
    instead: "The update keeps waiting; you can still discard it.",
  }))) return;
  await act(`${q.id}:${o.id}`, async () => {
    await call("/impeccable/update/answer", { ...to, body: { question: q.id, option: o.id, note }, timeout: WRITE });
    own.notes.delete(q.id);
  });
}

// The stop's one Discard: the answer its question offers, else the run's own discard while it waits.
export function discarding(run, questions) {
  const q = questions.find((x) => x.options.some((o) => o.id === "discard"));
  if (q) return { label: q.options.find((o) => o.id === "discard").label, q };
  return run.state === "waiting" ? { label: "Discard the update", q: null } : null;
}

export async function discard(run, d) {
  const p = run.published;
  const sure = await ask({
    title: "Discard the Impeccable update?", yes: d.label, no: "Keep it waiting",
    now: `The update started in ${run.name} ends here as discarded.`,
    then: "Nothing is activated: the pinned pack stays as it is, and the run's candidate is not used again.",
    after: p?.url ? `Its pull request #${p.number} stays open; close it on GitHub if you no longer want it.`
      : "Start a new update when you want one.",
    instead: "The update keeps waiting for your answer.",
  });
  if (!sure) return;
  if (d.q) {
    await act(`${d.q.id}:discard`, () => call("/impeccable/update/answer",
      { ...reach(run), body: { question: d.q.id, option: "discard", note: "" }, timeout: WRITE }));
  } else {
    await act("discard", () => call("/impeccable/update/discard", { ...reach(run), method: "POST", timeout: WRITE }));
  }
}

// A primary only where one answer has priority: activating at the end, or trying again once a cause is fixed when
// no repair is offered beside it. Unresolved alternatives keep equal emphasis.
export function emphasis(q, o) {
  const repair = q.options.some((x) => x.id === "repair");
  return o.id === "activate" || (o.id === "retry" && !repair) ? "primary" : "secondary";
}

export async function start() {
  const sure = await ask({
    title: "Update Impeccable?", yes: "Update", no: "Keep the current pack",
    now: "Delivery takes the newest upstream pack, detector pins and design skills together; an updater session "
      + "brings the skills, golden pages and detector glue in line, then the golden pages, calibration replay and a "
      + "challenger check it. The challenger's findings go back to the updater. It runs on this project's labels, "
      + "calibration and AI credits.",
    then: "Only if every stage passes, it activates the pack: it commits impeccable.json, skills/NOTICE.md and "
      + "the files the updater changed, opens a pull request to main and merges it once CI passes. It asks you here "
      + "before changed golden evidence counts and before a glue change goes into the pull request, and when the "
      + "rounds end without a pass or the challenger upholds a finding the updater rejected.",
    after: "Later visual rounds use the new pack. If a stage fails, nothing changes and this page says why.",
    instead: "The current pack stays active.",
  });
  if (!sure) return;
  const before = key(own.runs?.run);
  own.lost = false;
  await act("start", async () => {
    try {
      await call("/impeccable/update", { method: "POST", timeout: 10000 });
    } catch (e) {
      if (!(e instanceof Slow && e.sent)) throw e;
      own.awaiting = { before, until: Date.now() + ADMIT };  // its admission may still be under way
    }
  });
}

export function button(label, onclick, { id, variant = "secondary", busy = false, disabled = false, icon } = {}) {
  return html`<p-button id=${id ?? nothing} type="button" compact="true" variant=${variant} icon=${icon ?? nothing}
    .loading=${busy} ?disabled=${disabled} @click=${onclick}>${label}</p-button>`;
}
