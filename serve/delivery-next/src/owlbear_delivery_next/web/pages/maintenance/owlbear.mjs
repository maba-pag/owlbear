// Maintenance's OwlBear section (D-01M61GW2W73KV0F81W3E279H64, D-01M61GWRQSR2V3P0VWMP137Q32): the same in every
// project. The running version, the engine update with Update now, the pinned design pack and the one design pack
// update of this machine, kept in the project that started it: its actions go to that project's endpoints.
import { html, nothing } from "/assets/lit-html/3.3.3/lit-html.js";
import { live } from "/assets/lit-html/3.3.3/directives/live.js";
import { Slow, call, machineState, project, runUpdates } from "/assets/ui.mjs";

const WRITE = 60000;  // an answer may commit and push: a network round trip
const RESULTS = { pending: "not run", running: "running", passed: "passed", failed: "failed", skipped: "skipped",
  returned: "findings back to the updater", waiting: "waiting for you", completed: "session completed",
  findings: "findings", reused: "reused for this identity", answered: "answered by you",
  discarded: "discarded by you", stopped: "stopped", "not-reached": "not reached" };
const TAGS = { pending: "secondary", running: "info", passed: "success", failed: "error", skipped: "secondary",
  returned: "warning", waiting: "warning", completed: "info", findings: "warning", reused: "info", answered: "info",
  discarded: "secondary", stopped: "warning", "not-reached": "secondary" };
const ENDINGS = { idle: "Never run.", passed: "Last run passed: its pull request was merged into main.",
  failed: "Last run failed.", "up-to-date": "Last run: already up to date.",
  waiting: "The update waits for your answers below.", discarded: "Last run discarded: nothing changed." };
// TD-220: what became of each finding of the update's challenge rounds, in words.
const FOUND = { open: "to fix", fixed: "fixed by the updater", rejected: "rejected by the updater, not judged yet",
  standing: "rejected by the updater; the challenger accepted that",
  escalated: "rejected by the updater; the challenger upheld it", "owner-fix": "you decided: fix it",
  "owner-drop": "you dropped it", withdrawn: "withdrawn by the challenger" };

const own = { pinned: null, runs: null, unread: { pinned: "", runs: "" }, error: "", notes: new Map(), missing: "",
  busy: "", polling: null, reading: 0, show: () => {} };

// *show* renders the whole page; the section calls it whenever its state changes.
export function follow(show) {
  own.show = show;
  for (const kind of ["owlbear-machine", "owlbear-polled"]) document.addEventListener(kind, () => own.show());
}

function when(iso) {
  return iso ? new Date(iso).toLocaleString() : "";
}

function sentence(text) {
  return text ? text.charAt(0).toUpperCase() + text.slice(1) : "";
}

export async function readOwlbear() {
  const generation = ++own.reading;
  const [pinned, runs] = await Promise.allSettled([
    call("/maintenance/pack", { timeout: 15000 }), call("/maintenance/pack/runs", { timeout: 15000 }),
  ]);
  if (generation !== own.reading) return;  // a later read is under way; it shows the newer state
  if (pinned.status === "fulfilled") [own.pinned, own.unread.pinned] = [pinned.value, ""];
  else own.unread.pinned = pinned.reason.message;
  if (runs.status === "fulfilled") [own.runs, own.unread.runs] = [runs.value, ""];
  else own.unread.runs = runs.reason.message;
  own.show();
  clearTimeout(own.polling);
  const run = own.runs?.run;
  if (own.unread.runs || (run?.state === "running" && !run.interrupted)) own.polling = setTimeout(readOwlbear, 2000);
}

// Where the run's actions go: the project that started it. None on the machine host with no project chosen (the run
// is shown read-only), nor on a clone's own host for another project's run, which only the machine host reaches.
function reach(run) {
  const bar = machineState();
  if (!bar) return run.own ? { of: project } : null;
  if (!project) return null;
  return bar.projects.some((p) => p.id === run.pid && p.state === "loaded") ? { of: run.pid } : null;
}

