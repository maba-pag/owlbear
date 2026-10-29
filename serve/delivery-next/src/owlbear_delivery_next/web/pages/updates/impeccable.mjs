// Updates ▸ Impeccable (D-01M63C5VGFVT3DVCC888B78K2A), the same in every project and under All projects: the frame,
// where the pack stands (installed here, released with an OwlBear version, published by an update, the candidate an
// update validates), and the one Impeccable update of this machine, answerable from wherever the page is opened.
import { html, nothing, render } from "/assets/lit-html/3.3.3/lit-html.js";
import { defined, machineState, project } from "/assets/ui.mjs";
import { readChecks, update } from "./checks.mjs";
import { frame, framed, sentence, when } from "./frame.mjs";
import { ADMIT, button, follow, own, readPack, start } from "./pack.mjs";
import { others, runPart } from "./run.mjs";

function installed(i) {  // a missing pack is the running version's; one installing or failed names its version
  const whose = i.version ? `Impeccable of OwlBear ${i.version}` : "An Impeccable pack";
  return i.state === "missing" ? "This version's pack is not installed"
    : `${whose} ${i.state === "installing" ? "is being installed" : "failed to install"}`;
}

function released(bar) {
  const r = bar?.pack?.release;
  if (!bar) return "";
  if (r?.state === "newer") {
    return `OwlBear ${r.version} carries the newer pack ${r.pack}; this version pins ${r.running_pack}.`;
  }
  return "No released OwlBear version carries a newer pack.";
}

function published(run) {
  const p = run?.published;
  if (!p?.commit) return run ? `Nothing yet from the last update, run in ${run.name}.` : "Nothing yet.";
  const pr = p.url ? `pull request #${p.number}` : `commit ${p.commit.slice(0, 12)} on ${p.branch}`;
  return `${sentence(pr)}${p.merged ? `, merged into main as ${p.merged.slice(0, 12)}` : p.url ? ", not merged yet"
    : ""}; a machine takes it with the OwlBear version that carries it.`;
}

function candidate(run) {
  if (!run || !["running", "waiting"].includes(run.state)) return "None: no update runs now.";
  const made = (run.stages ?? []).find((s) => s.name === "candidate" && s.detail)?.detail;
  return `${made ?? "Being prepared"}, in ${run.name}'s update; it is not active anywhere until it is published and `
    + "released.";
}

function fact(term, said, id) {
  return said ? html`<div><dt>${term}</dt><dd id=${id}>${said}</dd></div>` : nothing;
}

function stands() {
  const pin = own.pinned, bar = machineState(), install = bar?.pack?.install, run = own.runs?.run;
  const plain = (t) => String(t).replaceAll(String.fromCharCode(96), "");  // the status is CLI text with code marks
  return html`<div class="part">
    <p-heading size="md"><h3 id="pack-stands-title">Where the pack stands</h3></p-heading>
    ${own.unread.pinned ? html`<p-inline-notification id="pack-read-error" state="error" dismiss-button="false">
      Could not read Impeccable: ${own.unread.pinned}.</p-inline-notification>` : nothing}
    <dl class="facts" aria-labelledby="pack-stands-title">
      ${pin || install ? html`<div><dt>Installed</dt>
        ${pin ? html`<dd id="pack-active">Pinned: ${pin.pack} from upstream ${pin.upstream}, identity ${
          pin.identity}. ${plain(pin.status)}.</dd>` : nothing}
        ${install ? html`<dd id="pack-install-state">${installed(install)} on this machine${install.detail
          ? `: ${install.detail}` : ""}.</dd>` : nothing}</div>` : nothing}
      ${fact("Released", released(bar), "pack-release")}
      ${own.runs ? fact("Published", published(run), "pack-published") : nothing}
      ${own.runs ? fact("Candidate", candidate(run), "pack-candidate") : nothing}
    </dl>
    <p-text id="pack-notice" size="xs" color="contrast-medium">${pin ? `Upstream: ${pin.notice.said}${pin.notice
      .checked_at ? `, checked ${when(pin.notice.checked_at)}` : ", not checked yet"}.` : ""}</p-text>
  </div>`;
}

function starting() {
  const r = own.runs, run = r?.run, open = run && ["running", "waiting"].includes(run.state);
  const canStart = Boolean(project || !machineState()), busy = Boolean(open || r?.holder);
  return html`<div class="part">
    <p-heading size="md"><h3 id="pack-update-title">Update</h3></p-heading>
    <p-text size="sm">An update takes the newest upstream pack and validates it with model requests. Only if every
      stage passes, or if you accept it after its challenge rounds end without a pass, it commits it on its own
      branch, opens a pull request to main and merges it once CI passes. One runs at a time on this machine.</p-text>
    <div class="row">
      ${button("Update Impeccable", start, { id: "pack-update", icon: "refresh", variant: "primary",
        busy: own.busy === "start" || Boolean(own.awaiting),
        disabled: busy || !canStart || Boolean(own.busy) || Boolean(own.awaiting) })}
      ${canStart ? nothing : html`<p-text id="pack-choose" size="sm">Choose a project above to start one: it runs on
        that project's labels, calibration and spend.</p-text>`}
    </div>
    ${own.awaiting ? html`<p-inline-notification id="pack-admitting" state="info" dismiss-button="false">
      Delivery has not answered the start yet; it may still be checking GitHub for an open Impeccable pull request.
      It was not sent again. This page looks for the run until ${new Date(own.awaiting.until)
        .toLocaleTimeString()}.</p-inline-notification>` : nothing}
    ${own.lost ? html`<p-inline-notification id="pack-start-unknown" state="warning" dismiss-button="false">
      Whether the update started is unknown: Delivery did not answer, and no new run appeared within
      ${ADMIT / 1000} s. It was not sent again. Reload the page to see Delivery's state before you start another.
      ${button("Reload", () => location.reload(), { id: "pack-reload" })}</p-inline-notification>` : nothing}
    ${own.error ? html`<p-inline-notification id="pack-error" state="error" dismiss-button="false">${
      sentence(own.error)}</p-inline-notification>` : nothing}
    ${own.unread.runs ? html`<p-inline-notification id="pack-runs-error" state="error" dismiss-button="false">
      Could not read the Impeccable runs: ${own.unread.runs}.</p-inline-notification>` : nothing}
  </div>`;
}

function view() {
  const r = own.runs;
  return html`${frame("impeccable", { running: "Pinned upstream" })}
    <section id="pack" class="panel" aria-labelledby="pack-title">
      <p-heading size="lg"><h2 id="pack-title">The pack</h2></p-heading>
      ${stands()}
      ${starting()}
      ${r ? html`<div class="part">${runPart(r.run)}${others(r)}</div>` : own.unread.runs ? nothing
        : html`<p-text size="sm">Reading the Impeccable runs…</p-text>`}
    </section>`;
}

function show() {
  render(view(), document.getElementById("page"));
}

// A search that found a newer upstream release also refreshed what the pack part says of upstream.
let looked = update("impeccable")?.checked_at;
function checked() {
  const at = update("impeccable")?.checked_at;
  if (at !== looked) [looked] = [at, readPack()];
  show();
}

await defined(["p-heading", "p-text", "p-button", "p-tag", "p-inline-notification", "p-textarea"]);
follow(show);
framed(checked);
document.addEventListener("visibilitychange", () => { if (!document.hidden) readPack(); });
show();
readPack();
readChecks();
