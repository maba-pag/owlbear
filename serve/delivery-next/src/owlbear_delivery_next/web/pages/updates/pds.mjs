// Updates ▸ Porsche Design System (D-01M63CBWYPQZF3WBZ915YY3Q28): the release the pages load and the newest on npm,
// Search for updates and the settings link; the one update of this machine that brings the pages to a newer release
// (pack.mjs acts, run.mjs shows it), and the check of the pages for deprecated use (audit.mjs).
import { html, nothing, render } from "/assets/lit-html/3.3.3/lit-html.js";
import { defined } from "/assets/ui.mjs";
import { auditPart, followAudit, readAudit } from "./audit.mjs";
import { frame, framed } from "./frame.mjs";
import { follow, own, readPack } from "./pack.mjs";
import { others, runPart, startPart } from "./run.mjs";

const CHECKS = "the deprecation audit and the browser tests";
own.kind = {
  name: "PDS", uses: "labels and spend", label: "Start update",
  pinned: null, runs: "/maintenance/pds/runs", update: "/pds/update",
  intro: `An update takes the newest release from npm, runs ${CHECKS} on the pages, has an updater session fix what `
    + "they find and a challenger check the change, all with model requests. Only if every check passes, or if you "
    + "accept it after its challenge rounds end without a pass, it commits the release and the changed pages on its "
    + "own branch, opens a pull request to main and merges it once CI passes.",
  start: {
    title: "Update the Porsche Design System?", yes: "Start update", no: "Keep the current release",
    now: "Delivery takes the newest release from npm with its skills and checks it against the one the pages "
      + `load; ${CHECKS} run on the pages, an updater session fixes what they find, and a challenger checks the `
      + "change. The challenger's findings go back to the updater. It runs on this project's labels and AI credits.",
    then: `Only if ${CHECKS} pass and the challenger passes the change, it commits the release, its skills and the `
      + "pages the updater changed, opens a pull request to main and merges it once CI passes; should the pages "
      + `change on the way, ${CHECKS} and the challenger run again first. It asks you here about the audit's manual `
      + "follow-ups, when the rounds end without a pass and when the challenger upholds a finding the updater "
      + "rejected.",
    after: "The pages load the new release once this machine takes the OwlBear version that carries it. If a stage "
      + "fails, nothing changes and this page says why.",
    instead: "The pages keep the release they load.",
  },
  activate: { title: "Publish the update without a passing challenge?",
    now: "Delivery publishes the candidate as it is now: it commits the release, its skills and the pages the "
      + "updater changed, opens a pull request to main and merges it once CI passes.",
    after: "The pages load the new release once this machine takes the OwlBear version that carries it." },
  discard: { title: "Discard the PDS update?",
    then: "Nothing is published: the pages keep the release they load, and the run's candidate is not used again." },
  merged: "The merged release reaches each machine as it takes the OwlBear version that carries it; until then its "
    + "pages load the release they have.",
};

function show() {
  const r = own.runs;
  render(html`${frame("pds", { running: "Pages load" })}
    <section id="pack" class="panel" aria-labelledby="pack-title">
      <p-heading size="lg"><h2 id="pack-title">The update</h2></p-heading>
      ${startPart()}
      ${r ? html`<div class="part">${runPart(r.run)}${others(r)}</div>` : own.unread.runs ? nothing
        : html`<p-text size="sm">Reading the PDS runs…</p-text>`}
    </section>
    ${auditPart()}`, document.getElementById("page"));
}

await defined(["p-heading", "p-text", "p-button", "p-tag", "p-inline-notification", "p-textarea", "p-radio-group"]);
follow(show);
framed(show);
followAudit(show);
document.addEventListener("visibilitychange", () => { if (!document.hidden) readPack(); });
show();
readPack();
readAudit();
