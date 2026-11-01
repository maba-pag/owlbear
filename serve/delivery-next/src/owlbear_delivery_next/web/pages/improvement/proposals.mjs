import { html, nothing } from "/assets/lit-html/3.3.3/lit-html.js";
import { state, act, post } from "./state.mjs";
import { DIALOG, button, empty, heading, plural, quiet, tag, text, when } from "./widgets.mjs";

// Retro's proposals, managed by direction (design §6): each card says what it would change, why, where it would land
// and its risks; the owner accepts, rejects, sets it aside or says how to redraft it. Every decision names the token
// of what he saw, so one made on a view that changed since is refused and nothing written.

const OPEN = new Set(["waiting", "shown", "later"]);
const DIRECTION = 1000;  // characters of a redirect's direction (proposal_apply.DIRECTION)
const STATES = { drafted: ["Under review", "secondary"], waiting: ["Waiting for you", "warning"],
  shown: ["Waiting for you", "warning"], later: ["Later", "secondary"], accepted: ["Accepted", "success"],
  rejected: ["Rejected", "secondary"], redirected: ["Redirected", "info"] };
const APPLIED = { pending: "Not made yet", partly: "Partly made", done: "Made", failed: "Failed" };

function title(p) {
  return p.publishable?.title || `${p.kind} for ${p.target || p.record || "the Spotter's looks"}`;
}

const synthetic = (p) => (p.provenance ?? "real") !== "real";

// Where a finding was seen: its project's name and Change, from "project-id:slug"; else its Retro unit.
export function seenIn(f) {
  const at = (f.change ?? "").lastIndexOf(":");
  if (at < 0) return f.unit;
  const pid = f.change.slice(0, at);
  return `${state.data?.spotter?.projects?.[pid]?.name ?? pid} \u00b7 ${f.change.slice(at + 1)}`;
}

// Where the proposal lands once accepted, in words.
function landing(d) {
  if (!d || d.error) return `It cannot be accepted: ${d?.error ?? "where it lands is not known"}.`;
  switch (d.kind) {
    case "memory": return `A pending memory in ${d.folder}, for ${d.roles?.length ? d.roles.join(", ") : "every "
      + "agent"}, recommended as a ${d.recommended} memory.`;
    case "issue": return `An issue in ${d.repository}${d.synthetic ? ", titled [synthetic] and closed at once" : ""}.`;
    case "backlog": return d.folder ? `A backlog entry in ${d.folder}'s backlog.` : "A shared backlog entry.";
    case "case": return `A Spotter case from record ${d.record}${d.call ? `, which should have been ${d.call}` : ""}`
      + `${d.synthetic ? ", marked synthetic" : ""}, then its paid check.`;
    default: return `A ${d.kind}.`;
  }
}

// What accepting makes now, what follows by itself and what cannot be undone, per destination.
const ACCEPT = {
  memory: ["OwlBear saves it as a pending memory, then shows it here as made.",
    "Nothing: a pending memory is used only once you approve it on the Memory page.",
    "Rejecting the memory there removes it; this proposal stays accepted."],
  issue: ["OwlBear opens the issue on GitHub; a synthetic one it closes at once.",
    "Nothing more: Delivery works on the issue only once you shape it into a Change.",
    "The issue stays on GitHub, public in a public repository; close it there."],
  backlog: ["OwlBear adds the entry to the backlog.", "Nothing more: the entry waits in the backlog.",
    "The entry stays in the backlog; close it there."],
  case: ["OwlBear adds the case as a candidate.",
    "It queues the case's check, a paid run within the Spotter cases' limits, before the case can be moved on.",
    "The case stays among the candidates until you move or remove it under Spotter cases."],
};

