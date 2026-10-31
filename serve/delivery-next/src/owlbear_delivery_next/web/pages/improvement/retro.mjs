import { html, nothing } from "/assets/lit-html/3.3.3/lit-html.js";
import { live } from "/assets/lit-html/3.3.3/directives/live.js";
import { here } from "/assets/ui.mjs";
import { act, post, show, state } from "./state.mjs";
import { DIALOG, button, credits, empty, heading, plural, quiet, tag, text, when } from "./widgets.mjs";

// Retro (design §6): its switches, what is queued, its units by state, its newest runs, and a run on one finished
// Change at the owner's word.

const SWITCHES = [["retro_after_change", "Run after each finished Change"], ["retro_when_idle", "Run when idle"]];
const RUNS = { open: ["Running", "info"], waiting: ["Waiting", "warning"], ended: ["Ended", "secondary"] };

function asked(q) {
  const what = q.change ? `Change ${q.change}` : q.chat ? `chat ${q.chat}` : q.synthetic ? `synthetic unit ${
    q.synthetic}` : q.redraft ? `the redraft of proposal ${q.redraft}` : `the follow-up of ${q.followup}`;
  return html`<li>${when(q.at)} \u00b7 ${what}${q.by ? ` \u00b7 asked by ${q.by}` : ""}</li>`;
}

function made(r) {
  if (r.followup) return `followed up as ${r.followup.repository} #${r.followup.id}`;
  if (r.redraft) return `redrafted as proposal ${r.redraft}`;
  return "";
}

function run(r) {
  const [said, variant] = RUNS[r.state] ?? [r.state, "secondary"];
  const spent = r.known === false ? `at least ${credits(r.spent)} (some not reported)` : credits(r.credits ?? r.spent);
  const parts = [r.unit, r.trigger && `by ${r.trigger}`, plural(r.calls ?? 0, "call"), spent, r.result, made(r)];
  return html`<li class="panel" id=${`run-${r.id}`}><div class="row">${tag(said, variant)}<span class="meta">${
    when(r.at)}${r.ended ? html` to ${when(r.ended)}` : nothing}</span></div>
    <p class="meta">${parts.filter(Boolean).join(" \u00b7 ")}</p>${r.why ? html`<p class="meta">${r.why}</p>`
      : nothing}</li>`;
}

function switches(s) {
  if (s.error) return html`<p-inline-notification state="error" dismiss-button="false"
    heading="Retro's switches could not be read" description=${s.error}></p-inline-notification>`;
  return html`<ul class="meta">${SWITCHES.map(([key, label]) => html`<li>${label}: ${s[key] ? "on" : "off"}</li>`)}
    </ul><p-link-pure icon="arrow-right"><a href=${here({}, "/config#set-machine-retro_after_change")}>Change them
    in Settings, This machine</a></p-link-pure>`;
}

async function runRetro(finished) {
  const chosen = finished.find((f) => f.change === state.retroOn);
  if (!chosen) return;
  const yes = await ask({
    title: `Run Retro on ${chosen.slug}?`,
    now: `OwlBear queues a Retro run of ${chosen.project}'s Change ${chosen.slug}; this machine's Retro job takes it `
      + "next.",
    then: "It reads the Change's record and chats and judges them: paid calls within Retro's limits. Its findings and "
      + "any proposals show here and on the Change's page.",
    after: "What it finds stays. A Change it judged already, unchanged since, is refused as not due: the run shows "
      + "here with why.",
    instead: "Nothing is queued.",
    yes: "Run Retro",
  });
  if (!yes) return;
  await act("retro", () => post("/improvement/retro", { change: chosen.change }),
    (a) => `Retro run of ${chosen.slug} queued as ${a.queued}.`);
}

function runner(finished) {
  if (!finished.length) return empty("No finished Change to run Retro on.");
  if (!finished.some((f) => f.change === state.retroOn)) state.retroOn = finished[0].change;
  return html`<div class="row"><p-select id="retro-change" label="Finished Change" compact="true"
      .value=${live(state.retroOn)} @change=${(e) => { state.retroOn = e.target.value; show(); }}>
    ${finished.map((f) => html`<p-select-option value=${f.change}>${f.project} \u00b7 ${f.slug}, finished ${
      new Date(f.at).toLocaleDateString()}</p-select-option>`)}</p-select>
    ${button("Run Retro", () => runRetro(finished), { busy: state.busy === "retro", disabled: !!state.busy,
      variant: "primary", aria: DIALOG })}</div>`;
}

export function retroSection(r) {
  const units = Object.entries(r.units);
  return html`<section id="retro" aria-labelledby="retro-title">${heading(2, "Retro", "lg", "retro-title")}
    ${quiet("It judges finished work after the fact, grades the Spotter's looks and proposes what to change.")}
    <div class="panel">${heading(3, "Switches", "sm")}${switches(r.switches)}</div>
    <div class="panel">${heading(3, "Run Retro now", "sm")}${runner(r.finished)}</div>
    <div class="panel">${heading(3, "Queued", "sm")}${r.queued.length
      ? html`<ol class="meta">${r.queued.map(asked)}</ol>` : text("Nothing is queued.", { size: "sm" })}</div>
    <div class="panel">${heading(3, "Units by state", "sm")}${units.length
      ? html`<ul class="meta">${units.map(([s, n]) => html`<li>${s}: ${n}</li>`)}</ul>`
      : text("No unit judged yet.", { size: "sm" })}</div>
    ${heading(3, "Runs", "md")}
    ${r.runs.length ? html`<ul class="cards">${r.runs.map(run)}</ul>` : empty("No Retro run yet.")}
  </section>`;
}
