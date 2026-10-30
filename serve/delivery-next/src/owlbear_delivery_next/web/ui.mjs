// What every Delivery page shares (TD-264): the token, calls to the host and the design system's arrival.
// Under the machine host (TD-242) ?project= names the project a page shows. The Changes page also shows all projects
// (TD-241): it declares <meta name="owlbear-scope" content="all">, and without ?project= it lists every project.

import { html, nothing, render } from "/assets/lit-html/3.3.3/lit-html.js";

const hash = new URLSearchParams(location.hash.slice(1));
if (hash.get("token")) {
  sessionStorage.setItem("token", hash.get("token"));
  history.replaceState(null, "", location.pathname + location.search);  // ?project= and ?change= stay
}
// Sections that moved to Menu ▸ Updates (D-01M63C5VGFWJ709X2GA0CE8Q5B): their old addresses open the new pages.
const MOVED = { "/maintenance#owlbear": "/updates/owlbear", "/config#pack": "/updates/impeccable" };
const moved = () => MOVED[location.pathname + location.hash];
function move() {  // the address bar's own fragment change does not load the page again
  if (moved()) location.replace(moved() + location.search);  // ?project= stays
}
addEventListener("hashchange", move);
if (moved()) {
  move();
  await new Promise(() => {});
}
export const token = sessionStorage.getItem("token");
export const project = new URLSearchParams(location.search).get("project") ?? "";
const scope = document.querySelector('meta[name="owlbear-scope"]')?.content ?? "project";

// Where a project answers (this page's unless *of* names another): its own API on the machine host, else the host's.
export function api(path, of = project) {
  return of ? `/p/${encodeURIComponent(of)}/api/next${path}` : `/api/next${path}`;
}

// A page address with the project kept and *params* set (an empty value drops one); a #section stays last.
export function here(params = {}, to = location.pathname) {
  const [path, section] = to.split("#");
  const query = new URLSearchParams(project ? { project } : {});
  for (const [key, value] of Object.entries(params)) {
    if (value) query.set(key, value);
    else query.delete(key);
  }
  const said = query.toString();
  return `${path}${said ? `?${said}` : ""}${section ? `#${section}` : ""}`;
}

export class HostDown extends Error {
  constructor() {
    super("Delivery is not running. Start it, then reload this page.");
  }
}

// Delivery did not answer within the call's time: it may be up but busy, so it is not said to be down. A call that
// changes something (*sent*) may have been done all the same; it is never sent again, and a caller that reads the
// state again says *reread* instead of the message.
export class Slow extends Error {
  constructor(sent, seconds) {
    const unsure = `Delivery did not answer within ${seconds} s, so this may have been done or not. It was not sent `
      + "again;";
    super(sent ? `${unsure} reload the page to see which before you try again.`
      : `Delivery is slow to answer: no reply within ${seconds} s. Try again in a moment.`);
    this.sent = sent;
    this.reread = sent ? `${unsure} the page now shows Delivery's state as read again.` : this.message;
  }
}

export class Restarted extends Error {
  constructor() {
    super("Delivery restarted at a new address. Open the link from chat or owlbear status.");
  }
}

// The host's error detail in words: a validation list names each field, anything else is said as given.
function said(detail) {
  if (Array.isArray(detail)) {
    return detail.map((e) => {
      const at = (e.loc ?? []).filter((p, i) => !(i === 0 && p === "body")).join(".");
      return at ? `${at}: ${e.msg}` : e.msg;
    }).join("; ");
  }
  return typeof detail === "string" ? detail : detail ? JSON.stringify(detail) : "";
}