async function act(name, work) {
  own.busy = name;
  own.error = "";
  own.show();
  try {
    await work();
  } catch (e) {
    own.error = e instanceof Slow ? e.reread : e.message;  // a timed-out action is never sent again: read back
  }
  own.busy = "";
  await readOwlbear();
}

async function answer(run, q, o) {
  const to = reach(run), note = own.notes.get(q.id) ?? "";
  if (o.id === "reconsider" && !note.trim()) {  // the host refuses it too; said here before anything is sent
    own.missing = q.id;
    own.show();
    document.querySelector(`[data-note="${CSS.escape(q.id)}"]`)?.focus();
    return;
  }
  own.missing = "";
  const left = ["rejected", "standing", "owner-drop"], loop = run.loop;
  const standing = (loop?.findings ?? []).filter((f) => left.includes(f.state));
  const items = [...(loop?.unreviewed ?? []).map((r) => `Repair ${r}: no challenger reviewed it.`),
    ...standing.map((f) => `${f.id} not changed for (${FOUND[f.state]}): ${f.text}`)];
  if (o.id === "activate" && !(await window.ask({
    title: "Activate the pack without a passing challenge?", yes: "Activate", no: "Keep it waiting",
    now: "Delivery activates the candidate as it is now: it commits design_pack.json, skills/NOTICE.md and the "
      + "files the updater changed, opens a pull request to main and merges it once CI passes. It activates "
      + (items.length ? "with these left as they are:" : "with no repair left unreviewed and no finding left open."),
    items,
    then: "The commit message records that the rounds ended without a pass and which findings were not changed for.",
    after: "Later visual rounds use the new pack; run another update when upstream moves on.",
    instead: "The update keeps waiting; you can still discard it.",
  }))) return;
  await act(`${q.id}:${o.id}`, async () => {
    await call("/design-pack/update/answer", { ...to, body: { question: q.id, option: o.id, note }, timeout: WRITE });
    own.notes.delete(q.id);
  });
}

// The stop's one Discard: the answer its question offers, else the run's own discard while it waits.
function discarding(run, questions) {
  const q = questions.find((x) => x.options.some((o) => o.id === "discard"));
  if (q) return { label: q.options.find((o) => o.id === "discard").label, q };
  return run.state === "waiting" ? { label: "Discard the update", q: null } : null;
}

async function discard(run, d) {
  const p = run.published;
  const sure = await window.ask({
    title: "Discard the design pack update?", yes: d.label, no: "Keep it waiting",
    now: `The update started in ${run.name} ends here as discarded.`,
    then: "Nothing is activated: the pinned pack stays as it is, and the run's candidate is not used again.",
    after: p?.url ? `Its pull request #${p.number} stays open; close it on GitHub if you no longer want it.`
      : "Start a new update when you want one.",
    instead: "The update keeps waiting for your answer.",
  });
  if (!sure) return;
  if (d.q) {
    await act(`${d.q.id}:discard`, () => call("/design-pack/update/answer",
      { ...reach(run), body: { question: d.q.id, option: "discard", note: "" }, timeout: WRITE }));
  } else {
    await act("discard", () => call("/design-pack/update/discard", { ...reach(run), method: "POST", timeout: WRITE }));
  }
}

// A primary only where one answer has priority: activating at the end, or trying again once a cause is fixed when
// no repair is offered beside it. Unresolved alternatives keep equal emphasis.
function emphasis(q, o) {
  const repair = q.options.some((x) => x.id === "repair");
  return o.id === "activate" || (o.id === "retry" && !repair) ? "primary" : "secondary";
}