async function accept(p) {
  const [now, then, after] = ACCEPT[p.destination.kind] ?? ["OwlBear makes it.", "", ""];
  const yes = await ask({ title: `Accept "${title(p)}"?`, now: `${landing(p.destination)} ${now}`, then, after,
    instead: "It stays waiting; Later sets it aside.", yes: "Accept" });
  if (!yes) return;
  await act(`accept:${p.id}`, async () => {
    await post(`/improvement/proposals/${p.id}/decide`, { state: "accepted", token: p.token });
    return post(`/improvement/proposals/${p.id}/apply`);
  }, (after) => after.apply_state === "done" ? `Accepted and made: ${title(p)}.`
    : `Accepted; making it ${after.apply_state === "failed" ? "failed" : "is not finished"}: use Apply again.`);
}

async function reject(p) {
  const yes = await ask({ title: `Reject "${title(p)}"?`, now: "It closes as rejected; nothing is made.",
    then: "Retro opens a proposal with the same aim again only on evidence this one did not hold.",
    after: "It cannot be reopened.", instead: "It stays as it is.", yes: "Reject", destructive: true });
  if (yes) await decide(p, "rejected", "Rejected");
}

// A redirect asks for the direction, then reads it back before anything is written.
async function redirect(p) {
  const direction = await ask({ title: `Redirect "${title(p)}"`, reason: "What should change", limit: DIRECTION,
    now: "Say how Retro should redraft it; you confirm it on the next step.", yes: "Next" });
  if (!direction) return;
  const yes = await ask({ title: "Send this direction?", now: "This proposal closes as redirected, with:",
    items: [direction], then: "Retro redrafts it at once, one paid call within its limits; the redraft comes back "
      + "here as a new proposal for you to decide.",
    after: "The redirected proposal cannot be reopened; redirect the redraft if it misses again.",
    instead: "Nothing is written; the proposal stays waiting.", yes: "Redirect" });
  if (yes) await decide(p, "redirected", "Redirected: Retro redrafts it now", { direction });
}

function decide(p, to, said, extra = {}) {
  return act(`${to}:${p.id}`, () => post(`/improvement/proposals/${p.id}/decide`, { state: to, token: p.token,
    ...extra }), `${said}: ${title(p)}.`);
}

function applyAgain(p) {
  return act(`apply:${p.id}`, () => post(`/improvement/proposals/${p.id}/apply`),
    (after) => after.apply_state === "done" ? `Made: ${title(p)}.` : `Still not made: ${title(p)}.`);
}

function redraftAgain(p) {
  return act(`redraft:${p.id}`, () => post(`/improvement/proposals/${p.id}/redraft`),
    (a) => `Redraft queued as ${a.queued}.`);
}

function actions(p) {
  const busy = (k) => state.busy === `${k}:${p.id}`, off = Boolean(state.busy);
  if (OPEN.has(p.state)) {
    const cannot = Boolean(p.destination?.error);
    return html`<div class="row actions">
      ${button("Accept", () => accept(p), { variant: "primary", busy: busy("accept"), disabled: off || cannot,
        aria: DIALOG })}
      ${button("Reject", () => reject(p), { busy: busy("rejected"), disabled: off, aria: DIALOG })}
      ${p.state === "later" ? nothing : button("Later", () => decide(p, "later", "Set aside"),
        { busy: busy("later"), disabled: off })}
      ${button("Redirect", () => redirect(p), { busy: busy("redirected"), disabled: off, aria: DIALOG })}</div>`;
  }
  if (p.state === "accepted" && ["pending", "partly", "failed"].includes(p.apply_state)) {
    return html`<div class="row actions">${button("Apply again", () => applyAgain(p), { busy: busy("apply"),
      disabled: off })}</div>`;
  }
  const run = p.redraft_run ?? {};
  if (p.state === "redirected" && !p.redraft && (!run.state || run.state === "ended")) {
    return html`<div class="row actions">${button("Redraft again", () => redraftAgain(p), { busy: busy("redraft"),
      disabled: off })}</div>`;
  }
  return nothing;
}