// One call to the host's API; GET without a body. Throws HostDown when it cannot be reached, Slow when it did not
// answer in *timeout* ms, Restarted, or an Error with the host's words.
// A *machine* call goes to the machine host's own routes; *of* names the project when it is not the page's.
export async function call(path, { method, body, timeout = 5000, machine = false, of = project } = {}) {
  if (!token) throw new Error("Open the URL the host printed, including #token=…");
  const init = { method: method ?? (body ? "POST" : "GET"), headers: { Authorization: `Bearer ${token}` },
    signal: AbortSignal.timeout(timeout) };
  if (body !== undefined) {
    init.body = JSON.stringify(body);
    init.headers["Content-Type"] = "application/json";
  }
  let response;
  try {
    response = await fetch(machine ? `/api/next${path}` : api(path, of), init);
  } catch (error) {
    if (error?.name === "TimeoutError") throw new Slow(init.method !== "GET", timeout / 1000);
    throw new HostDown();
  }
  if (response.status === 401) throw new Restarted();
  const data = await response.json().catch(() => null);
  if (!response.ok || data === null) {
    const error = new Error(said(data?.detail) || `Delivery answered ${response.status} ${response.statusText}`);
    error.status = response.status;
    throw error;
  }
  return data;
}

// Resolves once the design system defined *tags*, so property bindings reach upgraded elements.
export function defined(tags) {
  return Promise.all(tags.map((t) => customElements.whenDefined(t)));
}

let failed = "";  // why the machine host's state could not be read the last time, if it could not
let asked = 0, applied = 0, settled = 0;

// Reads the machine host's projects and pause into the bar: null on a clone's own host (which has no such route), what
// it last read when they cannot be read. Reads overlap (a poll and an action's reread) and settle in any order: an
// older answer never replaces a newer one's, and a newer read that failed never discards what an older one found.
async function read() {
  const n = ++asked;
  let data = null, why = "";
  try {
    data = await call("/projects", { machine: true });
  } catch (error) {
    if (error.status !== 404) why = error.message;
  }
  if (!why && n > applied) {
    applied = n;
    bar.data = data;
  }
  if (n > settled) {
    settled = n;
    failed = why;
  }
}

const bar = { data: null, busy: "", error: "", packed: "", installing: false };
await read();
const listed = (id) => bar.data.projects.some((p) => p.id === id);
if (bar.data && !listed(project) && (project || scope !== "all")) {
  const first = bar.data.projects.find((p) => p.state === "loaded") ?? bar.data.projects[0];
  if (first || project) {  // a project page shows one project: the first loaded one when the link named none
    location.replace(here({ project: first && scope !== "all" ? first.id : "" }, location.pathname + location.hash));
    await new Promise(() => {});
  }
}

// The projects a page shows: this one, or under the All filter every loaded one; null when no machine host serves it.
export function shown() {
  if (!bar.data) return null;
  return bar.data.projects.filter((p) => p.state === "loaded" && (!project || p.id === project));
}

// What keeps the page from opening another project or page: a page with unsaved edits registers it, saying why.
let unsaved = () => "";
export function guard(why) {
  unsaved = why;
}

// Whether unsaved edits keep the page where it is; the bar says why. Checked before anything changes or opens.
export function held() {
  if (!(bar.error = unsaved())) return false;
  showBar();
  return true;
}

// The machine's state changed (Resume, a project added or gone): pages that show it read it again.
function changed() {
  document.dispatchEvent(new CustomEvent("owlbear-machine", { detail: bar.data }));
}

// The machine host's state as last polled (its version, engine update and Impeccable); null when none serves the page.
export function machineState() {
  return bar.data;
}

// Why the machine host's state could not be read the last time, or "": what machineState() shows may be older.
export function unread() {
  return failed;
}

// Every loaded project, whatever the page shows: where an action may go; null when no machine host serves it.
export function loaded() {
  return bar.data ? bar.data.projects.filter((p) => p.state === "loaded") : null;
}
for (const link of document.querySelectorAll("#top a[href^='/']")) link.href = here({}, link.getAttribute("href"));
// The guard covers every link of the top row, the menu and the notes under it; a link opened in another tab leaves
// this page as it is.
document.addEventListener("click", (e) => {
  const away = !e.defaultPrevented && e.button === 0 && !(e.metaKey || e.ctrlKey || e.shiftKey || e.altKey);
  if (away && e.target.closest?.("#top a[href], #machine a[href]") && held()) e.preventDefault();
}, { capture: true });

