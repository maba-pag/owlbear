// The Projects page (D-01M63C8DA1D95Z7M9ZYWVYYNF7): the clones this machine serves, each with its state, the setup it
// still needs (Finish setup), Adopt for a replaced clone and Remove; Add a project's runs that are unfinished (Resume)
// or local only (Publish); and Add a project, one dialog for a repository, a folder or a new project (item 15).

import { html, nothing, render } from "/assets/lit-html/3.3.3/lit-html.js";
import { repeat } from "/assets/lit-html/3.3.3/directives/repeat.js";
import {
  OWN_TAG, Slow, call, defined, displayName, here, isOwn, machineState, ownFirst, project, reread, unread,
} from "/assets/ui.mjs";
import { openAdd } from "./onboarding.mjs";

const state = { busy: "", error: "", said: "", runs: [] };
const TAG = { loading: "info", failed: "error", replaced: "warning", stopped: "info" };  // loaded needs no tag

// One action at a time: its button shows it running; how it went is said under the page's heading until the next one.
async function act(name, work) {
  if (state.busy) return;
  Object.assign(state, { busy: name, error: "", said: "" });
  show();
  let failure = null;
  try {
    state.said = await work();
  } catch (error) {
    failure = error;
  }
  await reread();  // the top row and this page show what the machine now serves
  state.busy = "";
  if (failure) state.error = failure instanceof Slow && !unread() ? failure.reread : failure.message;
  show();
}

function button(label, onclick, { variant = "secondary", busy = null } = {}) {
  return html`<p-button type="button" compact="true" variant=${variant} .loading=${state.busy === busy}
    @click=${onclick}>${label}</p-button>`;
}

// The runs Add a project left unfinished or local only, read again whenever its dialog closes.
async function runs() {
  try {
    state.runs = (await call("/onboarding/jobs", { machine: true })).jobs;
  } catch (error) {
    state.runs = [{ id: "", unreadable: `Add a project's runs could not be read: ${error.message}` }];
  }
  show();
}

function adding(opts) {
  return openAdd(opts, async () => {
    await reread();
    await runs();
  });
}

// Moves focus to what *pick* finds when an action took it away: its button is gone, or the confirmation still holds it
// and gives it back only once it has closed. Focus the owner has moved elsewhere in the meantime stays there.
async function refocus(pick) {
  for (let tries = 0; tries < 40; tries += 1) {
    const now = document.activeElement;
    if (now !== document.body && !now?.closest?.("p-modal")) return;
    const target = pick();
    target?.focus();
    if (!target || document.activeElement === target) return;
    await new Promise((resolve) => setTimeout(resolve, 50));
  }
}

async function remove(p) {
  const at = ownFirst(machineState().projects).findIndex((o) => o.id === p.id), name = displayName(p);
  const yes = await ask({ title: `Remove ${name}?`, now: `OwlBear stops serving ${p.path}.`,
    then: "Its Changes, settings and memory stay in the clone; nothing is deleted.",
    after: "Add the folder again to serve it once more.", instead: "It keeps running.", yes: "Remove project",
    destructive: true });
  if (!yes) return;
  await act(`remove ${p.id}`, async () => {
    await call(`/projects/${p.id}`, { method: "DELETE", machine: true });
    if (p.id === project) location.replace(here({ project: "" }));  // the top row no longer has it to show
    return `Removed ${name}; nothing in ${p.path} was deleted.`;
  });
  await refocus(() => {  // the Remove button now in its place takes focus, or Folder when none is left
    const left = document.querySelectorAll(".projects > li");
    return left.length ? left[Math.max(0, Math.min(at, left.length - 1))].querySelector(".row p-button:last-child")
      : document.querySelector("#add p-button");
  });
}

async function adopt(p) {
  let adopted = null;
  await act(`adopt ${p.id}`, async () => {
    adopted = await call(`/projects/${p.id}/adopt`, { method: "POST", machine: true });
    if (p.id === project) location.replace(here({ project: adopted.id }));
    return `${displayName(adopted)} now serves the clone at ${adopted.path}.`;
  });
  if (adopted && p.id !== project) {  // its Adopt button is gone: the adopted project's Remove takes focus
    const row = `li[aria-labelledby="p-${CSS.escape(adopted.id)}"]`;
    await refocus(() => document.querySelector(`${row} .row p-button:last-child`));
  }
}

