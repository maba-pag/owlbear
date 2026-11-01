// The frame the three Updates pages share (D-01M63CBWYPQZF3WBZ915YY3Q28): the version in use and the newest one,
// Search for updates, the last successful check, a failure's time and reason only once two came in a row, and the
// link to the settings that say how often it looks.
import { html, nothing } from "/assets/lit-html/3.3.3/lit-html.js";
import { here, machineState } from "/assets/ui.mjs";
import { checks, listen, readChecks, search, update } from "./checks.mjs";

export const SETTINGS = "/config#machine-title";  // Settings ▸ This machine, where every update setting is
const STATES = { newer: ["newer version", "info"], current: ["up to date", "success"],
  unknown: ["not known", "secondary"], failed: ["check failed", "error"],
  running: ["update running", "secondary"], waiting: ["update waiting for you", "warning"],  // PDS's, its run's
  merged: ["merged, not released yet", "info"] };
const own = { busy: false, error: "", show: () => {} };

export function when(iso) {
  return iso ? new Date(iso).toLocaleString() : "";
}

export function sentence(text) {
  return text ? text.charAt(0).toUpperCase() + text.slice(1) : "";
}

// *show* renders the whole page; the frame calls it whenever the checks or its own state change.
export function framed(show) {
  own.show = show;
  listen(show);
  for (const kind of ["owlbear-machine", "owlbear-polled"]) document.addEventListener(kind, () => own.show());
}

async function searching(name) {
  Object.assign(own, { busy: true, error: "" });
  own.show();
  try {
    await search(name);
  } catch (e) {
    own.error = e.message;  // a timed-out search is never sent again: what the checks say now is read below
    await readChecks();
  }
  own.busy = false;
  own.show();
}

export function settingsLink(label = "Settings → This machine") {
  return html`<a href=${here({}, SETTINGS)}>${label}</a>`;
}

function often(u) {
  const by = u.hours ? `every ${u.hours} hour${u.hours === 1 ? "" : "s"}` : "only when OwlBear starts and when you "
    + "search";
  return html`<p-text id="check-settings" size="sm">It looks ${by}${u.next_at ? `; next ${when(u.next_at)}` : ""}.
    How often is set in ${settingsLink()}.</p-text>`;
}

// The state the page shows: once two failed checks are shown, the check could not answer, so it is never current
// (a newer version found before stays shown under Newest).
function standing(u) {
  return u.reason && !["failed", "unknown"].includes(u.state) ? "failed" : u.state;
}

function newest(u) {
  // the host keeps a newer version it found through failed checks, until it is applied or found withdrawn
  if (u.latest && u.latest !== u.current) {
    const last = standing(u) === "newer" ? "" : ", found by the last successful check";
    return `${u.latest}${u.detail ? ` (${u.detail})` : ""}${last}`;
  }
  if (standing(u) === "current") return `${u.latest || u.current}, the one in use`;
  return u.detail || "not known yet";
}

// The frame of update *name*: its versions and checks; *running* names the version in use.
export function frame(name, { running = "In use" } = {}) {
  if (!machineState()) {
    return html`<p-inline-notification id="check-none" state="info" dismiss-button="false" heading="Update checks are
      the machine host's" heading-tag="h2" description="This page is served by one project's own host. Open the
      address owlbear status prints to search for updates."></p-inline-notification>`;
  }
  const u = update(name);
  if (!u) {
    return checks.unread ? html`<p-inline-notification id="check-unread" state="error" dismiss-button="false">
      Could not read the update checks: ${checks.unread}.</p-inline-notification>`
      : html`<p-text id="check-reading" size="sm">Reading the update checks…</p-text>`;
  }
  const [word, tone] = STATES[standing(u)] ?? [u.state, "secondary"], busy = own.busy || u.checking;
  return html`<section id="check" class="panel" aria-labelledby="check-title">
    <div class="heading-row">
      <p-heading size="lg"><h2 id="check-title">Versions</h2></p-heading>
      <p-tag id="check-state" variant=${tone} compact="true">${word}</p-tag>
    </div>
    <dl class="facts">
      <div><dt>${running}</dt><dd id="check-current">${u.current || "not known"}</dd></div>
      <div><dt>Newest</dt><dd id="check-latest">${newest(u)}</dd></div>
      <div><dt>Last successful check</dt><dd id="check-when">${when(u.checked_at) || "none yet"}</dd></div>
    </dl>
    ${u.reason ? html`<p-inline-notification id="check-failure" state="warning" dismiss-button="false">The last
      ${u.failures} checks failed; the latest at ${when(u.attempted_at)}: ${u.reason}.</p-inline-notification>`
      : nothing}
    ${checks.unread ? html`<p-text id="check-unread" size="sm" role="alert">This may be out of date: ${checks.unread}
      </p-text>` : nothing}
    <div class="row">
      <p-button id="check-search" type="button" compact="true" variant="secondary" icon="search" .loading=${busy}
        @click=${() => searching(name)}>Search for updates</p-button>
      <p-text id="check-said" size="sm" role="status" aria-live="polite">${u.checking ? "Searching…" : ""}</p-text>
    </div>
    ${own.error ? html`<p-text id="check-error" size="sm" role="alert">${sentence(own.error)}</p-text>` : nothing}
    ${often(u)}
  </section>`;
}
