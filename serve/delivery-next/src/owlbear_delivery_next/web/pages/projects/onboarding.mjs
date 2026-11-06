// Add project (item 15): one dialog for every starting point — a repository on GitHub, a folder on this Mac, or a new
// project — that probes what exists, asks only what the stages left need, checks before anything is created, confirms
// (C-29), runs the machine host's job and ends with three facts and New Change.

import { html, nothing, render } from "/assets/lit-html/3.3.3/lit-html.js";
import { live } from "/assets/lit-html/3.3.3/directives/live.js";
import { call, defined } from "/assets/ui.mjs";

const PUSH_FIRST = new Set(["E3", "E3b", "E4a", "E4c", "E5"]);
const STAGE = {
  folder: "Folder", git: "Git", commit: "First commit", repository: "GitHub repository", push: "First push",
  ci: "CI", protection: "Branch protection", labels: "Labels", shared: "Shared settings folder",
  merge_method: "Merge method", readiness: "Readiness", detect: "Profile detection", profile: "Profile",
  files: "Chat-tool files", register: "Register", end: "Ending",
};
const DOES = {
  folder: (p) => p.entry === "E1" ? `clone ${p.repository} into ${p.folder}` : `create the folder ${p.folder}`,
  git: (p) => `set up Git in ${p.folder}${p.github ? `, with origin ${p.repository}` : ""}`,
  commit: () => "commit the first files", repository: (p) => `create ${p.repository} on GitHub (${p.visibility})`,
  push: () => "push the first commit (or pull the repository's)", ci: () => "wait for CI on the pushed commit",
  protection: () => "", labels: (p) => p.labels.length
    ? `create the labels ${p.labels.join(", ")}` : "",
  shared: () => "claim the project's shared settings folder", readiness: () => "check readiness",
  detect: () => "detect the project's profile", profile: () => "ask you to confirm the profile",
  files: () => "write the chat-tool files you ticked", register: () => "register the project on this machine",
};
const CHANGE = {  // a ruleset change in the words of GitHub's settings
  merge_method: "allow merge commits in its pull-request rule", linear_history: "stop requiring a linear history",
  up_to_date: "require branches to be up to date before merging",
  conversations: "require conversation resolution before merging",
  pull_requests: "require a pull request before merging", no_deletion: "restrict deletions",
  no_force_push: "block force pushes",
  no_approvals: "require no approvals: 0 reviews, no code-owner review, no approval of the most recent push",
};
const TASK = ["task", "Remove the folder-open task an earlier setup wrote into .vscode/tasks.json"];
const FILES = [["server", "Register Delivery's chat server in .mcp.json"],
  ["memory", "Register the memory server for the shaper"], ["harness", "Set the Copilot harness key"]];

let s, modal, poll, done, back;

// Where an unfinished or local-only run stands, in words, and the label of the one button that goes on with it.
export function standing(r) {
  if (r.ended === "local") return { text: "Set up on this Mac only, not on GitHub", action: "Publish" };
  const at = r.stages.find((x) => x.state !== "done"), name = STAGE[at?.name] ?? at?.name ?? "Ending";
  if (r.running) return { text: `${name}: running`, action: "Show progress" };
  if (at?.state === "waiting" && r.waiting?.kind === "profile") {
    return { text: "Waits for you to confirm its profile", action: "Confirm profile" };
  }
  if (at?.state === "waiting" && r.waiting?.kind === "shared_folder") {
    return { text: "Waits for you to name its shared settings folder", action: "Name the folder" };
  }
  if (at?.state === "failed") return { text: `${name} failed`, action: "Retry" };
  if (at?.state === "held") return { text: `${name} held: ${at.detail}`, action: "Resume" };
  return { text: `Stopped before ${name}`, action: "Resume" };
}