// One project: its name, folder and state, and each readiness check its host failed, whole; a replaced clone asks to
// be adopted, so Adopt is its one primary.
function entry(p, all) {
  const name = displayName(p), twin = all.some((o) => o !== p && displayName(o) === name);
  return html`<li class="project" aria-labelledby=${`p-${p.id}`}>
    <div class="heading-row">
      <p-heading size="md"><h3 id=${`p-${p.id}`}>${name}</h3></p-heading>
      ${isOwn(p) ? html`<p-tag compact="true">${OWN_TAG}</p-tag>` : nothing}
      ${TAG[p.state] ? html`<p-tag compact="true" variant=${TAG[p.state]}>${p.state}</p-tag>` : nothing}
      ${p.id === project ? html`<p-tag compact="true">shown now</p-tag>` : nothing}
    </div>
    <p-text size="sm" class="path">${twin ? "This clone: " : ""}<code>${p.path}</code></p-text>
    ${p.reason ? html`<p-text size="sm">${p.reason}</p-text>` : nothing}
    ${p.ready?.length ? html`<ul class="ready" aria-label="Failed readiness checks">
      ${p.ready.map((failed) => html`<li>${failed}</li>`)}</ul>` : nothing}
    ${p.setup ? html`<p-inline-notification state="warning" dismiss-button="false" heading="Setup required"
      heading-tag="h4">The chats of ${name} cannot reach Delivery yet. Finish setup here, or run
      <code>${p.setup}</code> in a terminal; then reload the project's VS Code window.</p-inline-notification>`
      : nothing}
    <div class="row">
      ${p.setup ? button("Finish setup", () => adding({ kind: "folder", folder: p.path }),
        { variant: "primary" }) : nothing}
      ${p.state === "replaced" ? button("Adopt the new clone", () => adopt(p),
        { variant: "primary", busy: `adopt ${p.id}` }) : nothing}
      ${button("Remove project", () => remove(p), { busy: `remove ${p.id}` })}
    </div>
  </li>`;
}

// One run of Add a project: unfinished ones resume, a local-only one publishes to GitHub (E3b).
function run(r) {
  if (r.unreadable) return html`<li class="project"><p-text role="alert">${r.unreadable}</p-text></li>`;
  const local = r.ended === "local", stuck = r.stages.find((x) => ["failed", "waiting", "held"].includes(x.state));
  return html`<li class="project" aria-labelledby=${`r-${r.id}`}>
    <div class="heading-row"><p-heading size="md"><h3 id=${`r-${r.id}`}>${r.plan.name}</h3></p-heading>
      <p-tag compact="true" variant=${local ? "info" : "warning"}>${local ? "Local only: not on GitHub"
        : stuck ? `${stuck.name}: ${stuck.state}` : "unfinished"}</p-tag></div>
    <p-text size="sm" class="path"><code>${r.plan.folder}</code></p-text>
    <div class="row">${local ? button("Publish", () => adding({ kind: "folder", folder: r.plan.folder, github: true }),
      { variant: "primary" }) : button("Resume", () => adding({ job: r }), { variant: "primary" })}</div>
  </li>`;
}

function view() {
  const machine = machineState(), why = unread();
  if (!machine && why) {  // the machine host did not answer, which says nothing about which host this is
    return html`<p-inline-notification state="error" dismiss-button="false" heading="Projects could not be read"
      heading-tag="h2">${why}</p-inline-notification>
      <div class="row">${button("Reload", () => location.reload())}</div>`;
  }
  if (!machine) {
    return html`<p-inline-notification state="info" dismiss-button="false" heading="Projects are the machine host's"
      heading-tag="h2" description="This page is served by one project's own host, which serves only that project.
      Open the address owlbear status prints to add, remove or adopt projects."></p-inline-notification>`;
  }
  const { projects } = machine, own = projects.filter(isOwn), consumers = projects.filter((p) => !isOwn(p));
  // keyed, so a row and its focused button stay with their project when the list changes
  const list = (id, label, of) => html`<ul id=${id} class="projects" aria-label=${label}>${repeat(of, (p) => p.id,
    (p) => entry(p, projects))}</ul>`;
  return html`
    ${state.error ? html`<p-text role="alert">${state.error}</p-text>` : nothing}
    ${state.said ? html`<p-text role="status">${state.said}</p-text>` : nothing}
    ${why ? html`<p-text role="alert">This list may be out of date: ${why}</p-text>` : nothing}
    ${machine.unshared ? html`<p-text id="unshared" role="alert">Shared data: ${machine.unshared}</p-text>` : nothing}
    ${machine.unretried ? html`<p-text id="unretried" role="alert"
      >Loading the failed projects again failed: ${machine.unretried}</p-text>` : nothing}
    ${own.length ? html`<section aria-labelledby="own-title">
      <p-heading size="lg"><h2 id="own-title">OwlBear</h2></p-heading>${list("own", "OwlBear", own)}</section>`
      : nothing}
    ${projects.length ? html`<section aria-labelledby="consumers-title">
      <p-heading size="lg"><h2 id="consumers-title">Consumer projects</h2></p-heading>
      ${consumers.length ? list("projects", "Consumer projects", consumers)
        : html`<p-text class="empty">No consumer project yet: add one below.</p-text>`}</section>`
      : html`<p-text class="empty">No project yet: add one below.</p-text>`}
    ${state.runs.length ? html`<section aria-labelledby="runs-title">
      <p-heading size="lg"><h2 id="runs-title">Add a project: runs</h2></p-heading>
      <ul class="projects" aria-label="Add a project's runs">${state.runs.map(run)}</ul></section>` : nothing}
    <section id="add" class="panel" aria-labelledby="add-title">
      <p-heading size="md"><h2 id="add-title">Add a project</h2></p-heading>
      <p-text size="sm">From a repository on GitHub, a folder on this Mac, or a new project.</p-text>
      <div class="row">${button("Add a project", () => adding({}), { variant: "primary" })}</div>
    </section>`;
}

function show() {
  render(view(), document.getElementById("page"));
}

await defined(["p-heading", "p-text", "p-button", "p-tag", "p-inline-notification"]);
for (const kind of ["owlbear-machine", "owlbear-polled"]) document.addEventListener(kind, show);
show();
runs();
if (new URLSearchParams(location.search).get("add")) adding({});  // `owlbear install`'s offer opens the dialog
