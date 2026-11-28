// The machine's update state and actions, shared by Impeccable and Porsche Design System.
import { html, nothing } from "/assets/lit-html/3.3.3/lit-html.js";
import { Slow, call, machineState } from "/assets/ui.mjs";

const WRITE = 60000;  // an answer may commit and push: a network round trip
export const ADMIT = 90000;  // a start that timed out may still be admitted: its pull request lookup can take a while
export const SETTINGS = "It runs on the machine's settings and its spend counts for the machine.";
const LOOK = 2500;  // how often the page looks for that run meanwhile
const IDLE = 15000;  // how often it looks for a run started or answered elsewhere
// TD-220: what became of each finding of the update's challenge rounds, in words.
export const FOUND = { open: "to fix", fixed: "fixed by the updater",
  rejected: "rejected by the updater, not judged yet",
  standing: "rejected by the updater; the challenger accepted that",
  escalated: "rejected by the updater; the challenger upheld it", "owner-fix": "you decided: fix it",
  "owner-drop": "you dropped it", withdrawn: "withdrawn by the challenger" };

// What differs between the kinds: where the runs are read and the update is answered, and what the dialogs say.
export const IMPECCABLE = {
  name: "Impeccable", label: "Update Impeccable",
  peer: { path: "/updates/pds", holders: ["PDS update", "check for deprecations"] },
  intro: "An update takes the newest upstream pack and validates it with model requests. Only if every stage "
    + "passes, or if you accept it after its challenge rounds end without a pass, it commits it on its own branch, "
    + "opens a pull request to main and merges it once CI passes.",
  pinned: "/maintenance/pack", runs: "/maintenance/pack/runs", update: "/impeccable/update",
  start: {
    title: "Update Impeccable?", yes: "Update", no: "Keep the current pack",
    now: "Delivery takes the newest upstream pack, detector pins and design skills together; an updater session "
      + "brings the skills, golden pages and detector glue in line, then the golden pages, calibration replay and a "
      + `challenger check it. The replay uses OwlBear's decided rounds. ${SETTINGS}`,
    then: "Only if every stage passes, it activates the pack: it commits impeccable.json, skills/NOTICE.md and "
      + "the files the updater changed, opens a pull request to main and merges it once CI passes. It asks you here "
      + "before changed golden evidence counts and before a glue change goes into the pull request, and when the "
      + "rounds end without a pass or the challenger upholds a finding the updater rejected.",
    after: "Later visual rounds use the new pack. If the update stops, this page says why and offers a retry "
      + "when the stopped stage can run again.",
    instead: "The current pack stays active.",
  },
  activate: { title: "Activate the pack without a passing challenge?",
    now: "Delivery activates the candidate as it is now: it commits impeccable.json, skills/NOTICE.md and the "
      + "files the updater changed, opens a pull request to main and merges it once CI passes.",
    after: "Later visual rounds use the new pack; run another update when upstream moves on." },
  discard: { title: "Discard the Impeccable update?",
    then: "Nothing is activated: the pinned pack stays as it is, and the run's candidate is not used again." },
  merged: "The merged pack reaches each machine as it takes the OwlBear version that carries it; until then a "
    + "machine keeps the pack it has.",
};

export const own = { kind: IMPECCABLE, pinned: null, runs: null, unread: { pinned: "", runs: "" }, error: null,
  notes: new Map(), choices: new Map(), unchosen: "", missing: "", busy: "", polling: null, reading: 0,
  awaiting: null, lost: false, show: () => {} };

// *show* renders the whole page; the panel calls it whenever its state changes.
export function follow(show) {
  own.show = show;
  for (const kind of ["owlbear-machine", "owlbear-polled"]) document.addEventListener(kind, () => own.show());
}