// Opens the dialog; *opts* starts it on a folder (Finish setup, Publish) or on a run (Resume). *onClose* rereads.
export async function openAdd(opts = {}, onClose = () => {}) {
  await defined(["p-modal", "p-radio-group", "p-radio-group-option", "p-checkbox", "p-input-text", "p-button",
    "p-heading", "p-text", "p-tag", "p-inline-notification"]);
  s = { step: "start", kind: opts.kind ?? "new", repository: "", folder: opts.folder ?? "", name: "",
    github: opts.github ?? true, found: null, c: {}, problems: [], job: null, busy: "", error: "", folderName: "",
    values: {}, started: "" };
  done = onClose;
  back = document.activeElement;  // focus goes back to the opener when the dialog closes
  modal = document.createElement("p-modal");
  modal.className = "onboarding";
  modal.setAttribute("aria", "{ 'aria-label': 'Add a project' }");
  modal.addEventListener("dismiss", close);
  document.body.append(modal);
  if (opts.job) follow(opts.job);
  draw();
  modal.open = true;
  if (opts.folder && !opts.job) await look();  // the open dialog keeps the page inert while the probe runs
}

function close() {
  s.closed = true;
  clearTimeout(poll);
  modal.open = false;
  const gone = modal;
  setTimeout(() => gone.remove(), 1000);
  const refocus = (tries) => {  // the open modal keeps the page inert, so focus is tried until it lands
    if (!back?.isConnected || (document.activeElement !== document.body && !gone.contains(document.activeElement))) {
      return;
    }
    back.focus?.();
    if (document.activeElement !== back && tries) setTimeout(() => refocus(tries - 1), 50);
  };
  refocus(40);
  done();
}

async function busy(name, work) {
  if (s.busy) return;
  Object.assign(s, { busy: name, error: "" });
  draw();
  try {
    await work();
  } catch (error) {
    s.error = error.message;
  }
  s.busy = "";
  draw();
}

function button(label, onclick, { variant = "secondary", name = "" } = {}) {
  return html`<p-button type="button" variant=${variant} .loading=${Boolean(name) && s.busy === name}
    @click=${onclick}>${label}</p-button>`;
}

function text(label, key, { into = s, hint = "" } = {}) {
  return html`<p-input-text label=${label} description=${hint || nothing} .value=${live(into[key] ?? "")}
    @input=${(e) => { into[key] = e.target.value ?? ""; }}></p-input-text>`;
}

function tick(label, key, { into = s.c, disabled = false, why = "" } = {}) {
  return html`<p-checkbox label=${why ? `${label} (${why})` : label} ?disabled=${disabled}
    .checked=${live(!disabled && Boolean(into[key]))}
    @change=${(e) => { into[key] = e.target.checked === true; draw(); }}></p-checkbox>`;
}

async function look() {
  const start = { kind: s.kind, github: s.github, folder: s.folder.trim() || undefined };
  if (s.kind === "github") start.repository = s.repository.trim();
  if (s.kind === "new") start.name = s.name.trim();
  await busy("look", async () => {
    s.found = await call("/onboarding/probe", { body: start, machine: true, timeout: 60000 });
    if (!s.found.refusal) s.c = defaults(s.found);
    s.step = s.found.refusal ? "start" : "choices";
  });
}

function defaults(f) {
  const [owner = ""] = (f.repository || "").split("/");
  const unmet = (f.rules?.items ?? []).filter((i) => !i.holds && i.applicable);
  return { owner, name: f.name, visibility: "private", ci: !f.state.workflows,
    protect: PUSH_FIRST.has(f.entry) && !unprotectable(f),
    needs: unmet.filter((i) => f.rules.needs.includes(i.key)).map((i) => i.key), advice: [],
    labels: (f.labels ?? []).length > 0, consents: { task: f.old_task, server: true, memory: true, harness: true },
    files_warned: false, author: { name: "", email: "" }, method: null };
}

