import { html, nothing } from "/assets/lit-html/3.3.3/lit-html.js";
import { live } from "/assets/lit-html/3.3.3/directives/live.js";
import { blockedOf, call, project } from "/assets/ui.mjs";

const ORDER = { high: 0, medium: 1, low: 2 };
const ACTIVE = new Set(["running", "publishing"]);
const when = (at) => new Date(at).toLocaleString();
const findingsOf = (last) => (last?.findings ?? []).map((f, i) => ({
  ...f, finding: i + 1, check: last.verdicts?.find((v) => v.finding === i + 1),
}));
const publishable = (last) => findingsOf(last).filter((f) => !last.verified || f.check?.verdict === "accepted");
const summaryPending = (last) => last?.verified && !last.summary_issue?.complete;
const unpublished = (last) => publishable(last).filter((f) => f.number == null).length
  + Number(!!summaryPending(last));

function verification(v) {
  return html`<p-text class="audit-text" size="sm">${v.reason}</p-text>
    ${v.decisions.length ? html`<p-text class="audit-text" size="sm">Authority: ${
      v.decisions.join(", ")}</p-text>` : nothing}
    ${v.duplicate_of ? html`<p-text class="audit-text" size="sm">Duplicate of: ${
      v.duplicate_of}</p-text>` : nothing}`;
}

