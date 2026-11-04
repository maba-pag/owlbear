import { html, nothing } from "/assets/lit-html/3.3.3/lit-html.js";
import { repeat } from "/assets/lit-html/3.3.3/directives/repeat.js";
import { live } from "/assets/lit-html/3.3.3/directives/live.js";
import { act, post, show, state } from "./state.mjs";
import { DIALOG, button, empty, heading, quiet, tag, text, when } from "./widgets.mjs";

// The Spotter cases (design §6): the newest version's cases by stage with their marks, a move to another stage, the
// versions and the replay runs. A change of the examples the Spotter is shown waits for its regression run to pass.

const STAGES = [["candidate", "Candidates"], ["test", "Tests"], ["example", "Examples"]];
const MOVES = [["candidate", "Candidate"], ["test", "Test"], ["example", "Example"], ["removed", "Remove"]];
const EXAMPLE = 800;  // characters of one example's text (cases.EXAMPLE)
// A case enters the tests or examples only with a review of its card: an unchecked candidate stays or goes.
const unchecked = (c) => c.stage === "candidate" && !c.review;
// A reserve, synthetic or unscored case is never an example (cases.problems).
const barred = (c) => (c.marks ?? []).some((m) => ["reserve", "synthetic", "unscored"].includes(m));

// What a move does now and next: one into or out of the examples changes what the Spotter is shown, so a paid
// regression run must pass first; any other move is a new version at once.
function told(c, to) {
  const shown = to === "example" || c.stage === "example";
  const where = to === "removed" ? "removes it from the next version" : `makes it ${to === "example" ? "an" : "a"} `
    + `${to} in the next version`;
  return shown ? {
    now: `OwlBear queues a regression run: the test cases replayed with the Spotter's prompt before and after this `
      + "move.",
    then: "This machine's job runs it: paid looks within the replay credit limit. Only if no count of wrong calls "
      + `rises does it write the version that ${where}; else the move is refused and the run says why.`,
    after: "Each version is kept: a later move can undo this one the same way.",
  } : {
    now: `OwlBear writes the version that ${where}.`,
    after: "Each version is kept: a later move can undo this one.",
  };
}

async function move(n, c) {
  const to = state.stages.get(c.id) ?? c.stage;
  const into = to === "example";
  const answer = await ask({
    title: `${to === "removed" ? "Remove" : "Move"} case ${c.id}${to === "removed" ? "" : ` to ${to}`}?`,
    ...told(c, to),
    instead: "Nothing is written.",
    yes: to === "removed" ? "Remove" : "Move",
    destructive: to === "removed",
    ...(into ? { reason: `The example text the Spotter is shown, at most ${EXAMPLE} characters`, value: c.prefill
      ?? "", limit: EXAMPLE } : {}),
  });
  if (!answer) return;
  const body = { stage: to, parent: n, ...(into ? { example: answer } : {}) };
  await act(`case-${c.id}`, () => post(`/improvement/cases/${encodeURIComponent(c.id)}/move`, body),
    (a) => (a.version !== undefined ? `Case ${c.id} moved: version ${a.version} written.`
      : `Regression run ${a.queued} queued: the move is written only if it passes.`));
}

function chooser(n, c, waiting) {
  const to = state.stages.get(c.id) ?? c.stage;
  const key = `case-${c.id}`;
  return html`<div class="row"><p-select id=${`stage-${c.id}`} label=${`Stage of case ${c.id}`} hide-label="true"
      compact="true" .value=${live(to)} @change=${(e) => { state.stages.set(c.id, e.target.value); show(); }}>
    ${MOVES.filter(([v]) => (!unchecked(c) || v === "candidate" || v === "removed") && (v !== "example" || !barred(c)))
      .map(([v, said]) => html`<p-select-option value=${v}>${said}</p-select-option>`)}</p-select>
    ${button(to === "removed" ? "Remove" : "Move", () => move(n, c), { busy: state.busy === key,
      disabled: !!state.busy || to === c.stage || waiting, aria: DIALOG })}</div>`;
}

// An unchecked candidate's way on: what its last check said (the run's own result when it ended before reviewing
// this case), then its check, asked already or to be asked.
function onward(c, asked) {
  const run = c.last_check;
  const last = run ? text(html`Its last check (${run.id}, ${when(run.at)}): ${run.result}.${
    run.note ? ` ${run.note}` : ""}`, { size: "sm" }) : nothing;
  return html`${last}${asked.has(c.id)
    ? html`<p class="meta">Its paid check is asked: a case it supports moves to the tests.</p>`
    : html`<p class="meta">It moves to the tests once ${run ? "a further" : "its"} paid check supports it:
      <code>owlbear cases check ${c.id}</code> queues one.</p>`}`;
}

