import { html, nothing } from "/assets/lit-html/3.3.3/lit-html.js";
import { call } from "/assets/ui.mjs";

const PATH = "/maintenance/audits/suppressions";
const when = (at) => new Date(at).toLocaleString();

export function suppressionReview(show, reload) {
  const state = { open: false, verdicts: [], error: "", reading: "", writing: false };

  async function refresh() {
    if (!state.open) return;
    try {
      state.verdicts = (await call(`${PATH}/verdicts`, { timeout: 15000 })).verdicts;
      state.reading = "";
    } catch (e) {
      state.reading = e.message;
    }
  }

  async function write(suffix, body) {
    state.writing = true;
    show();
    try {
      await call(`${PATH}${suffix}`, { body, timeout: 30000 });
      state.error = "";
    } catch (e) {
      state.error = e.message;
    } finally {
      state.writing = false;
      await reload();
    }
  }

  async function start(a) {
    const sure = await window.ask({
      title: "Start suppression review?", yes: "Start review", no: "Cancel",
      now: `Delivery fetches ${a.branch} and pins its head, excluding working changes. Quality judge: `
        + `${a.role.model}, ${a.role.effort} effort. Read-only, at most 10 batches of 60 directives and `
        + "lint configuration items. Existing verdicts count, except a chat's advice.",
      then: "Each completed batch is recorded. Refused groups become Backlog improvements, with no summary issue. "
        + "The run asks nothing and uses AI credits, also while Delivery is paused.",
      after: "This row shows counts and Backlog links. Start again for remaining items. Verdicts lets you accept "
        + "or judge again. A failure keeps completed verdicts; Finish publishing uses saved receipts.",
      instead: "Nothing starts; recorded verdicts stay as they are.",
    });
    if (sure) await write("", {});
  }

  async function finish() {
    const sure = await window.ask({
      title: "Finish publishing suppression review?", yes: "Finish publishing", no: "Cancel",
      now: "Delivery checks the saved receipts and finishes the refused groups' Backlog entries and detail comments.",
      then: "No judge session runs and no AI credits are used. Existing entries and comments are not opened again.",
      after: "This row shows the Backlog links and counts. Use Verdicts to read or change the recorded judgments.",
      instead: "Publication stays unfinished. You can finish it here later.",
    });
    if (sure) await write("/publish", {});
  }

  async function change(line, action) {
    const again = action === "again";
    const sure = await window.ask({
      title: again ? "Judge these suppressions again?" : "Accept these suppressions?",
      yes: again ? "Judge again" : "Accept", no: "Cancel", destructive: again,
      now: `${line.count} ${line.directive} in ${line.place}. ` + (again
        ? "Their counting verdicts are set aside. History is kept; no session starts now."
        : "Your acceptance replaces these refusals. The refusals stay in history; no session starts."),
      then: again
        ? "These copies count as not yet judged. The next Start takes them to the judge, using AI credits."
        : "These copies count as owner-accepted and the next review leaves them out. Existing Backlog entries stay open.",
      after: again
        ? "Start a review here when ready. Earlier Backlog entries remain for you to triage."
        : "You can use Judge again later. Triage any existing entry on the Backlog page.",
      instead: "The counting verdicts and Backlog entries stay as they are.",
    });
    if (sure) await write("/verdicts", { id: line.id, action });
  }

  async function toggle() {
    state.open = !state.open;
    show();
    await refresh();
    show();
  }

  function verdicts(a) {
    const busy = state.writing || a.blocked === "an audit is running for this project" || a.last?.state === "running";
    return html`<div><p-button type="button" variant="secondary" compact="true"
        @click=${toggle}>${state.open ? "Hide verdicts" : "Verdicts"}</p-button></div>
      ${state.open ? html`<section aria-label="Suppression verdicts">
        <p-heading size="md"><h4>Verdicts by rule and place</h4></p-heading>
        ${state.reading ? html`<p-text class="review-text" size="sm">Could not read the verdicts: ${
          state.reading}. The last successful list remains below.</p-text>` : nothing}
        ${state.verdicts.length ? html`<ul class="suppression-verdicts">${state.verdicts.map((line) => html`<li>
          <p-text class="review-text" size="sm">${line.directive} · ${line.place} · ${line.count} · ${
            line.verdict}</p-text>
          <p-text class="review-text" size="sm">${line.reason}</p-text>
          <div class="verdict-actions">
            <p-button type="button" variant="secondary" compact="true" ?disabled=${busy}
              @click=${() => change(line, "again")}>Judge again</p-button>
            ${line.verdict === "refused" ? html`<p-button type="button" variant="secondary" compact="true"
              ?disabled=${busy} @click=${() => change(line, "accept")}>Accept</p-button>` : nothing}
          </div>
        </li>`)}</ul>` : html`<p-text size="sm">No counting verdicts for the pinned inventory.</p-text>`}
      </section>` : nothing}`;
  }

  function lastRun(a) {
    const last = a.last;
    if (!last) return html`<p-text size="sm">Never run.</p-text>`;
    const counts = last.counts;
    const pin = last.commit ? `${last.branch} at ${last.commit}` : `fetching ${last.branch}`;
    const links = [...new Map([...(last.backlog_entries ?? []), ...(last.findings ?? [])]
      .filter((f) => f.url).map((f) => [f.url, f])).values()];
    return html`<p-text class="review-text" size="sm">${last.state === "running" ? "Running since" : "Last run:"} ${
      when(last.ended_at || last.started_at)} · ${pin} · ${last.state}${last.phase ? ` · ${last.phase}` : ""}</p-text>
      ${counts && "held" in counts ? html`<p-text class="review-text" size="sm">${counts.held} held · ${
        counts.accepted} accepted · ${counts.refused} refused · ${counts.unjudged} not yet judged</p-text>
        ${counts.unjudged ? html`<p-text class="review-text" size="sm">${`${counts.unjudged} not yet judged: start again to continue.`}</p-text>` : nothing}` : nothing}
      ${last.reason ? html`<p-text class="review-text" size="sm">${last.state === "publishing"
        ? "Publishing unfinished" : "Failed"}: ${last.reason}</p-text>` : nothing}
      ${last.backlog_error ? html`<p-text class="review-text" size="sm">Could not read the Backlog links: ${
        last.backlog_error}</p-text>` : nothing}
      ${last.judging_reason && last.state === "publishing" ? html`<p-text class="review-text" size="sm">
        Judging stopped: ${last.judging_reason}. Completed verdicts remain recorded.</p-text>` : nothing}
      ${links.length ? html`<p-text size="sm">Backlog entries:</p-text><ul>${links.map((f) => html`<li>
        <a href=${f.url} target="_blank" rel="noopener noreferrer">#${f.number}${f.title ? ` ${f.title}` : ""}</a></li>`)}</ul>` : nothing}
      ${last.state === "publishing" ? html`<p-text class="review-text" size="sm">Refused groups or their detail comments
        are not all published. Finish publishing uses the saved receipts.</p-text>
        <div><p-button type="button" variant="secondary" compact="true" ?disabled=${state.writing || a.blocked === "an audit is running for this project"}
          @click=${finish}>Finish publishing</p-button></div>` : nothing}`;
  }

  function row(a, why) {
    const blocked = why || (a.last?.state === "publishing" ? "Finish publishing the previous run before starting again." : "");
    return html`<div id="audit-suppressions" class="audit suppression-review">
      <div><p-button type="button" variant="primary" compact="true" .loading=${state.writing}
        ?disabled=${state.writing || !!blocked} @click=${() => start(a)}>Start review</p-button></div>
      ${blocked ? html`<p-text class="review-text" size="sm">${blocked}</p-text>` : nothing}
      ${state.error ? html`<p-inline-notification state="error" dismiss-button="false">
        <span class="review-text">${state.error}</span></p-inline-notification>` : nothing}
      ${lastRun(a)}
      ${verdicts(a)}
    </div>`;
  }

  return { row, refresh };
}
