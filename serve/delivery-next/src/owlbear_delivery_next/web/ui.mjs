// What every Delivery page shares (TD-264): the token, calls to the host and the design system's arrival.
// Under the machine host (TD-242) each page shows one project, named by ?project=, until one UI shows them all.

import { html, nothing, render } from "/assets/lit-html/3.3.3/lit-html.js";

const hash = new URLSearchParams(location.hash.slice(1));
if (hash.get("token")) {
  sessionStorage.setItem("token", hash.get("token"));
  history.replaceState(null, "", location.pathname + location.search);  // ?project= and ?change= stay
}
export const token = sessionStorage.getItem("token");
export const project = new URLSearchParams(location.search).get("project") ?? "";

// Where this page's project answers: its own API on the machine host, the host's own on a clone's host.
export function api(path) {
  return project ? `/p/${encodeURIComponent(project)}/api/next${path}` : `/api/next${path}`;
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

// One call to the host's API; GET without a body. Throws HostDown, Restarted, or an Error with the host's words.
// A *machine* call goes to the machine host's own routes rather than the project's.
export async function call(path, { method, body, timeout = 5000, machine = false } = {}) {
  if (!token) throw new Error("Open the URL the host printed, including #token=…");
  const init = { method: method ?? (body ? "POST" : "GET"), headers: { Authorization: `Bearer ${token}` },
    signal: AbortSignal.timeout(timeout) };
  if (body !== undefined) {
    init.body = JSON.stringify(body);
    init.headers["Content-Type"] = "application/json";
  }
  let response;
  try {
    response = await fetch(machine ? `/api/next${path}` : api(path), init);
  } catch {
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

// Whether the design system's components arrived within three seconds; without them the page shows plain controls.
export async function designSystem(tags = ["p-heading"]) {
  const ready = Promise.all(tags.map((t) => customElements.whenDefined(t))).then(() => true);
  const pds = await Promise.race([ready, new Promise((resolve) => setTimeout(resolve, 3000, false))]);
  if (!pds) document.documentElement.classList.add("no-pds");
  return pds;
}

// The machine host's projects and pause, or null on a clone's own host (which has no such route) or when down.
async function machine() {
  try {
    return await call("/projects", { machine: true });
  } catch (error) {
    if (error.status === 404 || error instanceof HostDown) return null;
    throw error;
  }
}

const bar = { data: token ? await machine().catch(() => null) : null, draft: "", busy: "", error: "" };
if (bar.data && !bar.data.projects.some((p) => p.id === project)) {
  const first = bar.data.projects.find((p) => p.state === "loaded") ?? bar.data.projects[0];
  if (first) {  // a page always shows one project; the first loaded one when the link named none it serves
    location.replace(here({ project: first.id }));
    await new Promise(() => {});
  }
}
for (const link of document.querySelectorAll("nav a[href^='/']")) link.href = here({}, link.getAttribute("href"));

// One action of the bar: its button shows it running; an error is said beside the bar until the next action.
async function act(name, work) {
  bar.busy = name;
  bar.error = "";
  showBar();
  try {
    await work();
  } catch (error) {
    bar.error = error.message;
  }
  bar.busy = "";
  bar.data = await machine().catch(() => bar.data);
  showBar();
}

function control(label, onclick, { variant = "secondary", busy = false } = {}) {
  return customElements.get("p-button")
    ? html`<p-button type="button" compact="true" variant=${variant} .loading=${busy} @click=${onclick}>${label}</p-button>`
    : html`<button type="button" .disabled=${busy} @click=${onclick}>${label}</button>`;
}

function chosen(p, all) {
  const twin = all.some((o) => o !== p && o.name === p.name);
  return `${p.name}${twin ? ` (${p.path})` : ""}${p.state === "loaded" ? "" : ` · ${p.state}`}`;
}

async function remove(p) {
  const yes = await window.ask({ title: `Remove ${p.name}?`, now: `OwlBear stops serving ${p.path}.`,
    then: "Its Changes, settings and memory stay in the clone; nothing is deleted.",
    after: "Add the folder again to serve it once more.", instead: "It keeps running.", yes: "Remove project" });
  if (!yes) return;
  await act("remove", async () => {
    await call(`/projects/${p.id}`, { method: "DELETE", machine: true });
    location.replace(here({ project: "" }));
  });
}

function view() {
  const { projects, paused, waiting } = bar.data;
  const p = projects.find((o) => o.id === project);
  const go = (e) => location.assign(here({ project: e.target.value, change: "" }));
  const add = () => act("add", async () => {
    const added = await call("/projects", { body: { path: bar.draft.trim() }, machine: true });
    location.assign(here({ project: added.id, change: "" }));
  });
  return html`
    <div class="projects">
      ${projects.length ? html`<label>Project <select .value=${project} @change=${go}>
        ${projects.map((o) => html`<option value=${o.id} ?selected=${o.id === project}>${chosen(o, projects)}</option>`)}
      </select></label>` : html`<span>No project yet: add the folder of a clone.</span>`}
      ${p ? control("Remove project", () => remove(p), { busy: bar.busy === "remove" }) : nothing}
      ${p?.state === "replaced" ? control("Adopt the new clone", () => act("adopt", async () => {
        const adopted = await call(`/projects/${p.id}/adopt`, { method: "POST", machine: true });
        location.assign(here({ project: adopted.id }));
      }), { busy: bar.busy === "adopt" }) : nothing}
      <details ?open=${!projects.length}><summary>Add project</summary>
        <label>Folder <input type="text" placeholder="~/Projects/my-app" .value=${bar.draft}
          @input=${(e) => { bar.draft = e.target.value; }}></label>
        ${control("Add", add, { busy: bar.busy === "add" })}
      </details>
    </div>
    ${p && p.state !== "loaded" ? html`<p role="status">${p.name} is ${p.state}: ${p.reason}</p>` : nothing}
    ${p?.setup ? html`<p role="status">Setup required: the chats of ${p.name} cannot reach Delivery yet. Run
      <code>${p.setup}</code> in a terminal, then reload the project's VS Code window.</p>` : nothing}
    ${paused ? html`<p class="paused" role="status">Delivery is paused since it started: ${waiting}
      Change${waiting === 1 ? "" : "s"} would continue.
      ${control("Resume", () => act("resume", () => call("/resume", { method: "POST", machine: true })),
        { variant: "primary", busy: bar.busy === "resume" })}</p>` : nothing}
    ${bar.error ? html`<p role="alert">${bar.error}</p>` : nothing}`;
}

function showBar() {
  let root = document.getElementById("machine");
  if (!root) {
    root = Object.assign(document.createElement("section"), { id: "machine" });
    root.setAttribute("aria-label", "OwlBear projects");
    document.querySelector("nav")?.after(root);
  }
  render(view(), root);
}

if (bar.data) {
  showBar();
  setInterval(async () => {
    if (bar.busy || document.activeElement?.closest?.("#machine")) return;  // never under the owner's typing
    bar.data = await machine().catch(() => bar.data);
    showBar();
  }, 5000);
}