function card(n, c, waiting, asked) {
  return html`<li class="panel case" id=${`case-${c.id}`}>
    <div class="row">${text(c.id, { weight: "semibold" })}${(c.marks ?? []).map((m) => tag(m))}</div>
    ${c.error ? html`<p-inline-notification state="error" dismiss-button="false" heading="This case cannot be read"
      description=${c.error}></p-inline-notification>` : nothing}
    <p class="meta">Should be: ${c.call || "unknown"}${c.source ? ` \u00b7 from ${c.source}` : ""}</p>
    ${c.why ? text(c.why, { size: "sm" }) : nothing}
    ${c.example ? html`<p class="meta">Example text: ${c.example}</p>` : nothing}
    ${unchecked(c) ? onward(c, asked) : nothing}
    ${c.error ? nothing : chooser(n, c, waiting)}</li>`;
}

function version(v) {
  return html`<li>${when(v.at)} \u00b7 version ${v.n} from ${v.parent}${v.by ? ` by ${v.by}` : ""}${v.reason
    ? `: ${v.reason}` : ""}${v.run ? ` (run ${v.run})` : ""}</li>`;
}

// Why each look that failed failed, by case and side: a failed answer with no note says nothing more.
function failedLooks(r) {
  const said = Object.entries(r.answers ?? {}).flatMap(([cid, sides]) => Object.entries(sides)
    .filter(([, a]) => a.category === "failed" && a.note).map(([side, a]) => `case ${cid}, ${side}: ${a.note}`));
  return said.length ? html`<ul>${said.map((s) => html`<li>${s}</li>`)}</ul>` : nothing;
}

function replay(r) {
  if ("applied" in r && !("result" in r)) return html`<li>${when(r.at)} \u00b7 run ${r.id}: ${r.applied === null
    ? r.why : `wrote version ${r.applied}`}</li>`;
  return html`<li>${when(r.ended ?? r.at)} \u00b7 ${r.kind ?? "run"} ${r.id}: <span class="said">${
    r.result ?? "no result"}</span>${failedLooks(r)}</li>`;
}

// The cases job's own failures, whole, before its runs: its last pass, and a publication sync that could not start.
function jobFailed(c) {
  const pass = "The job's last pass failed, and the next one tries again: ";
  const sync = "Not published, and the next sync tries again: ";
  return html`${c.failed ? html`<li id="cases-failed">${pass}${c.failed}</li>` : nothing}${c.unpublished
    ? html`<li id="cases-unpublished">${sync}${c.unpublished}</li>` : nothing}`;
}

export function casesSection(c) {
  const waiting = c.queued.length > 0;
  const asked = new Set(c.queued.filter((q) => q.kind === "check").flatMap((q) => Object.keys(q.ids ?? {})));
  const of = (stage) => c.cases.filter((x) => x.stage === stage);
  return html`<section id="cases" aria-labelledby="cases-title">${heading(2, "Spotter cases", "lg", "cases-title")}
    ${quiet(`Version ${c.n}. A case is a past look with the call it should have made: candidates wait, tests check `
      + "a changed prompt, examples are shown to the Spotter.")}
    ${waiting ? html`<p-inline-notification state="info" dismiss-button="false"
      heading="A replay run is queued or running"
      description=${`${c.queued.map((q) => q.id).join(", ")}: another move now would leave it stale and refused, `
        + "so moves wait until it has run."}>
      </p-inline-notification>` : nothing}
    ${STAGES.map(([stage, label]) => html`${heading(3, label, "md")}${of(stage).length
      ? html`<ul class="cards">${repeat(of(stage), (x) => x.id, (x) => card(c.n, x, waiting, asked))}</ul>`
      : empty(`No ${label.toLowerCase()}.`)}`)}
    <div class="panel">${heading(3, "Versions", "sm")}${c.versions.length
      ? html`<ol class="meta">${c.versions.map(version)}</ol>` : text("No version yet.", { size: "sm" })}</div>
    <div class="panel">${heading(3, "Replay runs", "sm")}${c.runs.length || c.failed || c.unpublished
      ? html`<ol class="meta">${jobFailed(c)}${c.runs.map(replay)}</ol>` : text("No replay run yet.", { size: "sm" })}
    </div>
  </section>`;
}