export function auditActions(show) {
  const state = { rows: [], notes: new Map(), errors: new Map(), opened: new Set(),
    reading: "", starting: "", generation: 0, applied: 0 };
  let again;

  async function refresh() {
    const generation = ++state.generation;
    try {
      const read = await call("/maintenance/audits", { timeout: 15000 });
      if (generation < state.applied) return;
      state.applied = generation;
      state.rows = read.audits;
      state.reading = "";
    } catch (e) {
      if (generation < state.applied) return;
      state.applied = generation;
      state.reading = e.message;
    }
    show();
    clearTimeout(again);
    if (state.rows.some((a) => ACTIVE.has(a.last?.state))) again = setTimeout(refresh, 5000);
  }

  async function start(a) {
    const note = state.notes.get(a.audit) ?? "", dropped = unpublished(a.last);
    const discardReport = dropped ? a.last.id : "";
    const sure = await window.ask({
      title: `Start ${a.name.toLowerCase()}?`, yes: "Start audit", no: "Cancel",
      destructive: !!dropped,
      now: `Delivery fetches ${a.branch} and pins its head. One auditor session on ${a.role.model} at `
        + `${a.role.effort} effort reads the project at that commit, read-only.`
        + (note ? " Your note goes to the auditor and verifier as written; it can change the scope, lenses, "
          + "strictness, the commit and where "
          + "the issues go." : "")
        + (dropped ? ` The last run's ${dropped} unfinished publication item${dropped === 1 ? "" : "s"} `
          + "(unpublished findings or summary) will be dropped. Its report is replaced; published issues remain." : ""),
      then: `A verifier on ${a.verifier?.model ?? "unset"} at ${a.verifier?.effort ?? "unset"} effort checks every `
        + "finding against the code and every decision. Accepted findings become Backlog entries with evidence, "
        + "type and severity, unless your note names another repository. Each run opens a summary issue; rejected "
        + "and unsure findings stay in the report and summary with reasons and authority. The run asks nothing and "
        + "uses AI credits for both sessions and their subagents. It runs also while Delivery is paused.",
      after: "This page shows the run, its results and where its issues are. Triage Backlog entries on the Backlog "
        + "page and take them into a Change; issues your note sent to another repository are handled there.",
      instead: "Nothing starts.",
    });
    if (sure) await write(a, "", { note, discard_report: discardReport });
  }

  async function finish(a) {
    const sure = await window.ask({
      title: `Finish publishing ${a.name.toLowerCase()}?`, yes: "Finish publishing", no: "Cancel",
      now: "Delivery checks the saved issue receipts, publishes the remaining findings and, for a verified run, "
        + "finishes its summary issue.",
      then: "No auditor or verifier session runs and no AI credits are used. Existing issues are not opened again.",
      after: "This page shows the updated report. Triage the published findings on the Backlog page, or in the "
        + "repository your note named. Published issues remain there.",
      instead: "The unfinished publication stays in this report for you to finish later.",
    });
    if (sure) await write(a, "/publish", {});
  }

  async function write(a, suffix, body) {
    state.starting = a.audit;
    show();
    try {
      await call(`/maintenance/audits/${a.audit}${suffix}`, { body, timeout: 30000 });
      state.errors.delete(a.audit);
    } catch (e) {
      state.errors.set(a.audit, e.message);
    } finally {
      state.starting = "";
      await refresh();
    }
  }

  function report(last, audit) {
    const findings = publishable(last).sort((a, b) => ORDER[a.severity] - ORDER[b.severity]);
    const declined = findingsOf(last).filter((f) => f.check && f.check.verdict !== "accepted");
    const toggle = () => {
      if (state.opened.has(audit)) state.opened.delete(audit);
      else state.opened.add(audit);
      show();
    };
    return html`<p-accordion heading="Results of the last run" .open=${state.opened.has(audit)} @update=${toggle}>
      <p-text size="sm">${when(last.started_at)} · ${last.branch} at ${last.commit}</p-text>
      ${last.note ? html`<p-text class="audit-text" size="sm">Note: ${last.note}</p-text>` : nothing}
      ${last.changed_defaults.map((d) => html`<p-text class="audit-text" size="sm">
        ${d.default}: ${d.to}; ${d.reason}</p-text>`)}
      ${last.destination ? html`<p-text size="sm">Issues: ${last.destination}, from your note.</p-text>` : nothing}
      <p-text class="audit-text" size="sm">${last.summary}</p-text>
      ${last.verified ? html`<p-text size="sm">Every finding was checked by the verifier.</p-text>
        ${last.summary_issue?.url ? html`<p-text size="sm"><a href=${last.summary_issue.url}
          target="_blank" rel="noopener noreferrer">Summary issue</a></p-text>` : nothing}
        ${summaryPending(last) ? html`<p-text size="sm">Summary issue publication is unfinished.</p-text>` : nothing}`
        : html`<p-text size="sm">Legacy report: these findings have not been verified. This run has no verified
          summary issue.</p-text>`}
      <p-heading size="md"><h4>${last.verified ? "Accepted findings"
        : "Findings (reported by the auditor, not verified)"}</h4></p-heading>
      ${findings.length ? html`<p-table caption="Audit findings"><p-table-head><p-table-head-row>
        ${["Severity", "Type", "Finding", "Where", ...(last.verified ? ["Verification"] : [])].map((h) =>
          html`<p-table-head-cell>${h}</p-table-head-cell>`)}
        </p-table-head-row></p-table-head><p-table-body>${findings.map((f) => html`
          <p-table-row><p-table-cell>${f.severity}</p-table-cell><p-table-cell>${f.type}</p-table-cell>
            <p-table-cell>${f.finding}. ${f.url ? html`<a href=${f.url} target="_blank"
              rel="noopener noreferrer">${f.title}</a>` : html`${f.title} (not published)`}</p-table-cell>
            <p-table-cell class="audit-text">${f.where}</p-table-cell>
            ${last.verified ? html`<p-table-cell>${verification(f.check)}</p-table-cell>` : nothing}
          </p-table-row>`)}</p-table-body></p-table>`
        : html`<p-text size="sm">${last.verified ? "No finding was accepted."
          : "The auditor reported no finding."}</p-text>`}
      ${last.destination && findings.length ? html`<p-text size="sm">These are issues in ${last.destination},
        not Backlog entries.</p-text>` : nothing}
      ${last.verified ? html`<p-heading size="md"><h4>Rejected and unsure findings</h4></p-heading>
        ${declined.length ? html`<ul>${declined.map((f) => html`<li>
          <p-text class="audit-text" size="sm">${f.finding}. ${f.title} · ${f.check.verdict}
            · ${f.severity} · ${f.type} · ${f.where}</p-text>${verification(f.check)}
          </li>`)}</ul>` : html`<p-text size="sm">None.</p-text>`}` : nothing}
      ${last.parts.length ? html`<p-heading size="md"><h4>Lens parts</h4></p-heading>
        <ul>${last.parts.map((p) => html`<li class="audit-text">${p.part}: ${
          p.ran ? "Ran" : "Not run"}; ${p.note}</li>`)}</ul>` : nothing}
      <p-heading size="md"><h4>Not covered</h4></p-heading>
      ${last.not_covered.length ? html`<ul>${last.not_covered.map((n) => html`<li class="audit-text">${n}</li>`)}</ul>`
        : html`<p-text size="sm">The auditor reported no coverage limit.</p-text>`}
    </p-accordion>`;
  }

  function lastRun(a) {
    const last = a.last;
    if (!last) return html`<p-text size="sm">Never run.</p-text>`;
    const findings = publishable(last), published = findings.filter((f) => f.number != null).length;
    const pending = unpublished(last), label = last.verified ? "accepted findings" : "findings";
    const pin = last.commit ? `${last.branch} at ${last.commit.slice(0, 7)}` : `fetching ${last.branch}`;
    if (last.state === "running") return html`<p-text size="sm">Running since ${when(last.started_at)} · ${pin} · ${
      last.phase}</p-text>`;
    if (!last.commit) return html`<p-text class="audit-text" size="sm">Failed: ${last.reason}</p-text>`;
    return html`
      <p-text size="sm">Last run: ${when(last.ended_at || last.started_at)} · ${pin} · ${last.state}${
        last.state === "done" ? ` · ${published} ${label} ${last.destination ? "published" : "in the Backlog"} · `
          + `${last.not_covered.length} areas not covered` : ""}</p-text>
      ${last.state === "publishing" ? html`<p-text class="audit-text" size="sm">${published} of ${
        findings.length} ${label} are published. ${pending} publication item${pending === 1 ? "" : "s"} unfinished.${
        summaryPending(last) ? " Summary issue publication is unfinished." : ""}${
        last.reason ? ` ${last.reason}` : ""}</p-text>
        <div><p-button type="button" compact="true" variant="secondary" .loading=${state.starting === a.audit}
          ?disabled=${!!state.starting} @click=${() => finish(a)}>Finish publishing</p-button></div>` : nothing}
      ${last.state === "failed" ? html`<p-text class="audit-text" size="sm">Failed: ${last.reason}</p-text>` : nothing}
      ${last.state === "done" || last.state === "publishing" ? report(last, a.audit) : nothing}`;
  }

  function row(action) {
    const key = action.href.slice("#audit-".length), a = state.rows.find((a) => a.audit === key);
    if (!a) return html`<p-text class="audit-text" size="sm">${state.reading
      ? `Could not read the audits: ${state.reading}` : "Reading the project's audits."}</p-text>`;
    const why = blockedOf(project) || a.blocked;
    const keep = (e) => state.notes.set(a.audit, e.target.value);
    return html`<div id=${`audit-${a.audit}`} class="audit">
      <p-textarea label=${`${a.name} note (optional)`} rows="2" max-length="2000" counter="true"
        description="Narrow or widen this run in your own words: scope, lenses, commit, strictness or issue repository."
        .value=${live(state.notes.get(a.audit) ?? "")} @input=${keep} @change=${keep}></p-textarea>
      <div><p-button type="button" compact="true" variant="primary" .loading=${state.starting === a.audit}
        ?disabled=${!!state.starting || !!why} @click=${() => start(a)}>Start audit</p-button></div>
      ${why ? html`<p-text class="audit-text" size="sm">${why}</p-text>` : nothing}
      ${state.reading ? html`<p-text class="audit-text" size="sm">Could not refresh the audits: ${
        state.reading}. The last successful result remains below.</p-text>` : nothing}
      ${state.errors.has(a.audit) ? html`<p-inline-notification state="error" dismiss-button="false">
        <span class="audit-text">${state.errors.get(a.audit)}</span></p-inline-notification>` : nothing}
      ${lastRun(a)}
    </div>`;
  }

  return { row, refresh };
}