async function start() {
  const sure = await window.ask({
    title: "Update the design pack?", yes: "Update", no: "Keep the current pack",
    now: "Delivery takes the newest upstream pack, detector pins and design skills together; an updater session "
      + "brings the skills, golden pages and detector glue in line, then the golden pages, calibration replay and a "
      + "challenger check it. The challenger's findings go back to the updater. It runs on this project's labels, "
      + "calibration and AI credits.",
    then: "Only if every stage passes, it activates the pack: it commits design_pack.json, skills/NOTICE.md and "
      + "the files the updater changed, opens a pull request to main and merges it once CI passes. It asks you here "
      + "before changed golden evidence counts and before a glue change goes into the pull request, and when the "
      + "rounds end without a pass or the challenger upholds a finding the updater rejected.",
    after: "Later visual rounds use the new pack. If a stage fails, nothing changes and this section says why.",
    instead: "The current pack stays active.",
  });
  if (!sure) return;
  await act("start", () => call("/design-pack/update", { method: "POST", timeout: 10000 }));
}

function button(label, onclick, { id, variant = "secondary", busy = false, disabled = false, icon } = {}) {
  return html`<p-button id=${id ?? nothing} type="button" compact="true" variant=${variant} icon=${icon ?? nothing}
    .loading=${busy} ?disabled=${disabled} @click=${onclick}>${label}</p-button>`;
}

// The run's state in a word, for its tag.
const STATES = { running: ["running", "info"], waiting: ["waiting for you", "warning"], passed: ["passed", "success"],
  failed: ["failed", "error"], discarded: ["discarded", "secondary"], "up-to-date": ["up to date", "success"],
  idle: ["never run", "secondary"], unreadable: ["unreadable", "error"] };
// Each question's heading, by kind; a kind not listed here is named by its own word.
const KINDS = { end: "The challenge rounds ended without a pass", evidence: "Changed golden evidence",
  code: "A change to the detector's glue", scope: "Changes the updater may not make",
  publish: "Publication stopped", "repair-config": "The CI repair changes configuration",
  "repair-approval": "The CI repair changed protected content" };

function runLine(u) {
  if (u.interrupted) return "Its host stopped while it ran; it is settled when that project's host starts again.";
  if (u.state === "running") return `Running since ${when(u.started_at)}.`;
  let line = ENDINGS[u.state] ?? sentence(u.state);
  if (u.started_at) line += ` Started ${when(u.started_at)}` + (u.ended_at ? `, ended ${when(u.ended_at)}.` : ".");
  return line;
}

// What runs now, from the run's invocations, or from its stage list in a record from before them.
function nowOf(u) {
  if (u.state !== "running" || u.interrupted) return "";
  const p = u.progress;
  if (p && !p.legacy) return p.now ? `${p.now.phase ? `${p.now.phase}, ` : ""}${p.now.label}` : "Starting the update";
  const at = (u.stages ?? []).findIndex((s) => s.name === u.stage);
  return at < 0 ? "Starting the update" : `Stage ${at + 1} of ${u.stages.length}: ${u.stages[at].label}`;
}

// What the owner has to do, in one sentence.
function todo(u, questions, to) {
  const elsewhere = to ? "" : `, from ${u.name}`;
  if (u.interrupted) return `Start ${u.name}'s host: the run is settled there.`;
  if (u.state === "running") return "Nothing for now: it runs by itself and asks here when it needs you.";
  if (u.state === "waiting") {
    if (!questions.length) return `Nothing to answer; you can discard it${elsewhere}.`;
    const n = questions.length;
    return `Answer ${n === 1 ? "the question" : `the ${n} questions`} below${elsewhere}.`;
  }
  if (u.state === "passed") {
    return "Nothing. The merged pack reaches each machine as it takes the OwlBear version that carries it; until "
      + "then a machine keeps the pack it has.";
  }
  if (u.state === "failed") return "Read why below, fix the cause, then start a new update.";
  return "Nothing.";
}

