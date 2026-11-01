// Updates ▸ Porsche Design System (D-01M63CBWYPQZF3WBZ915YY3Q28): the release the pages load and the newest on npm,
// Search for updates and the settings link, and the check of the pages for deprecated use (audit.mjs). Updating it
// is not offered yet; until then it never counts as available.
import { html, render } from "/assets/lit-html/3.3.3/lit-html.js";
import { defined, machineState } from "/assets/ui.mjs";
import { auditPart, followAudit, readAudit } from "./audit.mjs";
import { frame, framed } from "./frame.mjs";

function show() {
  render(html`${frame("pds", { running: "Pages load" })}
    ${machineState() ? html`<p-inline-notification id="pds-later" state="info" dismiss-button="false"
      heading="Updating it comes later" heading-tag="h2" description="OwlBear's pages load the release named above.
      Taking a newer one is not offered here yet, so a newer release is shown but not marked as available in the
      menu."></p-inline-notification>` : ""}
    ${auditPart()}`, document.getElementById("page"));
}

await defined(["p-heading", "p-text", "p-button", "p-tag", "p-inline-notification"]);
framed(show);
followAudit(show);
show();
readAudit();