// The machine's state read again after a page changed it (a project added, removed or adopted).
export async function reread() {
  await read();
  if (bar.data) showBar();
  changed();
}

// One action of the bar: its button shows it running; an error is said beside the bar until the next action.
async function act(name, work) {
  bar.busy = name;
  bar.error = "";
  showBar();
  try {
    await work();
  } catch (error) {
    bar.error = error instanceof Slow ? error.reread : error.message;  // the machine's state is read again below
  }
  bar.busy = "";
  await reread();
}

function control(label, onclick, { variant = "secondary", busy = false, title } = {}) {
  return html`<p-button type="button" compact="true" variant=${variant} .loading=${busy} title=${title ?? nothing}
    @click=${onclick}>${label}</p-button>`;
}

function chosen(p, all) {
  const twin = all.some((o) => o !== p && o.name === p.name);
  return `${p.name}${twin ? ` (${p.path})` : ""}${p.state === "loaded" ? "" : ` · ${p.state}`}`;
}

// The top row's end: which project the page shows, or Add project while there is none, and Pause. Adding, removing
// and adopting live on the Projects page (D-01M63C8DA1D95Z7M9ZYWVYYNF7).
function controls() {
  const { projects, paused } = bar.data;
  const go = (e) => {
    if (held()) {
      e.target.value = project;  // the page keeps showing the project being edited
      return showBar();
    }
    location.assign(here({ project: e.target.value, change: "" }));
  };
  return html`
    ${projects.length ? html`<p-select label="Project" hide-label="true" compact="true" .value=${project}
      @change=${go}>
      ${scope === "all" ? html`<p-select-option value="">All projects</p-select-option>` : nothing}
      ${projects.map((o) => html`<p-select-option value=${o.id}>${chosen(o, projects)}</p-select-option>`)}
    </p-select>` : html`<p-link compact="true" variant="primary"><a href=${location.pathname === "/projects" ? "#add"
      : here({}, "/projects")}>Add project</a></p-link>`}
    ${paused ? nothing : control("Pause Delivery", () => act("pause", () => call("/pause", { method: "POST",
      machine: true })), { busy: bar.busy === "pause", title: PAUSE_TIP })}`;
}

// What the owner should know under the top row: the shown project's trouble, the pause, updates and errors.
function notes() {
  if (!bar.data) return bar.error ? html`<p role="alert">${bar.error}</p>` : nothing;
  const { projects, paused, waiting, ending, left = [], update, updated, announce } = bar.data;
  const p = projects.find((o) => o.id === project);
  const trouble = location.pathname !== "/projects" && p && (p.state !== "loaded" ? `${p.name} is ${p.state}: ${
    p.reason}` : p.setup ? `${p.name} needs setup before its chats reach Delivery.` : "");
  return html`
    ${trouble ? html`<p role="status">${trouble} <a href=${here({}, "/projects")}>Open Projects</a></p>` : nothing}
    ${paused ? html`<p class="paused" role="status">${ending
        ? `OwlBear stops once nothing runs${left.length ? `; it waits for ${left.join("; ")}` : ""}.`
        : `Delivery is paused: ${waiting} Change${waiting === 1 ? "" : "s"} would continue.`}
      ${control("Resume", () => act("resume", () => call("/resume", { method: "POST", machine: true })),
        { variant: "primary", busy: bar.busy === "resume" })}
      ${ending ? nothing : control("Run updates now", runUpdates, { busy: bar.busy === "update" || updating(update) })}
      ${!ending && bar.data.update_while_paused ? control("Pause and stop when idle", stopWhenIdle,
        { busy: bar.busy === "pause-stop", title: STOP_TIP }) : nothing}</p>` : nothing}
    ${announce ? note("update-announce", "info", html`OwlBear updates to ${announce.version} in
      ${clock(announced())}.`, ["Postpone", () => act("postpone", seen), bar.busy === "postpone"]) : nothing}
    ${update?.phase && update.phase !== "idle" ? note("update-state", "info", html`Update${update.version
      ? ` to ${update.version}` : ""}: ${update.phase}${update.detail ? ` · ${update.detail}` : ""} ·
      ${updates("owlbear", "OwlBear")}`) : nothing}
    ${updated && localStorage.getItem(SEEN) !== updated ? note("update-done", "success", `OwlBear now runs
      ${updated}.`, ["OK", () => { localStorage.setItem(SEEN, updated); showBar(); }]) : nothing}
    ${banners(bar.data.pack)}
    ${bar.error ? html`<p role="alert">${bar.error}</p>` : nothing}`;
}