function summary(u, questions, to) {
  const [word, tone] = u.interrupted ? ["host stopped", "warning"] : STATES[u.state] ?? [u.state, "secondary"];
  const open = ["running", "waiting"].includes(u.state), now = nowOf(u), next = u.progress?.legacy
    ? null : u.progress?.next;
  return html`<div id="pack-summary" class="pack-summary">
    <div class="heading-row">
      <p-heading size="md"><h3 id="pack-run-title">${open ? "Current update" : "Last update"}</h3></p-heading>
      <p-tag id="pack-tag" variant=${tone} compact="true">${word}</p-tag>
    </div>
    <p-text id="pack-project" size="sm">${open ? "Started" : "Run"} in <strong>${u.name}</strong>: it uses that
      project's labels, calibration and spend${to ? "" : unreachable()}.</p-text>
    <p-text id="pack-state" size="sm" role="status" aria-live="polite">${runLine(u)}</p-text>
    <dl class="pack-facts">
      ${now ? html`<div><dt>Now</dt><dd id="pack-now">${now}…</dd></div>` : nothing}
      ${next ? html`<div><dt>Next</dt><dd id="pack-next">${next.label}${next.options.length
        ? ` (${next.options.join("; ")})` : ""}</dd></div>` : nothing}
      <div><dt>Your part</dt><dd id="pack-todo">${todo(u, questions, to)}</dd></div>
    </dl>
  </div>`;
}

function findings(found) {
  return found.map((f) => {
    const why = [f.reason && `Updater: ${f.reason}`, f.judgement && `Challenger: ${f.judgement}`,
      f.note && `Your note: ${f.note}`, f.clarified && `Reconsidered: ${f.clarified}`].filter(Boolean).join(" ");
    return html`<li>${f.id} (round ${f.raised}), ${FOUND[f.state] ?? f.state}: ${f.text}${why ? ` ${why}` : ""}</li>`;
  });
}

function fact(term, said, id) {
  return said ? html`<div><dt>${term}</dt><dd id=${id ?? nothing}>${said}</dd></div>` : nothing;
}

// The question in its records' own fields where the run keeps them (the finding it is about, the round's end);
// otherwise the host's own sentence.
function asked(run, q) {
  const lp = run.loop;
  const f = q.kind === "dispute" ? (lp?.findings ?? []).find((x) => x.id === q.finding) : null;
  if (f) {
    const unsure = f.reconsider === "unsure";
    return html`<p-text size="sm">${unsure ? "The challenger could not settle this finding with your note."
      : "The challenger did not accept the updater's rejection."}</p-text>
      <dl class="pack-facts">
        ${fact("Finding", f.text)}${fact("Updater's reason", f.reason)}${fact("Challenger's judgement", f.judgement)}
        ${fact("Your note", f.note)}${fact("Challenger, after your note", f.clarified)}
      </dl>`;
  }
  if (q.kind === "end" && lp) {
    const repair = lp.unreviewed?.length
      ? `The updater's last repair (${lp.unreviewed.join(", ")}) was not reviewed by a challenger.`
      : "The candidate is what the last round judged.";
    return html`<p-text size="sm">After round ${lp.round}. ${repair} Activating it opens a pull request to main and
      merges it once CI passes.</p-text>
      ${lp.findings?.length ? html`<ul class="pack-found">${lp.findings.map((x) => html`<li>${x.id}, ${FOUND[x.state]
        ?? x.state}: ${x.text}</li>`)}</ul>` : nothing}`;
  }
  return html`<p-text size="sm">${q.text}</p-text>`;
}

// The change as a diff, its + and - lines marked.
function diff(text) {
  const line = (l) => l.startsWith("+") && !l.startsWith("+++") ? "pack-add"
    : l.startsWith("-") && !l.startsWith("---") ? "pack-del" : l.startsWith("@@") ? "pack-hunk" : "";
  return html`<pre class="pack-diff" tabindex="0" aria-label="The change">${text.split("\n").map((l) => html`<span
    class=${line(l)}>${l}</span>\n`)}</pre>`;
}