// The merge method the project ends with: merge where OwlBear publishes first or protects, else the resolved one when
// allowed, else the one allowed method, else the owner's pick of several (preselected merge, squash, rebase).
function method(f, c) {
  const allowed = f.allowed ?? [], protecting = c.protect && !unprotectable(f);
  // protection makes merge allowed where OwlBear writes the rules: a new ruleset, or the change to the one there is
  const fixed = protecting && (!f.github || f.github.methods.includes("merge"))
    && (!f.rules?.any || f.rules.one_ruleset !== null);
  if ((allowed.includes("merge") || fixed) && (PUSH_FIRST.has(f.entry) || protecting)) return { write: "merge" };
  if (f.resolved_method && allowed.includes(f.resolved_method)) return { write: null, keeps: f.resolved_method };
  if (allowed.length === 1) return { write: allowed[0] };
  if (allowed.length > 1) return { write: c.method ?? ["merge", "squash", "rebase"].find((m) => allowed.includes(m)),
    ask: true };
  return { write: null };
}

// Why OwlBear's protection can't be had here, else "".
function unprotectable(f) {
  if (f.rules?.plan_limit) return f.rules.plan_limit;
  if (f.github && !f.github.methods.includes("merge")) return "this repository doesn't allow merge commits; "
    + "OwlBear's protection needs them";
  return "";
}

function plan() {
  const f = s.found, c = s.c, creating = f.stages.includes("repository");
  const protecting = f.on_github && c.protect && !unprotectable(f);
  const changing = protecting && f.rules?.any && f.rules.one_ruleset !== null;  // OwlBear writes only one ruleset
  const repository = f.on_github ? (creating ? `${c.owner.trim()}/${c.name.trim()}` : f.repository) : "";
  return { folder: f.folder, name: c.name.trim() || f.name, repository, github: f.on_github, entry: f.entry,
    stages: f.stages, visibility: c.visibility, ci: c.ci && f.on_github, protect: protecting,
    advice: changing ? c.advice : [], needs: changing ? c.needs : [], method: method(f, c).write,
    labels: c.labels ? f.labels : [], consents: c.consents, files_warned: c.files_warned,
    had_files: f.state.files, had_workflows: f.state.workflows,
    rules_items: f.rules?.items ?? null, author: f.author_missing ? c.author : null };
}

async function check() {
  const f = s.found, c = s.c;
  if (f.state.files && f.stages.includes("commit") && !c.files_warned) {
    s.error = "Tick that you checked the folder for secrets first.";
    return draw();
  }
  const sent = plan(), checked = JSON.stringify(sent);
  await busy("check", async () => {
    s.problems = (await call("/onboarding/preflight", { body: sent, machine: true, timeout: 60000 })).problems;
    if (s.problems.length) return;
    if (JSON.stringify(plan()) === checked) s.step = "confirm";
    else s.error = "The choices changed during the check: check them again.";
  });
}

async function run() {
  await busy("run", async () => {
    follow(await call("/onboarding/jobs", { body: plan(), machine: true, timeout: 30000 }));
  });
}

function follow(job) {
  s.job = job;
  s.step = job.ended || (job.stages.find((x) => x.name === "end")?.state === "done") ? "ending" : "progress";
  clearTimeout(poll);
  if (job.running) watch(job.id, s);
  draw();
}

// Reads the run again each second while this dialog is open; a failed read shows and is tried again, and an answer
// that arrives after the dialog closed or was replaced is dropped.
function watch(id, mine) {
  poll = setTimeout(async () => {
    try {
      const job = await call(`/onboarding/jobs/${id}`, { machine: true });
      if (s !== mine || mine.closed) return;
      s.error = "";
      follow(job);
    } catch (error) {
      if (s !== mine || mine.closed) return;
      s.error = error.message;
      draw();
      watch(id, mine);
    }
  }, 1000);
}

async function answer(kind, value) {
  await busy(kind, async () => follow(await call(`/onboarding/jobs/${s.job.id}/answer`,
    { body: { kind, value }, machine: true })));
}

async function resume() {
  await busy("resume", async () => follow(await call(`/onboarding/jobs/${s.job.id}/resume`,
    { method: "POST", machine: true })));
}