// S4: an update's news is a PDS notification, its one answer the notification's own button.
function note(id, state, said, [label, onaction, busy = false] = []) {
  return html`<p-inline-notification id=${id} state=${state} dismiss-button="false"
    action-label=${label ?? nothing} .actionLoading=${busy} @action=${onaction ?? nothing}>${said}
    </p-inline-notification>`;
}

function when(iso) {
  return iso ? new Date(iso).toLocaleString() : "";
}

function updates(name, label) {  // the Updates page a note leads to
  return html`<a href=${here({}, `/updates/${name}`)}>Updates → ${label}</a>`;
}

// D-01M61GW2EAHFFRFHF014A14K98: every page says when this version's Impeccable is missing or failed to install,
// with Install, and when a released OwlBear version carries a newer pack, with Update now.
function banners(pack) {
  const install = pack?.install, release = pack?.release, named = (p) => (p ? `Impeccable (${p})` : "Impeccable");
  let missing = nothing;
  if (install) {
    const running = install.state === "installing", of = install.version ? ` for OwlBear ${install.version}` : "";
    const said = running ? `Installing ${named(install.pack)}${of}…`
      : install.state === "failed" ? `Installing ${named(install.pack)}${of} failed${install.at
        ? ` (${when(install.at)})` : ""}${install.detail ? `: ${install.detail}` : "."}`
      : `${named(install.pack)} that this OwlBear version${install.version ? `, ${install.version},` : ""} pins is `
        + "not installed on this machine; the visual rounds use it.";
    missing = html`<p class="banner" role="status" id="pack-install-banner"><span>${said}
      ${updates("impeccable", "Impeccable")}</span>
      ${control("Install", installPack, { variant: "primary", busy: running || bar.busy === "install" })}</p>`;
  }
  const newer = release?.state === "newer" ? html`<p class="banner" role="status" id="pack-release-banner"><span>
    OwlBear ${release.version} carries a newer ${named(release.pack)}; this version pins ${named(release
      .running_pack)}. ${release.checked_at ? `Checked ${when(release.checked_at)}.`
      : "When it was checked is unknown."} ${updates("owlbear", "OwlBear")}
    </span>${control("Update now", runUpdates, { busy: bar.busy === "update" || updating(bar.data.update) })}</p>`
    : nothing;
  const done = bar.packed ? html`<p role="status" id="pack-install-said">${bar.packed}</p>` : nothing;
  return html`${missing}${newer}${done}`;
}

// Install answers at once and installs in the background: the polled state shows it running, then how it ended.
async function installPack() {
  bar.packed = "";
  await act("install", async () => {
    const got = await call("/impeccable/install", { method: "POST", machine: true, timeout: 15000 });
    if (got.refused) bar.packed = `Not installed now: ${got.refused}.`;
    else if (!got.install) bar.packed = "Impeccable is installed on this machine.";
    else if (got.install.state === "installing") bar.installing = true;
  });
}

