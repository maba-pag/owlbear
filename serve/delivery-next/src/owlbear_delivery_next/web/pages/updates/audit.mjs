// Updates ▸ Porsche Design System ▸ Deprecations (#777): the shown project's hand audit of the pages OwlBear serves,
// against the PDS release they load. It spends that project's AI credits and changes nothing, so a note follows the
// click instead of a dialog; the last audit's result, scope, version and commit stay shown with every finding.
import { html, nothing } from "/assets/lit-html/3.3.3/lit-html.js";
import { Slow, call, machineState, project } from "/assets/ui.mjs";
import { sentence, when } from "./frame.mjs";

const LOOK = 3000;  // how often the page reads a running audit
const RESULT = { pass: ["no deprecations", "success"], findings: ["deprecations found", "warning"],
  "follow-ups": ["for a person to check", "info"], stop: ["stopped", "error"] };
const own = { last: null, unread: "", busy: false, started: false, error: "", polling: null, show: () => {} };

// The audit is the shown project's: none under All projects on the machine host.
function reachable() {
  return Boolean(project || !machineState());
}

// *show* renders the whole page; the part calls it whenever its state changes.
export function followAudit(show) {
  own.show = show;
}

export async function readAudit() {
  if (!reachable()) return;
  try {
    [own.last, own.unread] = [await call("/pds/audit", { timeout: 15000 }), ""];
  } catch (e) {
    own.unread = e.message;
  }
  own.show();
  clearTimeout(own.polling);
  if (own.unread || own.last?.state === "running") own.polling = setTimeout(readAudit, LOOK);
}

async function start() {
  Object.assign(own, { busy: true, error: "", started: false });
  own.show();
  try {
    own.last = await call("/pds/audit", { method: "POST", timeout: 15000 });
    own.started = true;
  } catch (e) {
    own.error = e instanceof Slow && e.sent ? "Delivery did not answer in time; it was not sent again. The state "
      + "below shows whether it started." : e.message;
  }
  own.busy = false;
  await readAudit();
}

function place(f) {
  return html`<li class="finding">
    <p-text size="sm" weight="semibold">${f.title}</p-text>
    <p-text size="sm"><code>${f.path}:${f.line}</code></p-text>
    <pre class="log">${f.snippet}</pre>
    <p-text size="sm">${f.replacement ? html`Replace <code>${f.replacement.from}</code> with
      <code>${f.replacement.to}</code>. ` : nothing}${f.fix}</p-text>
  </li>`;
}

function followUp(f) {
  return html`<li class="finding">
    <p-text size="sm" weight="semibold">${f.subject}</p-text>
    <p-text size="sm">${f.reason}</p-text>
    ${f.evidence.map((e) => html`<p-text size="sm"><code>${e.path}:${e.line}</code> ${e.snippet}</p-text>`)}
  </li>`;
}

function scope(report) {
  const s = report?.scope;
  if (!s) return "";
  const left = s.excludedPaths.map((e) => `${e.path} (${e.reason})`).join("; ");
  return `${s.includedPaths.join(", ")}${left ? `; left out: ${left}` : ""}`;
}

function last(a) {
  if (!a) return own.unread ? nothing : html`<p-text size="sm">Reading the last audit…</p-text>`;
  if (a.state === "none") return html`<p-text id="audit-none" size="sm">No audit has run in this project
    yet.</p-text>`;
  if (a.state === "running") return html`<p-text id="audit-running" size="sm" role="status">Checking since
    ${when(a.started_at)}…</p-text>`;
  const [word, tone] = RESULT[a.outcome] ?? ["failed", "error"];
  return html`<div class="heading-row">
      <p-heading size="sm"><h4 id="audit-last-title">Last audit</h4></p-heading>
      <p-tag id="audit-result" variant=${tone} compact="true">${word}</p-tag>
    </div>
    ${a.reason ? html`<p-inline-notification id="audit-reason" state=${a.state === "failed" ? "error" : "info"}
      dismiss-button="false">${sentence(a.reason)}.</p-inline-notification>` : nothing}
    <dl class="facts" aria-labelledby="audit-last-title">
      <div><dt>Ended</dt><dd id="audit-when">${when(a.ended_at)}</dd></div>
      <div><dt>PDS version</dt><dd id="audit-version">${a.version ?? "not known"}</dd></div>
      <div><dt>OwlBear commit</dt><dd id="audit-commit">${a.commit ?? "not known"}</dd></div>
      ${a.report ? html`<div><dt>Scope</dt><dd id="audit-scope">${scope(a.report)}</dd></div>` : nothing}
    </dl>
    ${a.findings?.length ? html`<p-heading size="sm"><h4>Deprecated uses (${a.findings.length})</h4></p-heading>
      <ul id="audit-findings" class="findings">${a.findings.map(place)}</ul>` : nothing}
    ${a.follow_ups?.length ? html`<p-heading size="sm"><h4>For a person to check (${a.follow_ups.length})</h4>
      </p-heading><ul id="audit-follow-ups" class="findings">${a.follow_ups.map(followUp)}</ul>` : nothing}`;
}

export function auditPart() {
  const a = own.last, running = a?.state === "running";
  return html`<section id="audit" class="panel" aria-labelledby="audit-title">
    <p-heading size="lg"><h2 id="audit-title">Deprecations</h2></p-heading>
    <p-text size="sm">Checks the pages OwlBear serves for PDS features the release in use deprecates. An auditor
      session reads a copy of them; it spends this project's AI credits and changes nothing.</p-text>
    ${reachable() ? html`<div class="row">
        <p-button id="audit-start" type="button" compact="true" variant="secondary" icon="search"
          .loading=${own.busy || running} ?disabled=${own.busy || running} @click=${start}>Check for
          deprecations</p-button>
        <p-text id="audit-said" size="sm" role="status" aria-live="polite">${own.started ? "Started: the auditor "
          + "reads the pages, which takes a few minutes. This page shows the result when it ends." : ""}</p-text>
      </div>` : html`<p-text id="audit-choose" size="sm">Choose a project above to check the pages: the audit runs
        on that project's AI credits.</p-text>`}
    ${own.error ? html`<p-inline-notification id="audit-error" state="error" dismiss-button="false">${
      sentence(own.error)}</p-inline-notification>` : nothing}
    ${own.unread ? html`<p-text id="audit-unread" size="sm" role="alert">Could not read the last audit:
      ${own.unread}</p-text>` : nothing}
    ${reachable() ? html`<div class="part">${last(a)}</div>` : nothing}
  </section>`;
}
