// Updates ▸ OwlBear (D-01M63CC7CYSMN156SJEBVFAXTQ, D-01M63CCHPB2W34NM7K9NHEXFY3): the version in use and the newest,
// Start update now, refused with its reason while work runs instead of waiting, and the update's ten steps, each with
// its state, times and line, over a folded log.
import { html, nothing, render } from "/assets/lit-html/3.3.3/lit-html.js";
import { Slow, call, defined, machineState } from "/assets/ui.mjs";
import { frame, framed, sentence, settingsLink, when } from "./frame.mjs";

const RUNNING = 2000;  // how often it reads the steps while an update runs
const ENDED = ["idle", "current", "failed", "refused"];
const STEPS = { pending: ["not started", "secondary"], running: ["running", "info"], done: ["done", "success"],
  failed: ["failed", "error"], stopped: ["stopped", "warning"] };
const own = { report: null, unread: "", error: "", busy: false, polling: null, reading: 0 };

function running(r) {
  return Boolean(r?.phase) && !ENDED.includes(r.phase);
}

async function readReport() {
  if (!machineState()) return;
  const n = ++own.reading;
  try {
    const got = await call("/update", { machine: true });
    if (n !== own.reading) return;  // a later read is under way; it shows the newer state
    [own.report, own.unread] = [got, ""];
  } catch (e) {
    if (n !== own.reading) return;
    own.unread = e.message;  // a host handing over to the new version does not answer for a moment
  }
  show();
  clearTimeout(own.polling);
  if (running(own.report)) own.polling = setTimeout(readReport, RUNNING);
}

async function start() {
  const yes = await ask({ title: "Start the OwlBear update now?", yes: "Start update now", no: "Keep this version",
    now: "OwlBear gets the newest version of this machine's channel, builds it beside the running one, checks it and "
      + "installs its Impeccable. Each of the ten steps below shows how far it got.",
    then: "It switches to the new version once no step, check environment or Impeccable update runs; work that starts "
      + "meanwhile makes it wait. This page keeps working and says once which version runs.",
    after: "Delivery stays paused or running as it is. A failure before the switch leaves this version running. Once "
      + "switched there is no undo: OwlBear never goes back to an older version; a fix comes with a later one.",
    instead: `OwlBear keeps running ${machineState()?.updated || "this version"}; whether it updates by itself is set `
      + "in Settings, This machine." });
  if (!yes) return;
  Object.assign(own, { busy: true, error: "" });
  show();
  try {
    await call("/update/start", { method: "POST", machine: true, timeout: 10000 });
  } catch (e) {  // refused (409) with its reason: work started since the page last read
    own.error = e.status === 409 ? `Not started: ${e.message}.` : e instanceof Slow ? e.reread : e.message;
  }
  own.busy = false;
  await readReport();
}

function stateLine(r) {
  const to = r.version ? ` to ${r.version}` : "", at = r.at ? ` (${when(r.at)})` : "";
  if (!r.phase || r.phase === "idle") return "No update has run since OwlBear started.";
  if (r.phase === "current") return `The last update found nothing newer${at}.`;
  if (r.phase === "failed") return `The update${to} failed${at}: ${r.detail}`;
  if (r.phase === "refused") return `The update${to} did not start${at}: ${r.detail}`;
  return `Updating${to}: ${r.phase}${r.detail ? `, ${r.detail}` : ""}.`;
}

function step(s) {
  const [word, tone] = STEPS[s.state] ?? [s.state, "secondary"];
  const said = [sentence([s.started_at && `started ${when(s.started_at)}`, s.ended_at && `ended ${when(s.ended_at)}`]
    .filter(Boolean).join(", ")), s.line].filter(Boolean).join(". ");
  return html`<li><span class="step-head"><span>${s.label}</span>
    <p-tag variant=${tone} compact="true">${word}</p-tag></span>
    ${said ? html`<p-text size="xs" color="contrast-medium">${said}</p-text>` : nothing}</li>`;
}

function progress(r) {
  const steps = r.steps ?? [], log = r.log ?? [], label = Object.fromEntries(steps.map((s) => [s.key, s.label]));
  if (!steps.length) {
    return html`<p-text id="owlbear-steps-none" size="sm">No update has run on this machine yet: its ten steps show
      here once one starts.</p-text>`;
  }
  return html`<ol id="owlbear-steps" class="steps" aria-labelledby="owlbear-steps-title">${steps.map(step)}</ol>
    <details id="owlbear-log-box">
      <summary>Log of the update (${log.length} line${log.length === 1 ? "" : "s"})</summary>
      <pre id="owlbear-log" class="log">${log.length ? log.map((e) => `${when(e.at)} · ${label[e.step] ?? e.step}: ${
        e.line}`).join("\n") : "Nothing logged."}</pre>
    </details>`;
}

function updatePart() {
  const r = own.report;
  if (!r) {
    return own.unread ? html`<p-inline-notification id="owlbear-unread" state="error" dismiss-button="false">Could not
      read the update: ${own.unread}.</p-inline-notification>`
      : html`<p-text id="owlbear-reading" size="sm">Reading the update…</p-text>`;
  }
  const refused = !r.startable && !own.busy;
  return html`<section id="owlbear" class="panel" aria-labelledby="owlbear-title">
    <p-heading size="lg"><h2 id="owlbear-title">Update</h2></p-heading>
    <p-text id="owlbear-state" size="sm" role="status" aria-live="polite">${stateLine(r)}</p-text>
    ${own.unread ? html`<p-text id="owlbear-unread" size="sm" role="alert">This may be out of date: ${own.unread}
      </p-text>` : nothing}
    <div class="row">
      <p-button id="owlbear-start" type="button" compact="true" variant="primary" icon="refresh"
        .loading=${own.busy} ?disabled=${refused} @click=${start}>Start update now</p-button>
      ${refused ? html`<p-text id="owlbear-refused" size="sm">Not now: ${r.reason}.</p-text>` : nothing}
    </div>
    ${own.error ? html`<p-inline-notification id="owlbear-error" state="error" dismiss-button="false">${own.error}
      </p-inline-notification>` : nothing}
    <div class="part">
      <p-heading size="md"><h3 id="owlbear-steps-title">Steps</h3></p-heading>
      ${progress(r)}
    </div>
    <p-text id="owlbear-settings" size="sm">The update channel, whether OwlBear updates by itself and how often it
      looks are in ${settingsLink()}.</p-text>
  </section>`;
}

function show() {
  render(html`${frame("owlbear")}${machineState() ? updatePart() : nothing}`, document.getElementById("page"));
}

await defined(["p-heading", "p-text", "p-button", "p-tag", "p-inline-notification"]);
framed(show);
document.addEventListener("owlbear-polled", () => readReport());  // work that starts or ends elsewhere
show();
readReport();