const SEEN = "owlbear-version-seen";  // the version the owner was told about, so he is told once (TD-299)
// Plain Pause may still update; the stop-when-idle choice starts nothing and stops (TD-288).
const PAUSE_TIP = "Holds Delivery's work on Changes. OwlBear may still update itself while paused.";
const STOP_TIP = "Starts no work, waits for running steps, then stops OwlBear.";
const USE = 60_000;  // a page says the owner is at it at most once a minute (§7)
let told = 0, until = 0;

// The owner's use: a page he works in, while it is visible; polls never count.
function seen() {
  told = Date.now();
  return call("/seen", { method: "POST", machine: true });
}
for (const kind of ["keydown", "pointerdown", "wheel", "scroll", "focusin"]) {
  addEventListener(kind, () => {
    if (document.visibilityState === "visible" && bar.data && Date.now() - told >= USE) seen().catch(() => {});
  }, { passive: true, capture: true });
}

// Seconds left of an announced update, counted here between polls.
function announced() {
  return Math.max(0, Math.round((until - Date.now()) / 1000));
}

function clock(seconds) {
  return `${Math.floor(seconds / 60)}:${String(seconds % 60).padStart(2, "0")}`;
}

// Whether an update runs now: its button shows it running.
function updating(update) {
  return Boolean(update?.phase) && !["idle", "current", "failed", "refused"].includes(update.phase);
}

export async function runUpdates() {
  const yes = await window.ask({ title: "Run updates now?",
    now: "OwlBear installs the newest version of this machine's channel beside the running one and checks it.",
    then: "Once no step, check environment or Impeccable update runs, it switches to that version; this page "
      + "keeps working and says once which version runs.",
    after: "Delivery stays paused or running as it is.", instead: "OwlBear keeps running this version.",
    yes: "Run updates now" });
  if (yes) await act("update", () => call("/update", { method: "POST", machine: true }));
}

async function stopWhenIdle() {
  const yes = await window.ask({ title: "Pause and stop OwlBear when idle?",
    now: "No step starts from now on; running steps finish and check environments close.",
    then: "OwlBear stops once nothing runs. Start it again with owlbear start.",
    after: "Resume cancels the stop while OwlBear still waits.", instead: "Delivery stays paused and OwlBear runs.",
    yes: "Pause and stop" });
  if (yes) await act("pause-stop", () => call("/pause-stop", { method: "POST", machine: true }));
}

function showBar() {
  const top = document.getElementById("controls");
  if (top && bar.data) render(controls(), top);
  let root = document.getElementById("machine");
  if (!root) {
    root = Object.assign(document.createElement("section"), { id: "machine" });
    root.setAttribute("aria-label", "OwlBear's state");
    document.getElementById("top")?.after(root);
  }
  render(notes(), root);
}

if (bar.data) {
  await defined(["p-select", "p-select-option", "p-link", "p-button"]);
  showBar();
  const counted = () => { until = bar.data?.announce ? Date.now() + bar.data.announce.left * 1000 : 0; };
  counted();
  setInterval(async () => {
    if (bar.busy) return;
    const was = bar.data?.paused, before = Boolean(bar.data?.announce);
    await read();  // always read: an announcement must reach every page (§7)
    if (bar.installing && bar.data?.pack?.install?.state !== "installing") {  // the Install started here has ended
      bar.installing = false;
      bar.packed = bar.data.pack.install ? "" : "Impeccable is installed on this machine.";
      showBar();
    }
    counted();
    // never re-rendered under the owner's typing, unless an announcement starts or runs: its countdown stays true
    if (!document.activeElement?.closest?.("#machine, #controls") || before || bar.data?.announce) showBar();
    if (bar.data?.paused !== was) changed();
    document.dispatchEvent(new CustomEvent("owlbear-polled", { detail: bar.data }));  // what a page shows of it
  }, 5000);
  setInterval(() => { if (bar.data?.announce) showBar(); }, 1000);
}