function question(run, q, to) {
  let field = nothing;
  if (q.kind === "dispute") {
    const label = "Your note (guides the updater; needed to ask the challenger again)";
    const note = own.notes.get(q.id) ?? "", missing = own.missing === q.id;
    const keep = (e) => {
      own.notes.set(q.id, e.target.value ?? "");
      if (missing && (e.target.value ?? "").trim()) {
        own.missing = "";
        own.show();
      }
    };
    field = html`<p-textarea data-note=${q.id} label=${label} rows="2" max-length="2000" .value=${live(note)}
      state=${missing ? "error" : "none"} message=${missing ? "Asking the challenger to reconsider needs your note."
        : ""} @input=${keep} @change=${keep} ?disabled=${!to}></p-textarea>`;
  }
  const answers = q.options.filter((o) => o.id !== "discard");  // the stop's one Discard stands apart
  const f = q.kind === "dispute" ? (run.loop?.findings ?? []).find((x) => x.id === q.finding) : null;
  const title = f ? `Finding ${f.id}, raised in round ${f.raised}` : q.kind === "unsure"
    ? `A change to ${q.path} the challenger could not judge` : KINDS[q.kind] ?? sentence(q.kind);
  const head = `pack-q-${q.id.replaceAll(/[^\w-]/g, "-")}`;
  return html`<article class="pack-question" aria-labelledby=${head}>
    <p-heading size="sm"><h5 id=${head}>${title}</h5></p-heading>
    ${asked(run, q)}
    ${q.diff ? diff(q.diff) : nothing}
    ${field}
    ${to && answers.length ? html`<div class="row" role="group" aria-label="Your answer">${answers.map((o) =>
      button(o.label, () => answer(run, q, o), { variant: emphasis(q, o), busy: own.busy === `${q.id}:${o.id}`,
        disabled: Boolean(own.busy) }))}</div>` : nothing}
  </article>`;
}

// An invocation's detail in words; a replay with no decided rounds has no evidence, not a 0% agreement.
function detailOf(i) {
  if (i.operation === "replay" && /^0 decided rounds\b/.test(i.detail ?? "")) {
    return "No calibration evidence: there are no decided rounds to replay yet.";
  }
  return i.detail ?? "";
}

function step(i) {
  const said = detailOf(i), many = said.includes("\n"), times = [i.started_at && `started ${when(i.started_at)}`,
    i.ended_at && `ended ${when(i.ended_at)}`].filter(Boolean).join(", ");
  const tag = i.stale ? html`<p-tag class="pack-stale" variant="secondary" compact="true">out of date</p-tag>`
    : html`<p-tag variant=${TAGS[i.result] ?? "secondary"} compact="true">${said.startsWith("No calibration evidence")
      ? "no calibration evidence" : i.outcome}</p-tag>`;
  const more = [i.stale && `It judged an earlier candidate, which a later change replaced; it said: ${i.outcome}.`,
    times && sentence(`${times}.`)].filter(Boolean);
  return html`<li class=${i.stale ? "pack-step stale" : "pack-step"}>
    <span class="pack-step-head"><span>${i.label}${i.attempt > 1 ? ` (attempt ${i.attempt})` : ""}</span> ${tag}</span>
    ${said || i.stale ? html`<details class="pack-step-more"><summary>Details</summary>
      ${more.map((m) => html`<p-text size="xs" color="contrast-medium">${m}</p-text>`)}
      ${!said ? nothing : many ? html`<pre class="pack-detail">${said}</pre>`
        : html`<p-text size="xs">${said}</p-text>`}</details>` : nothing}
  </li>`;
}

function progress(u) {
  const p = u.progress;
  if (!p || p.legacy) {
    return html`<ol id="pack-stages" aria-label="Update stages">${(u.stages ?? []).map((s) => html`<li
      class="pack-step"><span class="pack-step-head"><span>${s.label}</span> <p-tag variant=${TAGS[s.result]
        ?? "secondary"} compact="true">${RESULTS[s.result] ?? s.result}</p-tag></span>${s.detail
        ? html`<p-text size="xs" color="contrast-medium">${detailOf({ operation: s.name, detail: s.detail })}</p-text>`
        : nothing}</li>`)}</ol>`;
  }
  return html`<div id="pack-progress">
    ${p.phases.map((ph) => html`<section class="pack-phase" aria-labelledby=${`pack-phase-${ph.key}`}>
      <h5 id=${`pack-phase-${ph.key}`}>${ph.label}</h5>
      <ol aria-labelledby=${`pack-phase-${ph.key}`}>${ph.invocations.map(step)}</ol>
    </section>`)}
  </div>`;
}