function startView() {
  const kind = html`<p-radio-group name="add-kind" label="Start from" .value=${live(s.kind)}
    @change=${(e) => { s.kind = e.target.value; draw(); }}>
    <p-radio-group-option value="github" label="A repository on GitHub"></p-radio-group-option>
    <p-radio-group-option value="folder" label="A folder on this Mac"></p-radio-group-option>
    <p-radio-group-option value="new" label="A new project"></p-radio-group-option></p-radio-group>`;
  const inputs = {
    github: html`${text("Repository", "repository", { hint: "owner/name or its URL" })}
      ${text("Folder", "folder", { hint: "Where to clone it; ~/Projects/<name> when empty" })}`,
    folder: html`${text("Folder", "folder", { hint: "~/Projects/my-app" })}${tick("Put it on GitHub", "github",
      { into: s })}`,
    new: html`${text("Name", "name")}${text("Folder", "folder", { hint: "~/Projects/<name> when empty" })}
      ${tick("Put it on GitHub", "github", { into: s })}`,
  }[s.kind];
  const f = s.found?.refusal ? s.found : null;
  const refused = f ? html`<p-inline-notification state="error" dismiss-button="false"
    heading="OwlBear can't add this" heading-tag="h3">${f.refusal}</p-inline-notification>` : nothing;
  const use = f?.enclosing ? button(`Use ${f.enclosing}`, () => {
    Object.assign(s, { kind: "folder", folder: f.enclosing });
    look();
  }) : nothing;
  return [html`${kind}${inputs}${refused}`, html`${button("Look", look, { variant: "primary", name: "look" })}${use}`];
}

function describe(f) {
  const git = { none: "no Git", unborn: "Git without commits", commits: "Git with commits" }[f.state.git];
  const where = f.state.exists ? `${f.folder} (${f.state.files ? "with files" : "empty"}, ${git})`
    : `no folder at ${f.folder}`;
  const gh = f.github ? `${f.repository} on GitHub (${f.github.empty ? "empty" : "with commits"})`
    : f.on_github ? "no GitHub repository yet" : "no GitHub repository, as chosen";
  return `${where}, ${gh}${f.registered ? ", registered here" : ""}`;
}

function rulesView(f, c) {
  const r = f.rules;
  if (!r?.any) return nothing;
  const one = r.one_ruleset !== null, changing = one && c.protect && !unprotectable(f);
  const flip = (key) => (e) => {
    c.advice = e.target.checked === true ? [...new Set([...c.advice, key])] : c.advice.filter((k) => k !== key);
  };
  const item = (i) => (!i.applicable || r.needs.includes(i.key) ? html`<li>${i.sentence}</li>`
    : html`<li><p-checkbox label=${i.holds ? `${i.sentence} (already set)` : i.sentence}
      ?disabled=${!changing || i.holds} .checked=${live(i.holds || (changing && c.advice.includes(i.key)))}
      @change=${flip(i.key)}></p-checkbox></li>`);
  const links = Object.entries(r.links).map(([source, url]) => html`<li><a href=${url} target="_blank"
    rel="noopener">Change ${source === "classic" ? "branch protection" : `ruleset ${source}`} on GitHub</a></li>`);
  return html`<section class="rules"><p-heading size="sm"><h3>The default branch's rules</h3></p-heading>
    <p-text size="sm">${r.summary}${one ? (changing ? "" : ". Tick Protect the default branch to change them.")
      : ". OwlBear changes no rule here: make these changes on GitHub."}</p-text>
    <ul>${r.items.map(item)}</ul>${one ? nothing : html`<ul>${links}</ul>`}</section>`;
}

