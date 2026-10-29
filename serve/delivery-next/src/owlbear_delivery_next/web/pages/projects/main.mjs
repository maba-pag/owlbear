// The Projects page (D-01M63C8DA1D95Z7M9ZYWVYYNF7): the clones this machine serves, each with its state, the setup it
// still needs, Adopt for a replaced clone and Remove; and Add for the folder of an existing clone. New project, the
// other way to add one (0ET1A6), will sit beside it.

import { html, nothing, render } from "/assets/lit-html/3.3.3/lit-html.js";
import { Slow, call, defined, here, machineState, project, reread, unread } from "/assets/ui.mjs";

const state = { draft: "", busy: "", error: "", said: "" };
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

function add() {
  const path = state.draft.trim();
  if (!path) {
    state.error = "Name the folder of a clone first.";
    return show();
  }
  return act("add", async () => {
    const added = await call("/projects", { body: { path }, machine: true });
    if (state.draft.trim() === path) state.draft = "";  // a folder typed in the meantime stays for the next Add
    return `Added ${added.name}.`;
  });
}

async function remove(p) {
  const yes = await ask({ title: `Remove ${p.name}?`, now: `OwlBear stops serving ${p.path}.`,
    then: "Its Changes, settings and memory stay in the clone; nothing is deleted.",
    after: "Add the folder again to serve it once more.", instead: "It keeps running.", yes: "Remove project" });
  if (!yes) return;
  const at = [...document.querySelectorAll("#projects > li")].findIndex((li) => li.contains(document.activeElement));
  await act(`remove ${p.id}`, async () => {
    await call(`/projects/${p.id}`, { method: "DELETE", machine: true });
    if (p.id === project) location.replace(here({ project: "" }));  // the top row no longer has it to show
    return `Removed ${p.name}; nothing in ${p.path} was deleted.`;
  });
  if (document.activeElement === document.body) {  // its Remove button is gone: the next project's takes focus
    const left = document.querySelectorAll("#projects > li");
    (left.length ? left[Math.max(0, Math.min(at, left.length - 1))].querySelector(".row p-button:last-child")
      : document.querySelector("#add p-input-text"))?.focus();
  }
}

async function adopt(p) {
  let adopted = null;
  await act(`adopt ${p.id}`, async () => {
    adopted = await call(`/projects/${p.id}/adopt`, { method: "POST", machine: true });
    if (p.id === project) location.replace(here({ project: adopted.id }));
    return `${adopted.name} now serves the clone at ${adopted.path}.`;
  });
  if (adopted && p.id !== project) {  // its Adopt button is gone: the adopted project's Remove takes focus
    document.querySelector(`li[aria-labelledby="p-${CSS.escape(adopted.id)}"] .row p-button:last-child`)?.focus();
  }
}

// One project: its name, folder and state; a replaced clone asks to be adopted, so Adopt is its one primary.
function entry(p, all) {
  const twin = all.some((o) => o !== p && o.name === p.name);
  return html`<li class="project" aria-labelledby=${`p-${p.id}`}>
    <div class="heading-row">
      <p-heading size="md"><h2 id=${`p-${p.id}`}>${p.name}</h2></p-heading>
      ${TAG[p.state] ? html`<p-tag compact="true" variant=${TAG[p.state]}>${p.state}</p-tag>` : nothing}
      ${p.id === project ? html`<p-tag compact="true">shown now</p-tag>` : nothing}
    </div>
    <p-text size="sm" class="path">${twin ? "This clone: " : ""}<code>${p.path}</code></p-text>
    ${p.reason ? html`<p-text size="sm">${p.reason}</p-text>` : nothing}
    ${p.setup ? html`<p-inline-notification state="warning" dismiss-button="false" heading="Setup required"
      heading-tag="h3">The chats of ${p.name} cannot reach Delivery yet. Run
      <code>${p.setup}</code> in a terminal, then reload the project's VS Code window.</p-inline-notification>`
      : nothing}
    <div class="row">
      ${p.state === "replaced" ? button("Adopt the new clone", () => adopt(p),
        { variant: "primary", busy: `adopt ${p.id}` }) : nothing}
      ${button("Remove project", () => remove(p), { busy: `remove ${p.id}` })}
    </div>
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
  const { projects } = machine;
  return html`
    ${state.error ? html`<p-text role="alert">${state.error}</p-text>` : nothing}
    ${state.said ? html`<p-text role="status">${state.said}</p-text>` : nothing}
    ${why ? html`<p-text role="alert">This list may be out of date: ${why}</p-text>` : nothing}
    ${projects.length ? html`<ul id="projects" aria-label="Projects">${projects.map((p) => entry(p, projects))}</ul>`
      : html`<p-text class="empty">No project yet: add the folder of a clone below.</p-text>`}
    <section id="add" class="panel" aria-labelledby="add-title">
      <p-heading size="md"><h2 id="add-title">Add a project</h2></p-heading>
      <p-text size="sm">An existing folder: a clone of the project's repository on this machine.</p-text>
      <div class="row">
        <p-input-text label="Folder" compact="true" placeholder="~/Projects/my-app" .value=${state.draft}
          @input=${(e) => { state.draft = e.target.value ?? ""; }}
          @keydown=${(e) => e.key === "Enter" && add()}></p-input-text>
        ${button("Add", add, { variant: "primary", busy: "add" })}
      </div>
    </section>`;
}

function show() {
  render(view(), document.getElementById("page"));
}

await defined(["p-heading", "p-text", "p-button", "p-input-text", "p-tag", "p-inline-notification"]);
for (const kind of ["owlbear-machine", "owlbear-polled"]) document.addEventListener(kind, show);
show();