// Why the run's actions are not offered here, when they are not.
function unreachable() {
  return project || !machineState() ? "; open that project to act on it" : "; choose a project above to act on it";
}

function runPart(run) {
  if (!run) return html`<p-text id="pack-state" size="sm">No project has run a design pack update yet.</p-text>`;
  const to = reach(run), questions = run.state === "waiting" ? run.questions ?? [] : [];
  const p = run.published, found = run.loop?.findings ?? [], d = discarding(run, questions);
  const why = run.state !== "running" ? run.reason : "";
  return html`<div id="pack-run" class="pack-run">
    ${summary(run, questions, to)}
    ${why ? html`<p-text id="pack-reason" size="sm">${why}</p-text>` : nothing}
    ${p?.commit ? html`<p-text id="pack-pushed" size="sm">Commit ${p.commit.slice(0, 12)} on ${p.branch}${p.url
      ? html`, <a href=${p.url} target="_blank" rel="noopener">pull request #${p.number}</a>` : nothing}${p.merged
      ? `, merged into main as ${p.merged.slice(0, 12)}` : p.url ? ", not merged yet" : ""}.</p-text>` : nothing}
    <div id="pack-ask" class="pack-ask" ?hidden=${!questions.length && !d}>
      <p-heading size="sm"><h4 id="pack-ask-title">Waiting for you</h4></p-heading>
      <div id="pack-questions">${questions.map((q) => question(run, q, to))}</div>
      ${to && d ? html`<div id="pack-discard-area" class="pack-discard">
        <p-text size="sm" color="contrast-medium">Or end this update without activating anything.</p-text>
        ${button(d.label, () => discard(run, d), { id: "pack-discard", icon: "close",
          busy: own.busy === "discard" || own.busy === `${d.q?.id}:discard`, disabled: Boolean(own.busy) })}
      </div>` : nothing}
    </div>
    <div class="pack-steps">
      <p-heading size="sm"><h4 id="pack-progress-title">Progress</h4></p-heading>
      ${progress(run)}
    </div>
    <details id="pack-findings-box" ?hidden=${!found.length}>
      <summary>Findings of the challenge rounds</summary>
      <ul id="pack-findings">${findings(found)}</ul>
    </details>
    <details>
      <summary>Log of the run</summary>
      <pre id="pack-log">${run.log?.length ? run.log.join("\n") : "Nothing logged."}</pre>
    </details>
  </div>`;
}

function others(r) {
  const listed = r.runs.filter((x) => x.state !== "idle" || x.error);
  if (listed.length < 2 && !r.registry) return nothing;
  return html`<details id="pack-runs"><summary>Each project's last design pack run</summary>
    ${r.registry ? html`<p-text size="sm">${sentence(r.registry)}.</p-text>` : nothing}
    <ul>${listed.map((x) => html`<li>${x.name}: ${x.error ? sentence(x.error) : `${x.state}${x.started_at
      ? `, started ${when(x.started_at)}` : ""}`}</li>`)}</ul></details>`;
}

function engine() {
  const bar = machineState();
  if (!bar) {
    return html`<p-text id="owlbear-version" size="sm">This page is served by a clone's own host: the engine
      updates through the machine host.</p-text>`;
  }
  const u = bar.update ?? {}, busy = Boolean(u.phase) && !["idle", "current", "failed", "refused"].includes(u.phase);
  return html`<p-text id="owlbear-version" size="sm">OwlBear runs ${bar.updated || "an unnumbered version"}.</p-text>
    <p-text id="owlbear-engine" size="sm">Engine update: ${u.phase && u.phase !== "idle" ? `${u.phase}${u.version
      ? ` (${u.version})` : ""}${u.detail ? `: ${u.detail}` : ""}${u.at ? `, ${when(u.at)}` : ""}`
      : "nothing checked since OwlBear started"}.</p-text>
    <div>${button("Update now", runUpdates, { id: "owlbear-update", busy, disabled: busy })}</div>`;
}