// One artefact a step made: what and where, linked when it has an address.
function made(a) {
  const { kind, where, ref, link } = a.artefact ?? {};
  const said = `${kind ?? a.step} ${ref ?? ""}${where ? ` in ${where}` : ""}`.trim();
  return link ? html`Made: <a href=${link} target="_blank" rel="noopener">${said}</a>` : `Made: ${said}`;
}

function outcome(p) {
  const lines = [];
  if (p.state === "accepted") {
    lines.push(`${APPLIED[p.apply_state] ?? p.apply_state}: ${landing(p.destination)}`);
    for (const a of p.applied) lines.push(made(a));
    if (p.failures.length) lines.push(`Last failure${p.failures[0].step ? ` (${p.failures[0].step})` : ""}: `
      + p.failures[0].error);
  }
  if (p.state === "redirected") {
    lines.push(`Your direction: ${p.direction}`);
    const run = p.redraft_run ?? {};
    if (p.redraft) lines.push(`Redrafted as ${p.redraft}.`);
    else if (run.state === "ended") lines.push(`The redraft run ended without one: ${run.result || "no result"}`
      + `${run.why ? `, ${run.why}` : ""}.`);
    else if (run.state === "queued") lines.push("Retro redrafts it on its next run.");
    else if (run.state) lines.push("Retro is redrafting it.");
    else lines.push("No redraft is queued or running: ask for it again.");
  }
  if (p.redraft_of) lines.push(`A redraft of ${p.redraft_of}, after your direction.`);
  return lines.length ? html`<ul class="meta">${lines.map((l) => html`<li>${l}</li>`)}</ul>` : nothing;
}

function card(p) {
  const [said, variant] = STATES[p.state] ?? [p.state, "secondary"], last = p.history.at(-1);
  const counts = [plural(p.findings.length, "finding"), plural(p.counterexamples?.count ?? 0, "counterexample")];
  return html`<li class="panel proposal" id=${`proposal-${p.id}`}>
    <div class="row">${tag(said, variant)}${tag(p.kind)}${synthetic(p) ? tag("Synthetic", "info") : nothing}
      ${quiet(html`${p.id} · ${when(last?.at)}`)}</div>
    ${heading(3, title(p), "md")}
    ${p.state === "drafted" ? quiet("Retro reviews it before you can decide on it.") : nothing}
    ${text(html`<strong>Why:</strong> ${p.why || p.mechanism || "not said yet"} (${counts.join(", ")}).`)}
    ${p.seen?.length ? html`<ul class="meta">${p.seen.map((f) => html`<li>Seen in ${seenIn(f)}: ${
      f.what}${f.cost ? html` <strong>Cost:</strong> ${f.cost}` : nothing}</li>`)}</ul>` : nothing}
    ${p.bar ? quiet(`Its bar: ${p.bar}.`) : nothing}
    ${p.publishable?.body ? text(html`<strong>What would change:</strong> ${p.publishable.body}`) : nothing}
    ${text(html`<strong>Where:</strong> ${landing(p.destination)}`)}
    ${p.verdict ? text(html`<strong>Review:</strong> ${p.verdict}`) : nothing}
    ${p.risks?.length ? html`<ul class="meta">${p.risks.map((r) => html`<li>Risk: ${r}</li>`)}</ul>` : nothing}
    ${p.assumptions?.length ? quiet(`Rests on ${p.assumptions.join(", ")}.`) : nothing}
    ${outcome(p)}${actions(p)}</li>`;
}

export function proposalsSection(list) {
  const waiting = list.filter((p) => ["waiting", "shown"].includes(p.state)).length;
  return html`<section id="proposals" aria-labelledby="proposals-title">
    ${heading(2, "Retro's proposals", "lg", "proposals-title")}
    ${quiet(waiting ? `${plural(waiting, "proposal")} ${waiting === 1 ? "waits" : "wait"} for you.`
      : "None waits for you.")}
    ${list.length ? html`<ul class="cards">${list.map(card)}</ul>` : empty("Retro has proposed nothing yet.")}
  </section>`;
}
