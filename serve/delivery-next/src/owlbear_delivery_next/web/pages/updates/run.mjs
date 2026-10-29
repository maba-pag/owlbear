// The Impeccable update's run as Updates ▸ Impeccable shows it: its state, what the owner has to do, its questions
// with their answers, its progress by invocation, its findings and log, and each project's last run (pack.mjs acts).
import { html, nothing } from "/assets/lit-html/3.3.3/lit-html.js";
import { live } from "/assets/lit-html/3.3.3/directives/live.js";
import { machineState } from "/assets/ui.mjs";
import { sentence, when } from "./frame.mjs";
import { FOUND, answer, button, discard, discarding, emphasis, own, reach } from "./pack.mjs";

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

// The run's state in a word, for its tag.
const STATES = { running: ["running", "info"], waiting: ["waiting for you", "warning"], passed: ["passed", "success"],
  failed: ["failed", "error"], discarded: ["discarded", "secondary"], "up-to-date": ["up to date", "success"],
  idle: ["never run", "secondary"], unreadable: ["unreadable", "error"] };
// Each question's heading, by kind; a kind not listed here is named by its own word.
const KINDS = { end: "The challenge rounds ended without a pass", evidence: "Changed golden evidence",
  code: "A change to the detector's glue", scope: "Changes the updater may not make",
  unsure: "A change the challenger is unsure about",
  publish: "Publication stopped", "repair-config": "The CI repair was held before its push",
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

// Alternatives with no priority among them are chosen, nothing preselected, and sent with one button: the lead
// question's is the panel's one primary (D-01M63C7BJZZ7RQV9XS4XVR0DNE) without favouring an answer.
function choose(run, q, answers, lead) {
  const picked = answers.find((o) => o.id === own.choices.get(q.id)), unset = own.unchosen === q.id && !picked;
  const pick = (e) => {
    own.choices.set(q.id, e.target.value);
    own.unchosen = "";
    own.show();
  };
  const send = () => {
    if (picked) return answer(run, q, picked);
    own.unchosen = q.id;
    own.show();
  };
  return html`<p-radio-group name=${`pack-answer-${q.id}`} label="Your answer" .value=${live(picked?.id ?? "")}
      state=${unset ? "error" : "none"} message=${unset ? "Choose an answer first." : ""} ?disabled=${Boolean(own.busy)}
      @change=${pick}>${answers.map((o) => html`<p-radio-group-option value=${o.id} label=${o.label}>
      </p-radio-group-option>`)}</p-radio-group>
    <div class="row">${button("Send answer", send, { variant: lead ? "primary" : "secondary",
      busy: own.busy.startsWith(`${q.id}:`), disabled: Boolean(own.busy) })}</div>`;
}

function question(run, q, to, lead) {
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
  const priority = answers.some((o) => emphasis(q, o) === "primary");
  const f = q.kind === "dispute" ? (run.loop?.findings ?? []).find((x) => x.id === q.finding) : null;
  const title = f ? `Finding ${f.id}, raised in round ${f.raised}` : q.kind === "unsure"
    ? `A change to ${q.path} the challenger could not judge` : KINDS[q.kind] ?? sentence(q.kind);
  const head = `pack-q-${q.id.replaceAll(/[^\w-]/g, "-")}`;
  return html`<article class="pack-question" aria-labelledby=${head}>
    <p-heading size="sm"><h5 id=${head}>${title}</h5></p-heading>
    ${asked(run, q)}
    ${q.diff ? diff(q.diff) : nothing}
    ${field}
    ${!to || !answers.length ? nothing : !priority ? choose(run, q, answers, lead) : html`<div class="row"
      role="group" aria-label="Your answer">${answers.map((o) => button(o.label, () => answer(run, q, o),
        { variant: lead ? emphasis(q, o) : "secondary", busy: own.busy === `${q.id}:${o.id}`,
          disabled: Boolean(own.busy) }))}</div>`}
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

// Why the run's actions are not offered here, when they are not: its project is not loaded on the machine host, or
// this is another project's own host.
function unreachable() {
  return machineState() ? "; its answers show here once that project is loaded" : "; open that project to act on it";
}

export function runPart(run) {
  if (!run) return html`<p-text id="pack-state" size="sm">No project has run an Impeccable update yet.</p-text>`;
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
      <div id="pack-questions">${questions.map((q, i) => question(run, q, to, i === 0))}</div>
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

export function others(r) {
  const listed = r.runs.filter((x) => x.state !== "idle" || x.error);
  if (listed.length < 2 && !r.registry) return nothing;
  return html`<details id="pack-runs"><summary>Each project's last Impeccable run</summary>
    ${r.registry ? html`<p-text size="sm">${sentence(r.registry)}.</p-text>` : nothing}
    <ul>${listed.map((x) => html`<li>${x.name}: ${x.error ? sentence(x.error) : `${x.state}${x.started_at
      ? `, started ${when(x.started_at)}` : ""}`}</li>`)}</ul></details>`;
}