function packed() {
  const pin = own.pinned, bar = machineState(), install = bar?.pack?.install, release = bar?.pack?.release;
  const plain = (t) => String(t).replaceAll(String.fromCharCode(96), "");  // the status is CLI text with code marks
  return html`
    ${own.unread.pinned ? html`<p-inline-notification id="pack-read-error" state="error" dismiss-button="false">
      Could not read the design pack: ${own.unread.pinned}.</p-inline-notification>` : nothing}
    <p-text id="pack-active" size="sm">${pin ? `Pinned: ${pin.pack} from upstream ${pin.upstream}, identity ${
      pin.identity}. ${plain(pin.status)}.` : ""}</p-text>
    <p-text id="pack-notice" size="xs" color="contrast-medium">${pin ? `Upstream: ${pin.notice.said}${pin.notice
      .checked_at ? `, checked ${when(pin.notice.checked_at)}` : ", not checked yet"}.` : ""}</p-text>
    ${install ? html`<p-text id="pack-install-state" size="sm">This version's pack ${install.state === "installing"
      ? "is being installed" : install.state === "failed" ? "failed to install" : "is not installed"} on this
      machine${install.detail ? `: ${install.detail}` : ""}.</p-text>` : nothing}
    ${release?.state === "newer" ? html`<p-text id="pack-release" size="sm">OwlBear ${release.version} carries the
      newer pack ${release.pack}; this version pins ${release.running_pack}.</p-text>` : nothing}`;
}

export function owlbearSection() {
  const r = own.runs, run = r?.run, open = run && ["running", "waiting"].includes(run.state);
  const canStart = Boolean(project || !machineState()), busy = Boolean(open || r?.holder);
  return html`<section id="owlbear" class="panel" aria-labelledby="owlbear-title">
    <div>
      <p-heading size="lg"><h2 id="owlbear-title">OwlBear</h2></p-heading>
      <p-text size="sm" color="contrast-medium">OwlBear's own maintenance, the same in every project.</p-text>
    </div>
    <div class="owlbear-part">
      <p-heading size="md"><h3 id="owlbear-version-title">Version</h3></p-heading>
      ${engine()}
    </div>
    <div class="owlbear-part">
      <p-heading size="md"><h3 id="pack-title">Design pack</h3></p-heading>
      ${packed()}
      <p-text size="sm">An update takes the newest upstream pack and validates it with model requests. Only if every
        stage passes, or if you accept it after its challenge rounds end without a pass, it commits it on its own
        branch, opens a pull request to main and merges it once CI passes. One runs at a time on this machine.</p-text>
      <div class="row">
        ${button("Update design pack", start, { id: "pack-update", icon: "refresh", variant: "primary",
          busy: own.busy === "start", disabled: busy || !canStart || Boolean(own.busy) })}
        ${canStart ? nothing : html`<p-text size="sm">Choose a project above to start one: it runs on that project's
          labels, calibration and spend.</p-text>`}
      </div>
      ${own.error ? html`<p-inline-notification id="pack-error" state="error" dismiss-button="false">${
        sentence(own.error)}</p-inline-notification>` : nothing}
      ${own.unread.runs ? html`<p-inline-notification id="pack-runs-error" state="error" dismiss-button="false">
        Could not read the design pack runs: ${own.unread.runs}.</p-inline-notification>` : nothing}
    </div>
    ${r ? html`<div class="owlbear-part">${runPart(run)}${others(r)}</div>` : own.unread.runs ? nothing
      : html`<p-text size="sm">Reading the design pack runs…</p-text>`}
  </section>`;
}