function choicesView() {
  const f = s.found, c = s.c, creating = f.stages.includes("repository"), m = method(f, c);
  const why = unprotectable(f), opt = !PUSH_FIRST.has(f.entry);
  const left = f.stages.filter((x) => DOES[x]).map((x) => STAGE[x]).join(" → ");
  return [html`<p-text>Found ${f.entry === "E5" ? "nothing yet" : describe(f)}. Left to do: ${left}.</p-text>
    ${f.job ? html`<p-inline-notification state="info" dismiss-button="false"
      heading="A run for this destination is unfinished" heading-tag="h3">Resume it instead of starting again.
      </p-inline-notification>` : nothing}
    ${creating ? html`<p-radio-group name="visibility" label="Visibility" .value=${live(c.visibility)}
      @change=${(e) => { c.visibility = e.target.value; }}>
      <p-radio-group-option value="private" label="Private"></p-radio-group-option>
      <p-radio-group-option value="public" label="Public"></p-radio-group-option></p-radio-group>
      ${text("Owner", "owner", { into: c })}${text("Name", "name", { into: c })}` : nothing}
    ${f.author_missing ? html`<p-text size="sm">Git has no author for this project: commits need one.</p-text>
      ${text("Author name", "name", { into: c.author })}${text("Author email", "email", { into: c.author })}`
      : nothing}
    ${f.stages.includes("commit") && f.on_github ? tick("Add a CI workflow named CI", "ci",
      { disabled: f.state.workflows, why: f.state.workflows ? "the folder has workflows; OwlBear adds none" : "" })
      : nothing}
    ${f.on_github ? tick(opt ? "Protect the default branch (opt-in: it has history)" : "Protect the default branch",
      "protect", { disabled: Boolean(why), why }) : nothing}
    ${rulesView(f, c)}
    ${m.ask ? html`<p-radio-group name="method" label="Merge method for this project" .value=${live(m.write)}
      @change=${(e) => { c.method = e.target.value; }}>${f.allowed.map((x) => html`<p-radio-group-option
      value=${x} label=${x}></p-radio-group-option>`)}</p-radio-group>` : nothing}
    ${f.on_github && f.labels?.length ? tick(`Create Global's labels: ${f.labels.join(", ")}`, "labels") : nothing}
    ${f.labels_error ? html`<p-text size="sm" role="alert">${f.labels_error}</p-text>` : nothing}
    ${f.stages.includes("files") ? [...(f.old_task ? [TASK] : []), ...FILES].map(([key, label]) => tick(label, key,
      { into: c.consents })) : nothing}
    ${f.state.files && f.stages.includes("commit") ? html`<p-inline-notification state="warning"
      dismiss-button="false" heading="Every file in the folder is committed" heading-tag="h3">OwlBear commits the
      folder's files as they are, except what .gitignore excludes, and doesn't look inside them. Make sure no secret
      (a key, a token, a password) is among them.</p-inline-notification>
      ${tick("I checked the folder: no secrets in it", "files_warned")}` : nothing}
    ${s.problems.length ? html`<p-inline-notification state="error" dismiss-button="false"
      heading="Nothing was created" heading-tag="h3"><ul>${s.problems.map((p) => html`<li>${p}</li>`)}</ul>
      </p-inline-notification>` : nothing}`,
  html`${f.job ? button("Resume", () => follow(f.job), { variant: "primary" }) : nothing}
    ${button("Check and continue", check, { variant: f.job ? "secondary" : "primary", name: "check" })}
    ${button("Back", () => { s.step = "start"; draw(); })}`];
}

function confirmView() {
  const f = s.found, p = plan(), m = method(f, s.c);
  const now = p.stages.map((x) => DOES[x]?.(p)).filter(Boolean);
  const changes = [...p.needs, ...p.advice].map((k) => CHANGE[k] ?? k);
  if (changes.length) now.push(`change ruleset ${f.rules.one_ruleset} of the default branch: ${changes.join("; ")}`);
  if (p.protect && !f.rules?.any) {  // OwlBear's own ruleset, on a branch without rules
    const ci = p.ci && p.stages.includes("commit") && !p.had_workflows;
    now.push("add a ruleset to the default branch: pull requests only, merge commits only, conversations resolved "
      + "before merging, no deletion or force push, no approvals required; " + (ci ? "required check: CI, once it "
        + "reports on the first push, with branches up to date before merging"
        : "required checks: none; existing workflows unchanged"));
  } else if (p.protect && f.rules.one_ruleset === null) {
    now.push("change no rule: the rules above that need changing are yours to change on GitHub, by their links");
  }
  if (p.github) {
    now.push(m.write ? `save the merge method ${m.write} for this project`
      : m.keeps ? `keep the merge method ${m.keeps}, from the settings`
        : "save no merge method: this repository and its rules allow none, so Delivery can't merge until they change");
  }
  const name = p.name;
  const then = p.github ? `Delivery serves ${name}: its work starts when you approve a Change's brief, and the `
    + "watcher decides when a real project's work may run." : `Nothing: OwlBear doesn't serve ${name} until you `
    + "publish it with Publish on the Projects page.";
  const kept = p.entry === "E1" ? "the clone stays" : "the folder stays";
  const undo = !p.github ? "Nothing is registered. The folder and its first commit stay on this Mac for you to delete."
    : f.publishes ? "A published repository and its commits stay on GitHub. Remove project on its row undoes the "
      + "registration; the folder and the GitHub repository stay for you to delete."
      : `Nothing is published. Remove project on its row undoes the registration; ${kept} for you to delete.`;
  // what the button does: clone a repository, create what is missing, or only set up what is there
  const verb = p.entry === "E1" ? "Clone and set up" : f.creates ? "Create and set up" : "Set up";
  return [html`<div class="parts">
    <div><p-text weight="semibold">Now</p-text><ul>${now.map((x) => html`<li>${x}</li>`)}</ul></div>
    <div><p-text weight="semibold">Then, by itself</p-text><p-text>${then}</p-text></div>
    <div><p-text weight="semibold">What can't be undone</p-text><p-text>${undo}</p-text></div>
    <div><p-text weight="semibold">If you don't</p-text><p-text>Nothing is created or changed.</p-text></div>
    </div>`,
  html`${button(p.github ? `${verb} ${name}` : `Set up ${name} on this Mac`, run,
    { variant: "primary", name: "run" })}${button("Back", () => { s.step = "choices"; draw(); })}`];
}

function progressView() {
  const j = s.job, failed = j.stages.find((x) => x.state === "failed" || x.state === "held");
  const w = j.waiting;
  // a stage that found nothing to do (protection unavailable, no CI generated, no method to save) says so
  const skipped = (x) => x.state === "done" && [x.result?.applied, x.result?.generated, x.result?.written]
    .includes(false);
  const shown = (x) => (skipped(x) ? "skipped" : x.state);
  const list = html`<ol class="stages">${j.stages.map((x) => html`<li><span>${STAGE[x.name] ?? x.name}${skipped(x)
    && x.result.why ? html`<p-text size="xs">${x.result.why}</p-text>` : nothing}</span>
    <p-tag compact="true" variant=${{ done: "success", failed: "error", waiting: "warning", held: "warning",
      running: "info" }[shown(x)] ?? "secondary"}>${shown(x)}</p-tag></li>`)}</ol>`;
  let body = nothing, actions = nothing;
  if (failed) {
    body = html`<p-inline-notification state="error" dismiss-button="false" heading=${`${STAGE[failed.name]} failed`}
      heading-tag="h3"><pre>${failed.detail}</pre></p-inline-notification>`;
    actions = button(failed.state === "held" ? "Resume" : "Retry", resume, { variant: "primary", name: "resume" });
  } else if (w?.kind === "shared_folder") {
    body = html`<p-text>${w.why}</p-text>${text("Folder name in the shared settings", "folderName")}`;
    actions = button("Continue", () => answer("shared_folder", s.folderName.trim()), { variant: "primary",
      name: "shared_folder" });
  } else if (w?.kind === "profile") {
    [body, actions] = profileView(w);
  } else if (!j.running) {
    actions = button("Resume", resume, { variant: "primary", name: "resume" });
  }
  return [html`${list}${body}`, html`${actions}${button("Close", close)}`];
}

function profileView(w) {
  const group = (state) => w.entries.filter((e) => e.state === state);
  // an unknown entry shows what was found of it and why it isn't known, above the field for the whole value
  const row = (e) => html`<li><code>${e.key}</code> = ${e.state === "unknown" && e.settable
    ? html`<p-text size="xs">${e.value ? `Found so far: ${e.value}. ` : ""}${e.evidence}</p-text>
      ${text(e.key, e.key, { into: s.values })}` : html`${JSON.stringify(e.value)}
    <p-text size="xs">${e.evidence}</p-text>`}</li>`;
  const part = (state, label) => group(state).length ? html`<p-heading size="sm"><h3>${label}</h3></p-heading>
    <ul>${group(state).map(row)}</ul>` : nothing;
  return [html`${(w.notes ?? []).map((n) => html`<p-inline-notification state="warning" dismiss-button="false"
      heading="Before you confirm" heading-tag="h3">${n}</p-inline-notification>`)}
    <p-text>Check what OwlBear detected; give a value for an unknown entry you know.</p-text>
    ${part("known", "Known")}${part("unknown", "Unknown")}${part("unsupported", "Unsupported")}`,
  button("Confirm profile", () => answer("profile", s.values), { variant: "primary", name: "profile" })];
}

function endingView() {
  const r = s.job.stages.find((x) => x.name === "end")?.result ?? {};
  const fact = (label, ok) => html`<li>${label}: <p-tag compact="true" variant=${ok ? "success" : "warning"}>${ok
    ? "yes" : "no"}</p-tag></li>`;
  const all = r.registered && r.profile && r.ready;
  return [html`${r.local ? html`<p-text>Set up on this Mac only. Publish on the Projects page puts it on GitHub.
    </p-text>` : html`<ul class="facts">${fact("Registered", r.registered)}${fact("Profile confirmed", r.profile)}
    ${fact("Ready for Delivery", r.ready)}</ul>`}
    ${r.missing?.length && !r.local ? html`<p-text weight="semibold">Missing</p-text><ul>${r.missing.map((m) =>
      html`<li>${m}</li>`)}</ul>` : nothing}
    ${r.files?.length ? html`<details><summary>Chat-tool files</summary><ul>${r.files.map((x) => html`<li>${x}</li>`)}
      </ul></details>` : nothing}
    ${s.started ? html`<p-text role="status">${s.started}</p-text>` : nothing}`,
  html`${all ? button("New Change", () => newChange(r.id), { variant: "primary", name: "new" }) : nothing}
    ${button("Close", close, { variant: all ? "secondary" : "primary" })}`];
}

// New Change for the onboarded project directly, as the Changes page opens it, without asking which project.
async function newChange(id) {
  const yes = await ask({ title: "Shape a new Change?", yes: "Open the chat", no: "Not now",
    now: "A chat opens in VS Code where the shaper works out the brief with you; the chat uses AI credits like any "
      + "Copilot chat.",
    then: "Nothing is built. When you save the brief in the chat, it appears on Changes for your approval.",
    after: "Approve it there to start the work, or keep shaping it in the chat.", instead: "Nothing opens." });
  if (!yes) return;
  await busy("new", async () => {
    const r = await call("/new-change", { body: {}, of: id, timeout: 30000 });
    let st = r.started ? { state: "opening" } : { state: "failed", ...r };
    while (st.state === "opening") {
      await new Promise((resolve) => setTimeout(resolve, 1000));
      st = await call(`/new-change/${encodeURIComponent(r.launch)}`, { of: id });
    }
    s.started = st.state === "open" ? "The shaping chat opened in VS Code."
      : `Could not open the shaping chat: ${st.reason}${st.command ? `. Run ${st.command}` : ""}`;
  });
}

function draw() {
  if (!modal) return;
  const [body, actions] = { start: startView, choices: choicesView, confirm: confirmView,
    progress: progressView, ending: endingView }[s.step]();
  const title = { start: "Add a project", choices: "Choices", confirm: "Confirm",
    progress: "Setting it up", ending: "Done" }[s.step];
  render(html`<p-heading slot="header" size="lg"><h2>${title}</h2></p-heading>
    <div class="body">${s.error ? html`<p-text role="alert">${s.error}</p-text>` : nothing}${body}</div>
    <div class="row" slot="footer">${actions}</div>`, modal);
}