// The pack and its runs are the machine's: read from the host itself, so a shown project that is not loaded (failed,
// replaced, removed meanwhile) hides neither.
export async function readPack() {
  if (!machineState()) return;
  const generation = ++own.reading;
  const k = own.kind;
  const [pinned, runs] = await Promise.allSettled([
    k.pinned ? call(k.pinned, { timeout: 15000, machine: true }) : null,
    call(k.runs, { timeout: 15000, machine: true }),
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
  return run ? `${run.run}:${run.started_at}` : "";
}

async function act(name, work, target = null) {
  own.busy = name;
  own.error = null;
  own.show();
  try {
    await work();
  } catch (e) {
    own.error = { target, message: e instanceof Slow ? e.reread : e.message };
  }
  own.busy = "";
  own.show();
  await readPack();
}

export async function answer(run, q, o) {
  const note = own.notes.get(q.id) ?? "";
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
  const a = own.kind.activate;
  if (o.id === "activate" && !(await ask({
    title: a.title, yes: "Activate", no: "Keep it waiting",
    now: `${a.now} It activates `
      + (items.length ? "with these left as they are:" : "with no repair left unreviewed and no finding left open."),
    items,
    then: "The commit message records that the rounds ended without a pass and which findings were not changed for.",
    after: a.after,
    instead: "The update keeps waiting; you can still discard it.",
  }))) return;
  await act(`${q.id}:${o.id}`, async () => {
    await call(`${own.kind.update}/answer`,
      { machine: true, body: { question: q.id, option: o.id, note }, timeout: WRITE });
    own.notes.delete(q.id);
    own.choices.delete(q.id);
  }, q.id);
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
    title: own.kind.discard.title, yes: d.label, no: "Keep it waiting", destructive: true,
    now: "The machine's update ends here as discarded.",
    then: own.kind.discard.then,
    after: p?.url ? `Its pull request #${p.number} stays open; close it on GitHub if you no longer want it.`
      : "Start a new update when you want one.",
    instead: "The update keeps waiting for your answer.",
  });
  if (!sure) return;
  if (d.q) {
    await act(`${d.q.id}:discard`, () => call(`${own.kind.update}/answer`,
      { machine: true, body: { question: d.q.id, option: "discard", note: "" }, timeout: WRITE }), "");
  } else {
    await act("discard", () => call(`${own.kind.update}/discard`,
      { machine: true, body: { run: run.run }, timeout: WRITE }), "");
  }
}

// Activating at the end, granting one updater session or retrying without a repair beside it has priority.
// Other alternatives are chosen and sent with one button instead (run.mjs).
export function emphasis(q, o) {
  const repair = q.options.some((x) => x.id === "repair");
  return o.id === "activate" || o.id === "more-updater" || (o.id === "retry" && !repair) ? "primary" : "secondary";
}

export async function start() {
  const sure = await ask(own.kind.start);
  if (!sure) return;
  const before = key(own.runs?.run);
  own.lost = false;
  await act("start", async () => {
    try {
      await call(own.kind.update, { machine: true, method: "POST", timeout: 10000 });
    } catch (e) {
      if (!(e instanceof Slow && e.sent)) throw e;
      own.awaiting = { before, until: Date.now() + ADMIT };  // its admission may still be under way
    }
  });
}

export async function replay() {
  const sure = await ask({
    title: "Replay OwlBear's decided rounds?", yes: "Replay", no: "Do not replay",
    now: "The design judge runs again on OwlBear's decided rounds using the installed pack.",
    then: `${SETTINGS} No pack files change.`,
    instead: "No replay runs and no credits are spent.",
  });
  if (!sure) return;
  own.replayed = "";
  await act("replay", async () => {
    const result = await call("/impeccable/replay", { machine: true, method: "POST", timeout: 3600000 });
    own.replayed = result.report;
  });
}

export function button(label, onclick, { id, variant = "secondary", busy = false, disabled = false, icon } = {}) {
  return html`<p-button id=${id ?? nothing} type="button" compact="true" variant=${variant} icon=${icon ?? nothing}
    .loading=${busy} ?disabled=${disabled} @click=${onclick}>${label}</p-button>`;
}
